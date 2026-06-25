# ESOL Aqueous Solubility Prediction — Workflow Report

## Overview

This workflow predicts aqueous solubility (log mol/L) from molecular SMILES
strings using the **MoleculeNet ESOL** benchmark split.  The training set
contains 874 labeled molecules; the test set contains 254
unlabeled molecules.

## Workflow

### 1. Descriptor computation

A compact set of 12 physicochemical descriptors was computed
using RDKit:

| Descriptor | Interpretation |
|---|---|
| `MolWt` | Molecular weight |
| `LogP` | Octanol-water partition coefficient (Wildman-Crippen) |
| `NumHDonors` | Number of hydrogen bond donors |
| `NumHAcceptors` | Number of hydrogen bond acceptors |
| `NumRotatableBonds` | Number of rotatable bonds |
| `TPSA` | Topological polar surface area |
| `RingCount` | Total number of rings |
| `FractionCSP3` | Fraction of sp³-hybridized carbons |
| `NumAromaticRings` | Number of aromatic rings |
| `NumSaturatedRings` | Number of saturated (non-aromatic) rings |
| `NumHeteroatoms` | Number of heteroatoms (non-carbon, non-hydrogen) |
| `HeavyAtomCount` | Number of heavy (non-hydrogen) atoms |

Molecules that RDKit cannot parse are dropped from the workflow.

### 2. Cross-validation strategy

**Deterministic Bemis-Murcko scaffold-aware cross-validation** (5 folds) was
used so that molecules sharing a Murcko scaffold are **never split** between
training and validation.

- Each molecule's Murcko scaffold is extracted via RDKit.
- Scaffolds are sorted by group size (largest first), with ties resolved by
  SHA-256 hash for deterministic ordering.
- Scaffold groups are assigned to folds via round-robin.
- A `StandardScaler` is fitted **independently** within each training fold –
  never exposed to validation-fold statistics.

This scheme provides a realistic assessment of generalization to new chemical
scaffolds, unlike random or cluster-based splits.

### 3. Models compared

| Model | Description |
|---|---|
| **TrainingMean** (baseline) | Always predicts the training mean — a zero-R sanity check |
| **LinearOLS** | Ordinary least squares linear regression (no regularization) |
| **Ridge** | Ridge regression with L2 penalty (α=1.0) |
| **RandomForest** | 500 trees, max depth 15, min samples leaf 5 |

Hyperparameters were not tuned; the purpose is model selection on a level
playing field, not optimization.

### 4. Model selection

The model with the **lowest validation RMSE** across the 5 scaffold-aware folds
was selected.

## Results

### Cross-validation metrics (scaffold-aware, 5-fold)

| Model | MAE | RMSE | R² |
|---|---|---|---|
| **TrainingMean** | 2.0323 | 2.4915 | -0.2309 |
| **Ridge** | 0.829 | 1.046 | 0.783 |
| **LinearOLS** | 0.8302 | 1.0469 | 0.7827 |
| **RandomForest** | 0.6429 | 0.8541 | 0.8554 |

**Selected model:** `RandomForest` (RMSE = 0.8541)

### Sanity checks

| Check | Status |
|---|---|
Predictions contain no NaN | True |
Prediction range plausible (−15 to +5) | True |
Training RDKit success rate | 100.0% |
Test RDKit success rate | 100.0% |

### Test predictions

The selected model was retrained on the **full training set** and applied to all
254 test molecules.  Results are in `predictions.csv`.

## Reproducibility

| Aspect | Method |
|---|---|
| Random seed | `20260614` (fixed date-based) |
| Scaffold ordering | Size + SHA-256 hash sorting |
| Descriptors | RDKit deterministic — same SMILES → same values |
| Library versions | Recorded in `run_metadata.json`; bitwise replication requires identical rdkit, sklearn, numpy versions |

## Limitations

1. **Descriptor scope**: Only 12 physicochemical descriptors.  No fingerprints,
   graph-based features, or learned representations were used.
2. **No hyperparameter tuning**: Ridge α and RandomForest parameters were
   chosen heuristically.
3. **Scaffold coverage**: The scaffold split may leave some test scaffolds
   unseen during training, especially for rare chemotypes.
4. **RDKit dependency**: Molecules that RDKit cannot parse are silently dropped
   (0 train, 0 test).
5. **No test labels**: The test CSV is unlabeled; no test-set metrics are
   reported.
