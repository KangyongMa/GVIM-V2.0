#!/usr/bin/env python3
"""DeepSeek Flash API-only ablation runner for the MaScQA 84 subset.

This script is intentionally separate from the DeerFlow/GVIM front-end runner.
It does not open the UI, does not call DeerFlow backend routes, and does not
use any Agent tools. It directly submits each prompt to the DeepSeek-compatible
chat completions API, records raw outputs and token usage, then scores saved
answers against the MaScQA public answer sheet using the published accuracy
definition.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
import time
import traceback
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPT_DIR.parents[1]

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_ENV_FILE = WORKSPACE_ROOT / "deer-flow-main" / ".env"
DEFAULT_QUESTIONS = SCRIPT_DIR / "mascqa-84-questions.native.jsonl"
DEFAULT_ANSWER_KEY = SCRIPT_DIR / "answer_key.jsonl"
DEFAULT_OUT_DIR = SCRIPT_DIR / "mascqa-api-ablation-runs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a direct DeepSeek Flash API-only ablation on the MaScQA 84 "
            "subset and score with MaScQA answer-key accuracy."
        )
    )
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument("--base-url", default=os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--model", default=os.getenv("DEEPSEEK_ABLATION_MODEL", DEFAULT_MODEL))
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--answer-key", type=Path, default=DEFAULT_ANSWER_KEY)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--limit", type=int, default=84)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument(
        "--thinking",
        choices=["enabled", "disabled", "omit"],
        default="disabled",
        help="Use 'omit' if a compatibility endpoint rejects the thinking field.",
    )
    parser.add_argument("--timeout-ms", type=int, default=180_000)
    parser.add_argument("--pause-ms", type=int, default=500)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    positive_ints = {
        "--start": args.start,
        "--limit": args.limit,
        "--max-tokens": args.max_tokens,
        "--timeout-ms": args.timeout_ms,
    }
    for name, value in positive_ints.items():
        if value < 1:
            parser.error(f"{name} must be a positive integer")

    nonnegative_ints = {
        "--pause-ms": args.pause_ms,
        "--max-retries": args.max_retries,
    }
    for name, value in nonnegative_ints.items():
        if value < 0:
            parser.error(f"{name} must be a non-negative integer")

    if args.temperature < 0:
        parser.error("--temperature must be non-negative")

    args.base_url = args.base_url.rstrip("/")
    return args


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def run_stamp() -> str:
    return utc_now().strftime("%Y-%m-%dT%H-%M-%S-%fZ")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def load_env_file(path: Path) -> tuple[bool, dict[str, str]]:
    if not path.exists():
        return False, {}

    values: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export ") :].strip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if (
                len(value) >= 2
                and ((value[0] == value[-1] == '"') or (value[0] == value[-1] == "'"))
            ):
                value = value[1:-1]
            values[key] = value
    return True, values


def get_api_key(args: argparse.Namespace, env_values: dict[str, str]) -> str:
    return os.getenv(args.api_key_env) or env_values.get(args.api_key_env, "")


def normalize_messages(question: dict[str, Any]) -> list[dict[str, str]]:
    messages = question.get("messages")
    if isinstance(messages, list) and messages:
        normalized: list[dict[str, str]] = []
        for message in messages:
            normalized.append(
                {
                    "role": str(message.get("role", "user")),
                    "content": str(message.get("content", "")),
                }
            )
        return normalized
    return [{"role": "user", "content": str(question["prompt"])}]


def make_request_body(question: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": args.model,
        "messages": normalize_messages(question),
        "stream": False,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
    }
    if args.thinking != "omit":
        body["thinking"] = {"type": args.thinking}
    return body


def is_retryable_status(status: int) -> bool:
    return status in {408, 409, 429} or status >= 500


def parse_json_maybe(text: str) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def post_completion(
    *,
    args: argparse.Namespace,
    api_key: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    endpoint = f"{args.base_url}/chat/completions"
    timeout_seconds = args.timeout_ms / 1000
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "Connection": "close",
    }

    for attempt in range(args.max_retries + 1):
        attempt_started = time.perf_counter()
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=body,
                timeout=(15, timeout_seconds),
            )
            elapsed_ms = round((time.perf_counter() - attempt_started) * 1000)

            if response.ok:
                return {
                    "ok": True,
                    "attempts": attempt + 1,
                    "http_status": response.status_code,
                    "elapsed_ms_last_attempt": elapsed_ms,
                    "raw_response": parse_json_maybe(response.text),
                }

            if attempt < args.max_retries and is_retryable_status(response.status_code):
                time.sleep(min(30, 2**attempt))
                continue
            return {
                "ok": False,
                "attempts": attempt + 1,
                "http_status": response.status_code,
                "elapsed_ms_last_attempt": elapsed_ms,
                "raw_response": parse_json_maybe(response.text),
                "error": {
                    "message": f"HTTP {response.status_code}",
                    "body_preview": response.text[:2000],
                },
            }
        except Exception as error:  # noqa: BLE001 - record execution-layer failure
            elapsed_ms = round((time.perf_counter() - attempt_started) * 1000)
            if attempt < args.max_retries:
                time.sleep(min(30, 2**attempt))
                continue
            return {
                "ok": False,
                "attempts": attempt + 1,
                "http_status": None,
                "elapsed_ms_last_attempt": elapsed_ms,
                "raw_response": None,
                "error": {
                    "message": str(error),
                    "type": type(error).__name__,
                    "traceback": traceback.format_exc(),
                },
            }

    raise RuntimeError("unreachable retry state")


def extract_choice(raw_response: Any) -> dict[str, Any]:
    if not isinstance(raw_response, dict):
        return {
            "message": None,
            "final_text": "",
            "reasoning_content": "",
            "finish_reason": None,
        }
    choices = raw_response.get("choices")
    choice = choices[0] if isinstance(choices, list) and choices else {}
    message = choice.get("message") if isinstance(choice, dict) else {}
    if not isinstance(message, dict):
        message = {}
    content = message.get("content")
    reasoning_content = message.get("reasoning_content")
    return {
        "message": message or None,
        "final_text": content.strip() if isinstance(content, str) else "",
        "reasoning_content": reasoning_content if isinstance(reasoning_content, str) else "",
        "finish_reason": choice.get("finish_reason") if isinstance(choice, dict) else None,
    }


def submit_one(
    question: dict[str, Any],
    args: argparse.Namespace,
    api_key: str,
    run_dir: Path,
) -> dict[str, Any]:
    started_at = utc_now()
    request_body = make_request_body(question, args)
    response = post_completion(args=args, api_key=api_key, body=request_body)
    finished_at = utc_now()

    choice = extract_choice(response.get("raw_response")) if response["ok"] else {}
    final_text = str(choice.get("final_text", ""))

    if not response["ok"]:
        status = "error"
    elif not final_text:
        status = "empty_response"
    else:
        status = "ok"

    prompt_chars = sum(len(str(message.get("content", ""))) for message in request_body["messages"])
    raw_response = response.get("raw_response")
    usage = raw_response.get("usage") if isinstance(raw_response, dict) else None

    result = {
        "idx": question["idx"],
        "uuid": question["uuid"],
        "global_idx": question.get("global_idx"),
        "source_id": question.get("source_id"),
        "topic": question.get("topic"),
        "mini_split": question.get("mini_split"),
        "question_type": question.get("question_type"),
        "status": status,
        "experiment": "deepseek_flash_api_only_mascqa_ablation",
        "provider": "deepseek",
        "model": args.model,
        "base_url": args.base_url,
        "started_at": iso(started_at),
        "finished_at": iso(finished_at),
        "latency_ms": round((finished_at - started_at).total_seconds() * 1000),
        "http_status": response.get("http_status"),
        "attempts": response.get("attempts"),
        "request": {
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "thinking": args.thinking,
            "message_count": len(request_body["messages"]),
            "prompt_chars": prompt_chars,
        },
        "final_text": final_text,
        "reasoning_content": choice.get("reasoning_content", ""),
        "finish_reason": choice.get("finish_reason"),
        "message": choice.get("message"),
        "usage": usage,
        "error": response.get("error"),
        "raw_response": raw_response,
    }

    result_path = run_dir / f"{int(question['idx']):03d}-{question['uuid']}.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def add_usage(total: dict[str, int | float], usage: Any) -> None:
    if not isinstance(usage, dict):
        return
    for key, value in usage.items():
        if isinstance(value, (int, float)):
            total[key] = total.get(key, 0) + value


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    def group_by(key: str) -> dict[str, dict[str, int]]:
        groups: dict[str, dict[str, int]] = {}
        for row in results:
            name = str(row.get(key, "unknown"))
            groups.setdefault(name, {"count": 0, "ok": 0, "errors": 0})
            groups[name]["count"] += 1
            if row["status"] == "ok":
                groups[name]["ok"] += 1
            else:
                groups[name]["errors"] += 1
        return groups

    usage_total: dict[str, int | float] = {}
    for row in results:
        add_usage(usage_total, row.get("usage"))

    return {
        "count": len(results),
        "ok": sum(1 for row in results if row["status"] == "ok"),
        "errors": sum(1 for row in results if row["status"] != "ok"),
        "empty_responses": sum(1 for row in results if row["status"] == "empty_response"),
        "usage_total": usage_total,
        "by_topic": group_by("topic"),
        "by_split": group_by("mini_split"),
        "by_type": group_by("question_type"),
    }


def extract_answer_text(text: str) -> str:
    if not text:
        return ""
    tagged = re.findall(r"\[ANSWER\](.*?)\[/ANSWER\]", text, flags=re.IGNORECASE | re.DOTALL)
    if tagged:
        return tagged[-1].strip()
    answer_lines = re.findall(r"(?:^|\b)Answer\s*:\s*([^\n\r]+)", text, flags=re.IGNORECASE)
    if answer_lines:
        return answer_lines[-1].strip()
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    return lines[-1] if lines else ""


def normalize_letter(text: str) -> str:
    if not text:
        return ""
    value = text.strip().upper()
    if value in {"A", "B", "C", "D"}:
        return value
    paren = re.search(r"\(([ABCD])\)", value)
    if paren:
        return paren.group(1)
    bare = re.search(r"\b([ABCD])\b", value)
    if bare:
        return bare.group(1)
    return value


def extract_numbers(text: str) -> list[float]:
    if not text:
        return []
    value = (
        str(text)
        .replace("−", "-")
        .replace("–", "-")
        .replace("—", "-")
        .replace("×", "x")
        .replace(",", "")
    )
    numbers: list[float] = []
    spans: list[tuple[int, int]] = []
    scientific = re.compile(
        r"([-+]?\d*\.?\d+)\s*(?:x|\*)\s*10\s*\^?\(?\s*([-+]?\d+)\s*\)?",
        re.IGNORECASE,
    )
    for match in scientific.finditer(value):
        try:
            numbers.append(float(match.group(1)) * 10 ** int(match.group(2)))
            spans.append(match.span())
        except ValueError:
            pass

    chars = list(value)
    for start, end in spans:
        for idx in range(start, end):
            chars[idx] = " "
    masked = "".join(chars)
    for raw_number in re.findall(r"(?<![A-Za-z])[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", masked):
        try:
            numbers.append(float(raw_number))
        except ValueError:
            pass
    return numbers


def parse_gold_range(gold_answer: str) -> tuple[float, float] | None:
    parts = re.split(r"\s+TO\s+", str(gold_answer).strip(), flags=re.IGNORECASE)
    if len(parts) == 2:
        low_values = extract_numbers(parts[0])
        high_values = extract_numbers(parts[1])
        if low_values and high_values:
            return min(low_values[-1], high_values[-1]), max(low_values[-1], high_values[-1])
    values = extract_numbers(gold_answer)
    if values:
        return values[-1], values[-1]
    return None


def score_prediction(prediction: str, gold_answer: str, question_type: str) -> bool:
    if not prediction:
        return False
    if question_type in {"MCQS", "MCQS-NUM", "MATCH"}:
        return normalize_letter(prediction) == normalize_letter(gold_answer)

    gold_range = parse_gold_range(gold_answer)
    predicted_values = extract_numbers(prediction)
    if not gold_range or not predicted_values:
        return False

    value = predicted_values[-1]
    low, high = gold_range
    if low == high:
        return math.isclose(value, low, rel_tol=1e-6, abs_tol=1e-6)
    return low - 1e-9 <= value <= high + 1e-9


def load_mascqa_answer_key(path: Path) -> dict[int, dict[str, Any]]:
    keys: dict[int, dict[str, Any]] = {}
    for row in read_jsonl(path):
        if row.get("suite") == "mascqa":
            keys[int(row["suite_idx"])] = row
    return keys


def score_saved_results(run_dir: Path, answer_key_path: Path) -> dict[str, Any]:
    keys = load_mascqa_answer_key(answer_key_path)
    rows: list[dict[str, Any]] = []
    by_idx: dict[int, dict[str, Any]] = {}

    for path in sorted(run_dir.glob("*.json")):
        if path.name in {"summary.json", "score_summary.json"}:
            continue
        result = json.loads(path.read_text(encoding="utf-8"))
        by_idx[int(result["idx"])] = result

    for idx in sorted(keys):
        result = by_idx.get(idx)
        key = keys[idx]
        prediction = extract_answer_text(str(result.get("final_text", ""))) if result else ""
        status = result.get("status", "missing") if result else "missing"
        correct = status == "ok" and score_prediction(
            prediction,
            str(key["gold_answer"]),
            str(key["question_type"]),
        )
        rows.append(
            {
                "idx": idx,
                "global_idx": key.get("global_idx"),
                "source_id": key.get("source_id"),
                "topic": result.get("topic") if result else "",
                "question_type": key.get("question_type"),
                "status": status,
                "prediction": prediction,
                "gold_answer": key.get("gold_answer"),
                "correct": bool(correct),
                "latency_ms": result.get("latency_ms") if result else "",
                "total_tokens": (
                    (result.get("usage") or {}).get("total_tokens")
                    if isinstance(result.get("usage"), dict)
                    else ""
                )
                if result
                else "",
                "record_file": str(run_dir / f"{idx:03d}-{key.get('source_id')}.json"),
            }
        )

    correct_total = sum(1 for row in rows if row["correct"])
    summary = {
        "dataset": "MaScQA selected 84-question subset",
        "model_system": "DeepSeek Flash API-only single-model ablation",
        "scoring_protocol": (
            "MaScQA published answer-key accuracy reproduced from public "
            "answer sheet; no DeerFlow/GVIM tools or front-end were used."
        ),
        "run_dir": str(run_dir),
        "answer_key": str(answer_key_path),
        "generated_at_utc": iso(utc_now()),
        "total": len(rows),
        "successful_records": sum(1 for row in rows if row["status"] == "ok"),
        "missing_records": sum(1 for row in rows if row["status"] == "missing"),
        "empty_prediction_indices": [row["idx"] for row in rows if not row["prediction"]],
        "not_ok_indices": [row["idx"] for row in rows if row["status"] != "ok"],
        "correct": correct_total,
        "accuracy_percent": round(correct_total / len(rows) * 100, 2) if rows else None,
    }

    for key_name in ("question_type", "topic"):
        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            group_name = str(row.get(key_name) or "unknown")
            grouped.setdefault(group_name, {"correct": 0, "total": 0, "accuracy_percent": 0.0})
            grouped[group_name]["total"] += 1
            if row["correct"]:
                grouped[group_name]["correct"] += 1
        for group in grouped.values():
            group["accuracy_percent"] = round(group["correct"] / group["total"] * 100, 2)
        summary[f"by_{key_name}"] = dict(sorted(grouped.items()))

    summary["wrong_indices"] = [row["idx"] for row in rows if not row["correct"]]

    (run_dir / "score_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (run_dir / "scored_rows.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    with (run_dir / "wrong_items.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            if not row["correct"]:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    return summary


def main() -> int:
    args = parse_args()
    questions = read_jsonl(args.questions)
    selected = questions[args.start - 1 : args.start - 1 + args.limit]
    env_exists, env_values = load_env_file(args.env_file)
    api_key = get_api_key(args, env_values)

    if not selected:
        raise RuntimeError("No questions selected. Check --start and --limit.")

    if args.dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "env_file": str(args.env_file),
                    "env_file_exists": env_exists,
                    "api_key_env": args.api_key_env,
                    "api_key_present": bool(api_key),
                    "base_url": args.base_url,
                    "model": args.model,
                    "questions": str(args.questions),
                    "answer_key": str(args.answer_key),
                    "start": args.start,
                    "limit": args.limit,
                    "selected_count": len(selected),
                    "first_idx": selected[0]["idx"],
                    "last_idx": selected[-1]["idx"],
                    "temperature": args.temperature,
                    "max_tokens": args.max_tokens,
                    "thinking": args.thinking,
                    "frontend_used": False,
                    "agent_tools_used": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if not api_key:
        raise RuntimeError(f"Missing {args.api_key_env}. Set it in the shell or {args.env_file}.")

    run_dir = args.out_dir / run_stamp()
    run_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    for offset, question in enumerate(selected, start=1):
        print(
            f"[{offset}/{len(selected)}] "
            f"idx={question['idx']} topic={question.get('topic')} type={question.get('question_type')}",
            flush=True,
        )
        result = submit_one(question, args, api_key, run_dir)
        results.append(result)
        token_count = "-"
        if isinstance(result.get("usage"), dict):
            token_count = str(result["usage"].get("total_tokens", "-"))
        print(
            f"  {result['status']} http={result.get('http_status') or '-'} "
            f"attempts={result.get('attempts')} tokens={token_count}",
            flush=True,
        )
        if args.pause_ms > 0 and offset < len(selected):
            time.sleep(args.pause_ms / 1000)

    run_summary = {
        "run_dir": str(run_dir),
        "experiment": "deepseek_flash_api_only_mascqa_ablation",
        "provider": "deepseek",
        "model": args.model,
        "base_url": args.base_url,
        "env_file": str(args.env_file),
        "api_key_env": args.api_key_env,
        "api_key_present": True,
        "questions": str(args.questions),
        "answer_key": str(args.answer_key),
        "start": args.start,
        "limit": args.limit,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "thinking": args.thinking,
        "timeout_ms": args.timeout_ms,
        "pause_ms": args.pause_ms,
        "max_retries": args.max_retries,
        "finished_at": iso(utc_now()),
        "frontend_used": False,
        "agent_tools_used": False,
        **summarize_results(results),
    }

    (run_dir / "results.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in results),
        encoding="utf-8",
    )
    (run_dir / "summary.json").write_text(
        json.dumps(run_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    score_summary = score_saved_results(run_dir, args.answer_key)
    combined = {"run_summary": run_summary, "score_summary": score_summary}
    (run_dir / "combined_summary.json").write_text(
        json.dumps(combined, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(combined, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:  # noqa: BLE001 - CLI should show concise failure
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
