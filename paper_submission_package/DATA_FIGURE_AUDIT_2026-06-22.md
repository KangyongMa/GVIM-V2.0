# Data and Figure Audit - 2026-06-22

## Scope
Audited the front-end-verified manuscript DOCX, Supporting Information DOCX, embedded media, publication figures, source CSV files, front-end thread outputs, and post-hoc public-gold scoring files in this package.

## Overall Finding
After removing one stale BACE policy alias from the Supporting Information, the numeric results used in the manuscript figures and tables are traceable to packaged source CSV/JSON files, front-end thread outputs, or explicitly labeled post-hoc public-gold scoring files. The main claim boundary remains essential: Matbench steels is fold 0 only, and no complete official Matbench steels five-fold front-end run is claimed.

## Expression and Deliverable Update - 2026-06-23
- The manuscript and Supporting Information were synchronized after a claim-boundary review. The BACE1 temporal case is described as a label-withheld, retrospective public-data evaluation with moderate external regression performance (R² = 0.369) and non-random prioritization, not as prospective discovery or experimental validation.
- The Matbench steels workflow is explicitly described as a single official fold-0 front-end demonstration. No full official Matbench five-fold front-end claim remains.
- The Matbench band-gap 95% interval is described as an archived exploratory interval because only three active-discovery seeds were run; it is not presented as strong inferential evidence.
- Figure 2 and Figure 6 high-resolution PNG, TIFF, and SVG exports have been added to `publication_figures_600dpi/`. Their plotting scripts are retained in `reproducibility_code/manuscript_and_figure_scripts/`.

## Text Risk Scan
- old steels official five-fold metrics 92.6/137.1/0.781: 0 residual hits
- old BACE duplicate alias: 0 residual hits
- old band-gap title: 0 residual hits
- Note: SI still contains accurate explanatory language about internal shuffled five-fold CV for Matbench steels fold 0; this is not a complete official five-fold claim.

## Figure 2 Benchmark Data
- ChemBench: GVIM 204/250=81.60%, API-only 189/250=75.60%
- MaScQA: GVIM 94/97=96.91%, API-only 73/97=75.26%
- ChemLLMBench: GVIM 27/53=50.94%, API-only 23/53=43.40%
- Descriptive total: GVIM 325/400=81.25%, API-only 285/400=71.25%
- Paired raw JSON: n=400, GVIM=325, API-only=285, both_correct=268, GVIM_only=57, API_only=17, both_wrong=58, delta=10.0 pp, McNemar p=3.397e-06, bootstrap CI=[6.0, 14.249999999999998]
- Raw 360/40 benchmark records have been added under `source_data_and_results/benchmark_400_raw_records/`.

## Front-End Demo and Case Metrics
- ESOL post-hoc public-label scoring: MAE=0.603, RMSE=0.741, R2=0.739, n_test=254.
- Matbench steels fold 0 post-hoc public-label scoring: MAE=111.444 MPa, RMSE=164.320 MPa, R2=0.684, n_test=63; folds=[0].
- MinerU/JATS reaction table: precision=0.981, recall=0.981, F1=0.981, row_accuracy=0.905; gold_cells=105.
- MS/MS retrieval: Top-1=0.800, Top-3=1.000, Top-5=1.000, MRR=0.900; n_queries=5.
- ChEMU NER: exact P/R/F1=0.931/0.728/0.817; relaxed F1=0.841; gold=92.
- BACE active discovery: random Recall@150=0.109; greedy=0.333; UCB=0.363; UCB EF@150=3.664; seeds=20.
  Alias check: `surrogate_active_search` present in raw metrics = yes; identical to `greedy_surrogate` = True. Manuscript/SI uses `greedy surrogate` only.
- Matbench experimental band-gap: cv_method=KFold(n_splits=5, shuffle=True, random_state=18012019); MAE=0.4513+/-0.0170, RMSE=0.8049+/-0.0456, R2=0.6854+/-0.0445; greedy Recall@150=0.2626; seeds=3.
- BACE1 temporal external validation: RF MAE=0.8215, RMSE=1.0278, R2=0.3687; Recall@10%=0.2609; EF=2.6054; n_external=1598.

## Embedded Figure Audit
- image1.jpeg: size=(1069, 1069), dpi=(220, 220), sha=736130aaa492, publication_figure_match=not in publication_figures_600dpi
- image2.png: size=(2640, 2996), dpi=(329.9968, 329.9968), sha=0c74fd884acc, publication_figure_match=not in publication_figures_600dpi
- image3.png: size=(4547, 3132), dpi=(599.9988, 599.9988), sha=e24525c7959d, publication_figure_match=not in publication_figures_600dpi
- image4.png: size=(4695, 3772), dpi=(599.9988, 599.9988), sha=a8e10095a969, publication_figure_match=Figure3_task_native_demos.png
- image5.png: size=(4290, 2457), dpi=(599.9988, 599.9988), sha=661715b94c19, publication_figure_match=Figure4_BACE_active_discovery.png
- image6.png: size=(5517, 3347), dpi=(599.9988, 599.9988), sha=c1cd827707dd, publication_figure_match=Figure5_matbench_bandgap.png
- image7.png: size=(4367, 3141), dpi=(599.9988, 599.9988), sha=120f607a1928, publication_figure_match=not in publication_figures_600dpi

## Render QA
- The corrected Supporting Information DOCX was exported to PDF and rasterized to 17 PNG pages under `rendered_si_after_audit_fix/`. The BACE policy table renders with only random, greedy surrogate, and ucb surrogate rows; no visible table break or overlap was observed.
- A scan hit for the phrase `No complete official Matbench steels five-fold front-end result is claimed` is an expected negative-boundary statement, not an affirmative claim.

## Remaining Interpretation Boundaries
- Figure 1/overview and the cover-style AI illustration are schematic/illustrative, not numerical evidence.
- Figure 2 benchmark totals are descriptive across benchmarks with different native scoring rules; per-benchmark results are the most interpretable units.
- Matbench steels is not a complete official five-fold front-end evaluation; only fold 0 was run through the front end.
- Matbench band-gap uses recorded shuffled KFold CV from the front-end artifact; it should not be described as official Matbench split semantics unless rerun that way.
- BACE active discovery and BACE1 temporal validation are retrospective public-label computational validations, not wet-lab or prospective experimental validation.


