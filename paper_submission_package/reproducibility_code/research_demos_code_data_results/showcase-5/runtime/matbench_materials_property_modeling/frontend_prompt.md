Using the uploaded Matbench `matbench_expt_gap` fold, design and execute a reproducible composition-based regression workflow to predict experimental band gaps.

Treat the uploaded manifest as the authoritative task specification. Train using only the labeled training CSV identified by the manifest, and generate a prediction for every row in the corresponding unlabeled test CSV. Select and justify an appropriate composition featurization method and regression algorithm.

Implement the workflow as a portable Python script with a `main()` function and an `if __name__ == "__main__":` guard; avoid uncontrolled multiprocessing.

Produce the following files:

1. `predictions.csv` with exactly these columns: `fold`, `row_id`, `composition`, `predicted_gap_eV`.
2. `run_metadata.json` recording the selected feature method, model class, model parameters, random seeds, package versions used, input row counts, and execution time.
3. `report.md` describing data inspection, method selection, execution, reproducibility settings, and limitations.

The test CSV is unlabeled. Do not report test-set MAE, RMSE, or R2 values.
