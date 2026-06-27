# Matbench Materials Property Modeling Demo

Task: `matbench_expt_gap`, experimental band gap regression from composition.

This run is a local reference execution for the first DeerFlow showcase demo.
It follows the Matbench regression fold rule documented for Matbench v0.1:
`KFold(n_splits=5, shuffle=True, random_state=18012019)`.

## Model

- Formula parser with elemental-fraction and simple composition statistics.
- ExtraTreesRegressor.

## Metrics

- MAE: 0.4726 eV
- RMSE: 0.8518 eV
- R2: 0.6503

MAE is the Matbench v0.1 regression score. RMSE and R2 are standard
regression metrics reported alongside it.

## Front-End Package

- Input directory: `E:\Demo of GVIM\deer-flow-mainnew\research-demos\showcase-5\runtime\matbench_materials_property_modeling\input`
- Fold manifest: `E:\Demo of GVIM\deer-flow-mainnew\research-demos\showcase-5\runtime\matbench_materials_property_modeling\input\matbench_expt_gap_5fold_manifest.json`
- Hidden gold CSV: `E:\Demo of GVIM\deer-flow-mainnew\research-demos\showcase-5\runtime\matbench_materials_property_modeling\gold\matbench_expt_gap_5fold_gold.csv`
- Front-end prompt: `E:\Demo of GVIM\deer-flow-mainnew\research-demos\showcase-5\runtime\matbench_materials_property_modeling\frontend_prompt.md`

The hidden gold file should not be uploaded to DeerFlow. It is used only by
the independent evaluator after the front-end run finishes.

## Caveat

This is not a leaderboard submission. It is a reproducible model run
designed to validate the DeerFlow end-to-end workflow with public Matbench
data and standard regression metrics.
