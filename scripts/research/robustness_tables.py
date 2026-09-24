#!/usr/bin/env python3
"""Turn the campaign aggregates into the LaTeX tables of the article.

Reads the output of robustness_analysis.py and writes paper/tables/robustness-*.tex.
Layout only: every number comes from the aggregates, nothing is selected here.
"""
import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "results-revision/solver-robustness"
POLICIES = ["Base", "Flat-GM", "Flat-L2", "Role-Hybrid"]
SOLVERS = {"gurobi": "Gurobi", "cplex": "CPLEX", "highs": "HiGHS"}
FAMILIES = ["Simple", "SG-Ter-Mer", "Full"]


def read(path):
    """Empty aggregates are normal while a stage is still running."""
    try:
        return pd.read_csv(path)
    except (pd.errors.EmptyDataError, FileNotFoundError):
        return pd.DataFrame()


def order(d):
    d = d.copy()
    d["_f"] = d.family.map({f: i for i, f in enumerate(FAMILIES)})
    d["_s"] = d.solver.map({s: i for i, s in enumerate(SOLVERS)})
    return d.sort_values(["_f", "_s", "gap"]).drop(columns=["_f", "_s"])


def fmt(x, digits=1):
    return "--" if pd.isna(x) else f"{x:,.{digits}f}".replace(",", r"\,")


def par10_table(cells, out):
    """PAR10 in seconds and completion rate, per family x solver x gap."""
    d = order(cells[cells.stage.eq("primary")])
    lines = [r"\begin{tabular}{llr" + "rr" * len(POLICIES) + "}", r"\toprule",
             r"& & & " + " & ".join(r"\multicolumn{2}{c}{%s}" % p for p in POLICIES) + r" \\",
             r"Family & Solver & Gap & " + " & ".join(["PAR10 & Compl."] * len(POLICIES)) + r" \\",
             r"\midrule"]
    for (fam, solver, gap), g in d.groupby(["family", "solver", "gap"], sort=False):
        row = g.set_index("policy")
        vals = []
        for p in POLICIES:
            if p in row.index:
                vals += [fmt(row.loc[p, "par10_mean_s"]),
                         fmt(100 * row.loc[p, "completion_rate"], 0) + r"\%"]
            else:
                vals += ["--", "--"]
        lines.append(f"{fam} & {SOLVERS.get(solver, solver)} & {float(gap)*100:g}\\% & "
                     + " & ".join(vals) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (out / "robustness-par10.tex").write_text("\n".join(lines) + "\n")


def paired_table(paired, out, name="robustness-paired.tex", endpoint="time"):
    """Policy/Base ratio on the instances every policy completed."""
    d = order(paired[paired.stage.eq("primary") & paired.endpoint.eq(endpoint)])
    pol = POLICIES[1:]
    lines = [r"\begin{tabular}{llrr" + "r" * len(pol) + "}", r"\toprule",
             r"Family & Solver & Gap & $n$ & " + " & ".join(pol) + r" \\", r"\midrule"]
    for (fam, solver, gap), g in d.groupby(["family", "solver", "gap"], sort=False):
        row = g.set_index("policy")
        vals = []
        for p in pol:
            if p in row.index:
                r = row.loc[p]
                vals.append(f"{r.geometric_mean_ratio:.3f} [{r.ci_low:.3f}, {r.ci_high:.3f}]")
            else:
                vals.append("--")
        n = int(g.n_pairs.max())
        lines.append(f"{fam} & {SOLVERS.get(solver, solver)} & {float(gap)*100:g}\\% & {n} & "
                     + " & ".join(vals) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (out / name).write_text("\n".join(lines) + "\n")


def clustered_table(clustered, out):
    """Multi-seed ratio with the instance as the resampling unit."""
    d = order(clustered)
    pol = POLICIES[1:]
    lines = [r"\begin{tabular}{llrr" + "r" * len(pol) + "}", r"\toprule",
             r"Family & Solver & Gap & Inst. & " + " & ".join(pol) + r" \\", r"\midrule"]
    for (fam, solver, gap), g in d.groupby(["family", "solver", "gap"], sort=False):
        row = g.set_index("policy")
        vals = [f"{row.loc[p].geometric_mean_ratio:.3f} [{row.loc[p].ci_low:.3f}, "
                f"{row.loc[p].ci_high:.3f}]" if p in row.index else "--" for p in pol]
        lines.append(f"{fam} & {SOLVERS.get(solver, solver)} & {float(gap)*100:g}\\% & "
                     f"{int(g.n_instances.max())} & " + " & ".join(vals) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (out / "robustness-multiseed.tex").write_text("\n".join(lines) + "\n")


def i077_table(runs, out):
    """Outcome of instance077 by version, solver, policy and gap."""
    d = runs[runs.stage.isin(["i077", "i077hist"])].copy()
    if d.empty:
        return
    d["version"] = d.instance.map(lambda s: "corrected" if s.endswith("c") else "historical")
    d["label"] = d.outcome.map(lambda o: {"COMPLETED": "solved", "TIME_LIMIT": "timeout",
                                          "TIME_LIMIT_NO_SOLUTION": "timeout, no incumbent"}.get(o, o))
    lines = [r"\begin{tabular}{lllrl}", r"\toprule",
             r"Version & Solver & Policy & Gap & Outcomes over seeds \\", r"\midrule"]
    for (ver, solver, policy, gap), g in d.groupby(["version", "solver", "policy", "gap"], sort=False):
        counts = g.label.value_counts().to_dict()
        text = ", ".join(f"{v}$\\times$ {k}" for k, v in sorted(counts.items()))
        lines.append(f"{ver} & {SOLVERS.get(solver, solver)} & {policy} & {float(gap)*100:g}\\% & "
                     f"{text} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (out / "robustness-i077.tex").write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--analysis", type=Path, default=BASE / "analysis")
    ap.add_argument("--tables", type=Path, default=ROOT / "paper/tables")
    args = ap.parse_args()
    args.tables.mkdir(parents=True, exist_ok=True)
    cells = read(args.analysis / "cells.csv")
    if len(cells) and cells.stage.eq("primary").any():
        par10_table(cells, args.tables)
    paired = read(args.analysis / "paired-primary.csv")
    if len(paired) and paired.stage.eq("primary").any():
        paired_table(paired, args.tables)
        if paired.endpoint.eq("effort").any():
            paired_table(paired, args.tables, "robustness-paired-effort.tex", "effort")
    clustered = read(args.analysis / "paired-clustered.csv")
    if len(clustered):
        clustered_table(clustered, args.tables)
    runs = read(args.analysis / "runs.csv")
    if len(runs):
        i077_table(runs, args.tables)
    print("wrote", sorted(p.name for p in args.tables.glob("robustness-*.tex")))


if __name__ == "__main__":
    main()
