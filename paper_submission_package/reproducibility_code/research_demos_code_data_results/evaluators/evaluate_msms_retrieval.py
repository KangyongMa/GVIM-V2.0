#!/usr/bin/env python3
"""Evaluate MS/MS candidate retrieval rankings with top-k accuracy and MRR."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def load_gold(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return {row["query_id"]: row["inchikey"] for row in csv.DictReader(handle)}


def normalize(value: str) -> str:
    return str(value or "").strip()


def evaluate(rankings_csv: Path, gold_csv: Path) -> dict[str, object]:
    gold = load_gold(gold_csv)
    by_query: dict[str, list[dict[str, str]]] = {query_id: [] for query_id in gold}
    with rankings_csv.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            query_id = normalize(row.get("query_id", ""))
            if query_id in by_query:
                by_query[query_id].append(row)

    reciprocal_ranks = []
    top_hits = {1: 0, 3: 0, 5: 0}
    query_results = []
    for query_id, true_inchikey in gold.items():
        ranked = sorted(by_query[query_id], key=lambda row: int(row.get("rank", "999999")))
        hit_rank = None
        for row in ranked:
            if normalize(row.get("candidate_inchikey", "")) == true_inchikey:
                hit_rank = int(row["rank"])
                break
        reciprocal_ranks.append(1.0 / hit_rank if hit_rank else 0.0)
        for k in top_hits:
            if hit_rank is not None and hit_rank <= k:
                top_hits[k] += 1
        query_results.append({"query_id": query_id, "true_inchikey": true_inchikey, "hit_rank": hit_rank})

    n = len(gold)
    return {
        "gold_source": "MassBank InChIKey identity from public MassBank-data records",
        "n_queries": n,
        "top1_accuracy": top_hits[1] / n,
        "top3_accuracy": top_hits[3] / n,
        "top5_accuracy": top_hits[5] / n,
        "mrr": sum(reciprocal_ranks) / n,
        "per_query": query_results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("rankings_csv", type=Path)
    parser.add_argument(
        "--gold",
        type=Path,
        default=(
            Path(__file__).resolve().parents[1]
            / "showcase-information-extraction"
            / "runtime"
            / "msms_retrieval"
            / "gold"
            / "gold_matches.csv"
        ),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(args.rankings_csv, args.gold)
    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
