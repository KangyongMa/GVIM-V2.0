# Matbench Steels Five-Fold Evaluation

## Protocol

- Dataset: Matbench v0.1 `matbench_steels`, 312 samples.
- Outer evaluation: official Matbench v0.1 predefined split IDs, loaded from
  `matbench_v0.1_validation.json`. These folds correspond to
  `KFold(n_splits=5, shuffle=True, random_state=18012019)`.
- Inner model selection: fixed-seed 5-fold cross-validation on each outer training fold.
- Candidate models: Ridge, Random Forest, and Gradient Boosting.
- Features: composition-derived elemental fractions.
- Selection criterion: lowest inner-validation RMSE.
- Primary reported metric: mean outer-fold MAE.
- Outer test labels were used only by the independent evaluator.

## Outer-Fold Results

| Fold | Train | Test | Selected Model | MAE (MPa) | RMSE (MPa) | R2 |
|---:|---:|---:|---|---:|---:|---:|
| 0 | 249 | 63 | Gradient Boosting | 111.44 | 164.32 | 0.6842 |
| 1 | 249 | 63 | Random Forest | 83.20 | 114.72 | 0.8425 |
| 2 | 250 | 62 | Gradient Boosting | 80.31 | 118.63 | 0.8334 |
| 3 | 250 | 62 | Random Forest | 95.99 | 128.73 | 0.8580 |
| 4 | 250 | 62 | Gradient Boosting | 91.98 | 159.28 | 0.6886 |

## Aggregate Results

| Metric | Mean | Standard Deviation |
|---|---:|---:|
| MAE (MPa) | **92.58** | 12.31 |
| RMSE (MPa) | **137.14** | 23.16 |
| R2 | **0.7813** | 0.0871 |

All 312 samples appear in exactly one outer test fold. The independent evaluator
verified complete prediction coverage and reproduced the aggregate metrics.

## Interpretation

The workflow selected different model families across folds, demonstrating
validation-driven model selection rather than use of one predetermined model.
These results support the case-study claim that the system can organize and
execute a reproducible materials-property modeling workflow. They should not be
described as a state-of-the-art Matbench result without direct comparison to
published leaderboard methods under the same protocol.
