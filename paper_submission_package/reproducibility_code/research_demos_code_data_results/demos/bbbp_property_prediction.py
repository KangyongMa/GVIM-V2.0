from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem
from rdkit import RDLogger
from rdkit.Chem import rdFingerprintGenerator
from rdkit.Chem.Scaffolds import MurckoScaffold
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit


DEMO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEMO_ROOT))
from common import prepare_result_dir, resolve_repo_path, write_json  # noqa: E402


DEMO_ID = "bbbp_property_prediction"
DATA_PATH = "benchmarks/_sources/ChemLLMBench/data/property_prediction/BBBP.csv"


def scaffold_split(
    smiles: list[str], labels: np.ndarray, train_fraction: float = 0.8
) -> tuple[list[int], list[int]]:
    scaffolds = []
    for value in smiles:
        mol = Chem.MolFromSmiles(value)
        scaffold = MurckoScaffold.MurckoScaffoldSmiles(mol=mol, includeChirality=False)
        scaffolds.append(scaffold)

    # Select a reproducible scaffold-disjoint split whose test class prevalence is
    # closest to the full dataset. This avoids undefined AUC from a single-class test
    # set while preserving the chemically important scaffold separation.
    overall_rate = float(labels.mean())
    candidates = GroupShuffleSplit(
        n_splits=200,
        train_size=train_fraction,
        random_state=42,
    )
    best: tuple[float, list[int], list[int]] | None = None
    for train_idx, test_idx in candidates.split(smiles, labels, groups=scaffolds):
        if len(np.unique(labels[train_idx])) < 2 or len(np.unique(labels[test_idx])) < 2:
            continue
        score = abs(float(labels[test_idx].mean()) - overall_rate) + abs(
            len(train_idx) / len(labels) - train_fraction
        )
        candidate = (score, train_idx.tolist(), test_idx.tolist())
        if best is None or candidate[0] < best[0]:
            best = candidate
    if best is None:
        raise ValueError("Could not construct a scaffold-disjoint split containing both classes.")
    return best[1], best[2]


def fingerprints(smiles: list[str]) -> tuple[np.ndarray, list[int]]:
    generator = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
    vectors = []
    valid_indices = []
    for index, value in enumerate(smiles):
        mol = Chem.MolFromSmiles(value)
        if mol is None:
            continue
        vectors.append(generator.GetFingerprintAsNumPy(mol))
        valid_indices.append(index)
    return np.asarray(vectors, dtype=np.uint8), valid_indices


def main() -> None:
    RDLogger.DisableLog("rdApp.*")
    data_path = resolve_repo_path(DATA_PATH)
    output_dir = prepare_result_dir(DEMO_ID)

    raw = pd.read_csv(data_path).dropna(subset=["smiles", "p_np"]).reset_index(drop=True)
    x, valid_indices = fingerprints(raw["smiles"].tolist())
    data = raw.iloc[valid_indices].reset_index(drop=True)
    y = data["p_np"].astype(int).to_numpy()

    train_idx, test_idx = scaffold_split(data["smiles"].tolist(), y)
    model = LogisticRegression(
        C=1.0,
        class_weight="balanced",
        max_iter=3000,
        random_state=42,
        solver="liblinear",
    )
    model.fit(x[train_idx], y[train_idx])
    probability = model.predict_proba(x[test_idx])[:, 1]
    prediction = (probability >= 0.5).astype(int)
    y_test = y[test_idx]

    metrics = {
        "accuracy": float(accuracy_score(y_test, prediction)),
        "f1": float(f1_score(y_test, prediction)),
        "roc_auc": float(roc_auc_score(y_test, probability)),
        "pr_auc": float(average_precision_score(y_test, probability)),
    }

    pd.DataFrame(
        {
            "row_id": test_idx,
            "smiles": data.iloc[test_idx]["smiles"].to_numpy(),
            "observed": y_test,
            "predicted": prediction,
            "probability": probability,
        }
    ).to_csv(output_dir / "predictions.csv", index=False)

    write_json(
        output_dir / "metrics.json",
        {
            "demo_id": DEMO_ID,
            "problem": "Blood-brain barrier penetration classification from SMILES",
            "data_path": DATA_PATH,
            "dataset": "BBBP",
            "split": "deterministic Bemis-Murcko scaffold split",
            "model": "Morgan fingerprint + balanced logistic regression",
            "n_total": int(len(data)),
            "n_train": int(len(train_idx)),
            "n_test": int(len(test_idx)),
            "positive_rate_test": float(y_test.mean()),
            "metrics": metrics,
        },
    )
    print(
        f"{DEMO_ID}: accuracy={metrics['accuracy']:.3f}, F1={metrics['f1']:.3f}, "
        f"ROC-AUC={metrics['roc_auc']:.3f}, PR-AUC={metrics['pr_auc']:.3f}"
    )


if __name__ == "__main__":
    main()
