#!/usr/bin/env python3
"""
Matbench Steels (fold 0): Yield Strength Prediction Pipeline
=============================================================
- Parse composition strings into element fraction features
- Compare: mean baseline, Ridge, Random Forest, Gradient Boosting
- 5-fold CV, fixed seed, select model with lowest RMSE
- Retrain on full training set, predict unlabeled test set
- Write predictions.csv, run_metadata.json, report.md
"""

import json
import time
import os
import sys
import warnings
import re
import textwrap

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.base import BaseEstimator, RegressorMixin
warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────────────────────────
# 0.  Fixed seed & paths
# ──────────────────────────────────────────────────────────────────────
RANDOM_SEED = 42
DATA_DIR = "E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/4d0cfbcc-f7f4-4a8e-be86-96856f93447a/threads/b4442f6a-a613-4598-9b55-448eaaa33c7c/user-data/uploads"
OUT_DIR  = "E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/4d0cfbcc-f7f4-4a8e-be86-96856f93447a/threads/b4442f6a-a613-4598-9b55-448eaaa33c7c/user-data/outputs"
TRAIN_CSV = os.path.join(DATA_DIR, "matbench_steels_fold0_train.csv")
TEST_CSV  = os.path.join(DATA_DIR, "matbench_steels_fold0_test_unlabeled.csv")

os.makedirs(OUT_DIR, exist_ok=True)

rng = np.random.default_rng(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# ──────────────────────────────────────────────────────────────────────
# 1.  Composition parsing → feature matrix
# ──────────────────────────────────────────────────────────────────────
_ELEMENT_PATTERN = re.compile(r"([A-Z][a-z]?)([0-9]*(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)")


def parse_composition(comp_str):
    """Parse 'Fe0.620C0.000953...' into {element: fraction} dict."""
    out = {}
    for el, frac_str in _ELEMENT_PATTERN.findall(comp_str):
        if frac_str == "":
            out[el] = 1.0
        else:
            out[el] = float(frac_str)
    return out


def build_feature_matrix(
    compositions, fill_unknown=True, known_elements=None
):
    """
    Convert a list of composition strings into a DataFrame of element fractions.
    Optionally restrict to a known set of columns.
    """
    rows = []
    for c in compositions:
        rows.append(parse_composition(c))
    df = pd.DataFrame(rows).fillna(0.0)
    if known_elements is not None:
        # ensure all known columns exist, drop extras
        for col in known_elements:
            if col not in df.columns:
                df[col] = 0.0
        df = df[list(known_elements)]
    # sort columns alphabetically for reproducibility
    df = df[sorted(df.columns)]
    return df


# ──────────────────────────────────────────────────────────────────────
# 2.  Baseline: training-mean predictor
# ──────────────────────────────────────────────────────────────────────
class MeanBaseline(BaseEstimator, RegressorMixin):
    def __init__(self):
        self.mean_ = None

    def fit(self, X, y):
        self.mean_ = float(np.mean(y))
        return self

    def predict(self, X):
        return np.full(X.shape[0], self.mean_)


# ──────────────────────────────────────────────────────────────────────
# 3.  Main pipeline
# ──────────────────────────────────────────────────────────────────────
def main():
    start_wall = time.time()
    start_cpu  = time.process_time()

    # ── Load data ──
    train = pd.read_csv(TRAIN_CSV)
    test  = pd.read_csv(TEST_CSV)

    train_compositions = train["composition"].tolist()
    train_y = train["yield_strength_mpa"].values
    test_compositions = test["composition"].tolist()

    # ── Build features on training set, determine element columns ──
    X_train_raw = build_feature_matrix(train_compositions)
    known_elements = set(X_train_raw.columns)

    # Build test features aligned to training columns
    X_test = build_feature_matrix(
        test_compositions, known_elements=known_elements
    )

    X_train = X_train_raw.values
    X_test_arr = X_test.values

    # Sanity checks
    n_train, n_feat = X_train.shape
    n_test  = X_test_arr.shape[0]
    element_cols = list(X_train_raw.columns)

    # Frame-level check: re-parsing consistency for a few rows
    parse_check_pairs = []
    for i in range(min(5, len(train_compositions))):
        recon = build_feature_matrix([train_compositions[i]],
                                     known_elements=element_cols)
        parse_check_pairs.append({
            "row_id": int(train.iloc[i]["row_id"]),
            "composition": train_compositions[i],
            "n_elements": int((recon.iloc[0] > 0).sum()),
            "sum_fractions": float(round(recon.iloc[0].sum(), 6)),
        })

    # ── Define models ──
    models = {
        "MeanBaseline": MeanBaseline(),
        "Ridge":         Ridge(alpha=1.0, random_state=RANDOM_SEED),
        "RandomForest":  RandomForestRegressor(
            n_estimators=200, max_depth=None,
            random_state=RANDOM_SEED, n_jobs=1
        ),
        "GradientBoosting": GradientBoostingRegressor(
            n_estimators=200, max_depth=3,
            random_state=RANDOM_SEED
        ),
    }

    # ── 5-fold CV ──
    kf = KFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    cv_results = {}

    train_y_mean = float(np.mean(train_y))

    for name, model in models.items():
        fold_mae  = []
        fold_rmse = []
        fold_r2   = []

        for train_idx, val_idx in kf.split(X_train):
            X_tr, X_val = X_train[train_idx], X_train[val_idx]
            y_tr, y_val = train_y[train_idx], train_y[val_idx]

            m = model
            if name == "MeanBaseline":
                m.fit(X_tr, y_tr)
            else:
                m.fit(X_tr, y_tr)

            y_pred = m.predict(X_val)
            fold_mae.append(mean_absolute_error(y_val, y_pred))
            fold_rmse.append(mean_squared_error(y_val, y_pred) ** 0.5)
            fold_r2.append(r2_score(y_val, y_pred))

        cv_results[name] = {
            "MAE_mean":  float(np.mean(fold_mae)),
            "MAE_std":   float(np.std(fold_mae, ddof=1)),
            "RMSE_mean": float(np.mean(fold_rmse)),
            "RMSE_std":  float(np.std(fold_rmse, ddof=1)),
            "R2_mean":   float(np.mean(fold_r2)),
            "R2_std":    float(np.std(fold_r2, ddof=1)),
            "fold_scores": {
                f"fold_{i}": {
                    "MAE":  round(fold_mae[i], 4),
                    "RMSE": round(fold_rmse[i], 4),
                    "R2":   round(fold_r2[i], 6),
                }
                for i in range(5)
            },
        }

    # ── Select best model ──
    best_model_name = min(cv_results, key=lambda n: cv_results[n]["RMSE_mean"])
    best_model = models[best_model_name]

    # ── Retrain on full training set ──
    best_model.fit(X_train, train_y)
    test_preds = best_model.predict(X_test_arr)

    # ── Build predictions.csv ──
    pred_df = pd.DataFrame({
        "fold":  [0] * n_test,
        "row_id": test["row_id"].values,
        "composition": test_compositions,
        "predicted_yield_strength_mpa": [round(float(v), 2) for v in test_preds],
    })
    pred_csv = os.path.join(OUT_DIR, "predictions.csv")
    pred_df.to_csv(pred_csv, index=False)

    # ── Sanity checks ──
    wall_elapsed = time.time() - start_wall
    cpu_elapsed  = time.process_time() - start_cpu

    # Check: predictions are finite and within reasonable range
    train_min = float(np.min(train_y))
    train_max = float(np.max(train_y))
    pred_min  = float(np.min(test_preds))
    pred_max  = float(np.max(test_preds))
    pred_finite = int(np.isfinite(test_preds).sum())
    pred_in_range = int(((test_preds >= train_min - 500) &
                         (test_preds <= train_max + 500)).sum())

    # ── Build run_metadata.json ──
    metadata = {
        "task": "matbench_steels",
        "fold": 0,
        "random_seed": RANDOM_SEED,
        "baseline": {
            "name": "MeanBaseline",
            "description": "Training-mean predictor",
            "training_mean_mpa": round(train_y_mean, 2),
        },
        "validation": {
            "strategy": "KFold(n_splits=5, shuffle=True)",
            "results": cv_results,
            "selected_model": best_model_name,
            "selection_criterion": "lowest RMSE_mean",
        },
        "selected_model": best_model_name,
        "model_params": {
            name: str(model.get_params()) for name, model in models.items()
        },
        "training": {
            "n_train": n_train,
            "n_test":  n_test,
            "n_features": n_feat,
            "element_columns": element_cols,
            "target_column": "yield_strength_mpa",
        },
        "sanity_checks": {
            "n_train_rows": n_train,
            "n_test_rows": n_test,
            "feature_dimension": n_feat,
            "feature_cols": element_cols,
            "train_target_range_mpa": [round(float(np.min(train_y)), 2),
                                       round(float(np.max(train_y)), 2)],
            "train_target_mean_mpa": round(train_y_mean, 2),
            "train_target_std_mpa": round(float(np.std(train_y, ddof=1)), 2),
            "predictions_all_finite": pred_finite == n_test,
            "predictions_in_reasonable_range": pred_in_range == n_test,
            "composition_parse_samples": parse_check_pairs,
            "sum_of_fractions_close_to_1": all(
                abs(p["sum_fractions"] - 1.0) < 0.02
                for p in parse_check_pairs
            ),
        },
        "execution": {
            "wall_time_seconds": round(wall_elapsed, 3),
            "cpu_time_seconds": round(cpu_elapsed, 3),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "python_version": sys.version,
            "numpy_version": np.__version__,
            "pandas_version": pd.__version__,
            "sklearn_version": __import__("sklearn").__version__,
        },
    }

    meta_path = os.path.join(OUT_DIR, "run_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    # ── Build report.md ──
    lines = []
    lines.append("# Steel Yield Strength Prediction — Matbench Fold 0")
    lines.append("")
    lines.append("## Workflow Description")
    lines.append("")
    lines.append(
        "This pipeline predicts steel yield strength (MPa) from composition "
        "strings for Matbench fold 0 of the `matbench_steels` benchmark. "
        "The workflow is fully reproducible: composition strings are parsed "
        "into element-fraction features, three regression models and a "
        "training-mean baseline are compared via 5-fold cross-validation, "
        "the model with the lowest validation RMSE is selected, retrained "
        "on all training data, and used to predict the unlabeled test set."
    )
    lines.append("")
    lines.append(f"- **Training samples**: {n_train}")
    lines.append(f"- **Test samples**: {n_test}")
    lines.append(f"- **Features**: {n_feat} element fractions: "
                 f"{', '.join(element_cols)}")
    lines.append(f"- **Random seed**: {RANDOM_SEED}")
    lines.append(f"- **Cross-validation**: 5-fold shuffled KFold")
    lines.append("")
    lines.append("## Validation-Based Selection")
    lines.append("")
    lines.append(
        "Four models were evaluated with 5-fold CV. The selection criterion "
        "was the lowest mean RMSE across folds."
    )
    lines.append("")
    lines.append("| Model | MAE (MPa) | RMSE (MPa) | R² |")
    lines.append("|-------|-----------|------------|-----|")
    for name in ["MeanBaseline", "Ridge", "RandomForest", "GradientBoosting"]:
        r = cv_results[name]
        lines.append(
            f"| {name} | {r['MAE_mean']:.1f} ± {r['MAE_std']:.1f} "
            f"| {r['RMSE_mean']:.1f} ± {r['RMSE_std']:.1f} "
            f"| {r['R2_mean']:.4f} ± {r['R2_std']:.4f} |"
        )
    lines.append("")
    sel = cv_results[best_model_name]
    lines.append(
        f"**Selected model**: `{best_model_name}` "
        f"(validation RMSE = {sel['RMSE_mean']:.1f} MPa)."
    )
    lines.append("")
    lines.append("### Per-Fold Validation Scores (Selected Model)")
    lines.append("")
    lines.append("| Fold | MAE (MPa) | RMSE (MPa) | R² |")
    lines.append("|------|-----------|------------|-----|")
    for i in range(5):
        fs = sel["fold_scores"][f"fold_{i}"]
        lines.append(
            f"| {i} | {fs['MAE']} | {fs['RMSE']} | {fs['R2']} |"
        )
    lines.append("")
    lines.append("## Reproducibility")
    lines.append("")
    lines.append(
        "1. **Fixed seed**: `random_state=42` is passed to all model "
        "initializations and the KFold splitter."
    )
    lines.append(
        "2. **Deterministic feature construction**: Composition strings are "
        "parsed into element-fraction vectors; the column set is determined "
        "from training data and reused for test data. Columns are sorted "
        "alphabetically."
    )
    lines.append(
        "3. **Single-script execution**: The entire pipeline — from "
        "data loading to output generation — runs in one Python invocation "
        "with no external dependencies beyond scikit-learn, numpy, and pandas."
    )
    lines.append(
        "4. **No hyperparameter tuning**: Models use fixed default-like "
        "parameters. No iterative search was performed."
    )
    lines.append(
        "5. **No multiprocessing**: `n_jobs=1` for RandomForest to ensure "
        "deterministic behavior."
    )
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    lines.append(
        "- **Composition-only features**: The model uses only elemental "
        "fractions as features. It does not account for heat treatment, "
        "processing conditions, grain size, or microstructure, which "
        "significantly affect yield strength."
    )
    lines.append(
        "- **No hyperparameter optimization**: Model parameters were chosen "
        "heuristically (e.g., `n_estimators=200`). Better performance may "
        "be possible with tuning."
    )
    lines.append(
        "- **Small dataset**: 249 training samples with ~20 features leads "
        "to a high feature-to-sample ratio, increasing the risk of "
        "overfitting."
    )
    lines.append(
        "- **Linear additivity assumption**: The model assumes yield "
        "strength is a function of weighted element fractions, ignoring "
        "nonlinear interactions among alloying elements that physical "
        "metallurgy would expect."
    )
    lines.append(
        "- **Test set unavailable**: No ground-truth labels are available "
        "for the test set, so no test-set metrics are reported."
    )
    lines.append(
        "- **Single fold**: Only fold 0 of the Matbench split is evaluated."
    )
    lines.append("")

    report_path = os.path.join(OUT_DIR, "report.md")
    with open(report_path, "w") as f:
        f.write("\n".join(lines))

    print("=" * 60)
    print(f"Pipeline complete.  Best model: {best_model_name}")
    print(f"  Validation RMSE: {sel['RMSE_mean']:.1f} ± {sel['RMSE_std']:.1f} MPa")
    print(f"  Validation MAE:  {sel['MAE_mean']:.1f} ± {sel['MAE_std']:.1f} MPa")
    print(f"  Validation R²:   {sel['R2_mean']:.4f} ± {sel['R2_std']:.4f}")
    print(f"  Predicted {n_test} test samples.")
    print(f"  Wall time:       {wall_elapsed:.2f}s")
    print("=" * 60)
    print(f"Output files in {OUT_DIR}:")
    for fname in ["predictions.csv", "run_metadata.json", "report.md"]:
        fpath = os.path.join(OUT_DIR, fname)
        sz = os.path.getsize(fpath)
        print(f"  {fname}  ({sz} bytes)")


if __name__ == "__main__":
    main()
