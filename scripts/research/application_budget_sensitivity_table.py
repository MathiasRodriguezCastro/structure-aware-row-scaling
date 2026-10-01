#!/usr/bin/env python3
"""LaTeX table of the budget-tightening sensitivity on one dispatch model."""
import argparse
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
KERNELS = ("Base", "Flat-GM", "Flat-L2")
ORDER = ["Generation identities, demand cap", "Generation definition, Bonete/Palmar",
         "Production envelope tangents", "Water balance, Bonete/Palmar",
         "Water balance, Baygorria", "Generation definition, Baygorria"]


def power(m):
    return rf"$10^{{{round(math.log10(m))}}}$"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, default=ROOT / "results-revision/research-audit"
                                                      "/application-budgets/caso46e-sensitivity.csv")
    ap.add_argument("--out", type=Path,
                    default=ROOT / "paper/tables/application-budget-sensitivity.tex")
    args = ap.parse_args()
    d = pd.read_csv(args.csv)

    lines = [r"\begin{tabular}{lrrrr}", r"\toprule",
             r"Constraint group & Rows & \multicolumn{3}{c}{Tightest admissible multiplier} \\",
             r"\cmidrule(lr){3-5}",
             r" &  & Base & Flat-GM & Flat-L2 \\", r"\midrule"]
    for label in ORDER:
        sub = d[d.constraint_group == label].sort_values("multiplier")
        n = int(sub["rows"].iloc[0])
        cells = []
        for k in KERNELS:
            full = sub[sub[f"{k}_admissible_rows"] == n]
            cells.append(power(full.multiplier.min()) if len(full) else "---")
        lines.append(f"{label} & {n:,} & " + " & ".join(cells) + r" \\")
    total = d.groupby("multiplier")[[f"{k}_admissible_rows" for k in KERNELS]].sum()
    rows_total = int(d.groupby("constraint_group")["rows"].first().sum())
    cells = [power(total.index[total[f"{k}_admissible_rows"] == rows_total].min())
             for k in KERNELS]
    lines += [r"\midrule", f"All groups & {rows_total:,} & " + " & ".join(cells) + r" \\",
              r"\bottomrule", r"\end{tabular}"]
    args.out.write_text("\n".join(lines) + "\n")
    print("wrote", args.out)


if __name__ == "__main__":
    main()
