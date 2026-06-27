# Agent Task: Spectra to Dihedral Angle

## Problem

Build a reproducible model that predicts the C-N=N-C dihedral angle from paired IR and
Raman spectra.

## Input

`research-demos/data/azobenzenes-spectra/IR_Raman_azo.csv`

The first 8,000 columns are paired spectral features. Column 8,001 is the target angle
in degrees.

## Required Workflow

1. Inspect and validate the data.
2. Select and justify a regression and validation method suitable for 20 samples.
3. Generate held-out predictions for every sample.
4. Save predictions and objective metrics.
5. Summarize limitations without using expert scoring.

## Required Output

- `predictions.csv`: `sample_id`, observed angle, predicted angle, absolute error.
- `metrics.json`: MAE, RMSE, R2, Pearson r, model, validation protocol, and provenance.

