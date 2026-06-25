# Agent Task: Molecular Property Prediction

## Problem

Predict whether molecules can penetrate the blood-brain barrier from their SMILES
representations.

## Input

`benchmarks/_sources/ChemLLMBench/data/property_prediction/BBBP.csv`

## Required Workflow

1. Validate and featurize SMILES.
2. Construct a scaffold-disjoint train/test split containing both classes.
3. Train a classifier without using held-out labels.
4. Save held-out probabilities and predictions.
5. Report objective metrics and invalid-SMILES failures.

## Required Output

- `predictions.csv`: row ID, SMILES, predicted class, positive-class probability.
- `metrics.json`: accuracy, F1, ROC-AUC, PR-AUC, split details, and provenance.

