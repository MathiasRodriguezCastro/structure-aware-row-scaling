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

    lines = [r"\begin{tabular}{llrrrr}", r"\toprule",
             r"Class & Policy & $n$ & As exported & 2 passes & 10 passes \\",
             r"\midrule"]
    summary = []
    for key, label in CLASSES:
        sub = d[d["class"] == key]
        if sub.empty:
            continue
        b = base.loc[key] if key in base.index.get_level_values(0) else None
        lines.append(f"{label} & Base ($\\kappa_1$) & {len(b)} & {sci(b[cols[0]].median())} & "
                     f"{sci(b[cols[2]].median())} & {sci(b[cols[4]].median())} \\\\")
        for pol in args.policies:
            p = sub[sub.variant == pol].set_index("instance")
            if p.empty:
                continue
            cells, rec = [], {"class": label, "policy": pol, "n": len(p)}
            for c, tag in ((cols[0], "unscaled"), (cols[2], "p2"), (cols[4], "p10")):
                r = (p[c] / b[c]).dropna()
                cells.append(f"{sci(r.median())} ({int((r < 1).sum())})")
                rec[tag] = r.median(); rec[tag + "_improved"] = int((r < 1).sum())
            summary.append(rec)
            lines.append(f" & {pol} & {len(p)} & " + " & ".join(cells) + r" \\")
        lines.append(r"\midrule")
    lines[-1] = r"\bottomrule"
    lines.append(r"\end{tabular}")
    args.out.write_text("\n".join(lines) + "\n")

    print(f"{'class':12s} {'policy':9s} {'n':>4s}  {'exported':>12s} {'2 passes':>12s} {'10 passes':>12s}")
    for r in summary:
        print(f"{r['class']:12s} {r['policy']:9s} {r['n']:4d}  "
              f"{r['unscaled']:9.3e}({r['unscaled_improved']:3d}) "
              f"{r['p2']:9.3e}({r['p2_improved']:3d}) {r['p10']:9.3e}({r['p10_improved']:3d})")
    base10 = base["kappa1_equilibrated_10"]
    print(f"\nmedian kappa1 of Base: as exported {base['kappa1_unscaled'].median():.3e}, "
          f"after 10 passes {base10.median():.3e}")
    print("wrote", args.out)


if __name__ == "__main__":
    main()
