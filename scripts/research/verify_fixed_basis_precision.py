#!/usr/bin/env python3
"""Precision check of the fixed-basis condition numbers on a stress sample.

For each selected basis B (stored binary64 matrix, hash-checked):
  * ||B||_1 is computed exactly in rational arithmetic.
  * Every column of B^{-1} is solved in double precision, giving the maximum
    column 1-norm N_dbl, and an a posteriori upper bound
        ||B^{-1}||_1 <= max_j ||x_j||_1 / (1 - max_j rho_j),
    where rho_j bounds ||B x_j - e_j||_1 including floating-point rounding terms.
  * For the largest columns, the solution is refined with residuals computed
    exactly in rational arithmetic, and ||x||_1 / ||B x||_1 (exact) certifies a
    lower bound on ||B^{-1}||_1 that holds for any nonsingular B.
"""
import argparse
import csv
import hashlib
import json
import math
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction
from pathlib import Path
import platform

import numpy as np
import scipy
import scipy.sparse as sp
import scipy.sparse.linalg as sla

EPS = np.finfo(float).eps
U = EPS / 2
VARIANTS = ("Base", "Flat-GM", "Flat-L2")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def exact_matvec(rows, x):
    """B x in exact rational arithmetic; rows[i] = [(j, Fraction(a_ij)), ...]."""
    xf = {}
    out = []
    for row in rows:
        s = Fraction(0)
        for j, a in row:
            v = xf.get(j)
            if v is None:
                v = xf[j] = Fraction(float(x[j]))
            s += a * v
        out.append(s)
    return out


def refine_column(lu, rows, n, j, max_iter=12):
    e = np.zeros(n); e[j] = 1.0
    x = lu.solve(e)
    history = []
    for _ in range(max_iter):
        bx = exact_matvec(rows, x)
        r = np.array([float(-v) for v in bx]); r[j] += 1.0
        r[j] = float(Fraction(1) - bx[j])
        d = lu.solve(r)
        rel = float(np.abs(d).sum() / np.abs(x).sum())
        history.append(rel)
        if len(history) > 1 and rel > 0.5 * history[-2]:
            break
        x = x + d
        if rel <= 4 * EPS:
            break
    bx = exact_matvec(rows, x)
    num = sum((abs(Fraction(float(v))) for v in x), Fraction(0))
    den = sum((abs(v) for v in bx), Fraction(0))
    lower = math.nextafter(float(num / den), 0.0)
    return x, lower, history


def analyze(task):
    root, cls, inst, variant, expected_sha, top = task
    path = Path(root) / "fresh" / cls / Path(inst).stem / (variant + "-basis.npz")
    assert sha(path) == expected_sha, path
    B = sp.load_npz(path).tocsc()
    n = B.shape[0]
    A = abs(B)
    # Exact ||B||_1 from the stored binary64 entries.
    colsum = [sum((Fraction(float(v)) for v in A.data[A.indptr[c]:A.indptr[c + 1]]), Fraction(0))
              for c in range(n)]
    norm_b = max(colsum)
    csr = B.tocsr()
    rows = [[(int(csr.indices[k]), Fraction(float(csr.data[k]))) for k in range(csr.indptr[i], csr.indptr[i + 1])]
            for i in range(n)]
    kmax = int(np.diff(csr.indptr).max()) + 1
    gamma = kmax * U / (1 - kmax * U)
    lu = sla.splu(B)
    xnorm = np.empty(n)
    rho = np.empty(n)
    for start in range(0, n, 512):
        stop = min(n, start + 512)
        E = np.zeros((n, stop - start)); E[np.arange(start, stop), np.arange(stop - start)] = 1.0
        X = lu.solve(E)
        R = B @ X - E
        absbx = A @ np.abs(X)
        xnorm[start:stop] = np.abs(X).sum(axis=0)
        rho[start:stop] = (1 + 2 * n * U) * (np.abs(R).sum(axis=0) + (gamma + 2 * U) * (absbx.sum(axis=0) + 1.0))
    n_dbl = float(xnorm.max())
    max_rho = float(rho.max())
    upper = n_dbl * (1 + 2 * n * U) / (1 - max_rho) * (1 + 1e-12) if max_rho < 1 else None
    order = np.argsort(-xnorm)[:top]
    columns = []
    best_lower = 0.0
    for j in order:
        _, lower, hist = refine_column(lu, rows, n, int(j))
        best_lower = max(best_lower, lower)
        columns.append({"column": int(j), "double_norm": float(xnorm[j]), "certified_lower": lower,
                        "relative_gap": abs(float(xnorm[j]) - lower) / float(xnorm[j]),
                        "refinement_corrections": hist})
    nb = float(norm_b)
    return {"class": cls, "instance": inst, "variant": variant, "n": n,
            "norm_B_1": nb, "max_row_nnz": kmax - 1,
            "kappa1_double_all_columns": nb * n_dbl,
            "kappa1_certified_lower": nb * best_lower * (1 - 8 * EPS),
            "kappa1_upper_bound": None if upper is None else nb * upper * (1 + 1e-12),
            "max_residual_bound": max_rho, "columns": columns}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=Path("results-revision/research-audit/fixed-basis-final-20260914"))
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--seed", type=int, default=20260915)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", type=Path, help="default: <root>/precision-check")
    args = ap.parse_args()
    out = args.out or args.root / "precision-check"
    out.mkdir(exist_ok=False)
    d = list(csv.DictReader((args.root / "fresh-results.csv").open()))
    cell = {(r["class"], r["instance"], r["variant"]): r for r in d}
    rng = np.random.default_rng(args.seed)
    selection = {}
    for cls in ("simple", "sgtm", "full"):
        names = sorted({r["instance"] for r in d if r["class"] == cls})
        base = {i: float(cell[cls, i, "Base"]["kappa1_seed0"]) for i in names}
        ratio = {i: float(cell[cls, i, "Flat-GM"]["kappa1_seed0"]) / base[i] for i in names}
        chosen = {"largest_base_estimate": max(names, key=base.get),
                  "largest_flat_gm_ratio": max(names, key=ratio.get)}
        rest = [i for i in names if i not in chosen.values()]
        chosen["seeded_random"] = str(rng.choice(rest))
        selection[cls] = chosen
    (out / "design.json").write_text(json.dumps({
        "selection_rule": "per class: largest Base estimate, largest Flat-GM/Base estimate ratio, one seeded random other instance",
        "seed": args.seed, "selection": selection, "variants": VARIANTS, "top_columns": args.top,
        "versions": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__},
        "script_sha256": sha(Path(__file__))}, indent=2) + "\n")
    tasks = [(str(args.root), cls, inst, v, cell[cls, inst, v]["basis_sha256"], args.top)
             for cls, chosen in selection.items() for inst in dict.fromkeys(chosen.values()) for v in VARIANTS]
    with ProcessPoolExecutor(args.workers) as pool:
        results = list(pool.map(analyze, tasks))
    for r in results:
        r["kappa1_estimate_seed0"] = float(cell[r["class"], r["instance"], r["variant"]]["kappa1_seed0"])
    (out / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    rows = []
    for r in results:
        rows.append({k: r[k] for k in ("class", "instance", "variant", "n", "kappa1_estimate_seed0",
                                       "kappa1_double_all_columns", "kappa1_certified_lower",
                                       "kappa1_upper_bound", "max_residual_bound")} |
                    {"max_top_column_relative_gap": max(c["relative_gap"] for c in r["columns"])})
    with (out / "results.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    by = {(r["class"], r["instance"], r["variant"]): r for r in results}
    ratios = []
    for cls, chosen in selection.items():
        for inst in dict.fromkeys(chosen.values()):
            base, gm, l2 = (by[cls, inst, v] for v in VARIANTS)
            ratios.append({"class": cls, "instance": inst,
                           "flat_gm_ratio_estimate": gm["kappa1_estimate_seed0"] / base["kappa1_estimate_seed0"],
                           "flat_gm_ratio_certified_upper": None if gm["kappa1_upper_bound"] is None
                           else gm["kappa1_upper_bound"] / base["kappa1_certified_lower"],
                           "flat_l2_certified_lower": l2["kappa1_certified_lower"],
                           "base_certified_lower": base["kappa1_certified_lower"]})
    (out / "summary.json").write_text(json.dumps({"ratios": ratios}, indent=2) + "\n")
    print(json.dumps(ratios, indent=2))


if __name__ == "__main__":
    main()
