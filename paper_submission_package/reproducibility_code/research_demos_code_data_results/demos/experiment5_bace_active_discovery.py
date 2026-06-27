from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.feature_selection import VarianceThreshold
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import RobustScaler


DEMO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEMO_ROOT))
from common import prepare_result_dir, resolve_repo_path, write_json  # noqa: E402


DEMO_ID = "experiment5_bace_active_discovery"
DATA_PATH = "benchmarks/_sources/ChemLLMBench/data/property_prediction/BACE.csv"

SEEDS = list(range(20))
INITIAL_SIZE = 30
BUDGET = 150
BATCH_SIZE = 10
TARGET_QUANTILE = 0.95
N_TREES = 30
UCB_WEIGHT = 0.75


def prepare_features(data: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    excluded = {"Class", "pIC50", "canvasUID", "CID"}
    numeric = data.select_dtypes(include=[np.number]).drop(columns=list(excluded), errors="ignore")
    feature_names = numeric.columns.tolist()
    pipeline = make_pipeline(
        SimpleImputer(strategy="median"),
        VarianceThreshold(threshold=0.0),
        RobustScaler(with_centering=True, with_scaling=True),
    )
    return pipeline.fit_transform(numeric), feature_names


def bootstrap_ci(values: np.ndarray, seed: int = 20260616, n_bootstrap: int = 10000) -> list[float]:
    rng = np.random.default_rng(seed)
    values = np.asarray(values, dtype=float)
    means = np.empty(n_bootstrap, dtype=float)
    for i in range(n_bootstrap):
        sample = rng.choice(values, size=len(values), replace=True)
        means[i] = sample.mean()
    return [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))]


def choose_candidates(
    x: np.ndarray,
    y: np.ndarray,
    observed: list[int],
    unobserved: set[int],
    seed: int,
    policy: str,
) -> list[int]:
    rng = np.random.default_rng(seed)
    pool = np.asarray(sorted(unobserved))
    if policy == "random":
        return rng.choice(pool, size=min(BATCH_SIZE, len(pool)), replace=False).tolist()

    model = ExtraTreesRegressor(
        n_estimators=N_TREES,
        min_samples_leaf=2,
        max_features=0.35,
        bootstrap=True,
        n_jobs=1,
        random_state=seed,
    )
    model.fit(x[observed], y[observed])
    tree_predictions = np.vstack([tree.predict(x[pool]) for tree in model.estimators_])
    mean = tree_predictions.mean(axis=0)
    std = tree_predictions.std(axis=0)
    if policy == "greedy_surrogate":
        score = mean
    elif policy == "ucb_surrogate":
        score = mean + UCB_WEIGHT * std
    else:
        raise ValueError(f"Unknown policy: {policy}")
    order = np.argsort(score)[-min(BATCH_SIZE, len(pool)) :]
    return pool[order].tolist()


def policy_trajectory(
    x: np.ndarray,
    y: np.ndarray,
    target_mask: np.ndarray,
    seed: int,
    policy: str,
) -> tuple[list[dict[str, Any]], list[int]]:
    rng = np.random.default_rng(seed)
    observed = list(rng.choice(len(y), size=INITIAL_SIZE, replace=False))
    unobserved = set(range(len(y))) - set(observed)
    rows: list[dict[str, Any]] = []

    while True:
        target_count = int(target_mask[observed].sum())
        rows.append(
            {
                "seed": seed,
                "policy": policy,
                "queries": len(observed),
                "targets_found": target_count,
                "target_recall": target_count / int(target_mask.sum()),
                "hit_rate": target_count / len(observed),
                "best_pIC50": float(y[observed].max()),
            }
        )
        if len(observed) >= BUDGET:
            break
        selected = choose_candidates(
            x=x,
            y=y,
            observed=observed,
            unobserved=unobserved,
            seed=seed * 1000 + len(observed),
            policy=policy,
        )
        observed.extend(selected)
        unobserved.difference_update(selected)
    return rows, observed


def summarize_trajectories(
    trajectories: pd.DataFrame,
    final_selections: pd.DataFrame,
    target_fraction: float,
) -> dict[str, dict[str, float]]:
    summary: dict[str, dict[str, float]] = {}
    for policy, group in trajectories.groupby("policy"):
        final = group[group["queries"] == BUDGET].copy()
        final["enrichment_factor"] = final["hit_rate"] / target_fraction
        first_hits = []
        for _, seed_group in group.groupby("seed"):
            hit_rows = seed_group[seed_group["targets_found"] > 0]
            first_hits.append(float(hit_rows["queries"].min()) if len(hit_rows) else float(BUDGET + 1))
        selection_rows = final_selections[final_selections["policy"] == policy]
        summary[policy] = {
            "success_at_budget": float((final["targets_found"] > 0).mean()),
            "queries_to_first_hit_mean": float(np.mean(first_hits)),
            "target_recall_at_budget_mean": float(final["target_recall"].mean()),
            "target_recall_at_budget_std": float(final["target_recall"].std(ddof=1)),
            "hit_rate_at_budget_mean": float(final["hit_rate"].mean()),
            "enrichment_factor_at_budget_mean": float(final["enrichment_factor"].mean()),
            "best_pIC50_at_budget_mean": float(final["best_pIC50"].mean()),
            "top_20_gold_targets_ever_selected": float(
                selection_rows[selection_rows["gold_rank_by_pIC50"] <= 20]["row_index"].nunique()
            ),
        }
    return summary


def make_candidate_frequency_table(
    data: pd.DataFrame,
    y: np.ndarray,
    target_mask: np.ndarray,
    final_observed: list[dict[str, Any]],
) -> pd.DataFrame:
    records = []
    order = np.argsort(-y)
    rank = np.empty_like(order)
    rank[order] = np.arange(1, len(y) + 1)
    for record in final_observed:
        for order, row_index in enumerate(record["observed"], start=1):
            records.append(
                {
                    "seed": record["seed"],
                    "policy": record["policy"],
                    "selection_order": order,
                    "row_index": row_index,
                    "mol": data.loc[row_index, "mol"],
                    "pIC50": float(y[row_index]),
                    "is_top5pct_target": bool(target_mask[row_index]),
                    "gold_rank_by_pIC50": int(rank[row_index]),
                }
            )
    return pd.DataFrame(records)


def make_plots(output_dir: Path, trajectories: pd.DataFrame, metrics_by_policy: dict[str, dict[str, float]]) -> None:
    plt.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 8,
            "axes.linewidth": 0.7,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
        }
    )
    colors = {
        "random": "#94A3B8",
        "greedy_surrogate": "#009E73",
        "ucb_surrogate": "#0072B2",
    }
    labels = {
        "random": "Random",
        "greedy_surrogate": "Greedy surrogate",
        "ucb_surrogate": "UCB surrogate",
    }

    curve = (
        trajectories.groupby(["policy", "queries"])["target_recall"]
        .agg(["mean", "std", "count"])
        .reset_index()
    )
    curve["sem"] = curve["std"].fillna(0) / np.sqrt(curve["count"])
    fig, ax = plt.subplots(figsize=(5.3, 3.6), dpi=300)
    for policy, group in curve.groupby("policy"):
        x_axis = group["queries"].to_numpy(dtype=float)
        mean = group["mean"].to_numpy(dtype=float)
        sem = group["sem"].to_numpy(dtype=float)
        ax.plot(x_axis, mean, marker="o", ms=3, lw=1.4, color=colors[policy], label=labels[policy])
        ax.fill_between(x_axis, mean - 1.96 * sem, mean + 1.96 * sem, color=colors[policy], alpha=0.14, lw=0)
    ax.set_xlabel("Number of queried molecules")
    ax.set_ylabel("Recall of top-5% pIC50 targets")
    ax.set_title("Retrospective active discovery on BACE", fontweight="bold")
    ax.legend(frameon=False)
    ax.grid(axis="y", color="#E5E7EB", lw=0.5)
    fig.tight_layout()
    fig.savefig(output_dir / "active_discovery_recall_curve.svg", bbox_inches="tight")
    fig.savefig(output_dir / "active_discovery_recall_curve.png", dpi=600, bbox_inches="tight")
    plt.close(fig)

    policies = ["random", "greedy_surrogate", "ucb_surrogate"]
    recall = [metrics_by_policy[p]["target_recall_at_budget_mean"] for p in policies]
    ef = [metrics_by_policy[p]["enrichment_factor_at_budget_mean"] for p in policies]
    x_axis = np.arange(len(policies))
    fig, axes = plt.subplots(1, 2, figsize=(6.2, 3.0), dpi=300)
    axes[0].bar(x_axis, recall, color=[colors[p] for p in policies], width=0.62)
    axes[0].set_xticks(x_axis)
    axes[0].set_xticklabels([labels[p] for p in policies], rotation=25, ha="right")
    axes[0].set_ylabel("Recall@150")
    axes[0].set_ylim(0, max(recall) * 1.28)
    axes[0].grid(axis="y", color="#E5E7EB", lw=0.5)
    for i, value in enumerate(recall):
        axes[0].text(i, value + max(recall) * 0.04, f"{value:.3f}", ha="center", fontsize=7)

    axes[1].bar(x_axis, ef, color=[colors[p] for p in policies], width=0.62)
    axes[1].set_xticks(x_axis)
    axes[1].set_xticklabels([labels[p] for p in policies], rotation=25, ha="right")
    axes[1].set_ylabel("Enrichment factor@150")
    axes[1].set_ylim(0, max(ef) * 1.28)
    axes[1].grid(axis="y", color="#E5E7EB", lw=0.5)
    for i, value in enumerate(ef):
        axes[1].text(i, value + max(ef) * 0.04, f"{value:.2f}", ha="center", fontsize=7)
    fig.tight_layout()
    fig.savefig(output_dir / "budget_metrics.svg", bbox_inches="tight")
    fig.savefig(output_dir / "budget_metrics.png", dpi=600, bbox_inches="tight")
    plt.close(fig)


def write_report(
    output_dir: Path,
    metrics_payload: dict[str, Any],
    candidate_frequency: pd.DataFrame,
) -> None:
    top_ucb = (
        candidate_frequency[candidate_frequency["policy"] == "ucb_surrogate"]
        .groupby(["row_index", "mol", "pIC50", "is_top5pct_target", "gold_rank_by_pIC50"])
        .agg(selection_frequency=("seed", "nunique"), median_selection_order=("selection_order", "median"))
        .reset_index()
        .sort_values(["is_top5pct_target", "selection_frequency", "pIC50"], ascending=[False, False, False])
        .head(12)
    )
    m = metrics_payload["metrics"]
    random = m["random"]
    greedy = m["greedy_surrogate"]
    ucb = m["ucb_surrogate"]
    report = f"""# Experiment 5: Retrospective Active Discovery of High-Activity BACE Inhibitors

## Scientific Question

Can a GVIM-style agent workflow organize a closed-loop molecular screening task and prioritize high-activity BACE inhibitor candidates from a public chemical library using only a limited query budget?

## Public Data And Gold Standard

- Dataset: ChemLLMBench copy of the MoleculeNet BACE table (`{DATA_PATH}`).
- Candidate library size: {metrics_payload['n_candidates']} molecules.
- Gold label: public experimental `pIC50`.
- High-activity target definition: molecules with `pIC50 >= {metrics_payload['target_threshold_pIC50']:.4f}`, corresponding to the top {int((1 - TARGET_QUANTILE) * 100)}% of the dataset.
- Number of gold targets: {metrics_payload['n_targets']}.

The gold labels of unqueried molecules are used only for retrospective evaluation.

## Workflow

1. Start each run with {INITIAL_SIZE} randomly queried molecules.
2. Train a surrogate model on only the queried molecules.
3. Select the next batch of {BATCH_SIZE} molecules using either random selection, greedy surrogate exploitation, or UCB-style exploration-exploitation.
4. Repeat until {BUDGET} molecules have been queried.
5. Evaluate the selected set against the public pIC50 gold standard.

## Objective Metrics

| Policy | Recall@{BUDGET} | Hit rate@{BUDGET} | Enrichment factor@{BUDGET} | Success@{BUDGET} | Mean best pIC50 |
|---|---:|---:|---:|---:|---:|
| Random | {random['target_recall_at_budget_mean']:.4f} | {random['hit_rate_at_budget_mean']:.4f} | {random['enrichment_factor_at_budget_mean']:.2f} | {random['success_at_budget']:.2f} | {random['best_pIC50_at_budget_mean']:.3f} |
| Greedy surrogate | {greedy['target_recall_at_budget_mean']:.4f} | {greedy['hit_rate_at_budget_mean']:.4f} | {greedy['enrichment_factor_at_budget_mean']:.2f} | {greedy['success_at_budget']:.2f} | {greedy['best_pIC50_at_budget_mean']:.3f} |
| UCB surrogate | {ucb['target_recall_at_budget_mean']:.4f} | {ucb['hit_rate_at_budget_mean']:.4f} | {ucb['enrichment_factor_at_budget_mean']:.2f} | {ucb['success_at_budget']:.2f} | {ucb['best_pIC50_at_budget_mean']:.3f} |

Paired bootstrap 95% CI for UCB minus random Recall@{BUDGET}: {metrics_payload['paired_deltas']['ucb_minus_random_recall_at_budget_ci95'][0]:.4f} to {metrics_payload['paired_deltas']['ucb_minus_random_recall_at_budget_ci95'][1]:.4f}.

## Frequently Selected UCB Candidates

| Row | pIC50 | Gold rank | Top-5% target | Selection frequency |
|---:|---:|---:|---:|---:|
"""
    for _, row in top_ucb.iterrows():
        report += (
            f"| {int(row['row_index'])} | {row['pIC50']:.3f} | {int(row['gold_rank_by_pIC50'])} | "
            f"{bool(row['is_top5pct_target'])} | {int(row['selection_frequency'])}/{len(SEEDS)} |\n"
        )
    report += """
## Interpretation

This experiment does not claim experimental validation or a new BACE inhibitor. It is a retrospective, public-label virtual screening experiment. Its value for the GVIM manuscript is that it connects an agentic workflow to a real chemical discovery-style task with objective metrics: top-target recall, hit rate, enrichment factor, and best observed activity under a fixed query budget.

For a Chemical Science submission, this experiment should be rerun through the GVIM front end with the same frozen input files, prompt, random seeds, and scoring script, then reported together with the workflow trace and generated artifacts.
"""
    (output_dir / "report.md").write_text(report, encoding="utf-8")


def main() -> None:
    data_path = resolve_repo_path(DATA_PATH)
    output_dir = prepare_result_dir(DEMO_ID)
    data = pd.read_csv(data_path).dropna(subset=["pIC50", "mol"]).reset_index(drop=True)
    x, feature_names = prepare_features(data)
    y = data["pIC50"].astype(float).to_numpy()
    threshold = float(np.quantile(y, TARGET_QUANTILE))
    target_mask = y >= threshold
    target_fraction = float(target_mask.mean())

    all_rows: list[dict[str, Any]] = []
    final_observed: list[dict[str, Any]] = []
    policies = ["random", "greedy_surrogate", "ucb_surrogate"]
    for seed in SEEDS:
        for policy in policies:
            rows, observed = policy_trajectory(x, y, target_mask, seed, policy)
            all_rows.extend(rows)
            final_observed.append({"seed": seed, "policy": policy, "observed": observed})

    trajectories = pd.DataFrame(all_rows)
    final_selections = make_candidate_frequency_table(data, y, target_mask, final_observed)
    metrics_by_policy = summarize_trajectories(trajectories, final_selections, target_fraction)

    final = trajectories[trajectories["queries"] == BUDGET].copy()
    final["enrichment_factor"] = final["hit_rate"] / target_fraction
    pivot_recall = final.pivot(index="seed", columns="policy", values="target_recall")
    pivot_ef = final.pivot(index="seed", columns="policy", values="enrichment_factor")
    paired_deltas = {
        "ucb_minus_random_recall_at_budget_mean": float(
            (pivot_recall["ucb_surrogate"] - pivot_recall["random"]).mean()
        ),
        "ucb_minus_random_recall_at_budget_ci95": bootstrap_ci(
            (pivot_recall["ucb_surrogate"] - pivot_recall["random"]).to_numpy()
        ),
        "ucb_minus_random_enrichment_factor_at_budget_mean": float(
            (pivot_ef["ucb_surrogate"] - pivot_ef["random"]).mean()
        ),
        "ucb_minus_random_enrichment_factor_at_budget_ci95": bootstrap_ci(
            (pivot_ef["ucb_surrogate"] - pivot_ef["random"]).to_numpy()
        ),
    }

    trajectories.to_csv(output_dir / "trajectories.csv", index=False)
    final_selections.to_csv(output_dir / "final_selected_candidates.csv", index=False)
    final.to_csv(output_dir / "final_seed_metrics.csv", index=False)

    metrics_payload: dict[str, Any] = {
        "demo_id": DEMO_ID,
        "problem": "Retrospective active discovery of high-activity BACE inhibitor candidates",
        "data_path": DATA_PATH,
        "dataset": "BACE molecular property dataset as distributed with ChemLLMBench",
        "gold_standard": "public pIC50 values",
        "n_candidates": int(len(data)),
        "n_features_after_preprocessing": int(x.shape[1]),
        "target_definition": f"pIC50 >= dataset {TARGET_QUANTILE:.0%} quantile",
        "target_threshold_pIC50": threshold,
        "n_targets": int(target_mask.sum()),
        "target_fraction": target_fraction,
        "initial_size": INITIAL_SIZE,
        "budget": BUDGET,
        "batch_size": BATCH_SIZE,
        "seeds": SEEDS,
        "policies": policies,
        "surrogate_model": {
            "model": "ExtraTreesRegressor",
            "n_estimators": N_TREES,
            "max_features": 0.35,
            "ucb_weight": UCB_WEIGHT,
        },
        "metrics": metrics_by_policy,
        "paired_deltas": paired_deltas,
        "output_files": {
            "trajectories": "trajectories.csv",
            "final_seed_metrics": "final_seed_metrics.csv",
            "final_selected_candidates": "final_selected_candidates.csv",
            "report": "report.md",
            "recall_curve": "active_discovery_recall_curve.svg",
            "budget_metrics": "budget_metrics.svg",
        },
    }
    write_json(output_dir / "metrics.json", metrics_payload)

    make_plots(output_dir, trajectories, metrics_by_policy)
    write_report(output_dir, metrics_payload, final_selections)

    source = pd.DataFrame(
        [
            {
                "policy": policy,
                **metrics_by_policy[policy],
            }
            for policy in policies
        ]
    )
    source.to_csv(output_dir / "source_data_budget_metrics.csv", index=False)

    for policy in policies:
        m = metrics_by_policy[policy]
        print(
            f"{policy}: recall@{BUDGET}={m['target_recall_at_budget_mean']:.3f}, "
            f"hit_rate={m['hit_rate_at_budget_mean']:.3f}, "
            f"EF={m['enrichment_factor_at_budget_mean']:.2f}, "
            f"best_pIC50={m['best_pIC50_at_budget_mean']:.3f}"
        )
    print(
        "UCB minus random recall delta "
        f"{paired_deltas['ucb_minus_random_recall_at_budget_mean']:.3f} "
        f"(95% CI {paired_deltas['ucb_minus_random_recall_at_budget_ci95'][0]:.3f}, "
        f"{paired_deltas['ucb_minus_random_recall_at_budget_ci95'][1]:.3f})"
    )


if __name__ == "__main__":
    main()
