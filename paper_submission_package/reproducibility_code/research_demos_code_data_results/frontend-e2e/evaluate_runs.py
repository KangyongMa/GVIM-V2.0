from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def extract_final_json(text: str) -> dict[str, Any] | None:
    fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    for candidate in reversed(fenced):
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value

    decoder = json.JSONDecoder()
    for start in range(len(text) - 1, -1, -1):
        if text[start] != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else math.nan


def mae(pairs: list[tuple[Any, Any]]) -> float:
    errors = []
    for predicted, expected in pairs:
        try:
            errors.append(abs(float(predicted) - float(expected)))
        except (TypeError, ValueError):
            errors.append(float("inf"))
    return mean(errors)


def exact_accuracy(pairs: list[tuple[Any, Any]]) -> float:
    return mean([float(predicted == expected) for predicted, expected in pairs])


def f1_binary(predicted: list[bool], expected: list[bool]) -> float:
    tp = sum(p and e for p, e in zip(predicted, expected))
    fp = sum(p and not e for p, e in zip(predicted, expected))
    fn = sum(not p and e for p, e in zip(predicted, expected))
    denominator = 2 * tp + fp + fn
    return 2 * tp / denominator if denominator else 1.0


def tool_coverage(tool_events: Any, required_groups: list[list[str]]) -> float:
    event_text = json.dumps(tool_events or [], ensure_ascii=False).lower()
    hits = [
        any(candidate.lower() in event_text for candidate in group)
        for group in required_groups
    ]
    return mean([float(hit) for hit in hits]) if hits else 1.0


def index_records(records: Any, key: str) -> dict[str, dict[str, Any]]:
    if not isinstance(records, list):
        return {}
    return {
        str(record.get(key)): record
        for record in records
        if isinstance(record, dict) and key in record
    }


def score_molecule_profile(output: dict[str, Any], gold: dict[str, Any]) -> dict[str, float]:
    exact_fields = ["canonical_smiles", "molecular_formula", "hba", "hbd", "conformer_generated"]
    numeric_fields = ["molecular_weight", "logp", "tpsa"]
    return {
        "exact_field_accuracy": exact_accuracy([(output.get(k), gold[k]) for k in exact_fields]),
        "descriptor_mae": mae([(output.get(k), gold[k]) for k in numeric_fields]),
    }


def score_ranked_records(output: dict[str, Any], spec: dict[str, Any]) -> dict[str, float]:
    records = output.get(spec["records_field"], [])
    expected = spec["gold"]
    predicted_order = [
        str(record.get(spec["record_key"]))
        for record in records
        if isinstance(record, dict)
    ]
    expected_order = [str(record[spec["record_key"]]) for record in expected]
    predicted_by_key = index_records(records, spec["record_key"])
    numeric_pairs = [
        (predicted_by_key.get(str(row[spec["record_key"]]), {}).get(field), row[field])
        for row in expected
        for field in spec["numeric_fields"]
    ]
    return {
        "top1_accuracy": float(bool(predicted_order) and predicted_order[0] == expected_order[0]),
        "ranking_exact_accuracy": float(predicted_order == expected_order),
        "value_mae": mae(numeric_pairs),
    }


def score_reaction_qc(output: dict[str, Any], gold: list[dict[str, Any]]) -> dict[str, float]:
    predicted = index_records(output.get("reactions"), "id")
    balance_pairs = [(predicted.get(row["id"], {}).get("balanced_elements"), row["balanced_elements"]) for row in gold]
    charge_pairs = [(predicted.get(row["id"], {}).get("charge_balanced"), row["charge_balanced"]) for row in gold]
    issue_pairs = [(predicted.get(row["id"], {}).get("issue_count"), row["issue_count"]) for row in gold]
    return {
        "element_balance_accuracy": exact_accuracy(balance_pairs),
        "element_balance_f1": f1_binary([bool(x[0]) for x in balance_pairs], [bool(x[1]) for x in balance_pairs]),
        "charge_balance_accuracy": exact_accuracy(charge_pairs),
        "issue_count_mae": mae(issue_pairs),
    }


def score_formula_audit(output: dict[str, Any], gold: list[dict[str, Any]]) -> dict[str, float]:
    predicted = index_records(output.get("materials"), "input_formula")
    reduced_pairs = [(predicted.get(row["input_formula"], {}).get("reduced_formula"), row["reduced_formula"]) for row in gold]
    mass_pairs = [(predicted.get(row["input_formula"], {}).get("molar_mass_g_mol"), row["molar_mass_g_mol"]) for row in gold]
    atom_pairs = [(predicted.get(row["input_formula"], {}).get("total_atoms_per_formula"), row["total_atoms_per_formula"]) for row in gold]
    return {
        "reduced_formula_accuracy": exact_accuracy(reduced_pairs),
        "molar_mass_mae": mae(mass_pairs),
        "total_atoms_mae": mae(atom_pairs),
    }


def score_precursor_plan(output: dict[str, Any], gold: dict[str, Any]) -> dict[str, float]:
    predicted = index_records(output.get("precursors"), "formula")
    coefficient_pairs = [(predicted.get(row["formula"], {}).get("coefficient_per_target_formula"), row["coefficient_per_target_formula"]) for row in gold["precursors"]]
    mass_pairs = [(predicted.get(row["formula"], {}).get("weigh_mass_g"), row["weigh_mass_g"]) for row in gold["precursors"]]
    return {
        "target_moles_absolute_error": mae([(output.get("target_moles"), gold["target_moles"])]),
        "basis_residual_absolute_error": mae([(output.get("basis_relative_residual"), gold["basis_relative_residual"])]),
        "coefficient_mae": mae(coefficient_pairs),
        "weigh_mass_mae_g": mae(mass_pairs),
    }


def task_success(scorer: str, metrics: dict[str, float]) -> bool:
    if metrics.get("tool_coverage", 0.0) < 1.0:
        return False
    if scorer == "molecule_profile":
        return metrics["exact_field_accuracy"] == 1.0 and metrics["descriptor_mae"] <= 0.01
    if scorer == "ranked_records":
        return metrics["ranking_exact_accuracy"] == 1.0 and metrics["value_mae"] <= 0.001
    if scorer == "reaction_qc":
        return metrics["element_balance_accuracy"] == 1.0 and metrics["charge_balance_accuracy"] == 1.0 and metrics["issue_count_mae"] == 0.0
    if scorer == "formula_audit":
        return metrics["reduced_formula_accuracy"] == 1.0 and metrics["molar_mass_mae"] <= 0.001 and metrics["total_atoms_mae"] == 0.0
    if scorer == "precursor_plan":
        return all(metrics[key] <= 0.001 for key in ["target_moles_absolute_error", "basis_residual_absolute_error", "coefficient_mae", "weigh_mass_mae_g"])
    return False


def evaluate_row(row: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    output = extract_final_json(row.get("final_text", ""))
    base = {
        "uuid": row.get("uuid"),
        "status": row.get("status"),
        "thread_id": row.get("thread_id"),
        "run_id": row.get("run_id"),
        "latency_ms": row.get("latency_ms"),
        "json_parsed": output is not None,
    }
    if output is None:
        return {**base, "task_success": False, "metrics": {"tool_coverage": tool_coverage(row.get("tool_events"), spec["required_tool_groups"])}}

    scorer = spec["scorer"]
    if scorer == "molecule_profile":
        metrics = score_molecule_profile(output, spec["gold"])
    elif scorer == "ranked_records":
        metrics = score_ranked_records(output, spec)
    elif scorer == "reaction_qc":
        metrics = score_reaction_qc(output, spec["gold"])
    elif scorer == "formula_audit":
        metrics = score_formula_audit(output, spec["gold"])
    elif scorer == "precursor_plan":
        metrics = score_precursor_plan(output, spec["gold"])
    else:
        raise ValueError(f"Unknown scorer: {scorer}")

    metrics["tool_coverage"] = tool_coverage(row.get("tool_events"), spec["required_tool_groups"])
    return {**base, "task_success": task_success(scorer, metrics), "metrics": metrics}


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate DeerFlow front-end research demo runs.")
    parser.add_argument("run_dir", type=Path, help="Run directory produced by native_submit.mjs")
    parser.add_argument("--gold", type=Path, default=ROOT / "gold.json")
    args = parser.parse_args()

    run_file = args.run_dir / "results.jsonl"
    rows = load_jsonl(run_file)
    specs = json.loads(args.gold.read_text(encoding="utf-8"))["tasks"]
    evaluated = [evaluate_row(row, specs[row["uuid"]]) for row in rows if row.get("uuid") in specs]
    summary = {
        "run_dir": str(args.run_dir.resolve()),
        "evaluated_tasks": len(evaluated),
        "json_parse_rate": mean([float(row["json_parsed"]) for row in evaluated]),
        "task_success_rate": mean([float(row["task_success"]) for row in evaluated]),
        "frontend_http_success_rate": mean([float(row["status"] == "ok") for row in evaluated]),
        "mean_latency_ms": mean([float(row["latency_ms"]) for row in evaluated if row.get("latency_ms") is not None]),
        "mean_tool_coverage": mean([row["metrics"]["tool_coverage"] for row in evaluated]),
    }
    (args.run_dir / "evaluation.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in evaluated),
        encoding="utf-8",
    )
    (args.run_dir / "evaluation_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
