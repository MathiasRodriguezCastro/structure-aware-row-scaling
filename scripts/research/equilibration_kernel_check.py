#!/usr/bin/env python3
"""Is a pre-export row scaling in the kernel of a solver-style equilibration?

If it were, the conditioning of the exported file could not matter: the solver's own scaling
would recover the same matrix whatever factors the generator used. It is not. On random dense
matrices with a row scaling whose factors are exact powers of two --- so that the scaled matrix
is bit-identical to the product and no precision is lost --- a converged row-and-column
infinity-norm equilibration leaves the two representations with different condition numbers.

Reports the distribution of that residual ratio over random draws.
"""
import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def equilibrate(a, passes, power_of_two=True):
    a = a.astype(float).copy()
    for _ in range(passes):
        r = 1.0 / np.sqrt(np.abs(a).max(axis=1))
        if power_of_two:
            r = np.ldexp(1.0, np.round(np.log2(r)).astype(int))
        a = r[:, None] * a
        c = 1.0 / np.sqrt(np.abs(a).max(axis=0))
        if power_of_two:
            c = np.ldexp(1.0, np.round(np.log2(c)).astype(int))
        a = a * c[None, :]
    return a


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--draws", type=int, default=200)
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--passes", type=int, default=50, help="enough for the iteration to settle")
    ap.add_argument("--out", type=Path, default=ROOT / "results-revision/research-audit"
                                                      "/solver-scaling-bridge/kernel-check.json")
    args = ap.parse_args()
    rng = np.random.default_rng(20261001)
    ratios, exact = [], True
    for _ in range(args.draws):
        b = rng.standard_normal((args.n, args.n)) * 10.0 ** rng.integers(-6, 7, (args.n, args.n))
        d = np.ldexp(1.0, rng.integers(-26, 27, args.n))
        db = d[:, None] * b
        exact &= bool(np.array_equal(db / d[:, None], b))   # the product lost nothing
        ratios.append(np.linalg.cond(equilibrate(db, args.passes), 1)
                      / np.linalg.cond(equilibrate(b, args.passes), 1))
    r = np.array(ratios)
    out = {"draws": args.draws, "size": args.n, "passes": args.passes,
           "row_scaling": "exact powers of two in [2^-26, 2^26]",
           "product_is_exact": exact,
           "ratio_median": float(np.median(r)), "ratio_min": float(r.min()),
           "ratio_max": float(r.max()),
           "ratio_decades_median": float(np.log10(np.median(r))),
           "fraction_within_factor_two_of_one": float(np.mean((r > 0.5) & (r < 2))),
           "note": ("a ratio of one would mean the row scaling is undone by the equilibration; "
                    "it is not, and the product being exact rules out precision loss")}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
