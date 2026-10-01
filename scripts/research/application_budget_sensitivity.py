#!/usr/bin/env python3
"""How much the declared budgets of the application table can be tightened.

The budgets of the application table are declared, not measured, so the natural question is
whether the conclusion --- every kernel the policies use is admissible on every interpretable
row --- depends on the particular numbers chosen. This scales all declared budgets by a common
factor and reports, per constraint group, the admissible row counts of the three kernels and the
tightest factor at which each still covers the whole group (Proposition 5.1). No model is
solved.
"""
import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from application_budgets import rows
from budget_scaling import select_factor

ROOT = Path(__file__).resolve().parents[2]
KERNELS = ("Base", "Flat-GM", "Flat-L2")


def kernel_factors(a):
    nz = np.abs(a[a != 0])
    gm = float(np.exp(-0.5 * (math.log(nz.min()) + math.log(nz.max()))))
    return {"Base": 1.0, "Flat-GM": gm, "Flat-L2": 1.0 / float(np.linalg.norm(a))}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lp", type=Path, required=True)
    ap.add_argument("--budgets", type=Path, required=True)
    ap.add_argument("--epsilon", type=float, default=1e-6)
    ap.add_argument("--floor", type=float, default=1e-9)
    ap.add_argument("--ceiling", type=float, default=1e9)
    ap.add_argument("--exponents", type=int, nargs=2, default=(-10, 2),
                    help="range of base-10 exponents for the common multiplier")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    declared = json.loads(args.budgets.read_text())
    groups = {}
    for family, a, _ in rows(args.lp):
        spec = next((v for k, v in declared.items() if family.startswith(k)), None)
        if spec is None:
            continue
        groups.setdefault((spec.get("label", family), spec["unit"], spec["budget"]), []).append(a)

    multipliers = [10.0 ** e for e in range(args.exponents[0], args.exponents[1] + 1)]
    out = []
    for (label, unit, delta), members in sorted(groups.items()):
        factors = [kernel_factors(a) for a in members]
        # The tightest multiplier that keeps a kernel admissible on every row of the group.
        tightest = {k: None for k in KERNELS}
        for m in multipliers:
            counts = {k: 0 for k in KERNELS}
            for a, f in zip(members, factors):
                d = select_factor(a, delta * m, epsilon=args.epsilon,
                                  coefficient_floor=args.floor, coefficient_ceiling=args.ceiling)
                for k in KERNELS:
                    counts[k] += int(d.lower <= f[k] <= d.upper)
            out.append({"constraint_group": label, "unit": unit, "declared_budget": delta,
                        "multiplier": m, "budget": delta * m, "rows": len(members)}
                       | {f"{k}_admissible_rows": counts[k] for k in KERNELS})
            for k in KERNELS:
                if counts[k] == len(members) and tightest[k] is None:
                    tightest[k] = m
        print(f"{label:38s} n={len(members):5d}  tightest admissible multiplier: " +
              "  ".join(f"{k} {('%g' % tightest[k]) if tightest[k] else 'none'}" for k in KERNELS))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader(); w.writerows(out)
    print("wrote", args.out, "rows", len(out))


if __name__ == "__main__":
    main()
