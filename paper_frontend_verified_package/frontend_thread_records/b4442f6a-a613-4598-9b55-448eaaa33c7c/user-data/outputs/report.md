# Steel Yield Strength Prediction — Matbench Fold 0

## Workflow Description

This pipeline predicts steel yield strength (MPa) from composition strings for Matbench fold 0 of the `matbench_steels` benchmark. The workflow is fully reproducible: composition strings are parsed into element-fraction features, three regression models and a training-mean baseline are compared via 5-fold cross-validation, the model with the lowest validation RMSE is selected, retrained on all training data, and used to predict the unlabeled test set.

- **Training samples**: 249
- **Test samples**: 63
- **Features**: 14 element fractions: Al, C, Co, Cr, Fe, Mn, Mo, N, Nb, Ni, Si, Ti, V, W
- **Random seed**: 42
- **Cross-validation**: 5-fold shuffled KFold

## Validation-Based Selection

Four models were evaluated with 5-fold CV. The selection criterion was the lowest mean RMSE across folds.

| Model | MAE (MPa) | RMSE (MPa) | R² |
|-------|-----------|------------|-----|
| MeanBaseline | 225.8 ± 35.9 | 299.1 ± 62.8 | -0.0214 ± 0.0163 |
| Ridge | 202.8 ± 37.2 | 272.9 ± 53.5 | 0.1393 ± 0.1017 |
| RandomForest | 94.3 ± 12.9 | 132.5 ± 18.7 | 0.7809 ± 0.0828 |
| GradientBoosting | 87.8 ± 16.6 | 123.8 ± 21.7 | 0.8192 ± 0.0393 |

**Selected model**: `GradientBoosting` (validation RMSE = 123.8 MPa).

### Per-Fold Validation Scores (Selected Model)

| Fold | MAE (MPa) | RMSE (MPa) | R² |
|------|-----------|------------|-----|
| 0 | 113.3974 | 152.0891 | 0.791489 |
| 1 | 68.7323 | 94.8264 | 0.788372 |
| 2 | 90.3159 | 134.9513 | 0.869082 |
| 3 | 79.2671 | 113.0747 | 0.854505 |
| 4 | 87.2274 | 123.9547 | 0.792557 |

## Reproducibility

1. **Fixed seed**: `random_state=42` is passed to all model initializations and the KFold splitter.
2. **Deterministic feature construction**: Composition strings are parsed into element-fraction vectors; the column set is determined from training data and reused for test data. Columns are sorted alphabetically.
3. **Single-script execution**: The entire pipeline — from data loading to output generation — runs in one Python invocation with no external dependencies beyond scikit-learn, numpy, and pandas.
4. **No hyperparameter tuning**: Models use fixed default-like parameters. No iterative search was performed.
5. **No multiprocessing**: `n_jobs=1` for RandomForest to ensure deterministic behavior.

## Limitations

- **Composition-only features**: The model uses only elemental fractions as features. It does not account for heat treatment, processing conditions, grain size, or microstructure, which significantly affect yield strength.
- **No hyperparameter optimization**: Model parameters were chosen heuristically (e.g., `n_estimators=200`). Better performance may be possible with tuning.
- **Small dataset**: 249 training samples with ~20 features leads to a high feature-to-sample ratio, increasing the risk of overfitting.
- **Linear additivity assumption**: The model assumes yield strength is a function of weighted element fractions, ignoring nonlinear interactions among alloying elements that physical metallurgy would expect.
- **Test set unavailable**: No ground-truth labels are available for the test set, so no test-set metrics are reported.
- **Single fold**: Only fold 0 of the Matbench split is evaluated.
