#!/usr/bin/env python3
"""Compare the operational reconstruction with its replication.

Puts the paired effort ratio of the reconstruction (Gurobi, seed 42) beside the same ratio
measured on the same instances with a second seed and with a second solver. Effort is each
solver's own measure --- work units for Gurobi, deterministic ticks for CPLEX --- so a column
is read within its solver, never across.
"""
import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
HIST = {"matricial_plano": "Flat-GM", "matricial_plano_l2": "Flat-L2", "role_hybrid": "Role-Hybrid"}
CELL = {"gurobi_simple_1pct": ("Simple", 0.01), "gurobi_simple_01pct": ("Simple", 0.001),
        "gurobi_sgtm_1pct": ("SG-Ter-Mer", 0.01), "gurobi_sgtm_01pct": ("SG-Ter-Mer", 0.001)}
ORDER = [("Simple", 0.01), ("Simple", 0.001), ("SG-Ter-Mer", 0.01), ("SG-Ter-Mer", 0.001)]


def historical(path):
    d = pd.read_csv(path)
    d = d[d.endpoint.eq("geomean_work_ratio_common_completed") & d.denominator.eq("base")]
    rows = []
    for _, r in d.iterrows():
        family, gap = CELL[r.cell]
        rows.append({"family": family, "gap": gap, "policy": HIST[r.numerator],
                     "condition": "Gurobi, seed 42", "ratio": r.estimate,
                     "ci_low": r.ci_low, "ci_high": r.ci_high, "n": int(r.n)})
    return pd.DataFrame(rows)


def replication(path):
    d = pd.read_csv(path)
    d = d[d.endpoint.eq("effort")]
    name = {("gurobi", 7): "Gurobi, seed 7", ("cplex", 42): "CPLEX, seed 42"}
    rows = []
    for _, r in d.iterrows():
        key = (r.solver, int(r.seed))
        if key not in name:
            continue
        rows.append({"family": r.family, "gap": float(r.gap), "policy": r.policy,
                     "condition": name[key], "ratio": r.geometric_mean_ratio,
                     "ci_low": r.ci_low, "ci_high": r.ci_high, "n": int(r.n_pairs)})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--historical", type=Path,
                    default=ROOT / "results-revision/research-audit/operational/paired_contrasts.csv")
    ap.add_argument("--replication", type=Path, required=True)
    ap.add_argument("--out", type=Path,
                    default=ROOT / "results-revision/research-audit/operational-replication/comparison.csv")
    ap.add_argument("--tex", type=Path, default=ROOT / "paper/tables/replication.tex")
    args = ap.parse_args()
    d = pd.concat([historical(args.historical), replication(args.replication)], ignore_index=True)
    d.to_csv(args.out, index=False)
    conditions = ["Gurobi, seed 42", "Gurobi, seed 7", "CPLEX, seed 42"]
    lines = [r"\begin{tabular}{llrrr}", r"\toprule",
             "& & " + " & ".join(conditions) + r" \\", r"\midrule"]
    for family, gap in ORDER:
        lines.append(r"\multicolumn{5}{l}{\emph{%s, gap %g\%%}} \\" % (family, gap * 100))
        for policy in ["Flat-GM", "Flat-L2", "Role-Hybrid"]:
            cells = []
            for cond in conditions:
                s = d[(d.family == family) & (d.gap == gap) & (d.policy == policy)
                      & (d.condition == cond)]
                cells.append(f"{s.iloc[0].ratio:.3f} [{s.iloc[0].ci_low:.2f}, {s.iloc[0].ci_high:.2f}]"
                             if len(s) else "--")
            lines.append(f"\\quad {policy} & & " + " & ".join(cells) + r" \\")
        lines.append(r"\addlinespace")
    lines = lines[:-1] + [r"\bottomrule", r"\end{tabular}"]
    args.tex.write_text("\n".join(lines) + "\n")
    print(d.pivot_table(index=["family", "gap", "policy"], columns="condition",
                        values="ratio").round(3).to_string())


if __name__ == "__main__":
    main()
