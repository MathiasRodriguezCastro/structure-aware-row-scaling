#!/usr/bin/env python3
"""Attribute a contradicted optimality claim on one instance.

Exports the unscaled model that the Base policy solves, then solves that file directly
with gurobipy under several settings. Reproducing the wrong answer from the exported file
rules out the C++ pipeline; recovering the right one with presolve off or a higher numerical
emphasis attributes the failure inside the solver.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import validar_preprocesamiento as vp  # noqa: E402

SETTINGS = [("default", {}),
            ("numericfocus3", {"NumericFocus": 3}),
            ("presolve_off", {"Presolve": 0}),
            ("numericfocus3_presolve_off", {"NumericFocus": 3, "Presolve": 0}),
            ("scaleflag2", {"ScaleFlag": 2})]


def export(instance, exe, lp_path):
    script = "\n".join([vp.clean_instance_text(instance), "",
                        "configurarSolver --Gurobi --timeout 60 --mipgap 0.01",
                        f"grabar {lp_path} --noConstante", "salir"]) + "\n"
    r = subprocess.run([str(exe)], input=script, text=True, cwd=str(exe.parent.parent),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if not lp_path.exists():
        raise SystemExit(r.stdout[-2000:])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--instance", type=Path, required=True)
    ap.add_argument("--exe", type=Path, default=ROOT / "code/build-robust/SistemaElectrico")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--gap", type=float, default=0.01)
    ap.add_argument("--time-limit", type=float, default=900.0)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    lp = args.out / "original.lp"  # absolute: the binary runs in its own directory
    if not lp.exists():
        export(args.instance, args.exe, lp)
    import gurobipy as gp
    m = gp.read(str(lp))
    m.setParam("OutputFlag", 0)
    results = {"instance": str(args.instance), "gap": args.gap, "seed": args.seed,
               "rows": m.NumConstrs, "columns": m.NumVars, "binaries": m.NumBinVars,
               "gurobipy": ".".join(map(str, gp.gurobi.version())), "settings": {}}
    for label, params in SETTINGS:
        m.reset()
        for k, v in [("Threads", 1), ("Seed", args.seed), ("MIPGap", args.gap),
                     ("TimeLimit", args.time_limit), ("FeasibilityTol", 1e-6),
                     ("IntFeasTol", 1e-5), ("NumericFocus", 0), ("Presolve", -1), ("ScaleFlag", -1)]:
            m.setParam(k, v)
        for k, v in params.items():
            m.setParam(k, v)
        t0 = time.perf_counter()
        m.optimize()
        results["settings"][label] = {"status": m.Status, "objective": m.ObjVal if m.SolCount else None,
                                      "bound": m.ObjBound, "gap": m.MIPGap, "nodes": m.NodeCount,
                                      "seconds": round(time.perf_counter() - t0, 2)}
        print(label, json.dumps(results["settings"][label]))
    (args.out / "direct-gurobi.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
