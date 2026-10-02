#!/usr/bin/env python3
"""What survives a solver-style scaling: table and summary of the bridge experiment."""
import argparse
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CLASSES = [("simple", "Simple"), ("sgtm", "SG-Ter-Mer"), ("full", "Full")]
PASSES = (1, 2, 4, 10)


def sci(x):
    if x is None or not math.isfinite(x):
        return "---"
    if 0.05 <= x < 1000:
        return f"{x:#.3g}".rstrip("0").rstrip(".")
    e = int(math.floor(math.log10(abs(x))))
    m = x / 10.0**e
    return rf"$10^{{{e}}}$" if abs(m - 1) < 5e-2 else rf"${m:.1f}\times10^{{{e}}}$"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, default=ROOT / "results-revision/research-audit"
                                                      "/solver-scaling-bridge/bridge.csv")
    ap.add_argument("--out", type=Path, default=ROOT / "paper/tables/solver-scaling-bridge.tex")
    ap.add_argument("--policies", nargs="*", default=["Flat-GM", "Flat-L2"])
    args = ap.parse_args()
    d = pd.read_csv(args.csv)
    cols = ["kappa1_unscaled"] + [f"kappa1_equilibrated_{p}" for p in PASSES]
    base = d[d.variant == "Base"].set_index(["class", "instance"])[cols]

    lines = [r"\begin{tabular}{llrrrrr}", r"\toprule",
             r"Class & Policy & $n$ & As exported & \multicolumn{3}{c}{After equilibration} \\",
             r"\cmidrule(lr){5-7}",
             r" & & & & 1 pass & 2 passes & 10 passes \\", r"\midrule"]
    summary = []
    for key, label in CLASSES:
        sub = d[d["class"] == key]
        if sub.empty:
            continue
        first = True
        for pol in args.policies:
            p = sub[sub.variant == pol].set_index(["class", "instance"])[cols]
            common = p.index.intersection(base.index)
            if not len(common):
                continue
            ratios = [(p.loc[common, c] / base.loc[common, c]).median() for c in cols]
            summary.append({"class": label, "policy": pol, "n": len(common),
                            "unscaled": ratios[0], "p1": ratios[1], "p2": ratios[2],
                            "p10": ratios[4]})
            lines.append(f"{label if first else ''} & {pol} & {len(common)} & "
                         f"{sci(ratios[0])} & {sci(ratios[1])} & {sci(ratios[2])} & "
                         f"{sci(ratios[4])} \\\\")
            first = False
    lines += [r"\bottomrule", r"\end{tabular}"]
    args.out.write_text("\n".join(lines) + "\n")

    print(f"{'class':12s} {'policy':9s} {'n':>4s}  {'exported':>10s} {'1 pass':>10s} "
          f"{'2 passes':>10s} {'10 passes':>10s}")
    for r in summary:
        print(f"{r['class']:12s} {r['policy']:9s} {r['n']:4d}  {r['unscaled']:10.3e} "
              f"{r['p1']:10.3e} {r['p2']:10.3e} {r['p10']:10.3e}")
    base10 = base["kappa1_equilibrated_10"]
    print(f"\nmedian kappa1 of Base: as exported {base['kappa1_unscaled'].median():.3e}, "
          f"after 10 passes {base10.median():.3e}")
    print("wrote", args.out)


if __name__ == "__main__":
    main()
