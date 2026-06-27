#!/usr/bin/env python3
"""Evaluate MinerU reaction-table extraction against publisher JATS gold."""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from pathlib import Path


FIELDS = ["entry", "catalyst", "solvent", "temperature_c", "yield_percent"]
ALIASES = {
    "entry": ["entry", "no", "no."],
    "catalyst": ["catalyst", "[m] cat.", "[m] cat", "cat.", "cat"],
    "solvent": ["solvent", "solvent (v/v)"],
    "temperature_c": ["temperature_c", "temperature", "temp", "t (°c)", "t (c)"],
    "yield_percent": ["yield_percent", "yield_value", "yield_raw", "yield (%)", "yield [%]"],
}


def normalize(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = re.sub(r"</?(?:sub|sup|i|b|em|strong)>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[$*_`^]", "", text)
    text = text.translate(str.maketrans({"‐": "-", "‑": "-", "–": "-", "—": "-", "−": "-"}))
    return "".join(text.split())


def find_value(row: dict[str, str], field: str) -> str:
    normalized_keys = {normalize(key).lower(): value for key, value in row.items()}
    for alias in ALIASES[field]:
        value = normalized_keys.get(normalize(alias).lower())
        if value is not None:
            return normalize(value)
    return ""


def load_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    result = {}
    for raw in rows:
        row = {field: find_value(raw, field) for field in FIELDS}
        if row["entry"]:
            result[row["entry"]] = row
    return result


def cell_set(rows: dict[str, dict[str, str]]) -> set[tuple[str, str, str]]:
    return {
        (entry, field, row[field])
        for entry, row in rows.items()
        for field in FIELDS
        if row[field]
    }


def divide(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def evaluate(prediction_csv: Path, gold_csv: Path) -> dict[str, object]:
    predicted = load_rows(prediction_csv)
    gold = load_rows(gold_csv)
    predicted_cells = cell_set(predicted)
    gold_cells = cell_set(gold)
    true_positive = len(predicted_cells & gold_cells)
    precision = divide(true_positive, len(predicted_cells))
    recall = divide(true_positive, len(gold_cells))
    f1 = divide(2 * precision * recall, precision + recall)

    exact_rows = sum(
        1
        for entry, gold_row in gold.items()
        if entry in predicted and predicted[entry] == gold_row
    )
    return {
        "metric_definition": "Exact match after Unicode NFKC, markup removal, whitespace collapse, and dash normalization",
        "gold_source": "Publisher JATS XML table nanomaterials-12-01070-t002",
        "gold_rows": len(gold),
        "predicted_rows": len(predicted),
        "gold_cells": len(gold_cells),
        "predicted_cells": len(predicted_cells),
        "true_positive_cells": true_positive,
        "exact_match_precision": precision,
        "exact_match_recall": recall,
        "exact_match_f1": f1,
        "exact_rows": exact_rows,
        "exact_row_accuracy": divide(exact_rows, len(gold)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("prediction_csv", type=Path)
    parser.add_argument(
        "--gold",
        type=Path,
        default=(
            Path(__file__).resolve().parents[1]
            / "showcase-information-extraction"
            / "runtime"
            / "mineru_reaction_table"
            / "gold"
            / "publisher_table2_gold.csv"
        ),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = evaluate(args.prediction_csv, args.gold)
    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
