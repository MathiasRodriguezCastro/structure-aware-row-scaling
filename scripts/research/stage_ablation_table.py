#!/usr/bin/env python3
"""Historical stage ablation: where did the operational gain of the structured rules sit?

The earlier preprocessing campaign split each structured rule into its conceptual stages and
ran the local stage alone and the coupling stage alone against Base and the full rule, on the
same instance banks. This reads those stored runs and reports the shifted geometric mean of
solver time, which is the summary that campaign used.

It belongs to the earlier campaign and to the earlier policies, not to the policy set of this
article, and it is reported as exploratory evidence about solver effort.
"""
import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "results-revision/r5-ablation"
CLASSES = [("simple", "Simple"), ("sgtm", "SG-Ter-Mer"), ("full", "Full")]
GAPS = [("1pct", r"1\%"), ("01pct", r"0.1\%")]
RULES = [("estructurado", "Structured"), ("matricial", "Matrix")]
STAGES = ["", "_solo_local", "_solo_acoplamiento"]


def sgm(values, shift=1.0):
    """Shifted geometric mean, the summary the campaign reported."""
    return math.exp(sum(math.log(v + shift) for v in values) / len(values)) - shift


def read(path):
    out = defaultdict(list)
    with path.open() as fh:
        for row in csv.DictReader(fh):
            t = row["tiempo_solver_s"]
            if t not in ("", "N/D", None):
                out[row["variante"]].append(float(t))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "paper/tables/stage-ablation.tex")
    ap.add_argument("--csv", type=Path, default=BASE / "stage-ablation.csv")
    args = ap.parse_args()

    records, lines = [], [r"\begin{tabular}{llrrrrr}", r"\toprule",
                          r"Class & Gap & $n$ & Base & Full rule & Local only & Coupling only \\",
                          r"\midrule"]
    for key, label in CLASSES:
        for gap, gap_label in GAPS:
            path = BASE / f"{key}-gurobi-{gap}" / "resumen.csv"
            if not path.exists():
                continue
            data = read(path)
            for prefix, rule in RULES:
                # The matrix rule stores its full variant under a different name.
                full = "estructurado_matricial" if prefix == "matricial" else "estructurado"
                names = [full] + [prefix + s for s in STAGES[1:]]
                if not all(n in data for n in names) or "base" not in data:
                    continue
                vals = [sgm(data["base"])] + [sgm(data[n]) for n in names]
                records.append({"class": label, "gap": gap, "rule": rule, "n": len(data["base"]),
                                "base": vals[0], "full": vals[1], "local_only": vals[2],
                                "coupling_only": vals[3]})
                if rule == "Structured":
                    lines.append(f"{label} & {gap_label} & {len(data['base'])} & "
                                 + " & ".join(f"{v:.2f}" for v in vals) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    args.out.write_text("\n".join(lines) + "\n")
    with args.csv.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(records[0])); w.writeheader(); w.writerows(records)

    print(f"{'class':12s} {'gap':6s} {'rule':11s} {'n':>4s} {'base':>8s} {'full':>8s} "
          f"{'local':>8s} {'coupling':>9s}")
    for r in records:
        print(f"{r['class']:12s} {r['gap']:6s} {r['rule']:11s} {r['n']:4d} {r['base']:8.2f} "
              f"{r['full']:8.2f} {r['local_only']:8.2f} {r['coupling_only']:9.2f}")
    print("\nwrote", args.out, "and", args.csv)


if __name__ == "__main__":
    main()
