#!/usr/bin/env python3
"""Does a solver-style scaling undo the scaling the file was exported with?

The fixed-basis audit measures the conditioning of the exported representation, before any
solver touches it. Every solver equilibrates internally, so the natural objection is that the
difference between representations is erased before it can matter. This measures what survives.

For each basis of the audit, rebuilt from the LP text, it applies an iterative row-and-column
infinity-norm equilibration with factors rounded to powers of two --- the scheme the three
solvers describe --- and recomputes kappa_1 after 1, 2, 4 and 10 passes. A representation whose
advantage the solver's own scaling removes would show ratios going to one.

No optimizer is called.
"""
import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as sla

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_identifiability_grid import parse

PASSES = (1, 2, 4, 10)


def rebuild(folder, tag):
    """The same square basis the audit measured, from the LP text and the stored basis names."""
    basis = json.loads((folder / "reference-basis.json").read_text())
    rnames, jnames, snames = (basis["row_names"], basis["basic_variables"],
                              basis["basic_slack_rows"])
    rmap = {n: i for i, n in enumerate(rnames)}
    jmap = {n: j for j, n in enumerate(jnames)}
    parsed, _ = parse(folder / (tag + ".lp"))
    rr, cc, vv = [], [], []
    for rname, row in parsed.items():
        for cname, value in row["terms"].items():
            if cname in jmap:
                rr.append(rmap[rname]); cc.append(jmap[cname]); vv.append(float(value))
    for k, rname in enumerate(snames):
        rr.append(rmap[rname]); cc.append(len(jnames) + k); vv.append(1.0)
    return sp.csc_matrix((vv, (rr, cc)), shape=(len(rnames), len(rnames)))


def equilibrate(a, passes):
    """Row-and-column infinity-norm equilibration, factors rounded to powers of two.

    Powers of two keep every scaled coefficient exact in binary64, which is why solvers use
    them; it also means the result cannot be an artifact of rounding the scaled matrix.
    """
    a = a.tocsr().copy()
    for _ in range(passes):
        rows = np.asarray(abs(a).max(axis=1).todense()).ravel()
        rows[rows == 0] = 1.0
        dr = np.ldexp(1.0, -np.round(np.log2(rows) / 2).astype(int))
        a = sp.diags(dr) @ a
        cols = np.asarray(abs(a).max(axis=0).todense()).ravel()
        cols[cols == 0] = 1.0
        dc = np.ldexp(1.0, -np.round(np.log2(cols) / 2).astype(int))
        a = (a @ sp.diags(dc)).tocsr()
    return a


def kappa1(a, seeds=(0, 1, 2)):
    a = a.tocsc()
    try:
        lu = sla.splu(a)
    except RuntimeError:
        return None
    op = sla.LinearOperator(a.shape, matvec=lu.solve,
                            rmatvec=lambda x: lu.solve(x, "T"),
                            matmat=lu.solve,
                            rmatmat=lambda x: lu.solve(x, "T"), dtype=np.float64)
    norm = float(abs(a).sum(axis=0).max())
    est = []
    for s in seeds:
        np.random.seed(s)
        est.append(norm * float(sla.onenormest(op, t=4)))
    return max(est) if all(math.isfinite(x) and x >= 1 for x in est) else None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path,
                    default=ROOT / "results-revision/research-audit/fixed-basis-final-20260914")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--limit", type=int, help="first N records, for a pilot")
    args = ap.parse_args()

    records = list(csv.DictReader((args.root / "fresh-results.csv").open()))
    if args.limit:
        records = records[:args.limit]
    out = []
    for n, rec in enumerate(records, 1):
        folder = args.root / "fresh" / rec["class"] / Path(rec["instance"]).stem
        b = rebuild(folder, rec["variant"])
        row = {"class": rec["class"], "instance": rec["instance"], "variant": rec["variant"],
               "kappa1_unscaled": kappa1(b)}
        for p in PASSES:
            row["kappa1_equilibrated_%d" % p] = kappa1(equilibrate(b, p))
        out.append(row)
        print(f"{n}/{len(records)} {rec['class']} {Path(rec['instance']).stem} {rec['variant']} "
              + " ".join(f"{k.split('_')[-1]}={v:.3e}" for k, v in row.items()
                         if k.startswith("kappa1") and v), flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader(); w.writerows(out)
    print("wrote", args.out, len(out), "records")


if __name__ == "__main__":
    main()
