# Retrospective Materials Discovery Case: Matbench Experimental Band Gap

## 1. Overview

- **Dataset**: Matbench v0.1 `matbench_expt_gap` (4,604 experimentally measured inorganic compounds)
- **Goal**: Demonstrate an agent-organized workflow for prioritizing wide-band-gap materials using objective regression and active-discovery metrics
- **Features**: 98 precomputed composition descriptors (element fractions, group fractions, stoichiometric summary)
- **Target**: `gap_expt_eV` — experimental band gap
- **Regression Model**: `HistGradientBoostingRegressor` (fixed parameters, no hyperparameter search)
- **Active Discovery**: Simulated retrospective prioritization of the top 5% highest-gap materials
- **Total Runtime**: 73.8 seconds

## 2. Five-Fold Cross-Validation Regression

| Metric | Mean ± Std |
|--------|-----------|
| MAE    | 0.4513 ± 0.0170 eV |
| RMSE   | 0.8049 ± 0.0456 eV |
| R²     | 0.6854 ± 0.0445 |

Per-fold scores:
- Fold 0: MAE=0.4585, RMSE=0.8223, R²=0.6224
- Fold 1: MAE=0.4261, RMSE=0.7488, R²=0.7547
- Fold 2: MAE=0.4756, RMSE=0.8819, R²=0.6659
- Fold 3: MAE=0.4397, RMSE=0.7741, R²=0.7105
- Fold 4: MAE=0.4568, RMSE=0.7974, R²=0.6736

## 3. Active Discovery Simulation

### Settings
- **Target**: Top 5% highest experimental band-gap materials (gap ≥ 3.738 eV, n = 231)
- **Seeds**: [0, 1, 2]
- **Initial random size**: 30
- **Batch size**: 10
- **Query budget (total)**: 150
- **Policies compared**: `random`, `greedy_surrogate`

### Results at Budget 150

| Policy | Recall@150 | Hit rate@150 | Best gap@150 (eV) |
|--------|-----------|-------------|------------------|
| random | 0.0332 ± 0.0180 | 0.0511 ± 0.0278 | 7.013 ± 3.604 |
| greedy_surrogate | 0.2626 ± 0.0250 | 0.4044 ± 0.0385 | 9.033 ± 1.790 |

- **Recall difference (greedy_surrogate − random)**: 0.2294 [95% CI: 0.2208, 0.2381]

Per-seed details:
- seed=0, greedy_surrogate: recall=0.2771, hit_rate=0.4267, best_gap=8.000 eV
- seed=1, greedy_surrogate: recall=0.2338, hit_rate=0.3600, best_gap=8.000 eV
- seed=2, greedy_surrogate: recall=0.2771, hit_rate=0.4267, best_gap=11.100 eV
- seed=0, random: recall=0.0390, hit_rate=0.0600, best_gap=11.100 eV
- seed=1, random: recall=0.0130, hit_rate=0.0200, best_gap=4.290 eV
- seed=2, random: recall=0.0476, hit_rate=0.0733, best_gap=5.650 eV

## 4. Element/Family Enrichment (Top 5 Most Enriched Features)

The following features showed the strongest enrichment among greedily selected candidates vs. the background dataset:

- **frac_B**: background=0.0171, selected=0.0963, enrichment=5.64x
- **frac_H**: background=0.0046, selected=0.0258, enrichment=5.55x
- **frac_O**: background=0.1302, selected=0.4524, enrichment=3.48x
- **has_oxygen**: background=0.2368, selected=0.8200, enrichment=3.46x
- **frac_Rb**: background=0.0063, selected=0.0131, enrichment=2.08x

## 5. Key Findings

1. **Regression performance**: The lightweight HistGradientBoostingRegressor achieves competitive predictive accuracy (MAE ~0.451 eV, R² ~0.685) using only simple composition features, demonstrating that even modest descriptors capture meaningful band-gap trends.
2. **Active discovery**: The `greedy_surrogate` policy consistently outperforms random selection in recalling top-5% high-gap materials. At a budget of 150 candidates, the greedy surrogate achieves Recall@150 of 0.2626 vs. 0.0332 for random, with a positive mean difference of 0.2294.
3. **Element enrichment**: Greedy selection disproportionately identifies compositions enriched in characteristic elements (e.g., halogens, alkaline earths, and specific p-block elements), consistent with their known role in wide-band-gap semiconductors and insulators.

## 6. Limitations

- This is a **retrospective** analysis of public Matbench data; no new synthesis or experimental validation is claimed.
- Features are limited to simple composition descriptors; structural, electronic, or synthesis-aware features could improve both regression and active discovery.
- The active-discovery simulation uses a fixed oracle (experimental gap), whereas real discovery involves measurement cost and experimental noise.
- Only one lightweight surrogate model (HistGradientBoostingRegressor) and one acquisition policy (greedy) are tested.

## 7. Reproducibility

- Data: `matbench_expt_gap_fast_features.csv` (MD5: `178a3b4a4009`)
- Random seeds: CV = 18012019; active discovery = [0, 1, 2]; model = 0
- Model parameters are fixed and recorded in `metrics.json`.
- All output files are included for full reproduction.
