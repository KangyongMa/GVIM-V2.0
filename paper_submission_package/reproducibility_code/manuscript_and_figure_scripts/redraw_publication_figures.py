from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(r"E:\Demo of GVIM\deer-flow-mainnew")
FIG_DIR = ROOT / "manuscript_assets" / "figures"
PUB_DIR = ROOT / "manuscript_assets" / "publication_figures"
SRC_DIR = ROOT / "manuscript_assets" / "source_data"
BACE_FRONTEND = ROOT / "research-demos" / "results" / "frontend_bace_fff9cae7" / "metrics.json"


COL_API = "#C9D4E2"
COL_GVIM = "#0072B2"
COL_RANDOM = "#9AA9BA"
COL_ACTIVE = "#009E73"
COL_UCB = "#0072B2"
COL_GREY = "#E5E9EF"
COL_GOLD = "#E69F00"
COL_DARK = "#25364A"


def set_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "Times New Roman",
            "font.serif": ["Times New Roman"],
            "mathtext.fontset": "stix",
            "mathtext.rm": "Times New Roman",
            "font.size": 7.5,
            "axes.titlesize": 8.8,
            "axes.labelsize": 8.0,
            "xtick.labelsize": 7.4,
            "ytick.labelsize": 7.4,
            "legend.fontsize": 7.3,
            "figure.titlesize": 9.0,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.8,
            "xtick.major.width": 0.8,
            "ytick.major.width": 0.8,
            "grid.linewidth": 0.6,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def panel_label(ax, label: str) -> None:
    ax.text(
        0.015,
        0.985,
        label,
        transform=ax.transAxes,
        fontsize=10.0,
        fontweight="bold",
        va="top",
        ha="left",
        bbox=dict(facecolor="white", edgecolor="none", pad=0.2, alpha=0.9),
    )


def save_figure(fig: plt.Figure, stem: str) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    PUB_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / f"{stem}.png", dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(FIG_DIR / f"{stem}.svg", bbox_inches="tight", facecolor="white")
    fig.savefig(PUB_DIR / f"{stem}.png", dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(PUB_DIR / f"{stem}.tiff", dpi=600, bbox_inches="tight", facecolor="white", pil_kwargs={"compression": "tiff_lzw"})
    fig.savefig(PUB_DIR / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    fig.savefig(PUB_DIR / f"{stem}.svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def redraw_architecture() -> None:
    fig = plt.figure(figsize=(7.4, 5.0))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 1.0], width_ratios=[1.35, 1.0], hspace=0.42, wspace=0.34)
    ax_flow = fig.add_subplot(gs[0, :])
    ax_evidence = fig.add_subplot(gs[1, 0])
    ax_outputs = fig.add_subplot(gs[1, 1])

    for ax in (ax_flow, ax_evidence, ax_outputs):
        ax.set_axis_off()

    def rounded_box(ax, xy, width, height, text, fc, ec="#354153", fontsize=8.2, weight="normal") -> None:
        patch = FancyBboxPatch(
            xy,
            width,
            height,
            boxstyle="round,pad=0.012,rounding_size=0.02",
            facecolor=fc,
            edgecolor=ec,
            linewidth=1.0,
            transform=ax.transAxes,
        )
        ax.add_patch(patch)
        ax.text(
            xy[0] + width / 2,
            xy[1] + height / 2,
            text,
            transform=ax.transAxes,
            ha="center",
            va="center",
            fontsize=fontsize,
            fontweight=weight,
            color="#111827",
            linespacing=1.15,
        )

    def arrow(ax, start, end, rad=0.0) -> None:
        arr = FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=12,
            linewidth=1.0,
            color="#354153",
            connectionstyle=f"arc3,rad={rad}",
            transform=ax.transAxes,
        )
        ax.add_patch(arr)

    panel_label(ax_flow, "a")
    ax_flow.text(
        0.045,
        0.97,
        "End-to-end scientific-agent workflow",
        transform=ax_flow.transAxes,
        ha="left",
        va="top",
        fontsize=10.2,
        fontweight="bold",
    )
    flow_boxes = [
        (0.035, 0.52, 0.12, 0.22, "Research\nquestion", "#E8F2FB"),
        (0.205, 0.52, 0.12, 0.22, "GVIM\nfront end", "#E8F2FB"),
        (0.375, 0.52, 0.13, 0.22, "Planner and\nmemory", "#EAF5F0"),
        (0.560, 0.52, 0.18, 0.22, "Chemistry/materials\nskills", "#EAF5F0"),
        (0.800, 0.52, 0.16, 0.22, "Tools, data,\ncode execution", "#FFF3DC"),
        (0.660, 0.16, 0.16, 0.20, "Native public\nmetrics", "#F3E8F2"),
        (0.445, 0.16, 0.16, 0.20, "Auditable\nartifacts", "#F3E8F2"),
    ]
    for item in flow_boxes:
        rounded_box(ax_flow, item[:2], item[2], item[3], item[4], item[5])
    for x0, x1 in [(0.155, 0.205), (0.325, 0.375), (0.505, 0.560), (0.740, 0.800)]:
        arrow(ax_flow, (x0, 0.63), (x1, 0.63))
    arrow(ax_flow, (0.880, 0.52), (0.740, 0.36))
    arrow(ax_flow, (0.660, 0.26), (0.605, 0.26))
    ax_flow.text(
        0.035,
        0.02,
        "Design principle: final artifacts are evaluated by public task-native metrics, not by subjective conversation quality.",
        transform=ax_flow.transAxes,
        ha="left",
        va="bottom",
        fontsize=7.2,
        color="#5F6D7C",
    )

    panel_label(ax_evidence, "b")
    ax_evidence.text(
        0.065,
        0.97,
        "Evidence layers in the present study",
        transform=ax_evidence.transAxes,
        ha="left",
        va="top",
        fontsize=9.6,
        fontweight="bold",
    )
    evidence = [
        ("Public benchmark QA", "400 tasks; official/native scoring", COL_GVIM),
        ("Task-native demos", "ML, extraction, retrieval, NER", COL_ACTIVE),
        ("Planned tool-use benchmark", "tool selection, parameters, result use", COL_GOLD),
        ("Planned ablations", "skills, tools, memory, verification", "#D55E00"),
    ]
    for i, (head, sub, color) in enumerate(evidence):
        y = 0.74 - i * 0.18
        ax_evidence.add_patch(plt.Rectangle((0.07, y - 0.025), 0.018, 0.05, transform=ax_evidence.transAxes, facecolor=color, edgecolor="none"))
        ax_evidence.text(0.115, y + 0.025, head, transform=ax_evidence.transAxes, ha="left", va="center", fontsize=8.4, fontweight="bold")
        ax_evidence.text(0.115, y - 0.045, sub, transform=ax_evidence.transAxes, ha="left", va="center", fontsize=7.4, color="#5F6D7C")

    panel_label(ax_outputs, "c")
    ax_outputs.text(
        0.10,
        0.97,
        "Output requirements",
        transform=ax_outputs.transAxes,
        ha="left",
        va="top",
        fontsize=9.6,
        fontweight="bold",
    )
    for i, item in enumerate(["predictions.csv", "metrics.json", "report.md", "trace/logs"]):
        rounded_box(ax_outputs, (0.20, 0.72 - i * 0.16), 0.50, 0.095, item, "#F3F5F7", ec="#C9D0D8", fontsize=8.2)
    ax_outputs.text(
        0.20,
        0.09,
        "Artifacts are scored by the\nbenchmark or dataset rule.",
        transform=ax_outputs.transAxes,
        ha="left",
        va="bottom",
        fontsize=7.3,
        color="#5F6D7C",
    )

    fig.subplots_adjust(left=0.035, right=0.985, top=0.965, bottom=0.055)
    save_figure(fig, "Fig1_GVIM_architecture")


def redraw_task_demos() -> None:
    data = pd.read_csv(SRC_DIR / "Fig3_demo_source_data.csv")

    palette = {
        "blue": COL_GVIM,
        "light_blue": "#56B4E9",
        "green": COL_ACTIVE,
        "pink": "#CC79A7",
        "gold": COL_GOLD,
        "grey": "#7A8794",
    }

    def values_for(demo: str) -> dict[str, float]:
        sub = data[data["demo"] == demo]
        return {r.metric: float(r.value) for r in sub.itertuples(index=False)}

    def bar_panel(
        ax,
        labels: list[str],
        values: list[float],
        colors: list[str],
        title: str,
        ylabel: str,
        note: str,
        label: str,
        ylim: tuple[float, float] = (0, 1.12),
        value_labels: list[str] | None = None,
    ) -> None:
        x = np.arange(len(labels))
        bars = ax.bar(x, values, width=0.56, color=colors, edgecolor="white", linewidth=0.8)
        ax.set_ylim(*ylim)
        ax.set_xticks(x, labels)
        ax.set_ylabel(ylabel)
        ax.set_title(title, pad=9, fontweight="bold")
        ax.grid(axis="y", color="#E8EDF3")
        panel_label(ax, label)
        if value_labels is None:
            value_labels = [f"{v:.3f}" if v < 0.995 else f"{v:.2f}" for v in values]
        span = ylim[1] - ylim[0]
        for bar, text in zip(bars, value_labels):
            y = min(bar.get_height() + 0.025 * span, ylim[1] - 0.055 * span)
            ax.text(bar.get_x() + bar.get_width() / 2, y, text, ha="center", va="bottom", fontsize=7.1)
        ax.text(
            0.5,
            -0.22,
            note,
            transform=ax.transAxes,
            ha="center",
            va="top",
            fontsize=6.8,
            color="#5F6D7C",
        )

    esol = values_for("ESOL solubility prediction")
    steels = values_for("Matbench steels")
    reaction = values_for("Reaction table extraction")
    msms = values_for("MS/MS retrieval")
    chemu = values_for("ChEMU entity extraction")

    fig = plt.figure(figsize=(7.4, 5.55))
    gs = fig.add_gridspec(2, 3, wspace=0.44, hspace=0.78)
    axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(3)]

    bar_panel(
        axes[0],
        ["MAE", "RMSE", "R²"],
        [esol["MAE"], esol["RMSE"], esol["R2"]],
        [palette["blue"], palette["light_blue"], palette["green"]],
        "Chemical ML: ESOL",
        "Metric value",
        "MoleculeNet ESOL; n_test=254",
        "a",
    )

    steels_display = [steels["MAE_MPa"] / 240.0, steels["RMSE_MPa"] / 190.0, steels["R2"]]
    bar_panel(
        axes[1],
        ["MAE", "RMSE", "R²"],
        steels_display,
        [palette["blue"], palette["light_blue"], palette["green"]],
        "Materials ML: Matbench steels",
        "Display scale",
        "Matbench v0.1 official fold 0; n_test=63",
        "b",
        value_labels=[f"{steels['MAE_MPa']:.1f} MPa", f"{steels['RMSE_MPa']:.1f} MPa", f"{steels['R2']:.3f}"],
    )

    bar_panel(
        axes[2],
        ["Prec.", "Rec.", "F1", "Row acc."],
        [
            reaction["Exact precision"],
            reaction["Exact recall"],
            reaction["Exact F1"],
            reaction["Exact row accuracy"],
        ],
        [palette["blue"], palette["light_blue"], palette["green"], palette["pink"]],
        "Reaction table extraction",
        "Score",
        "105 cells from publisher JATS gold",
        "c",
    )

    bar_panel(
        axes[3],
        ["Top-1", "Top-3", "Top-5", "MRR"],
        [msms["Top-1 accuracy"], msms["Top-3 accuracy"], msms["Top-5 accuracy"], msms["MRR"]],
        [palette["blue"], palette["light_blue"], palette["green"], palette["pink"]],
        "MS/MS candidate retrieval",
        "Score",
        "5 MassBank queries; InChIKey gold",
        "d",
    )

    bar_panel(
        axes[4],
        ["Prec.", "Rec.", "F1", "Relaxed\nF1"],
        [chemu["Exact precision"], chemu["Exact recall"], chemu["Exact F1"], chemu["Relaxed F1"]],
        [palette["blue"], palette["light_blue"], palette["green"], palette["pink"]],
        "ChEMU entity extraction",
        "Score",
        "92 gold spans; ChEMU sample v3",
        "e",
    )

    ax = axes[5]
    ax.axis("off")
    panel_label(ax, "f")
    ax.set_title("Coverage of workflow types", pad=9, fontweight="bold")
    coverage = [
        ("Property modelling", palette["blue"]),
        ("Materials prediction", palette["light_blue"]),
        ("Data extraction", palette["green"]),
        ("Spectral retrieval", palette["gold"]),
        ("Entity extraction", palette["pink"]),
    ]
    for i, (text, color) in enumerate(coverage):
        y = 0.82 - i * 0.13
        ax.add_patch(plt.Rectangle((0.08, y - 0.025), 0.035, 0.055, transform=ax.transAxes, facecolor=color, edgecolor="none"))
        ax.text(0.15, y, text, transform=ax.transAxes, ha="left", va="center", fontsize=8.0)
    ax.text(
        0.08,
        0.10,
        "Each panel reports task-native objective metrics\ncomputed from labelled public or paper-derived gold data.",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=6.9,
        color="#5F6D7C",
    )

    fig.text(
        0.03,
        0.035,
        "Heterogeneous task metrics are shown as task-native scores; values across tasks are not pooled into a custom aggregate.",
        fontsize=7.0,
        color="#5F6D7C",
    )
    fig.subplots_adjust(left=0.07, right=0.985, top=0.91, bottom=0.13)
    save_figure(fig, "Fig3_task_native_demos")


def redraw_benchmark() -> None:
    df = pd.read_csv(SRC_DIR / "Fig2_benchmark_source_data.csv")
    stats = pd.read_csv(SRC_DIR / "Fig2_paired_statistics.csv").iloc[0]
    model_path = SRC_DIR / "API_only_multimodel_400_source_data.csv"
    model_df = pd.read_csv(model_path) if model_path.exists() else pd.DataFrame()

    labels = []
    for r in df.itertuples(index=False):
        name = "Total" if r.benchmark == "Descriptive total" else r.benchmark
        labels.append(f"{name}\n{int(r.n)}")
    x = np.arange(len(df))
    width = 0.34

    fig = plt.figure(figsize=(7.4, 5.15))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.02, 1.05], width_ratios=[2.05, 1.30], wspace=0.42, hspace=0.72)
    ax = fig.add_subplot(gs[0, 0])
    ax_model = fig.add_subplot(gs[1, 0])
    right = gs[:, 1].subgridspec(2, 1, height_ratios=[3.6, 1.0], hspace=0.22)
    ax2 = fig.add_subplot(right[0])
    ax_stats = fig.add_subplot(right[1])

    b1 = ax.bar(
        x - width / 2,
        df["api_percent"],
        width,
        label="DeepSeek API-only",
        color=COL_API,
        edgecolor="#62758A",
        linewidth=0.8,
    )
    b2 = ax.bar(
        x + width / 2,
        df["gvim_percent"],
        width,
        label="GVIM full system",
        color=COL_GVIM,
        edgecolor="#00527F",
        linewidth=0.8,
    )
    ax.set_ylim(0, 124)
    ax.set_ylabel("Correct responses (%)")
    ax.set_xticks(x, labels)
    ax.grid(axis="y", color="#E8EDF3")
    ax.set_title("Same-base comparison by benchmark", pad=32, fontweight="bold")
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, 1.13),
        ncol=2,
        frameon=False,
        handlelength=1.2,
        columnspacing=1.8,
        borderaxespad=0.0,
    )
    panel_label(ax, "a")

    for bars, values, color in [(b1, df["api_percent"], "#5F6D7C"), (b2, df["gvim_percent"], "#1A1A1A")]:
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 2.2,
                f"{value:.1f}",
                ha="center",
                va="bottom",
                fontsize=7.0,
                color=color,
            )

    if not model_df.empty:
        display = model_df.copy()
        display["label"] = display["model"].replace(
            {
                "meta-llama/llama-4-scout-17b-16e-instruct": "Llama-4 Scout",
                "llama-3.3-70b-versatile": "Llama-3.3 70B",
                "qwen/qwen3-32b": "Qwen3 32B",
                "llama-3.1-8b-instant": "Llama-3.1 8B",
            }
        )
        display = display.sort_values("accuracy_percent", ascending=True)
        y = np.arange(len(display))
        colors = ["#A7B3C2"] * len(display)
        ax_model.barh(y, display["accuracy_percent"], color=colors, edgecolor="white", height=0.52)
        ax_model.axvline(81.25, color=COL_GVIM, linewidth=1.35)
        ax_model.text(
            82.0,
            len(display) - 0.45,
            "GVIM 81.25%",
            color=COL_GVIM,
            fontsize=6.8,
            va="center",
            ha="left",
            bbox=dict(facecolor="white", edgecolor="none", pad=0.15, alpha=0.9),
        )
        ax_model.set_yticks(y, display["label"])
        ax_model.set_xlim(0, 104)
        ax_model.set_xlabel("Correct responses (%)")
        ax_model.set_title("Complete 400-task API-only model ablation", pad=8, fontweight="bold")
        ax_model.grid(axis="x", color="#E8EDF3")
        for yi, (_, r) in enumerate(display.iterrows()):
            ax_model.text(
                r["accuracy_percent"] - 1.0,
                yi,
                f"{r['correct']:.0f}/400 ({r['accuracy_percent']:.1f}%)",
                va="center",
                ha="right",
                fontsize=7.2,
                color="#1A1A1A",
            )
        panel_label(ax_model, "b")
    else:
        ax_model.axis("off")

    cells = [
        (0, 1, "Both correct", int(stats["both_correct"]), COL_RANDOM, "white"),
        (1, 1, "API only", int(stats["api_only_correct"]), COL_GOLD, "#1A1A1A"),
        (0, 0, "GVIM only", int(stats["gvim_only_correct"]), COL_GVIM, "white"),
        (1, 0, "Both wrong", int(stats["both_wrong"]), COL_GREY, "#1A1A1A"),
    ]
    for x0, y0, lab, val, col, text_col in cells:
        ax2.add_patch(plt.Rectangle((x0, y0), 1, 1, facecolor=col, edgecolor="white", linewidth=1.2))
        ax2.text(x0 + 0.5, y0 + 0.5, f"{lab}\n{val}", ha="center", va="center", fontsize=7.4, color=text_col)

    ax2.set_xlim(0, 2)
    ax2.set_ylim(0, 2)
    ax2.set_aspect("equal")
    ax2.set_xticks([0.5, 1.5], ["GVIM\ncorrect", "GVIM\nwrong"])
    ax2.set_yticks([1.5, 0.5], ["API\ncorrect", "API\nwrong"])
    ax2.tick_params(axis="both", length=0, pad=4)
    ax2.set_title("Paired outcomes (n=400)", pad=12, fontweight="bold")
    for spine in ax2.spines.values():
        spine.set_visible(False)
    panel_label(ax2, "c")
    ax_stats.set_axis_off()
    p_value = float(stats["mcnemar_exact_two_sided_p"])
    exponent = int(np.floor(np.log10(p_value)))
    coefficient = p_value / (10**exponent)
    ax_stats.text(
        0.02,
        0.95,
        f"Difference: +{stats['delta_percentage_points']:.1f} percentage points\n"
        f"Bootstrap 95% CI: {stats['bootstrap_ci_low_pp']:.1f} to {stats['bootstrap_ci_high_pp']:.2f}\n"
        rf"Exact McNemar $p={coefficient:.2f}\times10^{{{exponent}}}$",
        transform=ax_stats.transAxes,
        ha="left",
        va="top",
        fontsize=7.0,
        linespacing=1.28,
        bbox=dict(boxstyle="round,pad=0.32", facecolor="#F8FAFC", edgecolor="#B9C6D5", linewidth=0.8),
    )
    ax_stats.text(
        0.02,
        0.05,
        "Paired comparison on the identical 400 questions.",
        transform=ax_stats.transAxes,
        ha="left",
        va="bottom",
        fontsize=6.4,
        color="#5F6D7C",
    )

    fig.subplots_adjust(left=0.085, right=0.985, top=0.91, bottom=0.105)
    save_figure(fig, "Fig2_benchmark_performance")


def metric_arrays(data: dict, policy: str, metric: str) -> tuple[float, float, np.ndarray | None]:
    item = data["aggregated_metrics"][policy][metric]
    values = item.get("values") or item.get("per_seed") or item.get("seed_values")
    values_array = None if values is None else np.asarray(values, dtype=float)
    return float(item["mean"]), float(item["std"]), values_array


def scatter_metric(ax, data: dict, policies: list[tuple[str, str, str]], metric: str, ylabel: str) -> None:
    rng = np.random.default_rng(11)
    xs = np.arange(len(policies))
    for i, (key, label, color) in enumerate(policies):
        mean, std, values = metric_arrays(data, key, metric)
        ax.bar(i, mean, width=0.46, color=color, alpha=0.88, edgecolor="white", linewidth=0.8, zorder=1)
        if values is not None:
            jitter = rng.uniform(-0.11, 0.11, size=len(values))
            ax.scatter(
                np.full(len(values), i) + jitter,
                values,
                s=12,
                color=color,
                alpha=0.55,
                edgecolor="white",
                linewidth=0.3,
                zorder=2,
            )
        ax.errorbar(
            i,
            mean,
            yerr=std,
            fmt="o",
            color="#1A1A1A",
            ecolor="#1A1A1A",
            elinewidth=1.0,
            capsize=3,
            markersize=4,
            zorder=3,
        )
        yr = ax.get_ylim()[1] - ax.get_ylim()[0]
        label_y = min(mean + std + 0.025 * yr, ax.get_ylim()[1] - 0.06 * yr)
        ax.text(i, label_y, f"{mean:.3f}", ha="center", va="bottom", fontsize=6.8)
    ax.set_xticks(xs, [label for _, label, _ in policies], rotation=20, ha="right")
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", color="#EDF1F5")


def redraw_bace() -> None:
    data = json.loads(BACE_FRONTEND.read_text(encoding="utf-8"))
    params = data["experiment_parameters"]
    policies = [
        ("random", "Random", COL_RANDOM),
        ("greedy_surrogate", "Greedy\nsurrogate", COL_ACTIVE),
        ("ucb_surrogate", "UCB", COL_UCB),
    ]

    fig = plt.figure(figsize=(7.2, 4.1))
    gs = fig.add_gridspec(2, 2, wspace=0.28, hspace=0.46)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, 0])
    ax4 = fig.add_subplot(gs[1, 1])

    ax1.set_ylim(0, 0.48)
    scatter_metric(ax1, data, policies, "recall_at_150", "Recall@150")
    ax1.set_title("Fixed-budget target recovery", fontweight="bold")
    panel_label(ax1, "a")

    ax2.set_ylim(0, 5.2)
    scatter_metric(ax2, data, policies, "enrichment_factor_at_150", "Enrichment factor@150")
    ax2.axhline(1.0, color="#8A96A3", linestyle="--", linewidth=0.8)
    ax2.set_title("Enrichment over random prevalence", fontweight="bold")
    panel_label(ax2, "b")

    ax3.set_ylim(7.8, 10.72)
    scatter_metric(ax3, data, policies, "best_pIC50_at_150", "Best pIC50@150")
    ax3.set_title("Best recovered candidate activity", fontweight="bold")
    panel_label(ax3, "c")

    comparisons = [
        (
            "Greedy surrogate\n- random",
            data["aggregated_metrics"]["greedy_surrogate"]["recall_at_150"]["mean"]
            - data["aggregated_metrics"]["random"]["recall_at_150"]["mean"],
            data["bootstrap_95_ci_active_minus_random_recall"]["lower"],
            data["bootstrap_95_ci_active_minus_random_recall"]["upper"],
            COL_ACTIVE,
        ),
        (
            "UCB\n- random",
            data["aggregated_metrics"]["ucb_surrogate"]["recall_at_150"]["mean"]
            - data["aggregated_metrics"]["random"]["recall_at_150"]["mean"],
            data["bootstrap_95_ci_ucb_surrogate_minus_random_recall"]["lower"],
            data["bootstrap_95_ci_ucb_surrogate_minus_random_recall"]["upper"],
            COL_UCB,
        ),
    ]
    y = np.arange(len(comparisons))
    means = np.array([c[1] for c in comparisons])
    lows = np.array([c[2] for c in comparisons])
    highs = np.array([c[3] for c in comparisons])
    colors = [c[4] for c in comparisons]
    ax4.barh(y, means, color=colors, edgecolor="white", height=0.45)
    ax4.errorbar(
        means,
        y,
        xerr=np.vstack([means - lows, highs - means]),
        fmt="none",
        ecolor="#1A1A1A",
        elinewidth=1.0,
        capsize=3,
    )
    for yi, mean, lo, hi in zip(y, means, lows, highs):
        ax4.text(
            0.295,
            yi,
            f"{mean:.3f} [{lo:.3f}, {hi:.3f}]",
            va="center",
            ha="left",
            fontsize=6.8,
            bbox=dict(facecolor="white", edgecolor="none", pad=0.15, alpha=0.9),
        )
    ax4.axvline(0, color="#7A8794", linewidth=0.8)
    ax4.set_yticks(y, [c[0] for c in comparisons])
    ax4.set_xlim(0, 0.44)
    ax4.set_xlabel("Recall@150 improvement")
    ax4.set_title("Bootstrap confidence intervals", fontweight="bold")
    ax4.grid(axis="x", color="#EDF1F5")
    panel_label(ax4, "d")

    fig.suptitle(
        "",
    )
    fig.text(
        0.08,
        0.025,
        f"Dataset: {params['n_molecules']} molecules; top-5% targets n={params['n_high_activity']}; "
        f"budget={params['total_budget']}; seeds={params['n_seeds']}.",
        fontsize=6.8,
        color="#5F6D7C",
    )
    fig.subplots_adjust(left=0.08, right=0.985, top=0.93, bottom=0.16, wspace=0.32, hspace=0.72)
    save_figure(fig, "Fig4_experiment5_bace_active_discovery")


def main() -> None:
    set_style()
    redraw_architecture()
    redraw_benchmark()
    redraw_task_demos()
    redraw_bace()
    print("Redrew Fig1_GVIM_architecture, Fig2_benchmark_performance, Fig3_task_native_demos, and Fig4_experiment5_bace_active_discovery")


if __name__ == "__main__":
    main()
