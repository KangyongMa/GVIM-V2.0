# Five Chemistry/Materials Showcase Demos

These five demos are designed to complement the existing 400-question score.
They are not knowledge questions. Each one starts from the DeerFlow front end,
uses uploaded scientific data or natural-language research intent, executes a
multi-step workflow, and produces files that can be scored with public or
standard metrics.

## Demo Set

| ID | Domain | Public task family | Main standard metrics |
|---|---|---|---|
| `materials_xrd_phase_identification` | Materials | XRD phase retrieval / materials characterization | top-1/top-k accuracy, precision, recall, peak MAE |
| `matbench_materials_property_modeling` | Materials | Matbench materials ML | MAE/RMSE/R2 or ROC-AUC/F1 |
| `moleculenet_molecular_property_workflow` | Chemistry | MoleculeNet molecular ML | ROC-AUC, PR-AUC, F1, RMSE, MAE |
| `spectra_to_structure_regression` | Chemistry | Spectroscopy-to-structure regression | MAE, RMSE, R2, Pearson r |
| `literature_extraction_to_dataset` | Chemistry/materials | Literature/table/figure information extraction | precision, recall, F1, exact match, numeric MAE |

## Stricter Paper-Facing Variant

For a high-level chemistry/materials journal, the strongest quantitative set
should use public benchmark frameworks whenever possible. In that stricter
version, keep `materials_xrd_phase_identification` as a visual supplementary
demo, and replace it in the main results table with a Matbench Discovery
screening demo:

| ID | Domain | Public task family | Main standard metrics |
|---|---|---|---|
| `matbench_materials_property_modeling` | Materials | Matbench materials ML | MAE/RMSE/R2 or ROC-AUC/F1 |
| `matbench_discovery_materials_screening` | Materials | Matbench Discovery stability screening | F1, precision, recall, MAE, R2, RMSE, DAF |
| `moleculenet_molecular_property_workflow` | Chemistry | MoleculeNet molecular ML | ROC-AUC, PR-AUC, F1, RMSE, MAE |
| `spectra_to_structure_regression` | Chemistry | Spectroscopy-to-structure regression | MAE, RMSE, R2, Pearson r |
| `matsci_nlp_sofc_extraction` | Chemistry/materials | MatSci-NLP or SOFC-Exp information extraction | precision, recall, micro/macro F1 |

See `../docs/external_benchmark_alignment.md` for the external benchmark
evidence and the recommended paper-facing evaluation table.

## Why These Are Different From the 400-Question Evaluation

The 400-question evaluation primarily measures answer accuracy on chemistry and
materials questions. This showcase measures whether DeerFlow can complete
research workflows:

- accept files through the front end;
- plan the analysis;
- invoke domain tools such as RDKit, pymatgen, XRD simulation, and extraction;
- run or repair code where needed;
- generate scientific artifacts such as CSV, JSON, plots, reports, structures,
  and audit logs;
- score outputs with task-native metrics.

## Recommended Execution Order

1. Start with `materials_xrd_phase_identification` because it best shows
   materials-domain file upload, structure parsing, XRD simulation, and visual
   evidence generation.
2. Run `moleculenet_molecular_property_workflow` to show chemistry ML with RDKit
   and standard molecular-property metrics.
3. Run `spectra_to_structure_regression` to show spectroscopy and continuous
   structure prediction.
4. Run `matbench_materials_property_modeling` to show materials ML beyond
   molecular datasets.
5. Run `literature_extraction_to_dataset` last because it is the longest and
   best used as a capstone demo.

## Files

- `manifest.json`: machine-readable definitions, workflows, metrics, and
  expected artifacts.
- `frontend_prompts.jsonl`: front-end prompts that can be used by the browser
  submitter or copied into the DeerFlow UI.
- `dataset_metric_registry.json`: public data sources, hidden-gold rules, and
  allowed objective metrics for each demo.
- `evaluation_protocol.md`: complete Chinese demo and evaluation protocol.
- `strict_manifest.json`: stricter paper-facing five-demo set using public
  benchmark or paper-derived gold standards.
- `strict_frontend_prompts.jsonl`: front-end prompts for the stricter
  paper-facing demo set.
