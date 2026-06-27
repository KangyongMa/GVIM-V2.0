from __future__ import annotations

import gzip
import json
import math
import urllib.request
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold
from sklearn.model_selection import KFold


RESEARCH_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = RESEARCH_ROOT.parent
SHOWCASE_ROOT = RESEARCH_ROOT / "showcase-fast-ml"

ESOL_URL = "https://raw.githubusercontent.com/deepchem/deepchem/master/datasets/delaney-processed.csv"
STEELS_URL = "https://ml.materialsproject.org/projects/matbench_steels.json.gz"
MATBENCH_VALIDATION_URL = "https://raw.githubusercontent.com/materialsproject/matbench/main/matbench/matbench_v0.1_validation.json"

ESOL_PROMPT = """Using the uploaded MoleculeNet ESOL split and manifest, create and run one reproducible Python workflow to predict aqueous solubility from SMILES. Train only on the labeled training CSV and predict every row of the unlabeled test CSV.

In a single script execution, compute a compact reusable set of RDKit physicochemical descriptors, compare a training-mean baseline and exactly three regression models, and select the model with the lowest validation RMSE. Evaluate models using fixed, deterministic Bemis-Murcko scaffold-aware cross-validation so molecules sharing a scaffold are never split between training and validation. Report validation MAE, RMSE, and R2.

Do not perform hyperparameter search, iterative refinement, high-dimensional fingerprint concatenation, or supervised feature selection outside cross-validation. Any preprocessing that learns from the target or feature distribution must be fitted independently within each validation fold.

Retrain the selected model on the full training set and produce:

1. `predictions.csv` with exactly `molecule_id`, `smiles`, and `predicted_log_solubility`.
2. `run_metadata.json` containing the baseline, scaffold-validation results, selected model, descriptor count, random seed, sanity checks, and execution time.
3. `report.md` describing the workflow, validation-based selection, reproducibility, and limitations.

Minimize tool calls: inspect the inputs once, write one portable script with a `main()` function and an `if __name__ == "__main__":` guard, execute it once, and verify the three output files once. The test CSV is unlabeled; do not use hidden test labels or report test-set metrics.
"""

STEELS_PROMPT = """Using the uploaded Matbench `matbench_steels` fold and manifest, create and run one reproducible Python workflow to predict steel yield strength from composition. Train only on the labeled training CSV and predict every row of the unlabeled test CSV.

In a single script execution, compute reusable composition features, compare a training-mean baseline and exactly three regression models using fixed-seed 5-fold cross-validation, and select the model with the lowest validation RMSE. Report validation MAE, RMSE, and R2. Do not perform hyperparameter search, iterative refinement, repeated feature generation, or uncontrolled multiprocessing.

Retrain the selected model on the full training set and produce:

1. `predictions.csv` with exactly `fold`, `row_id`, `composition`, and `predicted_yield_strength_mpa`.
2. `run_metadata.json` containing the baseline, validation results, selected model, random seed, sanity checks, and execution time.
3. `report.md` describing the workflow, validation-based selection, reproducibility, and limitations.

Minimize tool calls: inspect the inputs once, write one portable script with a `main()` function and an `if __name__ == "__main__":` guard, execute it once, and verify the three output files once. The test CSV is unlabeled; do not use hidden test labels or report test-set metrics.
"""

STEELS_5FOLD_PROMPT = """Using the uploaded Matbench `matbench_steels` five-fold manifest and CSV files, create and run one reproducible Python workflow that predicts steel yield strength for every unlabeled outer test fold.

For each official outer fold, train only on its corresponding labeled training CSV. Compute reusable elemental-fraction features, compare exactly three fixed regression models using fixed-seed internal cross-validation, select the model with the lowest validation RMSE, retrain it on the full outer-fold training set, and predict that fold's unlabeled test CSV. Do not use hidden test labels, perform hyperparameter search, or change the candidate models between folds.

Produce:

1. `predictions.csv` containing all five folds with exactly `fold`, `row_id`, `composition`, and `predicted_yield_strength_mpa`.
2. `run_metadata.json` containing each fold's validation results, selected model, random seeds, sanity checks, and execution time.
3. `report.md` describing the fixed five-fold workflow, model selections, reproducibility, and limitations.

Minimize tool calls: inspect the manifest once, write one portable script, execute it once, and verify the three output files once. Do not report outer-test metrics because the uploaded test CSV files are unlabeled.
"""


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def scaffold_for_smiles(smiles: str) -> str:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return f"invalid::{smiles}"
    scaffold = MurckoScaffold.MurckoScaffoldSmiles(mol=mol, includeChirality=False)
    return scaffold or f"no_scaffold::{Chem.MolToSmiles(mol, canonical=True)}"


def deterministic_scaffold_split(df: pd.DataFrame, smiles_col: str, test_fraction: float = 0.2) -> tuple[list[int], list[int]]:
    scaffolds: dict[str, list[int]] = defaultdict(list)
    for idx, smiles in df[smiles_col].items():
        scaffolds[scaffold_for_smiles(str(smiles))].append(int(idx))

    scaffold_sets = sorted(scaffolds.values(), key=lambda items: (-len(items), items[0]))
    test_target = math.ceil(len(df) * test_fraction)
    test_idx: list[int] = []
    train_idx: list[int] = []

    for items in scaffold_sets:
        if len(test_idx) < test_target and len(test_idx) + len(items) <= test_target * 1.15:
            test_idx.extend(items)
        else:
            train_idx.extend(items)

    if len(test_idx) < test_target:
        needed = test_target - len(test_idx)
        test_idx.extend(train_idx[-needed:])
        train_idx = train_idx[:-needed]

    return sorted(train_idx), sorted(test_idx)


def prepare_esol() -> None:
    df = pd.read_csv(ESOL_URL)
    prepared = pd.DataFrame(
        {
            "molecule_id": np.arange(len(df), dtype=int),
            "smiles": df["smiles"].astype(str).str.strip(),
            "log_solubility": df["measured log solubility in mols per litre"].astype(float),
        }
    )
    train_idx, test_idx = deterministic_scaffold_split(prepared, "smiles", test_fraction=0.2)

    demo_dir = WORKSPACE_ROOT / "Demo-ESOL"
    runtime_dir = SHOWCASE_ROOT / "runtime" / "esol_solubility_prediction"
    gold_dir = runtime_dir / "gold"
    demo_dir.mkdir(parents=True, exist_ok=True)
    gold_dir.mkdir(parents=True, exist_ok=True)

    train = prepared.iloc[train_idx].copy()
    test = prepared.iloc[test_idx][["molecule_id", "smiles"]].copy()
    gold = prepared.iloc[test_idx][["molecule_id", "log_solubility"]].copy()

    train_path = demo_dir / "esol_train.csv"
    test_path = demo_dir / "esol_test_unlabeled.csv"
    train.to_csv(train_path, index=False)
    test.to_csv(test_path, index=False)
    gold.to_csv(gold_dir / "esol_test_gold.csv", index=False)
    (demo_dir / "PROMPT.md").write_text(ESOL_PROMPT, encoding="utf-8")
    write_json(
        demo_dir / "manifest.json",
        {
            "benchmark": "MoleculeNet ESOL",
            "task": "aqueous solubility regression",
            "split_rule": "deterministic Bemis-Murcko scaffold split, test_fraction=0.2",
            "id_column": "molecule_id",
            "input_column": "smiles",
            "target_column": "log_solubility",
            "train_csv": train_path.name,
            "test_csv": test_path.name,
            "n_train": int(len(train)),
            "n_test": int(len(test)),
            "standard_metrics": ["MAE", "RMSE", "R2"],
            "source_url": ESOL_URL,
        },
    )


def load_matbench_steels() -> pd.DataFrame:
    request = urllib.request.Request(STEELS_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read()
    raw = json.loads(gzip.decompress(payload).decode("utf-8"))
    df = pd.DataFrame(raw["data"], columns=raw["columns"], index=raw["index"])
    return df.reset_index(drop=True)


def load_official_steels_folds() -> list[tuple[np.ndarray, np.ndarray]]:
    with urllib.request.urlopen(MATBENCH_VALIDATION_URL, timeout=60) as response:
        validation = json.loads(response.read().decode("utf-8"))
    split_data = validation["splits"]["matbench_steels"]
    folds = []
    for fold in range(5):
        split = split_data[f"fold_{fold}"]
        train_idx = np.asarray([int(value.rsplit("-", 1)[1]) - 1 for value in split["train"]])
        test_idx = np.asarray([int(value.rsplit("-", 1)[1]) - 1 for value in split["test"]])
        folds.append((train_idx, test_idx))
    return folds


def prepare_steels() -> None:
    df = load_matbench_steels()
    prepared = pd.DataFrame(
        {
            "row_id": np.arange(len(df), dtype=int),
            "composition": df["composition"].astype(str),
            "yield_strength_mpa": df["yield strength"].astype(float),
        }
    )
    folds = load_official_steels_folds()
    train_idx, test_idx = folds[0]

    demo_dir = WORKSPACE_ROOT / "Demo-Steels"
    runtime_dir = SHOWCASE_ROOT / "runtime" / "matbench_steels_strength"
    gold_dir = runtime_dir / "gold"
    demo_dir.mkdir(parents=True, exist_ok=True)
    gold_dir.mkdir(parents=True, exist_ok=True)

    train = prepared.iloc[train_idx].copy()
    test = prepared.iloc[test_idx][["row_id", "composition"]].copy()
    gold = prepared.iloc[test_idx][["row_id", "yield_strength_mpa"]].copy()
    gold.insert(0, "fold", 0)

    train_path = demo_dir / "matbench_steels_fold0_train.csv"
    test_path = demo_dir / "matbench_steels_fold0_test_unlabeled.csv"
    train.to_csv(train_path, index=False)
    test.to_csv(test_path, index=False)
    gold.to_csv(gold_dir / "matbench_steels_fold0_gold.csv", index=False)
    (demo_dir / "PROMPT.md").write_text(STEELS_PROMPT, encoding="utf-8")
    write_json(
        demo_dir / "manifest.json",
        {
            "benchmark": "Matbench v0.1",
            "task": "matbench_steels",
            "fold": 0,
            "fold_rule": "KFold(n_splits=5, shuffle=True, random_state=18012019)",
            "official_split_source": MATBENCH_VALIDATION_URL,
            "id_column": "row_id",
            "input_column": "composition",
            "target_column": "yield_strength_mpa",
            "train_csv": train_path.name,
            "test_csv": test_path.name,
            "n_train": int(len(train)),
            "n_test": int(len(test)),
            "standard_metrics": ["MAE", "RMSE", "R2"],
            "source_url": STEELS_URL,
        },
    )

    five_fold_dir = WORKSPACE_ROOT / "Demo-Steels-5Fold"
    five_fold_gold_dir = SHOWCASE_ROOT / "runtime" / "matbench_steels_strength_5fold" / "gold"
    five_fold_dir.mkdir(parents=True, exist_ok=True)
    five_fold_gold_dir.mkdir(parents=True, exist_ok=True)
    fold_specs = []
    all_gold = []
    for fold, (fold_train_idx, fold_test_idx) in enumerate(folds):
        fold_train = prepared.iloc[fold_train_idx].copy()
        fold_test = prepared.iloc[fold_test_idx][["row_id", "composition"]].copy()
        fold_gold = prepared.iloc[fold_test_idx][["row_id", "yield_strength_mpa"]].copy()
        fold_gold.insert(0, "fold", fold)
        train_name = f"matbench_steels_fold{fold}_train.csv"
        test_name = f"matbench_steels_fold{fold}_test_unlabeled.csv"
        fold_train.to_csv(five_fold_dir / train_name, index=False)
        fold_test.to_csv(five_fold_dir / test_name, index=False)
        all_gold.append(fold_gold)
        fold_specs.append(
            {
                "fold": fold,
                "train_csv": train_name,
                "test_csv": test_name,
                "n_train": int(len(fold_train)),
                "n_test": int(len(fold_test)),
            }
        )
    pd.concat(all_gold, ignore_index=True).to_csv(
        five_fold_gold_dir / "matbench_steels_5fold_gold.csv",
        index=False,
    )
    (five_fold_dir / "PROMPT.md").write_text(STEELS_5FOLD_PROMPT, encoding="utf-8")
    write_json(
        five_fold_dir / "manifest.json",
        {
            "benchmark": "Matbench v0.1",
            "task": "matbench_steels",
            "fold_rule": "KFold(n_splits=5, shuffle=True, random_state=18012019)",
            "official_split_source": MATBENCH_VALIDATION_URL,
            "primary_metric": "mean outer-fold MAE",
            "id_column": "row_id",
            "input_column": "composition",
            "target_column": "yield_strength_mpa",
            "folds": fold_specs,
            "standard_metrics": ["MAE", "RMSE", "R2"],
            "source_url": STEELS_URL,
        },
    )


def main() -> None:
    prepare_esol()
    prepare_steels()
    print("Prepared Demo-ESOL and Demo-Steels")


if __name__ == "__main__":
    main()
