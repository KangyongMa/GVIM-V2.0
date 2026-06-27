from __future__ import annotations

import gzip
import json
import math
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold


DEMO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEMO_ROOT))
from common import prepare_result_dir, write_json  # noqa: E402


DEMO_ID = "matbench_materials_property_modeling"
TASK_NAME = "matbench_expt_gap"
DATA_URL = "https://ml.materialsproject.org/projects/matbench_expt_gap.json.gz"
DATA_PATH = DEMO_ROOT / "data" / TASK_NAME / f"{TASK_NAME}.json.gz"
FRONTEND_RUNTIME = DEMO_ROOT / "showcase-5" / "runtime" / DEMO_ID
OFFICIAL_RANDOM_STATE = 18012019

PAPER_PROMPT = """Using the uploaded Matbench `matbench_expt_gap` fold, design and execute a reproducible composition-based regression workflow to predict experimental band gaps.

Treat the uploaded manifest as the authoritative task specification. Train using only the labeled training CSV identified by the manifest, and generate a prediction for every row in the corresponding unlabeled test CSV. Select and justify an appropriate composition featurization method and regression algorithm.

Implement the workflow as a portable Python script with a `main()` function and an `if __name__ == "__main__":` guard; avoid uncontrolled multiprocessing.

Produce the following files:

1. `predictions.csv` with exactly these columns: `fold`, `row_id`, `composition`, `predicted_gap_eV`.
2. `run_metadata.json` recording the selected feature method, model class, model parameters, random seeds, package versions used, input row counts, and execution time.
3. `report.md` describing data inspection, method selection, execution, reproducibility settings, and limitations.

The test CSV is unlabeled. Do not report test-set MAE, RMSE, or R2 values.
"""

ELEMENTS = [
    "H",
    "He",
    "Li",
    "Be",
    "B",
    "C",
    "N",
    "O",
    "F",
    "Ne",
    "Na",
    "Mg",
    "Al",
    "Si",
    "P",
    "S",
    "Cl",
    "Ar",
    "K",
    "Ca",
    "Sc",
    "Ti",
    "V",
    "Cr",
    "Mn",
    "Fe",
    "Co",
    "Ni",
    "Cu",
    "Zn",
    "Ga",
    "Ge",
    "As",
    "Se",
    "Br",
    "Kr",
    "Rb",
    "Sr",
    "Y",
    "Zr",
    "Nb",
    "Mo",
    "Tc",
    "Ru",
    "Rh",
    "Pd",
    "Ag",
    "Cd",
    "In",
    "Sn",
    "Sb",
    "Te",
    "I",
    "Xe",
    "Cs",
    "Ba",
    "La",
    "Ce",
    "Pr",
    "Nd",
    "Pm",
    "Sm",
    "Eu",
    "Gd",
    "Tb",
    "Dy",
    "Ho",
    "Er",
    "Tm",
    "Yb",
    "Lu",
    "Hf",
    "Ta",
    "W",
    "Re",
    "Os",
    "Ir",
    "Pt",
    "Au",
    "Hg",
    "Tl",
    "Pb",
    "Bi",
    "Po",
    "At",
    "Rn",
    "Fr",
    "Ra",
    "Ac",
    "Th",
    "Pa",
    "U",
    "Np",
    "Pu",
    "Am",
    "Cm",
    "Bk",
    "Cf",
    "Es",
    "Fm",
    "Md",
    "No",
    "Lr",
    "Rf",
    "Db",
    "Sg",
    "Bh",
    "Hs",
    "Mt",
    "Ds",
    "Rg",
    "Cn",
    "Nh",
    "Fl",
    "Mc",
    "Lv",
    "Ts",
    "Og",
]
ATOMIC_NUMBER = {symbol: index + 1 for index, symbol in enumerate(ELEMENTS)}


def ensure_dataset() -> Path:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_PATH.exists():
        urllib.request.urlretrieve(DATA_URL, DATA_PATH)
    return DATA_PATH


def load_matbench_expt_gap() -> pd.DataFrame:
    path = ensure_dataset()
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    data = pd.DataFrame(payload["data"], columns=payload["columns"])
    data = data.rename(columns={"gap expt": "gap_expt"})
    data.insert(0, "row_id", payload["index"])
    data["gap_expt"] = data["gap_expt"].astype(float)
    return data


def read_number(formula: str, index: int) -> tuple[float, int]:
    start = index
    while index < len(formula) and (formula[index].isdigit() or formula[index] == "."):
        index += 1
    if index == start:
        return 1.0, index
    return float(formula[start:index]), index


def parse_formula(formula: str) -> dict[str, float]:
    formula = formula.strip().replace(" ", "")
    stack: list[defaultdict[str, float]] = [defaultdict(float)]
    index = 0
    while index < len(formula):
        char = formula[index]
        if char in "([{":
            stack.append(defaultdict(float))
            index += 1
            continue
        if char in ")]}":
            if len(stack) == 1:
                raise ValueError(f"Unmatched closing bracket in formula: {formula}")
            group = stack.pop()
            multiplier, index = read_number(formula, index + 1)
            for element, amount in group.items():
                stack[-1][element] += amount * multiplier
            continue
        if char.isupper():
            start = index
            index += 1
            if index < len(formula) and formula[index].islower():
                index += 1
            element = formula[start:index]
            if element not in ATOMIC_NUMBER:
                raise ValueError(f"Unknown element {element!r} in formula: {formula}")
            amount, index = read_number(formula, index)
            stack[-1][element] += amount
            continue
        raise ValueError(f"Unexpected character {char!r} in formula: {formula}")
    if len(stack) != 1:
        raise ValueError(f"Unclosed bracket in formula: {formula}")
    return dict(stack[0])


def featurize_formula(formula: str) -> np.ndarray:
    counts = parse_formula(formula)
    total_atoms = float(sum(counts.values()))
    if total_atoms <= 0:
        raise ValueError(f"Formula has no atoms: {formula}")

    fractions = np.array([counts.get(element, 0.0) / total_atoms for element in ELEMENTS])
    present = fractions > 0
    z = np.array([ATOMIC_NUMBER[element] for element in ELEMENTS], dtype=float)
    weights = fractions
    mean_z = float(np.sum(weights * z))
    std_z = float(math.sqrt(np.sum(weights * (z - mean_z) ** 2)))
    z_present = z[present]
    max_fraction = float(fractions.max())
    entropy = float(-np.sum(fractions[present] * np.log(fractions[present])))
    summary = np.array(
        [
            math.log1p(total_atoms),
            float(present.sum()),
            max_fraction,
            entropy,
            mean_z,
            std_z,
            float(z_present.min()),
            float(z_present.max()),
        ],
        dtype=float,
    )
    return np.concatenate([fractions, summary])


def featurize(formulas: pd.Series) -> np.ndarray:
    return np.vstack([featurize_formula(formula) for formula in formulas])


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(math.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)),
    }


def train_predict_5fold(data: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    x = featurize(data["composition"])
    y = data["gap_expt"].to_numpy(dtype=float)
    splitter = KFold(n_splits=5, shuffle=True, random_state=OFFICIAL_RANDOM_STATE)

    prediction_rows = []
    fold_metrics = []
    for fold, (train_idx, test_idx) in enumerate(splitter.split(x)):
        model = ExtraTreesRegressor(
            n_estimators=500,
            min_samples_leaf=1,
            max_features="sqrt",
            random_state=42 + fold,
            n_jobs=-1,
        )
        model.fit(x[train_idx], y[train_idx])
        pred = np.maximum(model.predict(x[test_idx]), 0.0)

        fold_metrics.append(
            {
                "fold": fold,
                "n_train": int(len(train_idx)),
                "n_test": int(len(test_idx)),
                **regression_metrics(y[test_idx], pred),
            }
        )
        fold_frame = data.iloc[test_idx][["row_id", "composition"]].copy()
        fold_frame["fold"] = fold
        fold_frame["predicted_gap_eV"] = pred
        prediction_rows.append(fold_frame)

    predictions = pd.concat(prediction_rows, ignore_index=True).sort_values("row_id")
    mean_fold = {
        metric: float(np.mean([item[metric] for item in fold_metrics]))
        for metric in ["mae", "rmse", "r2"]
    }
    metrics = {
        "evaluation_protocol": {
            "benchmark": "Matbench v0.1",
            "task": TASK_NAME,
            "task_type": "regression",
            "splitter": "sklearn.model_selection.KFold",
            "n_splits": 5,
            "shuffle": True,
            "random_state": OFFICIAL_RANDOM_STATE,
            "official_score": "mean_fold.mae",
            "standard_metrics": ["mae", "rmse", "r2"],
        },
        "mean_fold": mean_fold,
        "folds": fold_metrics,
    }
    return predictions, metrics


def write_parity_plot(predictions: pd.DataFrame, gold: pd.DataFrame, output_path: Path) -> None:
    paired = predictions.merge(gold, on=["fold", "row_id"], how="inner")
    y_true = paired["gap_expt"].to_numpy(dtype=float)
    y_pred = paired["predicted_gap_eV"].to_numpy(dtype=float)
    limit = max(float(y_true.max()), float(y_pred.max()))
    plt.figure(figsize=(6.5, 6.0))
    plt.scatter(y_true, y_pred, s=14, alpha=0.45, edgecolors="none")
    plt.plot([0, limit], [0, limit], color="black", linewidth=1.2, linestyle="--")
    plt.xlabel("Observed experimental band gap (eV)")
    plt.ylabel("Predicted band gap (eV)")
    plt.title("Matbench expt_gap: observed vs predicted")
    plt.tight_layout()
    plt.savefig(output_path, dpi=220)
    plt.close()


def prepare_frontend_package(data: pd.DataFrame) -> dict[str, str]:
    splitter = KFold(n_splits=5, shuffle=True, random_state=OFFICIAL_RANDOM_STATE)

    input_dir = FRONTEND_RUNTIME / "input"
    isolated_root = FRONTEND_RUNTIME / "isolated_folds"
    gold_dir = FRONTEND_RUNTIME / "gold"
    output_dir = FRONTEND_RUNTIME / "expected_output_schema"
    input_dir.mkdir(parents=True, exist_ok=True)
    isolated_root.mkdir(parents=True, exist_ok=True)
    gold_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    fold_rows = []
    gold_rows = []
    for fold, (train_idx, test_idx) in enumerate(splitter.split(data)):
        train = data.iloc[train_idx][["row_id", "composition", "gap_expt"]].copy()
        test = data.iloc[test_idx][["row_id", "composition"]].copy()
        gold = data.iloc[test_idx][["row_id", "gap_expt"]].copy()
        gold.insert(0, "fold", fold)

        train_path = input_dir / f"matbench_expt_gap_fold{fold}_train.csv"
        test_path = input_dir / f"matbench_expt_gap_fold{fold}_test_unlabeled.csv"
        train.to_csv(train_path, index=False)
        test.to_csv(test_path, index=False)

        isolated_dir = isolated_root / f"fold{fold}"
        isolated_dir.mkdir(parents=True, exist_ok=True)
        isolated_train_path = isolated_dir / train_path.name
        isolated_test_path = isolated_dir / test_path.name
        train.to_csv(isolated_train_path, index=False)
        test.to_csv(isolated_test_path, index=False)
        write_json(
            isolated_dir / "manifest.json",
            {
                "benchmark": "Matbench v0.1",
                "task": TASK_NAME,
                "fold_rule": "KFold(n_splits=5, shuffle=True, random_state=18012019)",
                "fold": fold,
                "id_column": "row_id",
                "input_column": "composition",
                "target_column": "gap_expt",
                "train_csv": isolated_train_path.name,
                "test_csv": isolated_test_path.name,
                "n_train": int(len(train)),
                "n_test": int(len(test)),
            },
        )
        gold_rows.append(gold)
        fold_rows.append(
            {
                "fold": fold,
                "train_csv": train_path.name,
                "test_csv": test_path.name,
                "n_train": int(len(train)),
                "n_test": int(len(test)),
            }
        )

    gold_path = gold_dir / "matbench_expt_gap_5fold_gold.csv"
    fold_manifest_path = input_dir / "matbench_expt_gap_5fold_manifest.json"
    prompt_path = FRONTEND_RUNTIME / "frontend_prompt.md"
    schema_path = output_dir / "required_files.json"

    pd.concat(gold_rows, ignore_index=True).to_csv(gold_path, index=False)
    write_json(
        fold_manifest_path,
        {
            "task": TASK_NAME,
            "fold_rule": "KFold(n_splits=5, shuffle=True, random_state=18012019)",
            "id_column": "row_id",
            "input_column": "composition",
            "target_column": "gap_expt",
            "folds": fold_rows,
        },
    )
    prompt_path.write_text(PAPER_PROMPT, encoding="utf-8")
    write_json(
        schema_path,
        {
            "required_outputs": [
                "predictions.csv",
                "run_metadata.json",
                "report.md",
            ],
            "prediction_columns": ["fold", "row_id", "composition", "predicted_gap_eV"],
            "hidden_gold": str(gold_path),
            "official_fold_rule": "KFold(n_splits=5, shuffle=True, random_state=18012019)",
            "standard_metrics": ["MAE", "RMSE", "R2"],
        },
    )
    return {
        "input_dir": str(input_dir),
        "fold_manifest_json": str(fold_manifest_path),
        "isolated_folds_dir": str(isolated_root),
        "gold_csv": str(gold_path),
        "prompt_md": str(prompt_path),
        "schema_json": str(schema_path),
    }


def write_report(output_dir: Path, metrics: dict[str, object], package: dict[str, str]) -> None:
    mean_fold = metrics["mean_fold"]
    assert isinstance(mean_fold, dict)
    report = [
        "# Matbench Materials Property Modeling Demo",
        "",
        "Task: `matbench_expt_gap`, experimental band gap regression from composition.",
        "",
        "This run is a local reference execution for the first DeerFlow showcase demo.",
        "It follows the Matbench regression fold rule documented for Matbench v0.1:",
        "`KFold(n_splits=5, shuffle=True, random_state=18012019)`.",
        "",
        "## Model",
        "",
        "- Formula parser with elemental-fraction and simple composition statistics.",
        "- ExtraTreesRegressor.",
        "",
        "## Metrics",
        "",
        f"- MAE: {mean_fold['mae']:.4f} eV",
        f"- RMSE: {mean_fold['rmse']:.4f} eV",
        f"- R2: {mean_fold['r2']:.4f}",
        "",
        "MAE is the Matbench v0.1 regression score. RMSE and R2 are standard",
        "regression metrics reported alongside it.",
        "",
        "## Front-End Package",
        "",
        f"- Input directory: `{package['input_dir']}`",
        f"- Fold manifest: `{package['fold_manifest_json']}`",
        f"- Hidden gold CSV: `{package['gold_csv']}`",
        f"- Front-end prompt: `{package['prompt_md']}`",
        "",
        "The hidden gold file should not be uploaded to DeerFlow. It is used only by",
        "the independent evaluator after the front-end run finishes.",
        "",
        "## Caveat",
        "",
        "This is not a leaderboard submission. It is a reproducible model run",
        "designed to validate the DeerFlow end-to-end workflow with public Matbench",
        "data and standard regression metrics.",
    ]
    (output_dir / "model_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def main() -> None:
    data = load_matbench_expt_gap()
    output_dir = prepare_result_dir(DEMO_ID)
    package = prepare_frontend_package(data)

    predictions, metrics = train_predict_5fold(data)
    predictions.to_csv(output_dir / "predictions.csv", index=False)
    gold = pd.read_csv(package["gold_csv"])
    write_parity_plot(predictions, gold, output_dir / "parity_plot.png")
    write_json(
        output_dir / "metrics.json",
        {
            "demo_id": DEMO_ID,
            "task": TASK_NAME,
            "data_url": DATA_URL,
            "data_path": str(DATA_PATH),
            "n_samples": int(len(data)),
            "target": "experimental band gap in eV",
            "fold_rule": "KFold(n_splits=5, shuffle=True, random_state=18012019)",
            "model": "formula features + ExtraTreesRegressor",
            "metrics": metrics,
            "frontend_package": package,
        },
    )
    write_report(output_dir, metrics, package)
    mean_fold = metrics["mean_fold"]
    assert isinstance(mean_fold, dict)
    print(
        f"{DEMO_ID}: MAE={mean_fold['mae']:.4f} eV, "
        f"RMSE={mean_fold['rmse']:.4f} eV, R2={mean_fold['r2']:.4f}"
    )


if __name__ == "__main__":
    main()
