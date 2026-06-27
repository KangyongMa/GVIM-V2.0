# Front-End End-to-End Research Demo Design

## Goal

Measure whether a user can start from the DeerFlow front end and obtain a
correct, reproducible chemistry or materials result after autonomous tool use.
The evaluation must not depend on expert review or wet-lab validation.

## Design Basis

- ScienceAgentBench motivates tasks extracted from real scientific workflows,
  executable outputs, result correctness, and cost measurement.
- MatTools motivates real materials-tool execution and separate runnable-rate
  and task-success metrics.
- ChemCrow motivates iterative chemistry-tool selection instead of relying on
  language-model recall.
- Matbench and MoleculeNet motivate standard held-out metrics for later
  data-driven prediction demos.
- XRD automation literature motivates phase-ranking and novelty-triage tasks,
  while explicitly avoiding claims of phase-purity proof.

## Three Complementary Layers

### Layer A: Deterministic Domain-Tool Workflows

The initial six tasks exercise RDKit and pymatgen-backed science tools. They are
fast, inexpensive, and fully machine-scorable. They test autonomous tool
selection, multi-call consistency, structured reporting, and scientific
guardrails.

### Layer B: Uploaded-Data Research Workflows

The next extension should submit CSV or CIF files through the front-end upload
control. Recommended cases are:

1. molecular-property modeling on a held-out MoleculeNet split;
2. materials-property regression on a Matbench task;
3. spectra-to-structure regression using the published azobenzene dataset;
4. CIF structure analysis followed by theoretical XRD simulation and matching.

Primary metrics are MAE, RMSE, R2, ROC-AUC, PR-AUC, top-k accuracy, and
executable-artifact rate.

### Layer C: Evidence-Grounded Database Workflows

Materials Project tasks should ask DeerFlow to retrieve candidates, apply
explicit constraints, and produce a ranked evidence table. Evaluate retrieval
recall, constraint satisfaction, provenance completeness, and ranking
agreement against a frozen database snapshot. These tasks are optional when an
API key or stable snapshot is unavailable.

## Execution and Evidence

All formal runs use the real browser submitter. Each task starts in a fresh
chat and records the front-end page URL, thread ID, run ID, final answer, tool
events, latency, and errors. The held-out gold file is used only after
submission.

Fixed baseline scripts remain useful as reference implementations and gold
generators, but their metrics must never be reported as DeerFlow agent results.
