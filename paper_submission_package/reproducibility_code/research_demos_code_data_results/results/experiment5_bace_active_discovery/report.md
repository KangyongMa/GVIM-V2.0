# Experiment 5: Retrospective Active Discovery of High-Activity BACE Inhibitors

## Scientific Question

Can a GVIM-style agent workflow organize a closed-loop molecular screening task and prioritize high-activity BACE inhibitor candidates from a public chemical library using only a limited query budget?

## Public Data And Gold Standard

- Dataset: ChemLLMBench copy of the MoleculeNet BACE table (`benchmarks/_sources/ChemLLMBench/data/property_prediction/BACE.csv`).
- Candidate library size: 1513 molecules.
- Gold label: public experimental `pIC50`.
- High-activity target definition: molecules with `pIC50 >= 8.3979`, corresponding to the top 5% of the dataset.
- Number of gold targets: 79.

The gold labels of unqueried molecules are used only for retrospective evaluation.

## Workflow

1. Start each run with 30 randomly queried molecules.
2. Train a surrogate model on only the queried molecules.
3. Select the next batch of 10 molecules using either random selection, greedy surrogate exploitation, or UCB-style exploration-exploitation.
4. Repeat until 150 molecules have been queried.
5. Evaluate the selected set against the public pIC50 gold standard.

## Objective Metrics

| Policy | Recall@150 | Hit rate@150 | Enrichment factor@150 | Success@150 | Mean best pIC50 |
|---|---:|---:|---:|---:|---:|
| Random | 0.0962 | 0.0507 | 0.97 | 1.00 | 9.142 |
| Greedy surrogate | 0.3285 | 0.1730 | 3.31 | 1.00 | 9.238 |
| UCB surrogate | 0.3177 | 0.1673 | 3.20 | 1.00 | 9.294 |

Paired bootstrap 95% CI for UCB minus random Recall@150: 0.1943 to 0.2519.

## Frequently Selected UCB Candidates

| Row | pIC50 | Gold rank | Top-5% target | Selection frequency |
|---:|---:|---:|---:|---:|
| 208 | 9.000 | 10 | True | 12/20 |
| 295 | 8.398 | 75 | True | 12/20 |
| 1 | 8.854 | 18 | True | 11/20 |
| 255 | 8.854 | 19 | True | 11/20 |
| 256 | 8.824 | 20 | True | 11/20 |
| 261 | 8.699 | 26 | True | 11/20 |
| 273 | 8.585 | 49 | True | 11/20 |
| 274 | 8.585 | 48 | True | 11/20 |
| 275 | 8.585 | 47 | True | 11/20 |
| 250 | 9.004 | 8 | True | 10/20 |
| 251 | 9.000 | 16 | True | 10/20 |
| 259 | 8.699 | 36 | True | 10/20 |

## Interpretation

This experiment does not claim experimental validation or a new BACE inhibitor. It is a retrospective, public-label virtual screening experiment. Its value for the GVIM manuscript is that it connects an agentic workflow to a real chemical discovery-style task with objective metrics: top-target recall, hit rate, enrichment factor, and best observed activity under a fixed query budget.

For a Chemical Science submission, this experiment should be rerun through the GVIM front end with the same frozen input files, prompt, random seeds, and scoring script, then reported together with the workflow trace and generated artifacts.
