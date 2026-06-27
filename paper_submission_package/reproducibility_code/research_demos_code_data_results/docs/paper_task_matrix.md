# Paper-Derived Research Task Matrix

This matrix translates the six papers in `Paper/` into reproducible evaluation
opportunities under two current constraints: no expert scoring and no wet-lab
experiments.

## Recommended Positioning

The existing approximately 400-question evaluation establishes broad chemistry and
materials knowledge. The separate ChemToolBench subset establishes tool selection and
parameter filling. The research demos should make a different claim:

> DeerFlow can execute and evaluate multi-stage scientific workflows that transform
> domain data into predictions, analyses, or discovery decisions.

Do not combine all results into one opaque score. Report each scientific task with its
native metrics, plus workflow success rate, runtime, and failure analysis.

## Task Inventory

| Paper | Typical task and data | Paper evaluation | Reproducible demo under current constraints |
|---|---|---|---|
| `d5sc08794e` | Predict C-N=N-C dihedral angle from 4,400 simulated IR/Raman structure-spectrum pairs; transfer to 500/250 simulated samples and small experimental sets | MAE and correlation `r`; ablation MAE; transfer-learning curves | **Implemented:** experimental IR/Raman to angle regression with held-out MAE, RMSE, R2, and Pearson r. Extension: recover the 4,400-pair training set and reproduce transfer learning |
| `d5sc09921h` | Extract structured hydrogen-storage data from figures in 100 articles; build a database of more than 30,000 entries; predict gravimetric hydrogen density | extraction accuracy/completeness, caption-identification precision/recall/F1, standard regression metrics | Add a held-out figure/table extraction set scored by exact field F1 and numeric tolerance; add formula-to-hydrogen-density regression with MAE/RMSE/R2 when the released data are locally available |
| `s41524-026-02139-1` | Closed-loop search for target CO adsorption energies across 28 transition metals in two catalyst families | simulations required to reach target, success rate, search efficiency, normalized Shannon entropy | **Implemented analogue:** closed-loop active search on measured BACE activity. Preferred extension: use the paper supplementary CO adsorption table and report target hit rate, queries-to-hit, recall, and enrichment against random/heuristic policies |
| `s42004-025-01776-9` | Thirteen computational chemistry workflows over 360 instances, including reaction enthalpy and Gibbs free energy | task accuracy and number of tool calls; repeated-run mean and standard deviation | Add end-to-end reaction thermodynamics cases using the released ChemGraph gold workflows. Score numeric error, workflow completion, tool-call count, self-recovery rate, and runtime |
| `s43246-025-00994-x` | Materials retrieval, cellular automata, crystal generation, MD, and cross-agent execution | repeated-run consistency, parameter extraction success, correct routing/tool use, NVE energy conservation | Add CIF generation validation and MD conservation checks. Score parse success, composition/space-group accuracy, parameter exact match, drift in total energy, and repeated-run success |
| `s43246-026-01167-0` | Generate, validate, and repair Quantum ESPRESSO protocols from 295 human-authored prompts | early-execution success, zero-shot success, repair success, attempts to success, exponential-fit RMSE | Add protocol generation and static validation without production DFT. Score parse/validation pass rate, zero-shot rate, repair recovery rate, attempts-to-success, and hallucinated-keyword rate |

## First Three Complete Chains

### 1. Spectra to Molecular Structure

- **Problem definition:** infer the C-N=N-C dihedral angle from paired IR/Raman spectra.
- **Data input:** released experimental spectra from the azobenzene paper repository.
- **Agent workflow:** inspect data schema, preprocess spectra, select a regression method,
  run held-out validation, save predictions, and interpret errors.
- **Result output:** per-spectrum predicted angle and absolute error.
- **Standard metrics:** MAE, RMSE, R2, Pearson r.

### 2. Molecular Property Prediction

- **Problem definition:** predict blood-brain barrier penetration from SMILES.
- **Data input:** BBBP with molecular labels.
- **Agent workflow:** validate SMILES, featurize molecules, use a class-balanced
  scaffold-disjoint split, train a classifier, save probabilities, and analyze failure
  cases.
- **Result output:** held-out class probabilities and labels.
- **Standard metrics:** accuracy, F1, ROC-AUC, PR-AUC.

### 3. Closed-Loop Candidate Discovery

- **Problem definition:** discover top-1% activity compounds while minimizing the
  number of queried labels.
- **Data input:** a closed BACE candidate pool with hidden pIC50 values.
- **Agent workflow:** select an initial set, fit a surrogate, propose candidates, reveal
  their labels, update the model, and repeat until the budget is exhausted.
- **Result output:** complete search trajectory for every seed and policy.
- **Standard metrics:** success@budget, queries-to-first-hit, top-target recall, and
  enrichment factor relative to random search.

## Publication-Grade Experimental Design

For every demo, compare DeerFlow against a fixed-script baseline and at least one
ablated agent. Freeze input data, splits, random seeds, evaluator code, and budgets
before running the agent. Preserve full trajectories, generated code, intermediate
files, errors, retries, and final predictions.

Use confidence intervals or repeated-run mean and standard deviation. For predictive
tasks, include simple and strong baselines, leakage-resistant splits, and an external or
out-of-distribution test when available. For closed-loop discovery, compare equal
budgets and report the full discovery curve instead of only the final hit.
