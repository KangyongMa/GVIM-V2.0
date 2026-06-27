# Chemistry and Materials Research Demos

This suite complements the existing question-answer and tool-calling benchmarks with
small, reproducible research workflows. Every runnable demo has the same contract:

1. problem definition;
2. published or established data input;
3. deterministic execution workflow;
4. machine-readable outputs;
5. objective scientific metrics.

The first release deliberately excludes expert review and wet-lab validation. It focuses
on workflows that can be evaluated from held-out labels or closed-loop discovery
outcomes.

The real DeerFlow front-end evaluation suite is in
[`frontend-e2e/`](frontend-e2e/). It submits practical research requests through
the browser UI, records actual tool events, and scores the returned results against
held-out deterministic gold data.

The recommended five-demo chemistry/materials showcase is documented in
[`docs/five_showcase_demos.md`](docs/five_showcase_demos.md), with a
machine-readable manifest in [`showcase-5/manifest.json`](showcase-5/manifest.json).
The evaluation logic is aligned with the two local reference papers in
[`docs/reference_paper_alignment.md`](docs/reference_paper_alignment.md).
The full execution and scoring protocol is in
[`showcase-5/evaluation_protocol.md`](showcase-5/evaluation_protocol.md).

## Runnable Demos

| ID | Research task | Data | Main metrics |
|---|---|---|---|
| `spectra_to_dihedral` | Predict azobenzene dihedral angle from paired IR/Raman spectra | Data released with `d5sc08794e` | MAE, RMSE, R2, Pearson r |
| `bbbp_property_prediction` | Predict blood-brain barrier penetration from SMILES | BBBP from ChemLLMBench/MoleculeNet | Accuracy, F1, ROC-AUC, PR-AUC |
| `bace_active_search` | Find high-activity BACE inhibitors in a closed candidate pool | BACE from ChemLLMBench/MoleculeNet | success@budget, queries-to-first-hit, recall@budget, enrichment factor |

The paper-derived task inventory and recommended future extensions are documented in
[`docs/paper_task_matrix.md`](docs/paper_task_matrix.md).

## Run

From the repository root:

```powershell
python research-demos/run_all.py
```

Run one demo:

```powershell
python research-demos/demos/spectra_to_dihedral.py
python research-demos/demos/bbbp_property_prediction.py
python research-demos/demos/bace_active_search.py
```

Outputs are written to `research-demos/results/`. Each demo emits:

- `metrics.json`: objective evaluation metrics and provenance;
- `predictions.csv` or `trajectories.csv`: sample-level evidence;
- plots when useful for interpretation.

## Dependencies

The runnable baselines use Python 3.10+ with `numpy`, `pandas`, `scikit-learn`,
`matplotlib`, and `rdkit`. Install from the repository root with:

```powershell
python -m pip install -r research-demos/requirements.txt
```

## Agent Evaluation Protocol

The baseline scripts establish reference workflows and evaluator behavior. To evaluate
DeerFlow as a research agent, give the agent only the problem statement and input data,
then require it to produce a predictions or trajectory file matching the schema in
`manifest.json`. Score the output with the same objective metrics used here.

For shorter domain-tool workflows, use the front-end task queue and evaluator in
`frontend-e2e/`. Fixed-script metrics are baseline metrics only and must not be
reported as front-end Agent results.

For publication, report at least three conditions:

- fixed baseline workflow from this suite;
- DeerFlow-generated workflow;
- an ablation with planning, memory, or tool access disabled.

Use repeated seeds or cross-validation where the task permits it, and report mean,
standard deviation, failures, runtime, and generated artifacts.
