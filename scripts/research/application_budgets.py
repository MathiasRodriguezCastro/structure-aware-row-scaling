#!/usr/bin/env python3
"""What a declared residual budget implies for the rows of a real dispatch model.

The LP it reads is the unscaled export of an instance, produced by the C++ pipeline with
`grabar <path> --noConstante` after `configurarSolver`; provenance.json beside the results
records the instance, the binary and the hash of the export used here.

Reads an exported LP, groups its rows by the generator's own names, and asks, per group:
given a tolerance stated in the units of that constraint, which row factors are admissible
(Proposition 5.1), where does the plain geometric-mean factor fall, and what does the solver's
absolute tolerance become in original units under it. No solver is called and no model is
solved; the budgets are declared inputs, not measurements.
"""
import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from budget_scaling import select_factor

ROW = re.compile(r"^\s*([A-Za-z_][A-Za-z_0-9]*)(\([0-9]+\))?:\s*(.*)$")
# The coefficient must not swallow a leading sign: "- a1_v3h(342)" is a coefficient of -1.
TERM = re.compile(r"([+-]?)\s*((?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)?\s*"
                  r"([A-Za-z_][A-Za-z_0-9]*(?:\([0-9]+\))?)")
OP = re.compile(r"(<=|>=|=)\s*([-0-9.eE+]+)\s*$")


def rows(path):
    """(family, coefficients, rhs) for every constraint of an LP export."""
    text = path.read_text()
    body = text.split("Subject To", 1)[1]
    body = re.split(r"\nBounds\n|\nBinaries\n|\nGenerals\n|\nEnd\n", body)[0]
    current, out = None, []
    for line in body.splitlines():
        m = ROW.match(line)
        if m and ":" in line:
            if current:
                out.append(current)
            family = m.group(1)
            current = [family, [], None, m.group(3)]
        elif current is not None and line.strip():
            current[3] += " " + line.strip()
    if current:
        out.append(current)
    parsed = []
    for family, _, _, expr in out:
        op = OP.search(expr)
        if not op:
            continue
        rhs = float(op.group(2))
        coefficients = []
        for sign, value, _ in TERM.findall(expr[:op.start()]):
            c = 1.0 if not value else float(value)
            coefficients.append(-c if sign == "-" else c)
        if coefficients:
            parsed.append((family, np.array(coefficients), rhs))
    return parsed


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lp", type=Path, required=True)
    ap.add_argument("--budgets", type=Path, required=True,
                    help="JSON: {row family prefix: {unit, budget}} declared, not measured")
    ap.add_argument("--epsilon", type=float, default=1e-6,
                    help="solver absolute feasibility tolerance on the exported row")
    ap.add_argument("--floor", type=float, default=1e-9)
    ap.add_argument("--ceiling", type=float, default=1e9)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    declared = json.loads(args.budgets.read_text())
    data = rows(args.lp)
    groups = {}
    for family, a, rhs in data:
        spec = next((v for k, v in declared.items() if family.startswith(k)), None)
        if spec is None:
            continue
        key = (spec.get("label", family), spec["unit"], spec["budget"])
        groups.setdefault(key, []).append((a, rhs))
    out = []
    for (label, unit, delta), members in sorted(groups.items()):
        gm, admissible, residuals = [], 0, []
        lo_all, hi_all = [], []
        # The policies use three distinct kernels; Role-Hybrid picks one of the last two per row,
        # so it is admissible wherever both are.
        kernels = {"Base": 0, "Flat-GM": 0, "Flat-L2": 0}
        for a, _ in members:
            nz = np.abs(a[a != 0])
            d = select_factor(a, delta, epsilon=args.epsilon,
                              coefficient_floor=args.floor, coefficient_ceiling=args.ceiling)
            g = float(np.exp(-0.5 * (math.log(nz.min()) + math.log(nz.max()))))
            gm.append(g)
            lo_all.append(d.lower); hi_all.append(d.upper)
            admissible += int(d.lower <= g <= d.upper)
            residuals.append(args.epsilon / g)
            for name, factor in (("Base", 1.0), ("Flat-GM", g),
                                 ("Flat-L2", 1.0 / float(np.linalg.norm(a)))):
                kernels[name] += int(d.lower <= factor <= d.upper)
        out.append({"constraint_group": label, "rows": len(members), "unit": unit,
                    "declared_budget": delta,
                    "median_gm_factor": float(np.median(gm)),
                    "admissible_lower_max": float(np.max(lo_all)),
                    "admissible_upper_min": float(np.min(hi_all)),
                    "gm_admissible_rows": admissible,
                    "median_original_residual_under_gm": float(np.median(residuals)),
                    "max_original_residual_under_gm": float(np.max(residuals)),
                    "margin_factor": float(delta / np.max(residuals)),
                    "base_admissible_rows": kernels["Base"],
                    "flat_gm_admissible_rows": kernels["Flat-GM"],
                    "flat_l2_admissible_rows": kernels["Flat-L2"]})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader(); w.writerows(out)
    for r in out:
        print(f'{r["constraint_group"]:38s} n={r["rows"]:5d} budget {r["declared_budget"]:g} {r["unit"]:4s} '
              f'gm {r["median_gm_factor"]:.3e}  admissible {r["gm_admissible_rows"]}/{r["rows"]}  '
              f'worst residual {r["max_original_residual_under_gm"]:.3e} {r["unit"]}  '
              f'margin {r["margin_factor"]:.3g}x')


if __name__ == "__main__":
    main()
