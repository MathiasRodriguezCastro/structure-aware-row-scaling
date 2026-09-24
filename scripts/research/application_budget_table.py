#!/usr/bin/env python3
"""LaTeX table of the declared-budget analysis on one dispatch model."""
import argparse
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def sci(x, digits=1):
    """Three significant digits near one, scientific notation away from it."""
    if x == 0:
        return "0"
    e = int(math.floor(math.log10(abs(x))))
    m = x / 10.0**e
    if -2 <= e <= 2:
        return f"{x:#.3g}".rstrip("0").rstrip(".")
    return rf"${m:.{digits}f}\times10^{{{e}}}$"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path,
                    default=ROOT / "results-revision/research-audit/application-budgets/caso46e.csv")
    ap.add_argument("--out", type=Path, default=ROOT / "paper/tables/application-budget.tex")
    args = ap.parse_args()
    d = pd.read_csv(args.csv)
    order = ["Generation identities and demand cap", "Generation definitions, Bonete and Palmar",
             "Production envelope tangents", "Water balance, Bonete and Palmar",
             "Water balance, Baygorria", "Generation definition, Baygorria"]
    d["_o"] = d.constraint_group.map({k: i for i, k in enumerate(order)}).fillna(len(order))
    d = d.sort_values(["_o", "constraint_group"])
    unit = {"MW": "MW", "m3": r"m\textsuperscript{3}", "MW1e7": "row units"}
    lines = [r"\begin{tabular}{lrrrr}", r"\toprule",
             r"Constraint group & Budget $\delta$ & Admissible factors & GM factor & Residual at $\epsilon$ \\",
             r"\midrule"]
    for _, r in d.iterrows():
        u = unit.get(r.unit, r.unit)
        lines.append(f"{r.constraint_group} & {sci(r.declared_budget)}~{u} & "
                     f"[{sci(r.admissible_lower_max)}, {sci(r.admissible_upper_min)}] & "
                     f"{sci(r.median_gm_factor)} & {sci(r.max_original_residual_under_gm)}~{u} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    args.out.write_text("\n".join(lines) + "\n")
    print("wrote", args.out, "rows", len(d), "total constraints", int(d.rows.sum()))


if __name__ == "__main__":
    main()
