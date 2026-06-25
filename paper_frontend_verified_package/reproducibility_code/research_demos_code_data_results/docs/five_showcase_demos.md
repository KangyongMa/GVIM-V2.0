# Five Chemistry and Materials Showcase Demos

## Selection Criteria

These demos are chosen to show system-level capability, not another question
bank score. A demo is included only if it can show at least four of the
following DeerFlow features:

- front-end initiated workflow;
- scientific file upload or document upload;
- agent planning and multi-step execution;
- domain tools such as RDKit, pymatgen, XRD, literature extraction, or
  scikit-learn;
- code execution and reproducible artifacts;
- automatic repair or failure reporting;
- objective metrics used in public benchmarks or standard scientific ML.

## Evaluation Philosophy From the Two Reference Papers

The two local reference papers should guide how the demos are reported:

- `Paper/d5sc08794e.pdf` treats the agent as the organizer of experimental
  planning, simulation, spectral data generation, and machine-learning analysis.
  The scientific claim is then supported by quantitative model performance:
  MAE for C-N=N-C dihedral-angle prediction, correlation/Pearson r, and
  ablation or transfer-learning curves. Our spectroscopy and ML demos should
  follow the same pattern: DeerFlow plans and executes the workflow, but the
  evidence is the final prediction error and reproducible artifacts.
- `Paper/d5sc09921h.pdf` treats the agent as a workflow for converting
  literature into a reliable materials dataset. It evaluates extraction by
  matching AI-extracted records against manually annotated records, separating
  accuracy and completeness, and using precision, recall, and F1 for
  caption/figure identification. Our literature extraction, XRD, and screening
  demos should follow this pattern: DeerFlow may plan and call tools, but the
  claim is supported by field-level precision/recall/F1, coverage, exact match,
  numeric error, or top-k retrieval accuracy.

Therefore, each showcase demo reports two layers separately:

1. **Workflow reliability:** front-end submission success, tool-call coverage,
   artifact generation success, JSON/CSV parse rate, execution success, and
   repair success where applicable.
2. **Scientific result quality:** task-native metrics such as MAE, RMSE, R2,
   Pearson r, ROC-AUC, F1, precision, recall, top-k accuracy, and numeric
   extraction error.

Only the second layer should be used to argue that the produced chemistry or
materials result is scientifically useful. The first layer explains how well
DeerFlow completed the end-to-end workflow.

## 1. Unknown-Material XRD Phase Identification

**Domain:** Materials characterization.

**Public task family:** XRD phase retrieval and materials characterization.

**Front-end input:** The user uploads one observed XRD peak table and several
candidate CIF files, then asks DeerFlow to identify the most likely phase.

**Agent execution chain:** DeerFlow detects the file types, parses each CIF,
checks structure validity, simulates Cu K-alpha powder XRD, matches observed
and simulated peaks, ranks candidate phases, plots the overlay, and writes a
short report that distinguishes phase-triage from proof of phase purity.

**Outputs:** `candidate_ranking.csv`, `xrd_overlay.png`,
`xrd_match_report.md`, `metrics.json`.

**Evaluation metrics:** top-1 accuracy, top-k accuracy, precision, recall,
peak-position MAE, artifact generation success rate, and tool-selection F1.
These are standard retrieval, classification, and peak-matching metrics rather
than subjective scores.

**Reliability interpretation:** top-k accuracy and peak-position MAE support
the phase-ranking result; tool-selection F1 and artifact success only describe
whether DeerFlow executed the workflow correctly.

**Why it fits DeerFlow:** This is the most visually compelling materials demo:
front-end upload, materials structure parsing, XRD simulation, candidate
ranking, visualization, and scientific boundary-setting all happen in one
workflow.

## 2. Matbench-Style Materials Property Modeling

**Domain:** Materials machine learning.

**Public task family:** Matbench materials property prediction.

**Front-end input:** The user uploads a frozen Matbench-style dataset and split,
then asks DeerFlow to train and evaluate a baseline model.

**Agent execution chain:** DeerFlow inspects the schema, identifies whether the
task is regression or classification, builds composition or structure features,
trains reproducible scikit-learn baselines, saves predictions, generates plots,
and reports failure cases.

**Outputs:** `predictions.csv`, `metrics.json`, `model_report.md`,
`parity_or_roc_plot.png`.

**Evaluation metrics:** Matbench reports MAE for regression and ROC-AUC for
classification. For richer diagnostics we can also report RMSE, R2, accuracy,
and F1, but MAE or ROC-AUC remains the primary metric according to task type.

**Reliability interpretation:** model performance on the held-out split is the
scientific evidence. Execution success and artifact parse rate are reported
separately as agent workflow reliability.

**Why it fits DeerFlow:** This demonstrates that DeerFlow can operate as a
materials ML research assistant rather than a question-answering model.

## 3. MoleculeNet Molecular Property Workflow

**Domain:** Chemistry and molecular ML.

**Public task family:** MoleculeNet molecular property prediction.

**Front-end input:** The user uploads a MoleculeNet-style dataset such as BBBP,
HIV, ClinTox, Tox21, ESOL, or FreeSolv, with a fixed train/test split.

**Agent execution chain:** DeerFlow validates SMILES, computes RDKit
descriptors or Morgan fingerprints, trains a baseline model, saves held-out
predictions or probabilities, generates ROC/PR or parity plots, and writes an
error analysis for misclassified or high-error molecules.

**Outputs:** `molecular_predictions.csv`, `molecular_metrics.json`,
`roc_pr_or_parity_plot.png`, `error_analysis.md`.

**Evaluation metrics:** MoleculeNet recommends ROC-AUC or PR-AUC for
classification and RMSE or MAE for regression. Accuracy and F1 can be reported
as secondary metrics for thresholded classification.

**Reliability interpretation:** ROC-AUC/PR-AUC or RMSE/MAE support the
chemical prediction result; valid-SMILES rate and tool coverage diagnose
whether the chemistry workflow was executed correctly.

**Why it fits DeerFlow:** It shows chemistry-specific modeling through RDKit
and reproducible ML, rather than relying on the language model's chemical
intuition.

## 4. IR/Raman Spectra to Structure-Parameter Regression

**Domain:** Chemical spectroscopy and structure-property analysis.

**Public task family:** Spectroscopy-to-structure regression, aligned with the
azobenzene spectra-to-dihedral paper in the local `Paper/` directory.

**Front-end input:** The user uploads paired IR/Raman spectra and target
dihedral angles, then asks DeerFlow to build a regression workflow.

**Agent execution chain:** DeerFlow inspects the spectral matrix, preprocesses
features, chooses a regression model, runs cross-validation or held-out
testing, saves predictions, plots predicted vs. true structure parameters, and
summarizes the most informative spectral regions.

**Outputs:** `spectra_predictions.csv`, `spectra_metrics.json`,
`parity_plot.png`, `spectral_regions_report.md`.

**Evaluation metrics:** MAE and Pearson correlation are used in the source
paper; RMSE and R2 are standard regression diagnostics and should be reported
alongside them.

**Reliability interpretation:** this is the closest demo to
`d5sc08794e.pdf`. DeerFlow's value is demonstrated if it can autonomously
produce the prediction table, parity plot, and metrics, while the scientific
quality is judged by MAE, RMSE, R2, and Pearson r.

**Why it fits DeerFlow:** This is a real chemistry research workflow:
spectral data become a structural prediction, with interpretable outputs and
paper-compatible metrics.

## 5. Literature Extraction to Structured Dataset

**Domain:** Chemistry/materials literature mining.

**Public task family:** Chemical and materials information extraction from
papers, tables, captions, and supplementary information.

**Front-end input:** The user uploads a chemistry/materials article PDF,
supplementary Markdown, or a batch of converted snippets and asks DeerFlow to
extract structured records.

**Agent execution chain:** DeerFlow parses the document, identifies sections,
tables, captions, units, formulas, compounds, properties, conditions, and
source locations, normalizes values, validates formulas or structures where
possible, and exports the dataset plus an audit report.

**Outputs:** `extracted_records.csv`, `extracted_records.json`,
`extraction_audit.md`, `extraction_metrics.json`.

**Evaluation metrics:** field-level precision, recall, F1, record exact match,
numeric MAE, unit-normalization accuracy, and source-span hit rate. These
follow standard information extraction practice and align with DIVE-style
accuracy/completeness evaluation.

**Reliability interpretation:** this is the closest demo to
`d5sc09921h.pdf`. Completeness/recall measures how much of the target dataset
DeerFlow recovered, while precision and numeric MAE penalize hallucinated or
incorrect extracted records.

**Why it fits DeerFlow:** This is the best long-workflow capstone: it combines
document understanding, chemistry/materials normalization, provenance tracking,
and optional downstream modeling.

## Reporting Policy

Do not merge these five demos into the existing 400-question score. Report them
as a separate "front-end scientific workflow" evaluation with:

- per-demo native metrics;
- front-end HTTP success rate;
- JSON/CSV artifact parse rate;
- tool-selection and parameter F1 where a gold tool chain exists;
- execution success and repair success for code-heavy workflows;
- latency and generated artifact inventory;
- failure-case analysis.

The main manuscript or demo report should phrase the claim as:

> DeerFlow is evaluated as a planning and tool-orchestration system for
> chemistry/materials workflows. The system value is supported by the final
> task outputs, measured using standard prediction, retrieval, and extraction
> metrics, not by subjective judgments of answer quality.

This separation is important: the 400-question score answers "does the system
know chemistry/materials facts?", while these demos answer "can the system
perform chemistry/materials research work from the front end?"
