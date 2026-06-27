# Stage 1 Report – BACE1 Temporal External Validation

## Overview
**Model selection using ONLY early training data** (document year ≤ 2015).  
External features from late-period compounds (document year ≥ 2018) are predicted without using their labels.

| Property | Value |
|---|---|
| Training compounds | 5296 |
| External compounds | 1598 |
| Features | Morgan FP (radius=2, 1024 bits) + 8 RDKit descriptors → 1032 total |
| CV strategy | 3-fold GroupKFold grouped by murcko_scaffold (seed=42) |
| Candidate models | Ridge, RandomForestRegressor, ExtraTreesRegressor |
| Selection metric | Lowest mean validation MAE |
| **Selected model** | **RandomForest** |

## Cross-Validation Results

| Model | Mean MAE | Mean RMSE | Mean R² |
|---|---|---|---|
| Ridge | 0.6762 | 0.8720 | 0.4664 |
| RandomForest | 0.5787 | 0.7564 | 0.5985 |
| ExtraTrees | 0.6280 | 0.8358 | 0.5093 |

## Feature Engineering
- **Morgan fingerprints**: radius=2, 1024 bits (ECFP-like topological hashed fingerprints)
- **Lightweight RDKit descriptors** (8): MolWt, MolLogP, NumHDonors, NumHAcceptors, TPSA, NumRotatableBonds, NumAromaticRings, NumAliphaticRings
- Total feature dimensions: 1032

## External Predictions
- **1598** late-period compounds predicted using RandomForest (refit on all 5296 training compounds)
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
