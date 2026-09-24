#!/usr/bin/env python3
"""Fixed-basis conditioning audit over every archived dispatch input.

Reuses the export, row-scaling check, basis assembly and condition estimate of
audit_fixed_basis.py, with the policy set of the current manuscript. The design
(instances, variants, reference basis, estimator) is written before any solve.
"""
import argparse
import csv
import hashlib
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import platform
import statistics
import sys

import numpy as np
import scipy
import highspy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_fixed_basis as afb

ROOT = afb.ROOT
VARIANTS = {"Base": "--solodiagnostico",
            "Flat-GM": "--local-matricial --plano",
            "Flat-L2": "--local-matricial --plano --kernel-euclideo",
            "Role-Hybrid": "--local-matricial --acoplamiento-l2",
            "SA-Mat": "--local-matricial"}
afb.VARIANTS = VARIANTS


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def job(out, exe, cls, name, timelimit):
    try:
        return cls, name, afb.run_instance(out, exe, cls, name, timelimit), ""
    except Exception as exc:
        return cls, name, [], repr(exc)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--exe", default=str(ROOT / "code/build-audit/SistemaElectrico"))
    ap.add_argument("--timelimit", type=float, default=300.)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    exe = Path(args.exe).resolve()
    selected = {cls: sorted(p.name for p in (ROOT / "data/entradas" / folder).glob("*.txt"))
                for cls, folder in afb.CLASSES.items()}
    sources = [Path(__file__), Path(afb.__file__), ROOT / "scripts/validar_preprocesamiento.py",
               ROOT / "code/SystemController/Problema/ProblemaLp/ProblemaLp.cpp",
               ROOT / "code/SystemController/Problema/PreprocesamientoMIP/PreprocesamientoMIP.cpp"]
    (out / "source-snapshot").mkdir()
    for p in sources:
        (out / "source-snapshot" / p.name).write_bytes(p.read_bytes())
    afb.dump(out / "design.json", {
        "selection": "all archived inputs of the three dispatch classes; no exclusion",
        "selected": selected, "variants": VARIANTS,
        "reference_basis": "optimal basis of the Base LP relaxation (integrality dropped), HiGHS simplex, one thread, random_seed 0",
        "basis_assembly": "structural basic columns from each variant's own export; basic slacks as unscaled unit columns",
        "condition": "1-norm condition estimate: exact ||B||_1 times onenormest(t=4) of the sparse-LU inverse, seeds 0,1,2",
        "row_scaling_check_relative_tolerance": 2e-13, "reader_small_matrix_value": 1e-12,
        "lp_time_limit_s": args.timelimit, "workers": args.workers,
        "versions": {"python": platform.python_version(), "numpy": np.__version__,
                     "scipy": scipy.__version__, "highspy": highspy.Highs().version()},
        "exe": str(exe.relative_to(ROOT)), "exe_sha256": sha(exe),
        "sources": [{"path": str(p.relative_to(ROOT)), "sha256": sha(p)} for p in sources],
        "inputs": [{"path": str((ROOT / "data/entradas" / afb.CLASSES[c] / n).relative_to(ROOT)),
                    "sha256": sha(ROOT / "data/entradas" / afb.CLASSES[c] / n)}
                   for c, ns in selected.items() for n in ns]})
    rows, attempts = [], []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(job, out, exe, c, n, args.timelimit)
                   for c, ns in selected.items() for n in ns]
        for fut in as_completed(futures):
            cls, name, added, err = fut.result()
            rows.extend(added)
            attempts.append({"class": cls, "instance": name,
                             "status": "complete" if not err else "failed",
                             "records": len(added), "error": err})
            print(len(attempts), cls, name, "ok" if not err else "FAILED " + err, flush=True)
    order = {c: i for i, c in enumerate(afb.CLASSES)}
    key = lambda r: (order[r["class"]], r["instance"], list(VARIANTS).index(r["variant"]) if "variant" in r else 0)
    rows.sort(key=key)
    attempts.sort(key=lambda r: (order[r["class"]], r["instance"]))
    afb.write_csv(out / "fresh-results.csv", rows)
    afb.write_csv(out / "attempts.csv", attempts)
    summary = []
    for cls in afb.CLASSES:
        cells = {(r["instance"], r["variant"]): r for r in rows if r["class"] == cls}
        complete = sorted({i for i, _ in cells if all((i, v) in cells for v in VARIANTS)})
        for variant in VARIANTS:
            ratios = [cells[n, variant]["kappa1_seed0"] / cells[n, "Base"]["kappa1_seed0"] for n in complete]
            if ratios:
                summary.append({"class": cls, "variant": variant, "n": len(ratios),
                                "median_kappa_ratio_base": statistics.median(ratios),
                                "min_ratio": min(ratios), "max_ratio": max(ratios),
                                "improved": sum(r < 1 for r in ratios)})
    afb.write_csv(out / "fresh-summary.csv", summary)
    afb.dump(out / "completion.json", {
        "planned_instances": sum(map(len, selected.values())),
        "complete_instances": sum(a["status"] == "complete" for a in attempts),
        "failed_instances": sum(a["status"] != "complete" for a in attempts), "records": len(rows)})


if __name__ == "__main__":
    main()
