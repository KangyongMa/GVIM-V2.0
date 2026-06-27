from __future__ import annotations

import argparse
import gzip
import json
import math
import re
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin, clone
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold


STEELS_URL = "https://ml.materialsproject.org/projects/matbench_steels.json.gz"
MATBENCH_VALIDATION_URL = "https://raw.githubusercontent.com/materialsproject/matbench/main/matbench/matbench_v0.1_validation.json"
OUTER_SEED = 18012019
INNER_SEED = 42
ELEMENT_PATTERN = re.compile(r"([A-Z][a-z]?)([0-9]*(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)")


class MeanBaseline(BaseEstimator, RegressorMixin):
    def fit(self, X: np.ndarray, y: np.ndarray) -> "MeanBaseline":
        self.mean_ = float(np.mean(y))
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.full(len(X), self.mean_)


def load_matbench_steels() -> pd.DataFrame:
    request = urllib.request.Request(STEELS_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read()
    raw = json.loads(gzip.decompress(payload).decode("utf-8"))
    df = pd.DataFrame(raw["data"], columns=raw["columns"], index=raw["index"])
    return pd.DataFrame(
        {
            "row_id": np.arange(len(df), dtype=int),
            "composition": df["composition"].astype(str).to_numpy(),
            "yield_strength_mpa": df["yield strength"].astype(float).to_numpy(),
        }
    )


def load_official_outer_folds() -> list[tuple[np.ndarray, np.ndarray]]:
    with urllib.request.urlopen(MATBENCH_VALIDATION_URL, timeout=60) as response:
        validation = json.loads(response.read().decode("utf-8"))
    split_data = validation["splits"]["matbench_steels"]
    folds = []
    for fold in range(5):
        split = split_data[f"fold_{fold}"]
        train_idx = np.asarray([int(value.rsplit("-", 1)[1]) - 1 for value in split["train"]])
        test_idx = np.asarray([int(value.rsplit("-", 1)[1]) - 1 for value in split["test"]])
        folds.append((train_idx, test_idx))
    return folds


def parse_composition(composition: str) -> dict[str, float]:
    return {
        element: float(amount) if amount else 1.0
        for element, amount in ELEMENT_PATTERN.findall(composition)
    }


def build_features(
    compositions: pd.Series,
    columns: list[str] | None = None,
) -> tuple[np.ndarray, list[str]]:
    frame = pd.DataFrame([parse_composition(value) for value in compositions]).fillna(0.0)
    if columns is None:
        columns = sorted(frame.columns)
    frame = frame.reindex(columns=columns, fill_value=0.0)
    return frame.to_numpy(dtype=float), columns


def build_models() -> dict[str, BaseEstimator]:
    return {
        "Ridge": Ridge(alpha=1.0),
        "RandomForest": RandomForestRegressor(
            n_estimators=200,
            random_state=INNER_SEED,
            n_jobs=1,
        ),
        "GradientBoosting": GradientBoostingRegressor(
            n_estimators=200,
            max_depth=3,
            random_state=INNER_SEED,
        ),
    }


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(math.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)),
    }


def select_model(X: np.ndarray, y: np.ndarray) -> tuple[str, dict[str, dict[str, float]]]:
    inner_cv = KFold(n_splits=5, shuffle=True, random_state=INNER_SEED)
    results: dict[str, dict[str, float]] = {}

    baseline_predictions = np.empty_like(y, dtype=float)
    for train_idx, val_idx in inner_cv.split(X):
        baseline_predictions[val_idx] = MeanBaseline().fit(X[train_idx], y[train_idx]).predict(X[val_idx])
    results["MeanBaseline"] = regression_metrics(y, baseline_predictions)

    for name, model in build_models().items():
        predictions = np.empty_like(y, dtype=float)
        for train_idx, val_idx in inner_cv.split(X):
            fitted = clone(model).fit(X[train_idx], y[train_idx])
            predictions[val_idx] = fitted.predict(X[val_idx])
        results[name] = regression_metrics(y, predictions)

    selected = min(build_models(), key=lambda name: results[name]["rmse"])
    return selected, results


def summarize(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=float)
    return {
        "mean": float(np.mean(array)),
        "std": float(np.std(array, ddof=1)),
    }


def run(output_dir: Path) -> dict[str, object]:
    start = time.time()
    output_dir.mkdir(parents=True, exist_ok=True)
    data = load_matbench_steels()
    outer_folds = load_official_outer_folds()

    predictions: list[pd.DataFrame] = []
    fold_results: list[dict[str, object]] = []
    for fold, (train_idx, test_idx) in enumerate(outer_folds):
        train = data.iloc[train_idx].reset_index(drop=True)
        test = data.iloc[test_idx].reset_index(drop=True)
        X_train, columns = build_features(train["composition"])
        X_test, _ = build_features(test["composition"], columns)
        y_train = train["yield_strength_mpa"].to_numpy(dtype=float)
        y_test = test["yield_strength_mpa"].to_numpy(dtype=float)

        selected, validation = select_model(X_train, y_train)
        model = clone(build_models()[selected]).fit(X_train, y_train)
        y_pred = model.predict(X_test)
        metrics = regression_metrics(y_test, y_pred)
        fold_results.append(
            {
                "fold": fold,
                "n_train": len(train),
                "n_test": len(test),
                "n_features": len(columns),
                "selected_model": selected,
                "validation_results": validation,
                "test_metrics": metrics,
            }
        )
        predictions.append(
            pd.DataFrame(
                {
                    "fold": fold,
                    "row_id": test["row_id"].to_numpy(dtype=int),
                    "composition": test["composition"].to_numpy(),
                    "predicted_yield_strength_mpa": y_pred,
                }
            )
        )
        print(
            f"fold={fold} model={selected} "
            f"MAE={metrics['mae']:.4f} RMSE={metrics['rmse']:.4f} R2={metrics['r2']:.4f}"
        )

    prediction_frame = pd.concat(predictions, ignore_index=True)
    prediction_frame.to_csv(output_dir / "predictions.csv", index=False)
    aggregate = {
        metric: summarize([fold["test_metrics"][metric] for fold in fold_results])
        for metric in ("mae", "rmse", "r2")
    }
    result = {
        "benchmark": "Matbench v0.1",
        "task": "matbench_steels",
        "protocol": {
            "outer_cv": "KFold(n_splits=5, shuffle=True, random_state=18012019)",
            "official_split_source": MATBENCH_VALIDATION_URL,
            "inner_model_selection": "KFold(n_splits=5, shuffle=True, random_state=42)",
            "primary_metric": "mean outer-fold MAE",
        },
        "fold_results": fold_results,
        "aggregate_metrics": aggregate,
        "n_samples": len(data),
        "execution_time_seconds": time.time() - start,
    }
    (output_dir / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("research-demos/results/matbench_steels_5fold"),
    )
    args = parser.parse_args()
    result = run(args.output_dir)
    metrics = result["aggregate_metrics"]
    print(
        "aggregate "
        f"MAE={metrics['mae']['mean']:.4f}+/-{metrics['mae']['std']:.4f} MPa "
        f"RMSE={metrics['rmse']['mean']:.4f}+/-{metrics['rmse']['std']:.4f} MPa "
        f"R2={metrics['r2']['mean']:.4f}+/-{metrics['r2']['std']:.4f}"
    )


if __name__ == "__main__":
    main()
