#!/usr/bin/env python3
"""Independently check preserved fixed-basis artifacts without solving an LP/MIP.

Uses textual LP coefficients and archived basis names, not the driver or solver
model reader, to reconstruct every square matrix. Confirms no LP coefficient
was dropped, unit slack columns were kept, and the same named basis was used.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import sys

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as sla

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_identifiability_grid import parse


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def equilibrated_condition(b, rec):
    """Estimate the SAME inverse norm through a different exact row scaling.

    Q = D B, with power-of-two D, B^-1 = Q^-1 D. Unlike reporting the
    condition of Q, this is a consistency check on the original B estimate.
    """
    csr = b.tocsr()
    rowmax = np.asarray(abs(csr).max(axis=1).toarray()).ravel()
    assert np.all(rowmax > 0)
    _, exponents = np.frexp(rowmax)
    d = np.ldexp(np.ones(len(rowmax)), -exponents)
    q = csr.copy()
    repeated = np.repeat(exponents, np.diff(csr.indptr))
    q.data = np.ldexp(csr.data, -repeated)
    assert np.array_equal(np.ldexp(q.data, repeated), csr.data)
    lu = sla.splu(q.tocsc())

    def scale(x):
        return d * x if x.ndim == 1 else d[:,None] * x

    op = sla.LinearOperator(b.shape, matvec=lambda x: lu.solve(scale(x)),
                            rmatvec=lambda x: scale(lu.solve(x, "T")),
                            matmat=lambda x: lu.solve(scale(x)),
                            rmatmat=lambda x: scale(lu.solve(x, "T")), dtype=np.float64)
    norm = float(abs(b).sum(axis=0).max())
    estimates = []
    for seed in (0,1,2):
        np.random.seed(seed)
        estimates.append(norm * float(sla.onenormest(op, t=4)))
    assert all(math.isfinite(x) and x >= 1 for x in estimates)
    rng = np.random.default_rng(20260914)
    rhs = rng.standard_normal(b.shape[0]); x = lu.solve(d * rhs)
    den = abs(b) @ abs(x) + abs(rhs)
    berr = float(np.max(np.abs(b @ x - rhs) / np.maximum(den, np.finfo(float).tiny)))
    rawlu = sla.splu(b.tocsc()); rawx = rawlu.solve(rhs)
    xrel = float(np.linalg.norm(x-rawx, np.inf) / max(np.linalg.norm(x,np.inf),np.linalg.norm(rawx,np.inf)))
    raw = [float(rec[f"kappa1_seed{s}"]) for s in (0,1,2)]
    return {"equilibrated_kappa1_seed0":estimates[0],"equilibrated_kappa1_seed1":estimates[1],
            "equilibrated_kappa1_seed2":estimates[2],
            "equilibrated_vs_raw_max_relative_difference":max(abs(x-y)/max(x,y) for x,y in zip(estimates,raw)),
            "equilibrated_lu_componentwise_backward_error":berr,
            "equilibrated_vs_raw_test_solution_relative_difference":xrel,
            "equilibration_power_of_two_roundtrip_exact":True}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    args = ap.parse_args()
    root = Path(args.root)
    records = list(csv.DictReader((root / "fresh-results.csv").open()))
    checks = []
    for rec in records:
        folder = root / "fresh" / rec["class"] / Path(rec["instance"]).stem
        tag = rec["variant"]
        path = folder / (tag + ".lp")
        assert sha(path) == rec["lp_sha256"]
        basis_path = folder / (tag + "-basis.npz")
        assert sha(basis_path) == rec["basis_sha256"]
        basis = json.loads((folder / "reference-basis.json").read_text())
        rnames = basis["row_names"]
        jnames = basis["basic_variables"]
        snames = basis["basic_slack_rows"]
        rmap = {n:i for i,n in enumerate(rnames)}
        jmap = {n:j for j,n in enumerate(jnames)}
        assert len(rmap) == len(rnames) == len(jnames) + len(snames)
        parsed, _ = parse(path)
        assert set(parsed) == set(rnames)
        rr, cc, vv = [], [], []
        count = 0
        for rname, row in parsed.items():
            for cname, value in row["terms"].items():
                assert value != 0
                count += 1
                if cname in jmap:
                    rr.append(rmap[rname]); cc.append(jmap[cname]); vv.append(float(value))
        # Full textual nonzero count must equal reader nonzeros recorded by the
        # driver, separately from the exact basic-column comparison below.
        assert count == int(rec["nnz"])
        for k, rname in enumerate(snames):
            rr.append(rmap[rname]); cc.append(len(jnames)+k); vv.append(1.)
        rebuilt = sp.csc_matrix((vv,(rr,cc)),shape=(len(rnames),len(rnames)))
        stored = sp.load_npz(basis_path).tocsc()
        delta = stored - rebuilt
        assert delta.nnz == 0, (rec["class"],rec["instance"],tag,delta.nnz)
        alt = equilibrated_condition(rebuilt, rec)
        checks.append({"class":rec["class"],"instance":rec["instance"],"variant":tag,
                       "source_nonzeros":count,"basic_nonzeros":rebuilt.nnz,
                       "exact_basis_match":True, **alt})
        print(rec["class"],rec["instance"],tag,"verified", "route_relative_difference", alt["equilibrated_vs_raw_max_relative_difference"],flush=True)
    result = {"records":len(checks),"source_coefficients_checked":sum(c["source_nonzeros"] for c in checks),
              "basis_coefficients_reconstructed":sum(c["basic_nonzeros"] for c in checks),
              "all_exact_basis_matches":all(c["exact_basis_match"] for c in checks),
              "max_alternative_route_relative_difference":max(c["equilibrated_vs_raw_max_relative_difference"] for c in checks),
              "max_alternative_route_componentwise_backward_error":max(c["equilibrated_lu_componentwise_backward_error"] for c in checks),
              "max_alternative_route_test_solution_relative_difference":max(c["equilibrated_vs_raw_test_solution_relative_difference"] for c in checks),
              "independent_of_driver_and_highs_reader":True,
              "fresh_results_sha256":sha(root / "fresh-results.csv"),
              "verifier_sha256":sha(Path(__file__)),
              "text_parser_sha256":sha(ROOT / "scripts/audit_identifiability_grid.py"),
              "checks":checks}
    (root / "independent-verification.json").write_text(json.dumps(result,indent=2)+"\n")


if __name__ == "__main__":
    main()
