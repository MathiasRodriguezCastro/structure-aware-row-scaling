#!/usr/bin/env python3
"""Audit historical fixed-basis summaries and preserve a fresh LP-basis experiment.

Historical basis identities and exports were deleted by the original driver;
recomputing its CSV statistics is not a replay of its factorization. The fresh
experiment uses the first five archived names in each class, a newly solved
Base LP relaxation, and six current DummyLp exports. No MIP is solved.
"""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

import highspy
import numpy as np
import scipy
import scipy.sparse as sp
import scipy.sparse.linalg as sla

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from validar_preprocesamiento import clean_instance_text

CLASSES = {"simple": "entrada-modelo-simple", "full": "entrada-modelo-completo",
           "sgtm": "entrada-SG-Ter-Mer"}
VARIANTS = {"Base": "--solodiagnostico", "SA-Aug": "--local-estructurado",
            "Flat-Aug": "--local-estructurado --plano", "SA-Mat": "--local-matricial",
            "Flat-Mat": "--local-matricial --plano", "Ruiz": "--local-ruiz --ruiz-iters 4"}
SEEDS = (0, 1, 2)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def write_csv(path, rows):
    if rows:
        with Path(path).open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


def historical(out):
    summaries, selected, source_manifest, checks = [], {}, [], []
    for cls, folder in CLASSES.items():
        path = ROOT / "results-revision/fixed-basis" / (cls + ".csv")
        source_manifest.append({"path": str(path.relative_to(ROOT)), "sha256": sha(path)})
        cells = {}
        for row in csv.DictReader(path.open()):
            key = (row["instance"], row["variant"])
            assert key not in cells, key
            assert row["variant"] in VARIANTS
            assert int(row["singular"]) == 0 and math.isfinite(float(row["kappa1"]))
            assert float(row["kappa1"]) >= 1
            assert int(row["rows"]) == int(row["basic_structural"]) + int(row["basic_slack"])
            assert not row["note"]
            cells[key] = row
        names = sorted({x[0] for x in cells})
        for name in names:
            assert {v for i, v in cells if i == name} == set(VARIANTS)
            for field in ("rows", "basic_structural", "basic_slack", "mip_obj", "mip_gap"):
                assert len({cells[name, v][field] for v in VARIANTS}) == 1
        gaps = [float(cells[n, "Base"]["mip_gap"]) for n in names]
        checks.append({"class": cls, "instances": len(names), "records": len(cells),
                       "gaps_above_0.001": sum(x > .001 for x in gaps),
                       "nonfinite_gap_count": sum(not math.isfinite(x) for x in gaps),
                       "matched_basis_dimensions": True, "complete_variants": True,
                       "archived_basis_ids_available": False, "archived_lp_available": False})
        selected[cls] = [name for name in names if (ROOT / "data/entradas" / folder / name).exists()][:5]
        assert len(selected[cls]) == 5
        for variant in VARIANTS:
            ratios = [float(cells[n, variant]["kappa1"]) / float(cells[n, "Base"]["kappa1"]) for n in names]
            summaries.append({"class": cls, "variant": variant, "n": len(ratios),
                              "median_kappa_ratio_base": statistics.median(ratios),
                              "min_ratio": min(ratios), "max_ratio": max(ratios),
                              "improved": sum(x < 1 for x in ratios)})
    write_csv(out / "historical-summary.csv", summaries)
    dump(out / "historical-provenance.json", {"sources": source_manifest, "checks": checks,
         "limitation": "Statistics reconstructed from archived CSVs only; original LP exports and basis identities were not preserved. Nonzero MIP gaps support the fixed-incumbent Gurobi route rather than an LP-relaxation route. Exact historical factorizations cannot be replayed."})
    return selected


def read_lp(path):
    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("threads", 1)
    h.setOptionValue("small_matrix_value", 1e-12)
    status = h.readModel(str(path))
    if status != highspy.HighsStatus.kOk:
        raise ValueError("LP read failed: " + str(status))
    lp = h.getLp()
    am = lp.a_matrix_
    assert am.format_ == highspy.MatrixFormat.kColwise
    assert len(set(lp.row_names_)) == lp.num_row_
    assert len(set(lp.col_names_)) == lp.num_col_
    a = sp.csc_matrix((am.value_, am.index_, am.start_), shape=(lp.num_row_, lp.num_col_))
    assert np.isfinite(a.data).all() and np.all(a.data != 0)
    return h, lp, a


def check_scaling(base, variant, path):
    """Check named full matrices, RHS, variable bounds and objective before bases."""
    _, lp0, a0 = base
    _, lp, a = variant
    assert set(lp.row_names_) == set(lp0.row_names_)
    assert set(lp.col_names_) == set(lp0.col_names_)
    ri = {n: i for i, n in enumerate(lp.row_names_)}
    ci = {n: i for i, n in enumerate(lp.col_names_)}
    rperm = [ri[n] for n in lp0.row_names_]
    cperm = [ci[n] for n in lp0.col_names_]
    a = a[rperm, :][:, cperm].tocsr()
    a0 = a0.tocsr()
    for q in (a, a0):
        q.sort_indices()
    assert np.array_equal(a.indices, a0.indices)
    assert np.array_equal(a.indptr, a0.indptr)
    for attr in ("col_lower_", "col_upper_", "col_cost_"):
        assert np.array_equal(np.asarray(getattr(lp, attr))[cperm], getattr(lp0, attr))
    assert lp.offset_ == lp0.offset_ and lp.sense_ == lp0.sense_
    integrality = list(lp.integrality_)
    assert [integrality[j] for j in cperm] == list(lp0.integrality_)
    factors, errors, rhs_errors = [], [], []
    lo, hi = np.asarray(lp.row_lower_)[rperm], np.asarray(lp.row_upper_)[rperm]
    lo0, hi0 = np.asarray(lp0.row_lower_), np.asarray(lp0.row_upper_)
    for i, name in enumerate(lp0.row_names_):
        first, last = a0.indptr[i:i+2]
        assert first < last, "empty row requires a separate RHS scaling check"
        orig, scaled = a0.data[first:last], a.data[first:last]
        pivot = np.argmax(np.abs(orig))
        d = scaled[pivot] / orig[pivot]
        assert math.isfinite(d) and d > 0
        err = float(np.max(np.abs(scaled-d*orig) / np.maximum(np.abs(scaled), np.abs(d*orig))))
        rerr = 0.
        for old, new in ((lo0[i], lo[i]), (hi0[i], hi[i])):
            assert math.isfinite(old) == math.isfinite(new)
            if math.isfinite(old):
                rerr = max(rerr, abs(new-d*old)/max(abs(new),abs(d*old),1.))
            else:
                assert old == new
        assert err <= 2e-13 and rerr <= 2e-13, (name, err, rerr)
        factors.append(d); errors.append(err); rhs_errors.append(rerr)
    write_csv(path, [{"row_name": n, "factor": d, "coefficient_rel_error": e, "rhs_rel_error": re}
                     for n, d, e, re in zip(lp0.row_names_, factors, errors, rhs_errors)])
    return a.tocsc(), {"max_coefficient_rel_error": max(errors), "max_rhs_rel_error": max(rhs_errors),
                      "min_factor": min(factors), "max_factor": max(factors), "nnz": a.nnz}


def condition(b):
    assert b.shape[0] == b.shape[1] and np.isfinite(b.data).all()
    norm = float(abs(b).sum(axis=0).max())
    lu = sla.splu(b.tocsc())
    op = sla.LinearOperator(b.shape, matvec=lu.solve, rmatvec=lambda x: lu.solve(x, "T"), dtype=np.float64)
    vals = []
    for seed in SEEDS:
        np.random.seed(seed)
        vals.append(norm * float(sla.onenormest(op, t=4)))
    assert all(math.isfinite(x) and x >= 1 for x in vals)
    # Residual check is a diagnostic, not a certified forward-error bound.
    rng = np.random.default_rng(20260914)
    rhs = rng.standard_normal(b.shape[0]); x = lu.solve(rhs)
    den = abs(b) @ abs(x) + abs(rhs)
    berr = float(np.max(np.abs(b @ x - rhs) / np.maximum(den, np.finfo(float).tiny)))
    return {"kappa1_seed0": vals[0], "kappa1_seed1": vals[1], "kappa1_seed2": vals[2],
            "estimator_max_min": max(vals) / min(vals), "lu_componentwise_backward_error": berr}


def run_instance(out, exe, cls, name, timelimit):
    folder = out / "fresh" / cls / Path(name).stem
    folder.mkdir(parents=True, exist_ok=False)
    inp = ROOT / "data/entradas" / CLASSES[cls] / name
    original = clean_instance_text(inp)
    results = []
    # Export every variant before selecting a basis. Keep full logs and command inputs.
    for variant, flags in VARIANTS.items():
        target = folder / (variant + ".lp")
        commands = f"{original}\n\nconfigurarSolver --DummyLp\npreprocesar {flags}\ngrabar {target} --noConstante\nsalir\n"
        (folder / (variant + "-commands.txt")).write_text(commands)
        with (folder / (variant + "-export.log")).open("w") as log:
            p = subprocess.run([str(exe)], input=commands, text=True, cwd=ROOT / "code",
                               stdout=log, stderr=subprocess.STDOUT, timeout=60)
        assert p.returncode == 0 and target.exists() and target.stat().st_size
    base = read_lp(folder / "Base.lp")
    h, lp0, a0 = base
    h.setOptionValue("time_limit", timelimit)
    h.setOptionValue("solver", "simplex")
    h.setOptionValue("random_seed", 0)
    h.setOptionValue("log_file", str(folder / "reference-lp.log"))
    h.setOptionValue("output_flag", True)
    h.setOptionValue("log_to_console", False)
    for j in range(lp0.num_col_):
        h.changeColIntegrality(j, highspy.HighsVarType.kContinuous)
    start = time.perf_counter(); h.run(); elapsed = time.perf_counter() - start
    status = str(h.getModelStatus())
    dump(folder / "reference-status.json", {"status": status, "time_s": elapsed})
    if h.getModelStatus() != highspy.HighsModelStatus.kOptimal:
        raise RuntimeError("reference LP: " + status)
    basis = h.getBasis(); sol = h.getSolution()
    assert basis.valid
    jset = [j for j,s in enumerate(basis.col_status) if s == highspy.HighsBasisStatus.kBasic]
    iset = [i for i,s in enumerate(basis.row_status) if s == highspy.HighsBasisStatus.kBasic]
    assert len(jset)+len(iset) == lp0.num_row_
    rnames, cnames = list(lp0.row_names_), list(lp0.col_names_)
    dump(folder / "reference-basis.json", {"source": "Base LP relaxation, HiGHS simplex",
         "row_names": rnames, "col_names": cnames,
         "basic_variables": [cnames[j] for j in jset],
         "basic_slack_rows": [rnames[i] for i in iset],
         "column_status": [str(s) for s in basis.col_status], "row_status": [str(s) for s in basis.row_status],
         "objective": h.getObjectiveValue(), "solve_seconds": elapsed})
    np.savez_compressed(folder / "reference-solution.npz", x=sol.col_value, activity=sol.row_value)
    unit = sp.csc_matrix((np.ones(len(iset)), (iset, range(len(iset)))), shape=(lp0.num_row_, len(iset)))
    for variant in VARIANTS:
        var = read_lp(folder / (variant + ".lp"))
        a, scaling = check_scaling(base, var, folder / (variant + "-row-factors.csv"))
        b = sp.hstack([a[:, jset], unit], format="csc")
        sp.save_npz(folder / (variant + "-basis.npz"), b)
        cond = condition(b)
        row = {"class": cls, "instance": name, "variant": variant, "rows": b.shape[0],
               "basic_structural": len(jset), "basic_slack": len(iset), **scaling, **cond,
               "basis_sha256": sha(folder / (variant + "-basis.npz")), "lp_sha256": sha(folder / (variant + ".lp"))}
        results.append(row)
        print(cls, name, variant, "kappa1", cond["kappa1_seed0"], flush=True)
        write_csv(folder / "results.csv", results)
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--exe", default=str(ROOT / "code/build-audit/SistemaElectrico"))
    ap.add_argument("--timelimit", type=float, default=60.)
    ap.add_argument("--historical-only", action="store_true")
    args = ap.parse_args()
    out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=False)
    selected = historical(out)
    exe = Path(args.exe).resolve()
    sources = [Path(__file__), ROOT / "scripts/validar_preprocesamiento.py", ROOT / "scripts/fixed_basis_diagnostic.py",
               ROOT / "scripts/fixed_basis_analysis.py", ROOT / "cluster/run_fixed_basis.slurm",
               ROOT / "code/SystemController/Problema/ProblemaLp/ProblemaLp.cpp"]
    (out / "source-snapshot").mkdir()
    for p in sources:
        (out / "source-snapshot" / p.name).write_bytes(p.read_bytes())
    dump(out / "design.json", {"selection": "first five lexicographic archived names whose input exists per class, frozen before exports or solves",
         "selected": selected, "variants": VARIANTS, "reference_basis": "Base LP relaxation, no MIP, HiGHS simplex default presolve",
         "slacks": "unscaled unit columns", "condition": "estimated 1-norm condition from sparse LU and onenormest(t=4)",
         "estimator_seeds": SEEDS, "lp_time_limit_s": args.timelimit, "threads": 1,
         "reader_small_matrix_value": 1e-12, "row_scaling_check_relative_tolerance": 2e-13,
         "versions": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__, "highspy": highspy.Highs().version()},
         "exe": str(exe), "exe_sha256": sha(exe),
         "sources": [{"path":str(p.relative_to(ROOT)), "sha256":sha(p)} for p in sources],
         "inputs": [{"path":str((ROOT / "data/entradas" / CLASSES[c] / n).relative_to(ROOT)),
                     "sha256":sha(ROOT / "data/entradas" / CLASSES[c] / n)} for c,ns in selected.items() for n in ns]})
    if args.historical_only:
        return
    rows, attempts = [], []
    for cls, names in selected.items():
        for name in names:
            print("ATTEMPT", cls, name, flush=True)
            try:
                added = run_instance(out, exe, cls, name, args.timelimit)
                rows.extend(added)
                attempts.append({"class":cls, "instance":name, "status":"complete", "records":len(added), "error":""})
            except Exception as exc:
                print("FAILURE", cls, name, repr(exc), flush=True)
                attempts.append({"class":cls, "instance":name, "status":"failed", "records":0, "error":repr(exc)})
            write_csv(out / "fresh-results.csv", rows)
            write_csv(out / "attempts.csv", attempts)
    summary = []
    for cls in selected:
        cells = {(r["instance"],r["variant"]):r for r in rows if r["class"]==cls}
        complete = [name for name in selected[cls] if all((name,v) in cells for v in VARIANTS)]
        for variant in VARIANTS:
            ratios = [cells[n,variant]["kappa1_seed0"]/cells[n,"Base"]["kappa1_seed0"] for n in complete]
            if ratios:
                summary.append({"class":cls, "variant":variant, "n":len(ratios),
                                "median_kappa_ratio_base":statistics.median(ratios),
                                "min_ratio":min(ratios), "max_ratio":max(ratios), "improved":sum(r<1 for r in ratios)})
    write_csv(out / "fresh-summary.csv", summary)
    dump(out / "completion.json", {"planned_instances":15,"complete_instances":sum(a["status"]=="complete" for a in attempts),
                                    "failed_instances":sum(a["status"]!="complete" for a in attempts), "records":len(rows)})


if __name__ == "__main__":
    main()
