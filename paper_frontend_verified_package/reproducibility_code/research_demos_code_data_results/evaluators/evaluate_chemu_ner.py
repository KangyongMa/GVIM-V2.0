from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
    return rows


def flatten(rows: list[dict], label: str) -> list[tuple[str, str, int, int]]:
    entities = []
    seen_docs = set()
    for row in rows:
        doc_id = str(row["doc_id"])
        if doc_id in seen_docs:
            raise ValueError(f"{label} contains duplicate document {doc_id}")
        seen_docs.add(doc_id)
        for entity in row.get("entities", []):
            entities.append(
                (
                    doc_id,
                    str(entity["label"]),
                    int(entity["start"]),
                    int(entity["end"]),
                )
            )
    duplicates = len(entities) - len(set(entities))
    if duplicates:
        raise ValueError(f"{label} contains {duplicates} duplicate entities")
    return entities


def prf(tp: int, predicted: int, gold: int) -> dict[str, float | int]:
    precision = tp / predicted if predicted else 0.0
    recall = tp / gold if gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "true_positives": tp,
        "predicted": predicted,
        "gold": gold,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def relaxed_true_positives(
    predictions: list[tuple[str, str, int, int]],
    gold: list[tuple[str, str, int, int]],
) -> int:
    pred_groups: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
    gold_groups: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
    for doc_id, label, start, end in predictions:
        pred_groups[(doc_id, label)].append((start, end))
    for doc_id, label, start, end in gold:
        gold_groups[(doc_id, label)].append((start, end))

    matched = 0
    for key, pred_spans in pred_groups.items():
        gold_spans = gold_groups.get(key, [])
        adjacency = [
            [index for index, (gold_start, gold_end) in enumerate(gold_spans) if start < gold_end and gold_start < end]
            for start, end in pred_spans
        ]
        assigned: dict[int, int] = {}

        def augment(pred_index: int, visited: set[int]) -> bool:
            for gold_index in adjacency[pred_index]:
                if gold_index in visited:
                    continue
                visited.add(gold_index)
                if gold_index not in assigned or augment(assigned[gold_index], visited):
                    assigned[gold_index] = pred_index
                    return True
            return False

        matched += sum(augment(index, set()) for index in range(len(pred_spans)))
    return matched


def evaluate(predictions_path: Path, gold_path: Path) -> dict[str, object]:
    predictions = flatten(read_jsonl(predictions_path), "predictions")
    gold = flatten(read_jsonl(gold_path), "gold")
    exact_tp = len(set(predictions) & set(gold))
    relaxed_tp = relaxed_true_positives(predictions, gold)

    pred_by_label = Counter(entity[1] for entity in predictions)
    gold_by_label = Counter(entity[1] for entity in gold)
    exact_by_label = Counter(entity[1] for entity in set(predictions) & set(gold))
    labels = sorted(set(pred_by_label) | set(gold_by_label))
    return {
        "benchmark": "ChEMU 2020 Task 1 sample v3",
        "task": "chemical synthesis named entity extraction",
        "exact_match": prf(exact_tp, len(predictions), len(gold)),
        "relaxed_match": prf(relaxed_tp, len(predictions), len(gold)),
        "per_label_exact_match": {
            label: prf(exact_by_label[label], pred_by_label[label], gold_by_label[label])
            for label in labels
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--gold", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = evaluate(args.predictions, args.gold)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8", newline="\n")
    exact = result["exact_match"]
    relaxed = result["relaxed_match"]
    print(
        f"Exact P/R/F1={exact['precision']:.4f}/{exact['recall']:.4f}/{exact['f1']:.4f}; "
        f"Relaxed P/R/F1={relaxed['precision']:.4f}/{relaxed['recall']:.4f}/{relaxed['f1']:.4f}"
    )


if __name__ == "__main__":
    main()
