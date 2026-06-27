# DeerFlow Front-End Research Workflow Demos

This suite evaluates practical chemistry and materials workflows initiated from
the real DeerFlow front end. It is separate from the fixed baseline scripts in
the parent directory.

## Evaluation Contract

Each task must follow this chain:

1. a user prompt is submitted through the real DeerFlow chat textbox;
2. DeerFlow autonomously selects and executes science tools;
3. the final answer contains a machine-readable JSON result;
4. the submitter records the thread, run, tool events, latency, and answer;
5. an independent evaluator compares the result with deterministic gold data.

The gold file is never passed to DeerFlow during submission.

## Initial Practical Cases

| Task | Practical use | Objective metrics |
|---|---|---|
| Aspirin computed profile | Compound registration and 3D preparation | exact-field accuracy, descriptor MAE, tool coverage |
| Aspirin analogue ranking | Small virtual-screening triage | top-1 accuracy, exact ranking, Tanimoto MAE |
| Reaction data QC | Dataset cleaning before reaction-model training | accuracy, F1, issue-count MAE |
| Battery formula audit | Composition-table validation | reduced-formula accuracy, molar-mass MAE |
| XRD candidate ranking | Fast phase-identification triage | top-1 accuracy, ranking accuracy, score MAE |
| LiFePO4 precursor plan | Reproducible stoichiometric weighing calculation | coefficient MAE, mass MAE, residual error |

These cases require no expert review and no wet-lab execution. The XRD and
precursor cases explicitly avoid claiming phase purity or synthesis validity.

## Submit Through the Real Front End

Start DeerFlow first, then run from the repository root:

```powershell
node benchmarks\chembench-mini-236\native_submit.mjs `
  --questions research-demos\frontend-e2e\tasks.jsonl `
  --out-dir research-demos\frontend-e2e\runs `
  --limit 6 `
  --new-chat-every 1 `
  --timeout-ms 360000
```

This submitter opens the real browser UI and types into the real chat input. It
does not call the backend directly.

## Evaluate

```powershell
python research-demos\frontend-e2e\evaluate_runs.py `
  research-demos\frontend-e2e\runs\<run-directory>
```

The evaluator writes `evaluation.jsonl` and `evaluation_summary.json` inside the
run directory.

## Publication Reporting

Report at least:

- per-task success rate and metric values;
- tool coverage and tool-call failures;
- JSON parse rate and front-end HTTP success rate;
- mean and distribution of latency;
- three independent runs per task;
- ablations without science tools and without planning.

Do not combine this suite with the 400-question score as one undifferentiated
number. The question benchmark measures knowledge; this suite measures
front-end, end-to-end scientific workflow execution.
