"""
BACE1 Temporal External Validation - Stage 1
Feature design + model selection using ONLY early training data.
Predict on late external features (no labels used).
"""
import os, json, hashlib, time, warnings, numpy as np, pandas as pd
from pathlib import Path

warnings.filterwarnings("ignore")

# ── Paths ──────────────────────────────────────────────────────────────────
DATA_DIR = Path(r"E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/2473c8a4-9275-4d73-8c2f-92a8b6472310/threads/9ae4e85f-542b-4f94-9294-81189cf220be/user-data/uploads")
OUT_DIR  = Path(r"E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/2473c8a4-9275-4d73-8c2f-92a8b6472310/threads/9ae4e85f-542b-4f94-9294-81189cf220be/user-data/outputs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

train_file    = DATA_DIR / "bace1_early_training.csv"
ext_file      = DATA_DIR / "bace1_late_external_features.csv"

train = pd.read_csv(train_file)
ext   = pd.read_csv(ext_file)

# ── RDKit imports ──────────────────────────────────────────────────────────
from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, rdMolDescriptors, MolFromSmiles
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold

t0 = time.time()

# ── Feature Engineering ────────────────────────────────────────────────────
def morgan_fp(smiles, radius=2, n_bits=1024):
    mol = MolFromSmiles(smiles)
    if mol is None:
        return np.zeros(n_bits, dtype=np.float32)
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
    return np.array(fp, dtype=np.float32)

def lightweight_rdkit_descriptors(smiles):
    """Compute a small set of interpretable RDKit descriptors."""
    mol = MolFromSmiles(smiles)
    if mol is None:
        return np.zeros(8, dtype=np.float32)
    return np.array([
        Descriptors.MolWt(mol),
        Descriptors.MolLogP(mol),
        Descriptors.NumHDonors(mol),
        Descriptors.NumHAcceptors(mol),
        Descriptors.TPSA(mol),
        rdMolDescriptors.CalcNumRotatableBonds(mol),
        Descriptors.NumAromaticRings(mol),
        Descriptors.NumAliphaticRings(mol),
    ], dtype=np.float32)

def build_feature_matrix(df):
    fps_list, descs_list = [], []
    for smi in df["canonical_smiles"]:
        fps_list.append(morgan_fp(smi))
        descs_list.append(lightweight_rdkit_descriptors(smi))
    X_fp    = np.stack(fps_list, axis=0)    # (N, 1024)
    X_descs = np.stack(descs_list, axis=0)  # (N, 8)
    X = np.concatenate([X_fp, X_descs], axis=1)  # (N, 1032)
    return X

print("Building training feature matrix...")
X_train = build_feature_matrix(train)
y_train = train["pIC50"].values
groups   = train["murcko_scaffold"].values
print(f"  X_train shape: {X_train.shape}, y_train range: {y_train.min():.2f}–{y_train.max():.2f}")

# ── Cross-validation ───────────────────────────────────────────────────────
models = {
    "Ridge": Ridge(alpha=1.0, random_state=42),
    "RandomForest": RandomForestRegressor(
        n_estimators=100, max_depth=None, n_jobs=1, random_state=42
    ),
    "ExtraTrees": ExtraTreesRegressor(
        n_estimators=100, max_depth=None, n_jobs=1, random_state=42
    ),
}

gkf = GroupKFold(n_splits=3)

cv_records = []
for name, model in models.items():
    fold_scores = {"MAE": [], "RMSE": [], "R2": []}
    for fold_idx, (tr_idx, va_idx) in enumerate(gkf.split(X_train, y_train, groups)):
        X_tr, X_va = X_train[tr_idx], X_train[va_idx]
        y_tr, y_va = y_train[tr_idx], y_train[va_idx]
        model.fit(X_tr, y_tr)
        preds = model.predict(X_va)
        fold_scores["MAE"].append(mean_absolute_error(y_va, preds))
        fold_scores["RMSE"].append(np.sqrt(mean_squared_error(y_va, preds)))
        fold_scores["R2"].append(r2_score(y_va, preds))
        cv_records.append({
            "model": name, "fold": fold_idx,
            "MAE": fold_scores["MAE"][-1],
            "RMSE": fold_scores["RMSE"][-1],
            "R2": fold_scores["R2"][-1],
        })
    cv_records.append({
        "model": name, "fold": "mean",
        "MAE": np.mean(fold_scores["MAE"]),
        "RMSE": np.mean(fold_scores["RMSE"]),
        "R2": np.mean(fold_scores["R2"]),
    })
    cv_records.append({
        "model": name, "fold": "std",
        "MAE": np.std(fold_scores["MAE"], ddof=1),
        "RMSE": np.std(fold_scores["RMSE"], ddof=1),
        "R2": np.std(fold_scores["R2"], ddof=1),
    })
    print(f"  {name}: mean_val_MAE={np.mean(fold_scores['MAE']):.4f} ± {np.std(fold_scores['MAE'], ddof=1):.4f}")

cv_results = pd.DataFrame(cv_records)
cv_results.to_csv(OUT_DIR / "cv_results.csv", index=False)
print("  cv_results.csv saved.")

# ── Model Selection ────────────────────────────────────────────────────────
# Summarise mean MAE from folds (not mean/std rows)
fold_mae = {}
for name in models:
    fold_vals = [r["MAE"] for r in cv_records if r["model"] == name and isinstance(r["fold"], int)]
    fold_mae[name] = np.mean(fold_vals)

best_name = min(fold_mae, key=fold_mae.get)
print(f"\nSelected model: {best_name} (mean_val_MAE = {fold_mae[best_name]:.4f})")

model_selection = {
    "best_model": best_name,
    "mean_val_MAE_by_model": fold_mae,
    "cv_splits": 3,
    "cv_strategy": "GroupKFold, grouped by murcko_scaffold",
    "random_seed": 42,
    "features": "Morgan FP (radius 2, 1024 bits) + 8 lightweight RDKit descriptors",
}
with open(OUT_DIR / "model_selection.json", "w") as f:
    json.dump(model_selection, f, indent=2)
print("  model_selection.json saved.")

# ── Refit selected model on ALL early data ─────────────────────────────────
selected_model = models[best_name]
selected_model.fit(X_train, y_train)
print(f"  Refitted {best_name} on all {len(train)} training compounds.")

# ── Baseline: Ridge and mean ───────────────────────────────────────────────
ridge_model = Ridge(alpha=1.0, random_state=42)
ridge_model.fit(X_train, y_train)

mean_baseline = y_train.mean()
print(f"  Mean baseline (training): {mean_baseline:.4f}")

# ── Predict on external features ──────────────────────────────────────────
print("\nBuilding external feature matrix...")
X_ext = build_feature_matrix(ext)
print(f"  X_ext shape: {X_ext.shape}")

pred_selected = selected_model.predict(X_ext)
pred_ridge    = ridge_model.predict(X_ext)
pred_mean     = np.full(len(ext), mean_baseline)

ext_preds = ext[["compound_id"]].copy()
ext_preds["prediction_selected"] = np.round(pred_selected, 4)
ext_preds["prediction_ridge"]    = np.round(pred_ridge, 4)
ext_preds["prediction_mean"]     = np.round(pred_mean, 4)
ext_preds["scaffold_novel"]      = ext["scaffold_novel"].values

ext_preds.to_csv(OUT_DIR / "external_predictions.csv", index=False)
print(f"  external_predictions.csv saved ({len(ext_preds)} rows).")

# ── SHA-256 hash ───────────────────────────────────────────────────────────
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

pred_hash = sha256_file(OUT_DIR / "external_predictions.csv")

# ── Prediction manifest ────────────────────────────────────────────────────
import sklearn
import rdkit

runtime_s = time.time() - t0
manifest = {
    "workflow": "BACE1 Stage 1 – model selection on early training data only",
    "task_manifest": "task_manifest.json (bace1_temporal_external_validation)",
    "training_file": "bace1_early_training.csv",
    "training_n_compounds": len(train),
    "external_feature_file": "bace1_late_external_features.csv",
    "external_n_compounds": len(ext),
    "external_predictions_csv_sha256": pred_hash,
    "external_predictions_csv_columns": list(ext_preds.columns),
    "external_predictions_csv_n_rows": len(ext_preds),
    "selected_model": best_name,
    "selected_model_params": str(selected_model.get_params()),
    "random_seed": 42,
    "cv_strategy": "3-fold GroupKFold by murcko_scaffold",
    "selection_metric": "lowest mean validation MAE",
    "features": "Morgan FP radius=2, 1024bits + 8 RDKit descriptors",
    "package_versions": {
        "python": __import__("sys").version,
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scikit-learn": sklearn.__version__,
        "rdkit": rdkit.__version__,
    },
    "runtime_seconds": round(runtime_s, 2),
    "run_date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "claim_boundary": (
        "Model selection using ONLY early training data. "
        "External-set metrics intentionally excluded in Stage 1."
    ),
}
with open(OUT_DIR / "prediction_manifest.json", "w") as f:
    json.dump(manifest, f, indent=2)
print("  prediction_manifest.json saved.")

# ── CV Model Comparison Figure ────────────────────────────────────────────
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))

metrics = ["MAE", "RMSE", "R2"]
titles  = ["MAE (↓ better)", "RMSE (↓ better)", "R² (↑ better)"]
colors  = {"Ridge": "#4C72B0", "RandomForest": "#DD8452", "ExtraTrees": "#55A868"}

for i, (metric, title) in enumerate(zip(metrics, titles)):
    ax = axes[i]
    plot_data = {}
    for name in models:
        vals = [r[metric] for r in cv_records if r["model"] == name and isinstance(r["fold"], int)]
        plot_data[name] = vals
    positions = np.arange(len(models))
    bp = ax.boxplot(
        [plot_data[name] for name in models],
        positions=positions, widths=0.5, patch_artist=True,
    )
    for patch, name in zip(bp["boxes"], models):
        patch.set_facecolor(colors[name])
        patch.set_alpha(0.7)
    # scatter points
    for j, name in enumerate(models):
        y_vals = plot_data[name]
        x_jitter = np.random.default_rng(42).uniform(-0.1, 0.1, size=len(y_vals))
        ax.scatter(positions[j] + x_jitter, y_vals, color=colors[name],
                   edgecolors="white", s=50, zorder=5)
    ax.set_xticks(positions)
    ax.set_xticklabels(models.keys(), fontsize=10)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_ylabel(metric)

fig.suptitle("Stage 1 – CV Model Comparison (3-fold GroupKFold by Murcko Scaffold, seed=42)",
             fontsize=13, fontweight="bold", y=1.02)
plt.tight_layout()
plt.savefig(OUT_DIR / "figure_cv_model_comparison.png", dpi=200, bbox_inches="tight")
plt.close()
print("  figure_cv_model_comparison.png saved.")

# ── Stage 1 Report ─────────────────────────────────────────────────────────
report = f"""# Stage 1 Report – BACE1 Temporal External Validation

## Overview
**Model selection using ONLY early training data** (document year ≤ 2015).  
External features from late-period compounds (document year ≥ 2018) are predicted without using their labels.

| Property | Value |
|---|---|
| Training compounds | {len(train)} |
| External compounds | {len(ext)} |
| Features | Morgan FP (radius=2, 1024 bits) + 8 RDKit descriptors → 1032 total |
| CV strategy | 3-fold GroupKFold grouped by murcko_scaffold (seed=42) |
| Candidate models | Ridge, RandomForestRegressor, ExtraTreesRegressor |
| Selection metric | Lowest mean validation MAE |
| **Selected model** | **{best_name}** |

## Cross-Validation Results

| Model | Mean MAE | Mean RMSE | Mean R² |
|---|---|---|---|
""" + "\n".join(
    f"| {name} | {fold_mae[name]:.4f} | "
    f"{np.mean([r['RMSE'] for r in cv_records if r['model']==name and isinstance(r['fold'], int)]):.4f} | "
    f"{np.mean([r['R2'] for r in cv_records if r['model']==name and isinstance(r['fold'], int)]):.4f} |"
    for name in models
)

report += f"""

## Feature Engineering
- **Morgan fingerprints**: radius=2, 1024 bits (ECFP-like topological hashed fingerprints)
- **Lightweight RDKit descriptors** (8): MolWt, MolLogP, NumHDonors, NumHAcceptors, TPSA, NumRotatableBonds, NumAromaticRings, NumAliphaticRings
- Total feature dimensions: 1032

## External Predictions
- **{len(ext)}** late-period compounds predicted using {best_name} (refit on all {len(train)} training compounds)
- Ridge regression and mean-baseline predictions also saved for comparison
- Scaffold novelty flag (0/1) from `scaffold_novel` column preserved

## Output Files
| File | Description |
|---|---|
| `external_predictions.csv` | Predictions: selected-model, Ridge, mean-baseline + scaffold_novel |
| `prediction_manifest.json` | Row counts, model info, SHA-256, package versions, runtime |
| `cv_results.csv` | Per-fold CV metrics for all 3 models |
| `model_selection.json` | Best model name and mean MAE summary |
| `figure_cv_model_comparison.png` | Boxplot comparison of 3-fold MAE / RMSE / R² |
| `report_stage1.md` | This report |

## Claim Boundary
Model selection and internal CV use only early-training labels.  
External-set metrics (MAE, RMSE, R², enrichment factors) are **intentionally excluded** in Stage 1.
"""

with open(OUT_DIR / "report_stage1.md", "w") as f:
    f.write(report)
print("  report_stage1.md saved.")

print(f"\n✅ Stage 1 complete. Runtime: {runtime_s:.1f} s")
print(f"   Outputs in: {OUT_DIR}")
