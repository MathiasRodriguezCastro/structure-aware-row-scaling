#!/usr/bin/env python3
"""Figure of the campaign: conditional effort against failure-sensitive performance.

One point per family, solver, gap and scaled policy. The horizontal axis is the paired
time ratio against Base on the instances every policy completed; the vertical axis is the
PAR10 ratio against Base over the whole assigned pool. Points below one on both axes are
representations that are faster and no worse under failures; the lower right and upper left
quadrants are where the two endpoints disagree.
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter, ScalarFormatter
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "results-revision/solver-robustness"
POLICIES = ["Flat-GM", "Flat-L2", "Role-Hybrid"]
MARK = {"Simple": "o", "SG-Ter-Mer": "s", "Full": "^"}
COLOR = {"gurobi": "#264653", "cplex": "#e76f51", "highs": "#2a9d8f"}
LABEL = {"gurobi": "Gurobi", "cplex": "CPLEX", "highs": "HiGHS"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--analysis", type=Path, default=BASE / "analysis")
    ap.add_argument("--figures", type=Path, default=ROOT / "paper/figs/research")
    args = ap.parse_args()
    cells = pd.read_csv(args.analysis / "cells.csv")
    paired = pd.read_csv(args.analysis / "paired-primary.csv")
    cells = cells[cells.stage.eq("primary")]
    paired = paired[paired.stage.eq("primary") & paired.endpoint.eq("time")]
    if cells.empty or paired.empty:
        raise SystemExit("no primary data yet")
    par10 = cells.pivot_table(index=["family", "solver", "gap"], columns="policy",
                              values="par10_mean_s")
    args.figures.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42, "ps.fonttype": 42})
    fig, axes = plt.subplots(1, len(POLICIES), figsize=(9.5, 3.4), sharex=True, sharey=True,
                             layout="constrained")
    for ax, policy in zip(axes, POLICIES):
        sub = paired[paired.policy.eq(policy)]
        for _, r in sub.iterrows():
            key = (r.family, r.solver, r.gap)
            if key not in par10.index or policy not in par10.columns:
                continue
            base, pol = par10.loc[key, "Base"], par10.loc[key, policy]
            if not (base > 0 and pol > 0):
                continue
            ax.scatter(r.geometric_mean_ratio, pol / base, marker=MARK.get(r.family, "o"),
                       facecolor=COLOR.get(r.solver, "grey"), edgecolor="white", s=55,
                       linewidths=.6, zorder=3,
                       label=f"{LABEL.get(r.solver, r.solver)}, {r.family}")
        ax.axhline(1, color="black", lw=.8, ls="--"); ax.axvline(1, color="black", lw=.8, ls="--")
        ax.set_xscale("log"); ax.set_yscale("log")
        # Log axes around one: a handful of readable ticks, no minor labels.
        for axis, setter in ((ax.xaxis, ax.set_xticks), (ax.yaxis, ax.set_yticks)):
            axis.set_major_formatter(ScalarFormatter())
            axis.set_minor_formatter(NullFormatter())
        ticks = [0.25, 0.5, 0.75, 1, 1.5, 2, 3, 5, 10]
        ax.set_xticks(ticks, [str(v) for v in ticks])
        ax.set_yticks(ticks, [str(v) for v in ticks])
        ax.set_title(f"{policy} vs Base")
        ax.set_xlabel("paired time ratio (completed by all)")
    axes[0].set_ylabel("PAR10 ratio (assigned pool)")
    handles, labels = axes[0].get_legend_handles_labels()
    seen = dict(zip(labels, handles))
    axes[-1].legend(seen.values(), seen.keys(), fontsize=6.5, loc="best", framealpha=.9)
    fig.savefig(args.figures / "robustness-endpoints.pdf", bbox_inches="tight")
    fig.savefig(args.figures / "robustness-endpoints.png", dpi=180, bbox_inches="tight")
    print("wrote", args.figures / "robustness-endpoints.pdf")


if __name__ == "__main__":
    main()
