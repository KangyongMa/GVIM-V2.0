from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(r"E:\Demo of GVIM\deer-flow-mainnew")
RESULTS = ROOT / "research-demos" / "results" / "frontend_bace_temporal_9ae4e85f"
FIGURES = ROOT / "manuscript_assets" / "figures"
PUBLICATION = ROOT / "manuscript_assets" / "publication_figures"

BLUE = "#0072B2"
LIGHT_BLUE = "#56B4E9"
GREEN = "#009E73"
ORANGE = "#E69F00"
GREY = "#9AA9BA"
GRID = "#E7ECF2"


def metric(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float, float]:
    residual = y_true - y_pred
    mae = float(np.mean(np.abs(residual)))
    rmse = float(np.sqrt(np.mean(residual**2)))
    r2 = float(1 - np.sum(residual**2) / np.sum((y_true - np.mean(y_true)) ** 2))
    return mae, rmse, r2


def panel_label(axis: plt.Axes, label: str) -> None:
    axis.text(
        0.01,
        0.99,
        label,
        transform=axis.transAxes,
        ha="left",
        va="top",
        fontsize=10,
        fontweight="bold",
        bbox=dict(facecolor="white", edgecolor="none", pad=0.2, alpha=0.9),
    )


def main() -> None:
    plt.rcParams.update(
        {
            "font.family": "Times New Roman",
            "font.serif": ["Times New Roman"],
            "mathtext.fontset": "stix",
            "mathtext.rm": "Times New Roman",
            "font.size": 7.5,
            "axes.titlesize": 9,
            "axes.labelsize": 8,
            "xtick.labelsize": 7.3,
            "ytick.labelsize": 7.3,
            "legend.fontsize": 7.2,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.8,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    cv = pd.read_csv(RESULTS / "cv_results.csv")
    external = pd.read_csv(RESULTS / "external_predictions_with_gold.csv")
    metrics = json.loads((RESULTS / "metrics.json").read_text(encoding="utf-8"))

    models = ["Ridge", "RandomForest", "ExtraTrees"]
    cv_fold = cv[cv["fold"].astype(str).isin(["0", "1", "2"])].copy()
    cv_means = [float(cv_fold.loc[cv_fold["model"] == model, "MAE"].mean()) for model in models]
    cv_stds = [float(cv_fold.loc[cv_fold["model"] == model, "MAE"].std(ddof=0)) for model in models]

    y_true = external["pIC50"].to_numpy(dtype=float)
    y_pred = external["prediction_selected"].to_numpy(dtype=float)
    mae, rmse, r2 = metric(y_true, y_pred)

    subset_errors = []
    for novel in (0, 1):
        subset = external[external["scaffold_novel"] == novel]
        subset_errors.append(
            metric(
                subset["pIC50"].to_numpy(dtype=float),
                subset["prediction_selected"].to_numpy(dtype=float),
            )[:2]
        )

    ranking = {row["subset"]: row for row in metrics["ranking_metrics"]}
    rank_keys = ["all_external", "scaffold_novel_0", "scaffold_novel_1"]

    fig = plt.figure(figsize=(7.4, 5.1))
    grid = fig.add_gridspec(2, 2, hspace=0.48, wspace=0.34)
    ax_a = fig.add_subplot(grid[0, 0])
    ax_b = fig.add_subplot(grid[0, 1])
    ax_c = fig.add_subplot(grid[1, 0])
    ax_d = fig.add_subplot(grid[1, 1])

    x = np.arange(len(models))
    bars = ax_a.bar(
        x,
        cv_means,
        yerr=cv_stds,
        capsize=3,
        color=[GREY, BLUE, LIGHT_BLUE],
        edgecolor="white",
        linewidth=0.8,
        width=0.58,
    )
    ax_a.set_xticks(x, models)
    ax_a.set_ylabel("Validation MAE (pIC50 units)")
    ax_a.set_title("Scaffold-grouped model selection", fontweight="bold", pad=8)
    ax_a.grid(axis="y", color=GRID)
    ax_a.set_ylim(0, 0.76)
    for bar, value in zip(bars, cv_means):
        ax_a.text(bar.get_x() + bar.get_width() / 2, value + 0.025, f"{value:.3f}", ha="center")
    panel_label(ax_a, "a")

    known = external["scaffold_novel"] == 0
    ax_b.scatter(y_true[known], y_pred[known], s=9, alpha=0.50, color=BLUE, edgecolor="none", label="Known scaffold")
    ax_b.scatter(y_true[~known], y_pred[~known], s=9, alpha=0.35, color=ORANGE, edgecolor="none", label="Novel scaffold")
    limits = (3.8, 11.2)
    ax_b.plot(limits, limits, color="#59636F", linewidth=0.9, linestyle="--")
    ax_b.set_xlim(*limits)
    ax_b.set_ylim(*limits)
    ax_b.set_xlabel("Experimental pIC50")
    ax_b.set_ylabel("Predicted pIC50")
    ax_b.set_title("Post-2018 temporal external set", fontweight="bold", pad=8)
    ax_b.grid(color=GRID)
    ax_b.legend(loc="upper left", frameon=False, markerscale=1.4)
    ax_b.text(
        0.97,
        0.04,
        f"n={len(external)}\nMAE={mae:.3f}\nRMSE={rmse:.3f}\n$R^2$={r2:.3f}",
        transform=ax_b.transAxes,
        ha="right",
        va="bottom",
        bbox=dict(facecolor="white", edgecolor="#BAC4D0", boxstyle="round,pad=0.25"),
    )
    panel_label(ax_b, "b")

    labels = ["Known\n(n=323)", "Novel\n(n=1,275)"]
    width = 0.32
    x2 = np.arange(2)
    mae_values = [value[0] for value in subset_errors]
    rmse_values = [value[1] for value in subset_errors]
    bar_mae = ax_c.bar(x2 - width / 2, mae_values, width, color=BLUE, label="MAE")
    bar_rmse = ax_c.bar(x2 + width / 2, rmse_values, width, color=LIGHT_BLUE, label="RMSE")
    ax_c.set_xticks(x2, labels)
    ax_c.set_ylabel("Error (pIC50 units)")
    ax_c.set_title("Scaffold generalization", fontweight="bold", pad=8)
    ax_c.grid(axis="y", color=GRID)
    ax_c.legend(frameon=False, ncol=2, loc="upper left")
    ax_c.set_ylim(0, 1.18)
    for bars_group in (bar_mae, bar_rmse):
        for bar in bars_group:
            ax_c.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.025, f"{bar.get_height():.3f}", ha="center")
    panel_label(ax_c, "c")

    recall = [ranking[key]["recall_at_k"] for key in rank_keys]
    enrichment = [ranking[key]["enrichment_factor"] for key in rank_keys]
    bars_d = ax_d.bar(x2.tolist() + [2], recall, width=0.56, color=[GREEN, BLUE, ORANGE], edgecolor="white")
    ax_d.set_xticks([0, 1, 2], ["All external", "Known\nscaffold", "Novel\nscaffold"])
    ax_d.set_ylabel("Top-10% recall at k=10%")
    ax_d.set_title("Fixed-budget virtual screening", fontweight="bold", pad=8)
    ax_d.grid(axis="y", color=GRID)
    ax_d.set_ylim(0, 0.52)
    for bar, rec, ef in zip(bars_d, recall, enrichment):
        ax_d.text(
            bar.get_x() + bar.get_width() / 2,
            rec + 0.018,
            f"Recall={rec:.3f}\nEF={ef:.2f}",
            ha="center",
            va="bottom",
            fontsize=7.0,
        )
    panel_label(ax_d, "d")

    fig.text(
        0.075,
        0.015,
        "Historical training: 5,296 compounds (document year <=2015); external validation: 1,598 non-overlapping compounds (document year >=2018).",
        fontsize=6.8,
        color="#5F6D7C",
    )
    fig.subplots_adjust(left=0.08, right=0.985, top=0.96, bottom=0.10)

    FIGURES.mkdir(parents=True, exist_ok=True)
    PUBLICATION.mkdir(parents=True, exist_ok=True)
    stem = "Fig6_bace_temporal_external_validation"
    for directory in (FIGURES, PUBLICATION):
        fig.savefig(directory / f"{stem}.png", dpi=600, bbox_inches="tight", facecolor="white")
        fig.savefig(directory / f"{stem}.svg", bbox_inches="tight", facecolor="white")
    fig.savefig(PUBLICATION / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    fig.savefig(
        PUBLICATION / f"{stem}.tiff",
        dpi=600,
        bbox_inches="tight",
        facecolor="white",
        pil_kwargs={"compression": "tiff_lzw"},
    )
    plt.close(fig)


if __name__ == "__main__":
    main()
