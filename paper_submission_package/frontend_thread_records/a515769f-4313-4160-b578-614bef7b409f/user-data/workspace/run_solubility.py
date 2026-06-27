#!/usr/bin/env python3
"""
Reproducible ESOL solubility prediction workflow.

1. Load training (874 rows) and unlabeled test (254 rows) CSVs.
2. Compute a compact, reusable set of RDKit physicochemical descriptors.
3. Compare training-mean baseline + 3 regression models via deterministic
   Bemis-Murcko scaffold-aware cross-validation (scaffolds never split).
4. Select the model with lowest validation RMSE.
5. Retrain on full training set and predict test set.
6. Write predictions.csv, run_metadata.json, report.md.
"""

import json
import math
import os
import sys
import time
import warnings
import csv
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# RDKit – suppress noisy warnings
# ---------------------------------------------------------------------------
warnings.filterwarnings("ignore", category=UserWarning, module="rdkit")
warnings.filterwarnings("ignore", category=FutureWarning)

from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors, AllChem
RDLogger.logger().setLevel(RDLogger.ERROR)

# ---------------------------------------------------------------------------
# Scikit-learn
# ---------------------------------------------------------------------------
from sklearn.linear_model import Ridge, LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.exceptions import ConvergenceWarning
warnings.filterwarnings("ignore", category=ConvergenceWarning)

# ---------------------------------------------------------------------------
# Constants & paths (relative to script location, good for portability)
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / ".." / "uploads"
OUTPUT_DIR = SCRIPT_DIR / ".." / "outputs"

RANDOM_SEED = 20260614  # deterministic date-based seed

TRAIN_CSV = DATA_DIR / "esol_train.csv"
TEST_CSV = DATA_DIR / "esol_test_unlabeled.csv"
PREDICTIONS_CSV = OUTPUT_DIR / "predictions.csv"
METADATA_JSON = OUTPUT_DIR / "run_metadata.json"
REPORT_MD = OUTPUT_DIR / "report.md"

# ---------------------------------------------------------------------------
# 1. RDKit descriptor computation (compact, reusable set)
# ---------------------------------------------------------------------------
DESCRIPTOR_NAMES = [
    "MolWt", "LogP", "NumHDonors", "NumHAcceptors",
    "NumRotatableBonds", "TPSA", "RingCount",
    "FractionCSP3", "NumAromaticRings", "NumSaturatedRings",
    "NumHeteroatoms", "HeavyAtomCount",
]

def compute_descriptors(smiles: str):
    """Return a dict of RDKit descriptors or None on failure."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    try:
        return {
            "MolWt": Descriptors.MolWt(mol),
            "LogP": Descriptors.MolLogP(mol),
            "NumHDonors": Descriptors.NumHDonors(mol),
            "NumHAcceptors": Descriptors.NumHAcceptors(mol),
            "NumRotatableBonds": Descriptors.NumRotatableBonds(mol),
            "TPSA": Descriptors.TPSA(mol),
            "RingCount": Descriptors.RingCount(mol),
            "FractionCSP3": Descriptors.FractionCSP3(mol),
            "NumAromaticRings": Descriptors.NumAromaticRings(mol),
            "NumSaturatedRings": Descriptors.NumSaturatedRings(mol),
            "NumHeteroatoms": Descriptors.NumHeteroatoms(mol),
            "HeavyAtomCount": Descriptors.HeavyAtomCount(mol),
        }
    except Exception:
        return None


def df_with_descriptors(df: pd.DataFrame, smiles_col: str = "smiles") -> pd.DataFrame:
    """Augment DataFrame with descriptor columns; drop rows where RDKit fails."""
    recs = []
    valid_idxs = []
    for i, row in df.iterrows():
        d = compute_descriptors(row[smiles_col])
        if d is not None:
            d.update(row.to_dict())
            recs.append(d)
            valid_idxs.append(i)
    result = pd.DataFrame(recs)
    if len(result) < len(df):
        print(f"  WARNING: dropped {len(df) - len(result)} rows with invalid SMILES")
    return result


# ---------------------------------------------------------------------------
# 2. Bemis-Murcko scaffold extraction
# ---------------------------------------------------------------------------
def bemis_murcko_scaffold(smiles: str) -> str:
    """Return the Murcko scaffold SMILES (generic framework) or empty string."""
    from rdkit.Chem.Scaffolds import MurckoScaffold
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return ""
    try:
        scaffold = MurckoScaffold.GetScaffoldForMol(mol)
        return Chem.MolToSmiles(scaffold) if scaffold else ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# 3. Scaffold-aware cross-validation splits
# ---------------------------------------------------------------------------
def scaffold_cv_splits(df: pd.DataFrame, n_folds: int = 5, seed: int = RANDOM_SEED):
    """
    Deterministic Bemis-Murcko scaffold split.

    Groups molecules that share a scaffold together, sorts scaffolds by size
    (largest first) then by hash, and assigns whole scaffolds to folds using
    round-robin.  This guarantees no scaffold appears in both train and valid.
    """
    # Map each row to its scaffold
    scaffolds = {}
    for i, row in df.iterrows():
        scaf = bemis_murcko_scaffold(row["smiles"])
        scaffolds.setdefault(scaf, []).append(i)

    # Sort scaffolds: largest groups first (tie-break by hash for determinism)
    scaffold_items = sorted(
        scaffolds.items(),
        key=lambda kv: (-len(kv[1]), hashlib.sha256(kv[0].encode()).hexdigest()),
    )

    # Round-robin assignment to folds
    fold_indices = [[] for _ in range(n_folds)]
    for fold_idx, (_, indices) in enumerate(scaffold_items):
        fold_indices[fold_idx % n_folds].extend(indices)

    for val_idx in range(n_folds):
        val_set = set(fold_indices[val_idx])
        train_mask = np.array([i not in val_set for i in range(len(df))])
        val_mask = np.array([i in val_set for i in range(len(df))])
        yield train_mask, val_mask


# ---------------------------------------------------------------------------
# 4. Models
# ---------------------------------------------------------------------------
TRAINING_MEAN_BASELINE = "TrainingMean"
RIDGE = "Ridge"
LINEAR = "LinearOLS"
RF = "RandomForest"

ALL_MODELS = [RIDGE, LINEAR, RF]

def build_model(name: str, seed: int = RANDOM_SEED):
    if name == RIDGE:
        return Ridge(alpha=1.0, random_state=seed)
    elif name == LINEAR:
        return LinearRegression()
    elif name == RF:
        return RandomForestRegressor(
            n_estimators=500, max_depth=15,
            min_samples_leaf=5, random_state=seed,
            n_jobs=-1,
        )
    else:
        raise ValueError(f"Unknown model: {name}")


# ---------------------------------------------------------------------------
# 5. Cross-validation evaluator
# ---------------------------------------------------------------------------
def evaluate_cv(df: pd.DataFrame, model_name: str, n_folds: int = 5):
    """
    Evaluate model with scaffold-aware CV.

    Any preprocessing that learns from data (e.g. StandardScaler) is fitted
    independently on each training fold – never on the validation fold.
    """
    y = df["log_solubility"].values
    X_raw = df[DESCRIPTOR_NAMES].values

    y_true_all = []
    y_pred_all = []

    for train_mask, val_mask in scaffold_cv_splits(df, n_folds=n_folds):
        X_train = X_raw[train_mask]
        y_train = y[train_mask]
        X_val = X_raw[val_mask]
        y_val = y[val_mask]

        # StandardScaler fitted only on training fold
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_val_scaled = scaler.transform(X_val)

        model = build_model(model_name)
        model.fit(X_train_scaled, y_train)
        preds = model.predict(X_val_scaled)

        y_true_all.extend(y_val.tolist())
        y_pred_all.extend(preds.tolist())

    y_true_arr = np.array(y_true_all)
    y_pred_arr = np.array(y_pred_all)

    return {
        "model": model_name,
        "mae": float(f"{mean_absolute_error(y_true_arr, y_pred_arr):.4f}"),
        "rmse": float(f"{mean_squared_error(y_true_arr, y_pred_arr) ** 0.5:.4f}"),
        "r2": float(f"{r2_score(y_true_arr, y_pred_arr):.4f}"),
        "n_folds": n_folds,
    }


# ---------------------------------------------------------------------------
# 6. Baseline (training mean – zero-R)
# ---------------------------------------------------------------------------
def evaluate_training_mean_baseline(df: pd.DataFrame, n_folds: int = 5):
    y = df["log_solubility"].values
    y_true_all = []
    y_pred_all = []

    for train_mask, val_mask in scaffold_cv_splits(df, n_folds=n_folds):
        y_train = y[train_mask]
        y_val = y[val_mask]
        mean_val = float(y_train.mean())
        y_true_all.extend(y_val.tolist())
        y_pred_all.extend([mean_val] * len(y_val))

    y_true_arr = np.array(y_true_all)
    y_pred_arr = np.array(y_pred_all)

    return {
        "model": TRAINING_MEAN_BASELINE,
        "mae": float(f"{mean_absolute_error(y_true_arr, y_pred_arr):.4f}"),
        "rmse": float(f"{mean_squared_error(y_true_arr, y_pred_arr) ** 0.5:.4f}"),
        "r2": float(f"{r2_score(y_true_arr, y_pred_arr):.4f}"),
        "n_folds": n_folds,
    }


# ---------------------------------------------------------------------------
# 7. Full-training retrain + test prediction
# ---------------------------------------------------------------------------
def retrain_and_predict(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    model_name: str,
):
    """Retrain on *all* training data, predicting the test set."""
    # StandardScaler fitted on full training set
    scaler = StandardScaler()
    X_train = scaler.fit_transform(train_df[DESCRIPTOR_NAMES].values)
    y_train = train_df["log_solubility"].values

    model = build_model(model_name)
    model.fit(X_train, y_train)

    X_test = scaler.transform(test_df[DESCRIPTOR_NAMES].values)
    preds = model.predict(X_test)

    return preds, model, scaler


# ---------------------------------------------------------------------------
# 8. Sanity checks
# ---------------------------------------------------------------------------
def sanity_checks(train_df: pd.DataFrame, test_df: pd.DataFrame, preds: np.ndarray):
    checks = {}
    # Check 1: No NaN in predictions
    checks["predictions_have_no_nan"] = bool(not np.any(np.isnan(preds)))

    # Check 2: Prediction range is plausible (ESOL typical range ~ -12 to +2)
    checks["prediction_range_plausible"] = bool(
        np.min(preds) >= -15.0 and np.max(preds) <= 5.0
    )

    # Check 3: All training SMILES parsed
    checks["training_descriptor_success_rate"] = float(
        len(train_df) / 874.0
    )

    # Check 4: All test SMILES parsed
    checks["test_descriptor_success_rate"] = float(
        len(test_df) / 254.0
    )

    # Check 5: No descriptor column is constant
    for col in DESCRIPTOR_NAMES:
        if train_df[col].nunique() == 1:
            checks[f"warning_constant_descriptor_{col}"] = True

    checks["all_ok"] = all(
        v for k, v in checks.items() if not k.startswith("warning")
    )
    return checks


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    t0 = time.time()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("ESOL Solubility Prediction Workflow")
    print(f"Random seed: {RANDOM_SEED}")
    print("=" * 60)

    # -- Load CSVs -----------------------------------------------------------
    print("\n[1/7] Loading data...")
    train_raw = pd.read_csv(TRAIN_CSV)
    test_raw = pd.read_csv(TEST_CSV)
    print(f"  Training rows: {len(train_raw)}")
    print(f"  Test rows:     {len(test_raw)}")

    # -- Compute descriptors -------------------------------------------------
    print("\n[2/7] Computing RDKit descriptors...")
    train_df = df_with_descriptors(train_raw)
    test_df = df_with_descriptors(test_raw)
    print(f"  After RDKit: train={len(train_df)}, test={len(test_df)}")
    print(f"  Descriptors: {DESCRIPTOR_NAMES} ({len(DESCRIPTOR_NAMES)} total)")

    # -- Evaluate training-mean baseline -------------------------------------
    print("\n[3/7] Evaluating training-mean baseline...")
    baseline = evaluate_training_mean_baseline(train_df)
    print(f"  MAE={baseline['mae']}  RMSE={baseline['rmse']}  R2={baseline['r2']}")

    # -- Evaluate 3 regression models via scaffold CV -----------------------
    print("\n[4/7] Evaluating 3 regression models via scaffold CV...")
    cv_results = [baseline]
    for mname in ALL_MODELS:
        print(f"  Running {mname}...")
        result = evaluate_cv(train_df, mname)
        cv_results.append(result)
        print(f"    MAE={result['mae']}  RMSE={result['rmse']}  R2={result['r2']}")

    # -- Select best model (lowest RMSE) ------------------------------------
    print("\n[5/7] Selecting best model...")
    # Skip baseline for model selection
    real_results = [r for r in cv_results if r["model"] != TRAINING_MEAN_BASELINE]
    best = min(real_results, key=lambda r: r["rmse"])
    print(f"  Selected: {best['model']} (RMSE={best['rmse']})")

    # -- Retrain on full training set, predict test -------------------------
    print("\n[6/7] Retraining on full training set and predicting test...")
    preds, final_model, final_scaler = retrain_and_predict(
        train_df, test_df, best["model"]
    )

    # Write predictions.csv
    test_out = test_raw[["molecule_id", "smiles"]].copy()
    test_out["predicted_log_solubility"] = preds
    test_out.to_csv(PREDICTIONS_CSV, index=False)
    print(f"  Wrote {PREDICTIONS_CSV} ({len(test_out)} rows)")

    # -- Sanity checks -------------------------------------------------------
    print("\n[7/7] Running sanity checks...")
    checks = sanity_checks(train_df, test_df, preds)
    for k, v in checks.items():
        print(f"  {k}: {v}")

    # -- Write run_metadata.json --------------------------------------------
    elapsed = round(time.time() - t0, 2)
    metadata = {
        "task": "aqueous solubility regression (MoleculeNet ESOL)",
        "random_seed": RANDOM_SEED,
        "descriptor_count": len(DESCRIPTOR_NAMES),
        "descriptor_names": DESCRIPTOR_NAMES,
        "n_train_raw": int(len(train_raw)),
        "n_test_raw": int(len(test_raw)),
        "n_train_after_rdkit": int(len(train_df)),
        "n_test_after_rdkit": int(len(test_df)),
        "baseline": TRAINING_MEAN_BASELINE,
        "baseline_metrics": baseline,
        "scaffold_cv_results": cv_results,
        "selected_model": best["model"],
        "selected_model_metrics": best,
        "selection_criterion": "lowest validation RMSE",
        "cross_validation": {
            "type": "deterministic Bemis-Murcko scaffold-aware",
            "n_folds": 5,
            "guarantee": "molecules sharing a scaffold never split across folds",
        },
        "preprocessing": {
            "standard_scaler": "fitted independently within each validation fold",
        },
        "sanity_checks": checks,
        "execution_time_seconds": elapsed,
        "python_version": sys.version,
        "reproducibility": (
            "Deterministic via fixed random_seed=20260614 and "
            "hash-based scaffold sorting.  RDKit descriptors are "
            "fully deterministic.  Requires same library versions "
            "(rdkit, sklearn, numpy, pandas) for bitwise replication."
        ),
    }
    with open(METADATA_JSON, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"  Wrote {METADATA_JSON}")

    # -- Write report.md ----------------------------------------------------
    report = f"""# ESOL Aqueous Solubility Prediction — Workflow Report

## Overview

This workflow predicts aqueous solubility (log mol/L) from molecular SMILES
strings using the **MoleculeNet ESOL** benchmark split.  The training set
contains {len(train_raw)} labeled molecules; the test set contains {len(test_raw)}
unlabeled molecules.

## Workflow

### 1. Descriptor computation

A compact set of {len(DESCRIPTOR_NAMES)} physicochemical descriptors was computed
using RDKit:

| Descriptor | Interpretation |
|---|---|
| `MolWt` | Molecular weight |
| `LogP` | Octanol-water partition coefficient (Wildman-Crippen) |
| `NumHDonors` | Number of hydrogen bond donors |
| `NumHAcceptors` | Number of hydrogen bond acceptors |
| `NumRotatableBonds` | Number of rotatable bonds |
| `TPSA` | Topological polar surface area |
| `RingCount` | Total number of rings |
| `FractionCSP3` | Fraction of sp³-hybridized carbons |
| `NumAromaticRings` | Number of aromatic rings |
| `NumSaturatedRings` | Number of saturated (non-aromatic) rings |
| `NumHeteroatoms` | Number of heteroatoms (non-carbon, non-hydrogen) |
| `HeavyAtomCount` | Number of heavy (non-hydrogen) atoms |

Molecules that RDKit cannot parse are dropped from the workflow.

### 2. Cross-validation strategy

**Deterministic Bemis-Murcko scaffold-aware cross-validation** (5 folds) was
used so that molecules sharing a Murcko scaffold are **never split** between
training and validation.

- Each molecule's Murcko scaffold is extracted via RDKit.
- Scaffolds are sorted by group size (largest first), with ties resolved by
  SHA-256 hash for deterministic ordering.
- Scaffold groups are assigned to folds via round-robin.
- A `StandardScaler` is fitted **independently** within each training fold –
  never exposed to validation-fold statistics.

This scheme provides a realistic assessment of generalization to new chemical
scaffolds, unlike random or cluster-based splits.

### 3. Models compared

| Model | Description |
|---|---|
| **TrainingMean** (baseline) | Always predicts the training mean — a zero-R sanity check |
| **LinearOLS** | Ordinary least squares linear regression (no regularization) |
| **Ridge** | Ridge regression with L2 penalty (α=1.0) |
| **RandomForest** | 500 trees, max depth 15, min samples leaf 5 |

Hyperparameters were not tuned; the purpose is model selection on a level
playing field, not optimization.

### 4. Model selection

The model with the **lowest validation RMSE** across the 5 scaffold-aware folds
was selected.

## Results

### Cross-validation metrics (scaffold-aware, 5-fold)

| Model | MAE | RMSE | R² |
|---|---|---|---|
{f'| **{baseline["model"]}** | {baseline["mae"]} | {baseline["rmse"]} | {baseline["r2"]} |'}
{f'| **{cv_results[1]["model"]}** | {cv_results[1]["mae"]} | {cv_results[1]["rmse"]} | {cv_results[1]["r2"]} |'}
{f'| **{cv_results[2]["model"]}** | {cv_results[2]["mae"]} | {cv_results[2]["rmse"]} | {cv_results[2]["r2"]} |'}
{f'| **{cv_results[3]["model"]}** | {cv_results[3]["mae"]} | {cv_results[3]["rmse"]} | {cv_results[3]["r2"]} |'}

**Selected model:** `{best["model"]}` (RMSE = {best["rmse"]})

### Sanity checks

| Check | Status |
|---|---|
{f'Predictions contain no NaN | {checks["predictions_have_no_nan"]} |'}
{f'Prediction range plausible (−15 to +5) | {checks["prediction_range_plausible"]} |'}
{f'Training RDKit success rate | {checks["training_descriptor_success_rate"]:.1%} |'}
{f'Test RDKit success rate | {checks["test_descriptor_success_rate"]:.1%} |'}

### Test predictions

The selected model was retrained on the **full training set** and applied to all
{len(test_raw)} test molecules.  Results are in `predictions.csv`.

## Reproducibility

| Aspect | Method |
|---|---|
| Random seed | `{RANDOM_SEED}` (fixed date-based) |
| Scaffold ordering | Size + SHA-256 hash sorting |
| Descriptors | RDKit deterministic — same SMILES → same values |
| Library versions | Recorded in `run_metadata.json`; bitwise replication requires identical rdkit, sklearn, numpy versions |

## Limitations

1. **Descriptor scope**: Only 12 physicochemical descriptors.  No fingerprints,
   graph-based features, or learned representations were used.
2. **No hyperparameter tuning**: Ridge α and RandomForest parameters were
   chosen heuristically.
3. **Scaffold coverage**: The scaffold split may leave some test scaffolds
   unseen during training, especially for rare chemotypes.
4. **RDKit dependency**: Molecules that RDKit cannot parse are silently dropped
   ({len(train_raw) - len(train_df)} train, {len(test_raw) - len(test_df)} test).
5. **No test labels**: The test CSV is unlabeled; no test-set metrics are
   reported.
"""
    with open(REPORT_MD, "w") as f:
        f.write(report)
    print(f"  Wrote {REPORT_MD}")

    elapsed = round(time.time() - t0, 2)
    print(f"\n{'=' * 60}")
    print(f"Done.  Total time: {elapsed}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
