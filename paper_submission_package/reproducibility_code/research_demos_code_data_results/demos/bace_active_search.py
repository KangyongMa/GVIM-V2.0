from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.impute import SimpleImputer
from sklearn.feature_selection import VarianceThreshold
from sklearn.pipeline import make_pipeline


DEMO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEMO_ROOT))
from common import prepare_result_dir, resolve_repo_path, write_json  # noqa: E402


DEMO_ID = "bace_active_search"
DATA_PATH = "benchmarks/_sources/ChemLLMBench/data/property_prediction/BACE.csv"
SEEDS = list(range(10))
INITIAL_SIZE = 20
BUDGET = 60
BATCH_SIZE = 5
TARGET_QUANTILE = 0.99


def prepare_features(data: pd.DataFrame) -> np.ndarray:
    excluded = {"Class", "pIC50", "canvasUID"}
    numeric = data.select_dtypes(include=[np.number]).drop(columns=list(excluded), errors="ignore")
    pipeline = make_pipeline(
        SimpleImputer(strategy="median"),
        VarianceThreshold(threshold=0.0),
    )
    return pipeline.fit_transform(numeric)


def policy_trajectory(
    x: np.ndarray,
    y: np.ndarray,
    target_mask: np.ndarray,
    seed: int,
    policy: str,
) -> list[dict[str, float | int | str]]:
    rng = np.random.default_rng(seed)
    observed = list(rng.choice(len(y), size=INITIAL_SIZE, replace=False))
    unobserved = set(range(len(y))) - set(observed)
    initial_found = int(target_mask[observed].sum())
    rows: list[dict[str, float | int | str]] = [
        {
            "seed": seed,
            "policy": policy,
            "queries": len(observed),
            "targets_found": initial_found,
            "target_recall": initial_found / int(target_mask.sum()),
            "best_pIC50": float(y[observed].max()),
        }
    ]

    while len(observed) < BUDGET:
        if policy == "random":
            selected = list(rng.choice(sorted(unobserved), size=BATCH_SIZE, replace=False))
        else:
            model = ExtraTreesRegressor(
                n_estimators=80,
                min_samples_leaf=2,
                max_features=0.7,
                n_jobs=-1,
                random_state=seed + len(observed),
            )
            model.fit(x[observed], y[observed])
            pool = np.asarray(sorted(unobserved))
            tree_predictions = np.vstack([tree.predict(x[pool]) for tree in model.estimators_])
            score = tree_predictions.mean(axis=0) + tree_predictions.std(axis=0)
            selected = pool[np.argsort(score)[-BATCH_SIZE:]].tolist()

        observed.extend(selected)
        unobserved.difference_update(selected)
        found = int(target_mask[observed].sum())
        rows.append(
            {
                "seed": seed,
                "policy": policy,
                "queries": len(observed),
                "targets_found": found,
                "target_recall": found / int(target_mask.sum()),
                "best_pIC50": float(y[observed].max()),
            }
        )
    return rows


def summarize(trajectories: pd.DataFrame, target_fraction: float) -> dict[str, dict[str, float]]:
    summary: dict[str, dict[str, float]] = {}
    for policy, group in trajectories.groupby("policy"):
        final = group[group["queries"] == BUDGET]
        first_hits = []
        for _, seed_group in group.groupby("seed"):
            hit_rows = seed_group[seed_group["targets_found"] > 0]
            first_hits.append(float(hit_rows["queries"].min()) if len(hit_rows) else float(BUDGET + 1))
        summary[policy] = {
            "success_at_budget": float((final["targets_found"] > 0).mean()),
            "queries_to_first_hit_mean": float(np.mean(first_hits)),
            "target_recall_at_budget_mean": float(final["target_recall"].mean()),
            "enrichment_factor_at_budget_mean": float(
                (final["targets_found"] / BUDGET / target_fraction).mean()
            ),
            "best_pIC50_at_budget_mean": float(final["best_pIC50"].mean()),
        }
    return summary


def main() -> None:
    data_path = resolve_repo_path(DATA_PATH)
    output_dir = prepare_result_dir(DEMO_ID)
    data = pd.read_csv(data_path).dropna(subset=["pIC50"]).reset_index(drop=True)
    x = prepare_features(data)
    y = data["pIC50"].astype(float).to_numpy()
    threshold = float(np.quantile(y, TARGET_QUANTILE))
    target_mask = y >= threshold

    rows = []
    for seed in SEEDS:
        rows.extend(policy_trajectory(x, y, target_mask, seed, "random"))
        rows.extend(policy_trajectory(x, y, target_mask, seed, "ucb_surrogate"))
    trajectories = pd.DataFrame(rows)
    trajectories.to_csv(output_dir / "trajectories.csv", index=False)

    summary = summarize(trajectories, float(target_mask.mean()))
    write_json(
        output_dir / "metrics.json",
        {
            "demo_id": DEMO_ID,
            "problem": "Closed-loop discovery of high-activity BACE inhibitor candidates",
            "inspiration": "Reasoning-guided active search in s41524-026-02139-1",
            "data_path": DATA_PATH,
            "n_candidates": int(len(data)),
            "n_features": int(x.shape[1]),
            "target_definition": f"pIC50 >= dataset {TARGET_QUANTILE:.0%} quantile",
            "target_threshold_pIC50": threshold,
            "n_targets": int(target_mask.sum()),
            "initial_size": INITIAL_SIZE,
            "budget": BUDGET,
            "batch_size": BATCH_SIZE,
            "seeds": SEEDS,
            "metrics": summary,
        },
    )

    plot_data = trajectories.groupby(["policy", "queries"])["target_recall"].agg(["mean", "std"]).reset_index()
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    for policy, group in plot_data.groupby("policy"):
        x_axis = group["queries"].to_numpy(dtype=float)
        mean = group["mean"].to_numpy(dtype=float)
        std = group["std"].fillna(0).to_numpy(dtype=float)
        ax.plot(x_axis, mean, marker="o", label=policy)
        ax.fill_between(x_axis, mean - std, mean + std, alpha=0.15)
    ax.set_xlabel("Candidates queried")
    ax.set_ylabel("Recall of top-5% activity candidates")
    ax.set_title("Closed-loop candidate discovery")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "active_search_recall.png", dpi=180)
    plt.close(fig)

    for policy, values in summary.items():
        print(
            f"{DEMO_ID}/{policy}: success={values['success_at_budget']:.3f}, "
            f"recall={values['target_recall_at_budget_mean']:.3f}, "
            f"EF={values['enrichment_factor_at_budget_mean']:.2f}"
        )


if __name__ == "__main__":
    main()
