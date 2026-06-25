from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


REQUIRED_PREDICTION_COLUMNS = {"fold", "row_id", "predicted_gap_eV"}
REQUIRED_GOLD_COLUMNS = {"fold", "row_id", "gap_expt"}


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(math.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)),
    }


def read_csv(path: Path, required_columns: set[str], label: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = sorted(required_columns - set(frame.columns))
    if missing:
        raise ValueError(f"{label} is missing required columns: {missing}")
    return frame


def evaluate(predictions_path: Path, gold_path: Path) -> dict[str, object]:
    predictions = read_csv(predictions_path, REQUIRED_PREDICTION_COLUMNS, "predictions")
    gold = read_csv(gold_path, REQUIRED_GOLD_COLUMNS, "gold")

    predictions = predictions.copy()
    gold = gold.copy()
    predictions["fold"] = predictions["fold"].astype(int)
    gold["fold"] = gold["fold"].astype(int)
    predictions["row_id"] = predictions["row_id"].astype(int)
    gold["row_id"] = gold["row_id"].astype(int)

    duplicate_predictions = predictions.duplicated(["fold", "row_id"]).sum()
    if duplicate_predictions:
        raise ValueError(f"predictions contain {duplicate_predictions} duplicate fold,row_id rows")

    merged = gold.merge(
        predictions[["fold", "row_id", "predicted_gap_eV"]],
        on=["fold", "row_id"],
        how="left",
        validate="one_to_one",
    )
    if merged["predicted_gap_eV"].isna().any():
        missing = int(merged["predicted_gap_eV"].isna().sum())
        raise ValueError(f"predictions are missing {missing} gold rows")

    folds = []
    for fold, fold_frame in merged.groupby("fold", sort=True):
        y_true = fold_frame["gap_expt"].to_numpy(dtype=float)
        y_pred = fold_frame["predicted_gap_eV"].to_numpy(dtype=float)
        folds.append(
            {
                "fold": int(fold),
                "n_test": int(len(fold_frame)),
                **regression_metrics(y_true, y_pred),
            }
        )

    mean_fold = {
        metric: float(np.mean([item[metric] for item in folds]))
        for metric in ["mae", "rmse", "r2"]
    }
    return {
        "benchmark": "Matbench v0.1",
        "task": "matbench_expt_gap",
        "fold_rule": "KFold(n_splits=5, shuffle=True, random_state=18012019)",
        "metrics": {
            "mean_fold": mean_fold,
            "folds": folds,
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
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    mean_fold = result["metrics"]["mean_fold"]
    print(
        f"MAE={mean_fold['mae']:.4f} eV, "
        f"RMSE={mean_fold['rmse']:.4f} eV, R2={mean_fold['r2']:.4f}"
    )


if __name__ == "__main__":
    main()
