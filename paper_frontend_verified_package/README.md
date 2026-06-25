# GVIM2.0 Front-End Verified Submission Package

This folder is the consolidated submission and reproducibility package for the GVIM2.0 manuscript. It is organized to keep manuscript files, public figures, front-end execution records, post-hoc public-label scoring, source data, and reproducibility scripts in one auditable location.

## Main Submission Files

- `submission_files/GVIM2.0_frontend_verified.docx`  
  Front-end-verified manuscript draft. Claims about demonstrations are restricted to recorded DeerFlow/GVIM front-end runs or clearly labeled post-hoc scoring of frozen front-end outputs.

- `submission_files/GVIM2.0_Supporting_Information_frontend_verified.docx`  
  Supporting Information draft, including methodological details, evidence boundaries, and reproducibility information.

- `publication_figures_600dpi/`  
  Corrected publication figures exported at 600 DPI, with PNG, TIFF, and SVG deliverables for Figures 2 and 6 and SVG counterparts for the other figures. `publication_figures_600dpi/README.md` maps each figure to its data source and reproduction script. The data-provenance corrections currently applied are:
  - Figure 3: Matbench steels is described as front-end official fold 0 with post-hoc withheld-label scoring, not a complete official five-fold front-end run.
  - Figure 4: BACE discovery labels use the actual front-end policies: random, greedy surrogate, and UCB surrogate.
  - Figure 5: Matbench band-gap cross-validation is described as recorded shuffled five-fold CV, not official Matbench task splits.

## Front-End Evidence

- `frontend_thread_records/`  
  Copied DeerFlow/GVIM thread directories. Each included thread contains the uploaded inputs, generated workspace files, outputs, or artifacts used to support the manuscript.

- `frontend_evidence_manifest.csv`  
  Human-readable index of the included front-end runs, thread IDs, task identities, objective metrics, and provenance notes.

- `posthoc_gold_scoring/`  
  Public-label or deterministic scoring files used only after front-end predictions/extractions were frozen. These are used for cases where the front-end test inputs were unlabeled, such as ESOL and Matbench steels fold 0.

- `excluded_non_frontend/`  
  Results retained only for transparency. These files are not used as front-end workflow claims. In particular, the Matbench steels official five-fold local result is kept here because the complete official five-fold evaluation was not run through the GVIM front end.

## Reproducibility Code and Data

- `reproducibility_code/manuscript_and_figure_scripts/`  
  Python and PowerShell scripts used to build the verified package, update the Word/SI files, redraw corrected figures, and perform document/figure checks.
  In particular, `redraw_publication_figures.py` reproduces Figure 2 and
  `draw_bace_temporal_publication_figure.py` reproduces Figure 6 from the
  packaged source data and front-end artifacts.

- `reproducibility_code/research_demos_code_data_results/`  
  Full copy of the `research-demos` workspace, including demo task code, evaluators, input data, test utilities, generated result folders, and prompt/demo materials.

- `source_data_and_results/`  
  Manuscript source data, working figures, publication figure intermediates, and QA records copied from `manuscript_assets`.
- `source_data_and_results/benchmark_400_raw_records/`  
  Raw and scored records supporting the Figure 2 paired 400-task benchmark, including the earlier 360-task chemistry/materials benchmark records and the public-extension-40 GVIM/API-only paired records used to compute the final n=400 contingency table.

- `DATA_FIGURE_AUDIT_2026-06-22.md`  
  Audit note generated after scanning the manuscript/SI text, embedded media, figure source files, front-end outputs, and post-hoc public-gold scoring files.

## Integrity Files

- `SHA256_MANIFEST.csv`  
  Hash manifest generated before this expanded consolidation.

- `SHA256_MANIFEST_full_package.csv`  
  Full hash manifest for the current consolidated package. Use this for final integrity checking.

## Claim Boundary

A result is described as a GVIM front-end workflow only when its DeerFlow/GVIM thread directory records the user upload, workspace execution, and generated artifacts. When metrics were computed after the fact from public gold labels or deterministic rules, they are explicitly described as post-hoc scoring of frozen front-end outputs.

No expert subjective grading, hidden manual relabeling, prospective wet-lab validation, or fabricated benchmark scores are included in this package.

## Critical Matbench Steels Note

The front-end Matbench steels run corresponds to official fold 0 only: 249 labeled training rows and 63 unlabeled test rows were submitted through the front end. The front-end workflow performed internal cross-validation on the fold-0 training partition for model selection. The fold-0 test metrics were computed post hoc by comparing frozen front-end predictions with withheld public labels.

The separate official Matbench steels five-fold result is not a GVIM front-end run and is stored only under `excluded_non_frontend/` for audit transparency.

