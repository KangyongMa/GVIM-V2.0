#!/usr/bin/env python3
"""DeepSeek Flash API-only ablation and ChemLLMBench-40 scoring.

This script is intentionally separate from the DeerFlow/GVIM front-end runner.
It can:

1. Score a saved front-end Agent run against the ChemLLMBench task answer key.
2. Directly submit the same 40 prompts to the DeepSeek-compatible chat API,
   without opening the UI, calling DeerFlow backend routes, or using Agent tools.

Scoring follows the selected ChemLLMBench task definitions in this workspace:
binary property prediction is Yes/No accuracy; Suzuki component selection is
exact match against the optimal candidate SMILES recorded in the answer key.
ChemLLMBench does not provide a standalone parser package analogous to
ChemBench, so the deterministic parser below is fixed before evaluation and
records its rule in every summary file.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
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
DEFAULT_QUESTIONS = SCRIPT_DIR / "chemllmbench-40-questions.native.jsonl"
DEFAULT_ANSWER_KEY = SCRIPT_DIR / "answer_key.jsonl"
DEFAULT_API_OUT_DIR = SCRIPT_DIR / "chemllmbench-api-ablation-runs"
DEFAULT_FINAL_OUT_DIR = (
    SCRIPT_DIR
    / "chemllmbench-final-results"
    / "2026-06-06-chemllmbench-40-deepseek-flash-gvim"
)

SCORING_RULE = (
    "ChemLLMBench task-specific answer-key metric; property prediction uses "
    "Yes/No accuracy; Suzuki component selection uses exact match to the "
    "optimal candidate SMILES. Deterministic parser fixed before evaluation."
)


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


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run/score ChemLLMBench-40 DeepSeek Flash ablation."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
        subparser.add_argument("--answer-key", type=Path, default=DEFAULT_ANSWER_KEY)

    score_native = subparsers.add_parser(
        "score-native",
        help="Score an existing front-end native_submit run directory.",
    )
    add_common(score_native)
    score_native.add_argument("--native-run-dir", type=Path, required=True)
    score_native.add_argument("--score-out-dir", type=Path, default=DEFAULT_FINAL_OUT_DIR)

    run_api = subparsers.add_parser(
        "run-api",
        help="Run direct DeepSeek Flash API-only ablation and score it.",
    )
    add_common(run_api)
    run_api.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    run_api.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    run_api.add_argument("--base-url", default=os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL))
    run_api.add_argument("--model", default=os.getenv("DEEPSEEK_ABLATION_MODEL", DEFAULT_MODEL))
    run_api.add_argument("--out-dir", type=Path, default=DEFAULT_API_OUT_DIR)
    run_api.add_argument("--start", type=int, default=1)
    run_api.add_argument("--limit", type=int, default=40)
    run_api.add_argument("--temperature", type=float, default=0.0)
    run_api.add_argument("--max-tokens", type=int, default=1024)
    run_api.add_argument(
        "--thinking",
        choices=["enabled", "disabled", "omit"],
        default="disabled",
        help="Use 'omit' if a compatibility endpoint rejects the thinking field.",
    )
    run_api.add_argument("--timeout-ms", type=int, default=180_000)
    run_api.add_argument("--pause-ms", type=int, default=500)
    run_api.add_argument("--max-retries", type=int, default=2)
    run_api.add_argument("--dry-run", action="store_true")

    compare = subparsers.add_parser("compare", help="Compare two scored result CSV files.")
    compare.add_argument("--agent-score-csv", type=Path, required=True)
    compare.add_argument("--api-score-csv", type=Path, required=True)
    compare.add_argument("--out", type=Path, required=True)

    args = parser.parse_args()
    if hasattr(args, "base_url"):
        args.base_url = args.base_url.rstrip("/")
    if hasattr(args, "start") and args.start < 1:
        parser.error("--start must be positive")
    if hasattr(args, "limit") and args.limit < 1:
        parser.error("--limit must be positive")
    if hasattr(args, "max_tokens") and args.max_tokens < 1:
        parser.error("--max-tokens must be positive")
    if hasattr(args, "temperature") and args.temperature < 0:
        parser.error("--temperature must be non-negative")
    return args


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
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            values[key] = value
    return True, values


def get_api_key(args: argparse.Namespace, env_values: dict[str, str]) -> str:
    return os.getenv(args.api_key_env) or env_values.get(args.api_key_env, "")


def load_questions(path: Path, start: int | None = None, limit: int | None = None) -> list[dict[str, Any]]:
    rows = read_jsonl(path)
    rows.sort(key=lambda row: int(row["idx"]))
    if start is not None:
        rows = [row for row in rows if int(row["idx"]) >= start]
    if limit is not None:
        rows = rows[:limit]
    return rows


def load_chemllmbench_answer_key(path: Path) -> dict[int, dict[str, Any]]:
    keys: dict[int, dict[str, Any]] = {}
    for row in read_jsonl(path):
        if row.get("suite") != "chemllmbench":
            continue
        suite_idx = int(row["suite_idx"])
        keys[suite_idx] = row
    return keys


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


def normalize_yes_no(text: str) -> str:
    value = extract_answer_text(text).strip().lower()
    value = re.sub(r"^[`'\"\s]+|[`'\"\s.。:：;；]+$", "", value)
    if value in {"yes", "y", "true", "1"}:
        return "yes"
    if value in {"no", "n", "false", "0"}:
        return "no"
    matches = re.findall(r"\b(yes|no)\b", value, flags=re.IGNORECASE)
    return matches[-1].lower() if matches else value


def normalize_smiles_answer(text: str) -> str:
    value = extract_answer_text(text).strip()
    value = re.sub(r"^```(?:smiles)?\s*|\s*```$", "", value, flags=re.IGNORECASE | re.DOTALL)
    value = value.strip().strip("\"'")
    return re.sub(r"\s+", "", value)


def score_prediction(prediction_text: str, key: dict[str, Any]) -> tuple[bool, str, str]:
    answer_format = str(key.get("answer_format", ""))
    gold = str(key.get("gold_answer", ""))
    if answer_format == "yes_no":
        pred_norm = normalize_yes_no(prediction_text)
        gold_norm = normalize_yes_no(gold)
        return pred_norm == gold_norm, pred_norm, gold_norm
    if answer_format == "exact_smiles_candidate":
        pred_norm = normalize_smiles_answer(prediction_text)
        gold_norm = normalize_smiles_answer(gold)
        return pred_norm == gold_norm, pred_norm, gold_norm
    raise ValueError(f"Unsupported ChemLLMBench answer format: {answer_format}")


def collect_native_records(run_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(run_dir.glob("*.json")):
        if path.name in {"summary.json", "score_summary.json", "run_manifest.json"}:
            continue
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if "idx" not in row:
            continue
        row["_record_file"] = str(path)
        row["_source_kind"] = "frontend_agent"
        records.append(row)
    records.sort(key=lambda row: int(row["idx"]))
    return records


def summarize_scored(rows: list[dict[str, Any]], *, source_kind: str, source_run_dir: Path | None) -> dict[str, Any]:
    def grouped(key: str) -> dict[str, dict[str, Any]]:
        groups: dict[str, dict[str, Any]] = {}
        for row in rows:
            name = str(row.get(key) or "unknown")
            group = groups.setdefault(name, {"count": 0, "correct": 0, "accuracy": 0.0})
            group["count"] += 1
            if row["correct"]:
                group["correct"] += 1
        for group in groups.values():
            group["accuracy"] = group["correct"] / group["count"] if group["count"] else 0.0
        return groups

    total = len(rows)
    correct = sum(1 for row in rows if row["correct"])
    return {
        "generated_at": iso(utc_now()),
        "source_kind": source_kind,
        "source_run_dir": str(source_run_dir) if source_run_dir else None,
        "suite": "chemllmbench",
        "subset": "ChemLLMBench 40",
        "scoring_rule": SCORING_RULE,
        "total": total,
        "correct": correct,
        "accuracy": correct / total if total else 0.0,
        "parse_empty": sum(1 for row in rows if not row["prediction_normalized"]),
        "by_type": grouped("question_type"),
        "by_topic": grouped("topic"),
        "wrong_indices": [row["idx"] for row in rows if not row["correct"]],
    }


def write_scored_outputs(
    rows: list[dict[str, Any]],
    out_dir: Path,
    *,
    source_kind: str,
    source_run_dir: Path | None,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = summarize_scored(rows, source_kind=source_kind, source_run_dir=source_run_dir)
    summary["output_dir"] = str(out_dir)

    csv_path = out_dir / "scored_rows.csv"
    fieldnames = [
        "idx",
        "global_idx",
        "source_id",
        "topic",
        "question_type",
        "answer_format",
        "status",
        "prediction_raw",
        "prediction_normalized",
        "gold_answer",
        "gold_normalized",
        "correct",
        "latency_ms",
        "thread_id",
        "run_id",
        "record_file",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})

    wrong_path = out_dir / "wrong_items.jsonl"
    with wrong_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            if not row["correct"]:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    write_json(out_dir / "score_summary.json", summary)
    write_json(out_dir / "run_manifest.json", manifest)
    return summary


def score_records(
    records: list[dict[str, Any]],
    answer_key: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for record in records:
        idx = int(record["idx"])
        key = answer_key[idx]
        final_text = str(record.get("final_text") or record.get("stream_final_text") or "")
        prediction_raw = extract_answer_text(final_text)
        correct, pred_norm, gold_norm = score_prediction(final_text, key)
        scored.append(
            {
                "idx": idx,
                "global_idx": key.get("global_idx") or record.get("global_idx"),
                "source_id": key.get("source_id") or record.get("source_id") or record.get("uuid"),
                "topic": key.get("topic") or record.get("topic"),
                "question_type": key.get("question_type") or record.get("question_type"),
                "answer_format": key.get("answer_format"),
                "status": record.get("status", ""),
                "prediction_raw": prediction_raw,
                "prediction_normalized": pred_norm,
                "gold_answer": key.get("gold_answer"),
                "gold_normalized": gold_norm,
                "correct": bool(correct),
                "latency_ms": record.get("latency_ms", ""),
                "thread_id": record.get("thread_id", ""),
                "run_id": record.get("run_id", ""),
                "record_file": record.get("_record_file", ""),
            }
        )
    return scored


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
        "experiment": "deepseek_flash_api_only_chemllmbench_ablation",
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
        "_record_file": "",
        "_source_kind": "deepseek_flash_api_only",
    }

    result_path = run_dir / f"{int(question['idx']):03d}-{question['uuid']}.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["_record_file"] = str(result_path)
    return result


def add_usage(total: dict[str, int | float], usage: Any) -> None:
    if not isinstance(usage, dict):
        return
    for key, value in usage.items():
        if isinstance(value, (int, float)):
            total[key] = total.get(key, 0) + value


def summarize_api_results(results: list[dict[str, Any]]) -> dict[str, Any]:
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


def run_api_ablation(args: argparse.Namespace) -> None:
    env_exists, env_values = load_env_file(args.env_file)
    api_key = get_api_key(args, env_values)
    questions = load_questions(args.questions, start=args.start, limit=args.limit)
    answer_key = load_chemllmbench_answer_key(args.answer_key)
    missing = [int(row["idx"]) for row in questions if int(row["idx"]) not in answer_key]
    if missing:
        raise SystemExit(f"Missing ChemLLMBench answer-key rows for idx: {missing}")

    if args.dry_run:
        preview = {
            "dry_run": True,
            "question_count": len(questions),
            "start": args.start,
            "limit": args.limit,
            "model": args.model,
            "base_url": args.base_url,
            "env_file": str(args.env_file),
            "env_file_exists": env_exists,
            "api_key_present": bool(api_key),
            "first_idx": questions[0]["idx"] if questions else None,
            "last_idx": questions[-1]["idx"] if questions else None,
        }
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        return

    if not api_key:
        raise SystemExit(
            f"No API key found. Set {args.api_key_env} or provide it in {args.env_file}."
        )

    run_dir = args.out_dir / run_stamp()
    run_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    started_at = utc_now()

    manifest = {
        "experiment": "deepseek_flash_api_only_chemllmbench_ablation",
        "started_at": iso(started_at),
        "questions": str(args.questions),
        "answer_key": str(args.answer_key),
        "out_dir": str(run_dir),
        "env_file": str(args.env_file),
        "env_file_exists": env_exists,
        "api_key_env": args.api_key_env,
        "api_key_present": bool(api_key),
        "base_url": args.base_url,
        "model": args.model,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "thinking": args.thinking,
        "timeout_ms": args.timeout_ms,
        "pause_ms": args.pause_ms,
        "max_retries": args.max_retries,
        "start": args.start,
        "limit": args.limit,
        "question_count": len(questions),
        "scoring_rule": SCORING_RULE,
    }
    write_json(run_dir / "run_manifest.json", manifest)

    try:
        for offset, question in enumerate(questions, start=1):
            print(
                f"[{offset}/{len(questions)}] idx={question['idx']} "
                f"type={question.get('question_type')} topic={question.get('topic')}",
                flush=True,
            )
            result = submit_one(question, args, api_key, run_dir)
            results.append(result)
            print(
                f"  -> {result['status']} {result.get('latency_ms')}ms "
                f"answer={extract_answer_text(result.get('final_text', ''))!r}",
                flush=True,
            )
            if args.pause_ms and offset < len(questions):
                time.sleep(args.pause_ms / 1000)
    finally:
        summary = summarize_api_results(results)
        summary.update(
            {
                "run_dir": str(run_dir),
                "base_url": args.base_url,
                "model": args.model,
                "finished_at": iso(utc_now()),
            }
        )
        write_json(run_dir / "summary.json", summary)
        with (run_dir / "results.jsonl").open("w", encoding="utf-8") as handle:
            for row in results:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    scored = score_records(results, answer_key)
    scoring_manifest = dict(manifest)
    scoring_manifest["finished_at"] = iso(utc_now())
    score_summary = write_scored_outputs(
        scored,
        run_dir,
        source_kind="deepseek_flash_api_only",
        source_run_dir=run_dir,
        manifest=scoring_manifest,
    )
    print(json.dumps(score_summary, ensure_ascii=False, indent=2))


def score_native_run(args: argparse.Namespace) -> None:
    answer_key = load_chemllmbench_answer_key(args.answer_key)
    records = collect_native_records(args.native_run_dir)
    missing = [int(row["idx"]) for row in records if int(row["idx"]) not in answer_key]
    if missing:
        raise SystemExit(f"Missing ChemLLMBench answer-key rows for idx: {missing}")
    scored = score_records(records, answer_key)
    manifest = {
        "experiment": "frontend_agent_chemllmbench_40",
        "generated_at": iso(utc_now()),
        "native_run_dir": str(args.native_run_dir),
        "questions": str(args.questions),
        "answer_key": str(args.answer_key),
        "record_count": len(records),
        "scoring_rule": SCORING_RULE,
    }
    summary_path = args.native_run_dir / "summary.json"
    if summary_path.exists():
        manifest["native_run_summary"] = json.loads(summary_path.read_text(encoding="utf-8"))
    score_summary = write_scored_outputs(
        scored,
        args.score_out_dir,
        source_kind="frontend_agent",
        source_run_dir=args.native_run_dir,
        manifest=manifest,
    )
    print(json.dumps(score_summary, ensure_ascii=False, indent=2))


def read_score_csv(path: Path) -> dict[int, dict[str, Any]]:
    rows: dict[int, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            idx = int(row["idx"])
            row["correct"] = str(row["correct"]).lower() == "true"
            rows[idx] = row
    return rows


def compare_scores(args: argparse.Namespace) -> None:
    agent_rows = read_score_csv(args.agent_score_csv)
    api_rows = read_score_csv(args.api_score_csv)
    shared = sorted(set(agent_rows) & set(api_rows))

    matrix = defaultdict(int)
    details: list[dict[str, Any]] = []
    for idx in shared:
        agent = agent_rows[idx]
        api = api_rows[idx]
        key = f"agent_{agent['correct']}_api_{api['correct']}"
        matrix[key] += 1
        if agent["correct"] != api["correct"] or not agent["correct"]:
            details.append(
                {
                    "idx": idx,
                    "topic": agent.get("topic"),
                    "question_type": agent.get("question_type"),
                    "gold_answer": agent.get("gold_answer"),
                    "agent_correct": agent["correct"],
                    "agent_prediction": agent.get("prediction_normalized"),
                    "api_correct": api["correct"],
                    "api_prediction": api.get("prediction_normalized"),
                }
            )

    agent_correct = sum(1 for idx in shared if agent_rows[idx]["correct"])
    api_correct = sum(1 for idx in shared if api_rows[idx]["correct"])
    payload = {
        "generated_at": iso(utc_now()),
        "suite": "chemllmbench",
        "subset": "ChemLLMBench 40",
        "scoring_rule": SCORING_RULE,
        "agent_score_csv": str(args.agent_score_csv),
        "api_score_csv": str(args.api_score_csv),
        "shared_count": len(shared),
        "agent_correct": agent_correct,
        "agent_accuracy": agent_correct / len(shared) if shared else 0.0,
        "api_correct": api_correct,
        "api_accuracy": api_correct / len(shared) if shared else 0.0,
        "delta_accuracy_agent_minus_api": (
            (agent_correct - api_correct) / len(shared) if shared else 0.0
        ),
        "confusion": dict(matrix),
        "disagreements_or_errors": details,
    }
    write_json(args.out, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> None:
    args = parse_args()
    if args.command == "score-native":
        score_native_run(args)
    elif args.command == "run-api":
        run_api_ablation(args)
    elif args.command == "compare":
        compare_scores(args)
    else:
        raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
