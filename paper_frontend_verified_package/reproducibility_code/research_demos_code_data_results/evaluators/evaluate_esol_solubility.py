from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


REQUIRED_PREDICTION_COLUMNS = {"molecule_id", "predicted_log_solubility"}
REQUIRED_GOLD_COLUMNS = {"molecule_id", "log_solubility"}


def read_csv(path: Path, required: set[str], label: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{label} is missing required columns: {sorted(missing)}")
    return df


def evaluate(predictions_path: Path, gold_path: Path) -> dict[str, object]:
    predictions = read_csv(predictions_path, REQUIRED_PREDICTION_COLUMNS, "predictions").copy()
    gold = read_csv(gold_path, REQUIRED_GOLD_COLUMNS, "gold").copy()
    predictions["molecule_id"] = predictions["molecule_id"].astype(int)
    gold["molecule_id"] = gold["molecule_id"].astype(int)

    duplicates = predictions.duplicated(["molecule_id"]).sum()
    if duplicates:
        raise ValueError(f"predictions contain {duplicates} duplicate molecule_id rows")

    merged = gold.merge(predictions[["molecule_id", "predicted_log_solubility"]], on="molecule_id", how="left")
    if merged["predicted_log_solubility"].isna().any():
        missing = merged.loc[merged["predicted_log_solubility"].isna(), "molecule_id"].tolist()
        raise ValueError(f"predictions are missing {len(missing)} gold rows")

    y_true = merged["log_solubility"].to_numpy(dtype=float)
    y_pred = merged["predicted_log_solubility"].to_numpy(dtype=float)
    metrics = {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(math.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)),
    }
    return {
        "benchmark": "MoleculeNet ESOL",
        "task": "aqueous solubility regression",
        "n_test": int(len(merged)),
        "metrics": metrics,
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
    metrics = result["metrics"]
    print(f"MAE={metrics['mae']:.4f}, RMSE={metrics['rmse']:.4f}, R2={metrics['r2']:.4f}")


if __name__ == "__main__":
    main()
