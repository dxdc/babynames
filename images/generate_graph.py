#!/usr/bin/env python3
"""Generate the cumulative name distribution chart for the README.

Usage:
    python images/generate_graph.py

Reads data/boys.csv and data/girls.csv and writes images/graph.png.
"""

import csv
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker


ROOT = Path(__file__).resolve().parent.parent


def load_cumulative(csv_path: str) -> tuple[list[int], list[float]]:
    """Return (ranks, cumulative_pcts) from a CSV file."""
    ranks: list[int] = []
    pcts: list[float] = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ranks.append(int(row["rank"]))
            pcts.append(float(row["cumulative_pct"]))
    return ranks, pcts


def find_threshold(ranks: list[int], pcts: list[float], target: float) -> tuple[int, float]:
    """Find the rank where cumulative_pct first reaches `target`."""
    for r, p in zip(ranks, pcts):
        if p >= target:
            return r, p
    return ranks[-1], pcts[-1]


def main() -> None:
    boys_path = ROOT / "data" / "boys.csv"
    girls_path = ROOT / "data" / "girls.csv"
    out_path = ROOT / "images" / "graph.png"

    b_ranks, b_pcts = load_cumulative(boys_path)
    g_ranks, g_pcts = load_cumulative(girls_path)

    # Detect year range from data
    max_year = 0
    with open(boys_path, newline="") as f:
        for row in csv.DictReader(f):
            yr = int(row["year_max"])
            if yr > max_year:
                max_year = yr

    # Limit x-axis to 5000 names (the interesting part of the curve)
    x_limit = 5000
    b_r = [r for r in b_ranks if r <= x_limit]
    b_p = [p for r, p in zip(b_ranks, b_pcts) if r <= x_limit]
    g_r = [r for r in g_ranks if r <= x_limit]
    g_p = [p for r, p in zip(g_ranks, g_pcts) if r <= x_limit]

    # Key thresholds
    b90 = find_threshold(b_ranks, b_pcts, 90.0)
    b95 = find_threshold(b_ranks, b_pcts, 95.0)
    g90 = find_threshold(g_ranks, g_pcts, 90.0)
    g95 = find_threshold(g_ranks, g_pcts, 95.0)

    # --- Plot ---------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=180)

    # Colors
    c_boys = "#3b82f6"
    c_girls = "#e11d48"
    c_grid = "#e2e8f0"
    c_text = "#334155"
    c_bg = "#ffffff"

    fig.patch.set_facecolor(c_bg)
    ax.set_facecolor(c_bg)

    # Fill under curves
    ax.fill_between(b_r, b_p, alpha=0.08, color=c_boys, linewidth=0)
    ax.fill_between(g_r, g_p, alpha=0.08, color=c_girls, linewidth=0)

    # Main curves
    ax.plot(b_r, b_p, color=c_boys, linewidth=2.2, label="Boys", zorder=3)
    ax.plot(g_r, g_p, color=c_girls, linewidth=2.2, label="Girls", zorder=3)

    # Threshold annotations
    annotations = [
        (b90, c_boys, (15, 12)),
        (b95, c_boys, (15, 10)),
        (g90, c_girls, (15, -14)),
        (g95, c_girls, (15, 10)),
    ]
    for (rank, pct), color, (dx, dy) in annotations:
        if rank <= x_limit:
            ax.plot(rank, pct, "o", color=color, markersize=5, zorder=4)
            ax.annotate(
                f"{rank:,} names → {pct:.0f}%",
                xy=(rank, pct),
                xytext=(dx, dy),
                textcoords="offset points",
                fontsize=7.5,
                color=color,
                fontweight="600",
                va="center",
            )

    # 90% and 95% horizontal reference lines
    for pct_line in [90, 95]:
        ax.axhline(y=pct_line, color=c_grid, linewidth=0.8, linestyle="--", zorder=1)
        ax.text(
            x_limit + 50,
            pct_line,
            f"{pct_line}%",
            fontsize=7,
            color="#94a3b8",
            va="center",
        )

    # Axes
    ax.set_xlim(0, x_limit)
    ax.set_ylim(0, 100)
    ax.set_xlabel("Number of Names Reviewed", fontsize=10, color=c_text, labelpad=8)
    ax.set_ylabel("Cumulative % of All Babies", fontsize=10, color=c_text, labelpad=8)
    ax.set_title(
        f"Baby Name Distribution (1880–{max_year})",
        fontsize=13,
        fontweight="bold",
        color=c_text,
        pad=12,
    )

    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.tick_params(axis="both", labelsize=8.5, colors=c_text)

    # Grid
    ax.grid(axis="y", color=c_grid, linewidth=0.5, zorder=0)
    ax.grid(axis="x", color=c_grid, linewidth=0.3, zorder=0)
    for spine in ax.spines.values():
        spine.set_color(c_grid)

    # Legend
    ax.legend(
        loc="lower right",
        fontsize=9,
        frameon=True,
        fancybox=False,
        edgecolor=c_grid,
        framealpha=0.95,
    )

    # Subtitle / takeaway
    fig.text(
        0.5,
        -0.01,
        "Reviewing ~2,000–3,000 names covers 90–95% of the most common names.",
        ha="center",
        fontsize=8.5,
        color="#64748b",
        style="italic",
    )

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight", facecolor=c_bg)
    print(f"Saved {out_path} ({os.path.getsize(out_path) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
