# Agent Task: Closed-Loop Candidate Discovery

## Problem

Find top-1% pIC50 BACE inhibitor candidates while querying as few hidden activity
labels as possible.

## Input

`benchmarks/_sources/ChemLLMBench/data/property_prediction/BACE.csv`

Treat `pIC50` as hidden until a candidate is selected. Use an initial random set of 20,
a total budget of 60 candidates, batches of 5, and seeds 0 through 9.

## Required Workflow

1. Build a candidate representation without using hidden pIC50 values.
2. Observe the initial random set.
3. Propose the next candidate batch.
4. Reveal selected labels, update the strategy, and repeat.
5. Compare against equal-budget random search.

## Required Output

- `trajectories.csv`: seed, policy, queries, targets found, target recall, best pIC50.
- `metrics.json`: success@budget, queries-to-first-hit, target recall, enrichment factor,
  policy definition, budget, seeds, and provenance.

