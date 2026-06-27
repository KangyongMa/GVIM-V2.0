# Alignment With Two Reference Papers

This note clarifies how the five DeerFlow showcase demos should borrow the
evaluation logic of the two local reference papers:

- `Paper/d5sc08794e.pdf`
- `Paper/d5sc09921h.pdf`

## Shared Principle

Both papers use AI or agentic components as workflow organizers, but they do
not rely on subjective judgments such as "the answer looks good." They support
their claims with objective downstream results:

- prediction error or correlation for machine-learning workflows;
- extraction accuracy, completeness, precision, recall, and F1 for literature
  mining workflows;
- generated datasets or predictions that can be independently checked.

The DeerFlow demos should follow the same separation:

1. **Agent/workflow evidence:** Did DeerFlow start from the front end, plan the
   work, call the correct tools, execute code, recover from failures, and
   produce the required artifacts?
2. **Scientific result evidence:** Are the produced predictions, extracted
   records, phase rankings, or screened candidates correct under standard
   metrics?

## `d5sc08794e.pdf`: Spectra to Structure

The paper connects IR/Raman spectra to molecular structure by predicting the
C-N=N-C dihedral angle. The scientific evidence is quantitative model
performance, especially MAE and correlation/Pearson r, with additional
ablation and transfer-learning analyses.

For DeerFlow, this maps most directly to:

- `spectra_to_structure_regression`
- `matbench_materials_property_modeling`
- `moleculenet_molecular_property_workflow`

Primary metrics:

- MAE
- RMSE
- R2
- Pearson r
- ROC-AUC / PR-AUC for classification tasks

Required artifacts:

- predictions table
- metrics JSON
- parity, ROC, PR, or residual plot
- reproducible code or execution log

## `d5sc09921h.pdf`: Literature to Materials Dataset

The DIVE-style workflow extracts structured materials records from papers and
evaluates extraction by comparing AI-generated records with annotated records.
It separates accuracy and completeness and uses precision, recall, and F1 for
caption/figure identification.

For DeerFlow, this maps most directly to:

- `literature_extraction_to_dataset`
- `materials_xrd_phase_identification`

Primary metrics:

- field precision
- field recall
- field F1
- record exact match
- numeric MAE
- unit-normalization accuracy
- source-span hit rate
- top-k accuracy for retrieval/ranking tasks

Required artifacts:

- extracted records in CSV/JSON
- source-span or page/table trace
- metrics JSON
- extraction audit report

## Recommended Manuscript Wording

Use wording like:

> The proposed demos evaluate DeerFlow as a chemistry/materials workflow
> agent. Following the evaluation philosophy of spectra-to-structure prediction
> and literature-to-dataset extraction studies, DeerFlow is not scored by
> subjective answer quality. Instead, the system is given realistic front-end
> research tasks and judged by the objective quality of its final artifacts:
> prediction error, correlation, classification AUC, extraction precision and
> recall, top-k retrieval accuracy, and artifact execution success.

