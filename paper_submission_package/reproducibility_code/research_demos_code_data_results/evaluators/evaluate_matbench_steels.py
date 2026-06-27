from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


REQUIRED_PREDICTION_COLUMNS = {"fold", "row_id", "predicted_yield_strength_mpa"}
REQUIRED_GOLD_COLUMNS = {"fold", "row_id", "yield_strength_mpa"}


def read_csv(path: Path, required: set[str], label: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{label} is missing required columns: {sorted(missing)}")
    return df


def evaluate(predictions_path: Path, gold_path: Path) -> dict[str, object]:
    predictions = read_csv(predictions_path, REQUIRED_PREDICTION_COLUMNS, "predictions").copy()
    gold = read_csv(gold_path, REQUIRED_GOLD_COLUMNS, "gold").copy()
    predictions["fold"] = predictions["fold"].astype(int)
    predictions["row_id"] = predictions["row_id"].astype(int)
    gold["fold"] = gold["fold"].astype(int)
    gold["row_id"] = gold["row_id"].astype(int)

    duplicates = predictions.duplicated(["fold", "row_id"]).sum()
    if duplicates:
        raise ValueError(f"predictions contain {duplicates} duplicate fold,row_id rows")

    prediction_keys = set(map(tuple, predictions[["fold", "row_id"]].to_numpy()))
    gold_keys = set(map(tuple, gold[["fold", "row_id"]].to_numpy()))
    missing_keys = gold_keys - prediction_keys
    extra_keys = prediction_keys - gold_keys
    if missing_keys:
        raise ValueError(f"predictions are missing {len(missing_keys)} gold fold,row_id rows")
    if extra_keys:
        raise ValueError(f"predictions contain {len(extra_keys)} unexpected fold,row_id rows")

    merged = gold.merge(
        predictions[["fold", "row_id", "predicted_yield_strength_mpa"]],
        on=["fold", "row_id"],
        how="left",
    )
    if merged["predicted_yield_strength_mpa"].isna().any():
        missing = merged.loc[merged["predicted_yield_strength_mpa"].isna(), ["fold", "row_id"]]
        raise ValueError(f"predictions are missing {len(missing)} gold rows")

    per_fold: list[dict[str, object]] = []
    for fold, frame in merged.groupby("fold", sort=True):
        y_true = frame["yield_strength_mpa"].to_numpy(dtype=float)
        y_pred = frame["predicted_yield_strength_mpa"].to_numpy(dtype=float)
        per_fold.append(
            {
                "fold": int(fold),
                "n_test": int(len(frame)),
                "metrics": {
                    "mae": float(mean_absolute_error(y_true, y_pred)),
                    "rmse": float(math.sqrt(mean_squared_error(y_true, y_pred))),
                    "r2": float(r2_score(y_true, y_pred)),
                },
            }
        )
    aggregate_metrics = {}
    for metric in ("mae", "rmse", "r2"):
        values = np.asarray([fold["metrics"][metric] for fold in per_fold], dtype=float)
        aggregate_metrics[metric] = {
            "mean": float(np.mean(values)),
            "std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
        }
    return {
        "benchmark": "Matbench v0.1",
        "task": "matbench_steels",
        "folds": [fold["fold"] for fold in per_fold],
        "n_test": int(len(merged)),
        "per_fold": per_fold,
        "aggregate_metrics": aggregate_metrics,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--gold", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = evaluate(args.predictions, args.gold)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    metrics = result["aggregate_metrics"]
    print(
        f"MAE={metrics['mae']['mean']:.4f} +/- {metrics['mae']['std']:.4f} MPa, "
        f"RMSE={metrics['rmse']['mean']:.4f} +/- {metrics['rmse']['std']:.4f} MPa, "
        f"R2={metrics['r2']['mean']:.4f} +/- {metrics['r2']['std']:.4f}"
    )


if __name__ == "__main__":
    main()
