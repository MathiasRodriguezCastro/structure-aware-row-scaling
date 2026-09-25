#!/usr/bin/env python3
"""Execute one shard of a frozen robustness run table.

Each run is one process of the dispatch binary (policy x solver x gap x seed on
one instance). The native log is kept compressed next to a run.json record with
provenance, solver outcome, effort and original-model residuals. Completed runs
are skipped, so a shard can be resubmitted after an infrastructure failure.
"""
import argparse
import csv
import datetime as dt
import gzip
import json
import os
import platform
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import validar_preprocesamiento as vp  # noqa: E402

POLICY_VARIANT = {"Base": "base", "Flat-GM": "matricial_plano",
                  "Flat-L2": "matricial_plano_l2", "Role-Hybrid": "role_hybrid"}
SOLVER_FLAG = {"gurobi": "Gurobi", "cplex": "Cplex", "highs": "Highs"}
LICENSE_RE = re.compile(r"Too many sessions|has expired|Overage for too long|token\.gurobi\.com|"
                        r"Error al inicializar Gurobi|No Gurobi license|CPXERR_NO_LICENSE|"
                        r"license.*(invalid|not found)", re.I)
STARTED_RE = re.compile(r"Optimize a model with|Version identifier:|Running HiGHS|\[pipeline\] Resolviendo")
NOSOL_RE = re.compile(r"\[NOSOL\] status=(\S+).*?tiempo_solver_s=([0-9.eE+\-]+)"
                      r"(?:.*?dettime=([0-9.eE+\-]+))?.*?best_bound=([0-9.eE+\-]+).*?nodos=([0-9.eE+\-]+)")
VERSION_RE = [(re.compile(r"Gurobi Optimizer version (\S+)"), 1),
              (re.compile(r"Version identifier: (\S+)"), 1),
              (re.compile(r"Running HiGHS (\S+)"), 1)]
HIGHS_RE = re.compile(r"\[HIGHS\] model_status=(.+?) run_status=(-?\d+).*?lp_iterations=(\d+)")
FIELDS_FROM_PARSE = ["status_solver", "tiempo_solver_s", "gap_pct", "objetivo_solver", "best_bound",
                     "nodos_explorados", "iter_simplex", "work_units", "dettime_ticks", "root_gap",
                     "root_time", "presolve_time_s", "rows_presolved", "cols_presolved",
                     "solver_warnings", "solver_warnings_txt"]


def cpu_model():
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor()


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def classify(rc, text, parsed, nosol, external_timeout):
    """Return (outcome, infrastructure_failure)."""
    if LICENSE_RE.search(text):
        return "LICENSE_FAILURE", True
    if not STARTED_RE.search(text):
        return "INFRASTRUCTURE_FAILURE", True
    if external_timeout:
        return "WRAPPER_TIMEOUT", False
    # Killed by a signal with nothing from the solver: a resource limit or a node event,
    # not an outcome of the solve.
    if rc < 0 and not nosol and not parsed.get("status_solver"):
        return "KILLED_BY_SIGNAL", True
    if nosol:
        status = nosol[0]
        if status == "TIME_LIMIT":
            return "TIME_LIMIT_NO_SOLUTION", False
    else:
        status = parsed.get("status_solver")
        if status == "OPTIMAL" and rc == 0:
            return "COMPLETED", False
        if status == "TIME_LIMIT" and rc == 0:
            return "TIME_LIMIT", False
    if status in ("INFEASIBLE", "INF_OR_UNBD"):
        return "SOLVER_INFEASIBLE", False
    if status == "NUMERIC":
        return "SOLVER_NUMERICAL", False
    return f"SOLVER_OTHER_{status}", False


def execute(row, args, out_dir):
    run_dir = out_dir / row["run_id"]
    record_path = run_dir / "run.json"
    if record_path.exists():
        prev = json.loads(record_path.read_text())
        if not prev.get("infrastructure_failure"):
            return prev["outcome"], True
    run_dir.mkdir(parents=True, exist_ok=True)
    instance = ROOT / row["instance_path"]
    cap = float(row["cap_s"])
    extra = f"--seed {row['seed']} --feastol {args.feastol:g} --inttol {args.inttol:g} --sin-kappa"
    csv_path = run_dir / "solution.csv"
    script = vp.build_script(instance, SOLVER_FLAG[row["solver"]], cap, float(row["gap"]),
                             POLICY_VARIANT[row["policy"]], csv_path, verificar_original=True)
    solver_line = f"configurarSolver --{SOLVER_FLAG[row['solver']]} --timeout {cap:g} --mipgap {float(row['gap']):g}"
    assert solver_line in script
    script = script.replace(solver_line, f"{solver_line} {extra}", 1)
    (run_dir / "script.txt").write_text(script)
    env = dict(os.environ, OMP_NUM_THREADS=str(row["threads"]))
    started, t0 = now(), time.monotonic()
    external_timeout = False
    try:
        proc = subprocess.run([str(args.exe)], input=script, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, cwd=str(args.exe.parent.parent), env=env,
                              timeout=cap + args.margin, check=False)
        text, rc = proc.stdout or "", proc.returncode
    except subprocess.TimeoutExpired as exc:
        text = exc.output if isinstance(exc.output, str) else (exc.output or b"").decode("utf-8", "ignore")
        rc, external_timeout = 124, True
    wall = time.monotonic() - t0
    finished = now()
    log_path = run_dir / "log.txt"
    log_path.write_text(text)
    parsed = vp.parse_log(log_path)
    clean = vp.ANSI_RE.sub("", text)
    m = NOSOL_RE.search(clean)
    nosol = m.groups() if m else None
    outcome, infra = classify(rc, clean, parsed, nosol, external_timeout)
    version = next((m.group(g) for rx, g in VERSION_RE if (m := rx.search(clean))), None)
    hm = HIGHS_RE.search(clean)
    record = {k: row[k] for k in row}
    record.update({
        "campaign_id": args.campaign_id, "manifest_sha256": args.manifest_sha256,
        "git_commit": args.git_commit, "binary_sha256": args.binary_sha256,
        "solver_version": version, "primal_feasibility_tol": args.feastol,
        "integrality_tol": args.inttol, "presolve": "solver default",
        "internal_scaling": "solver default", "node": socket.gethostname(), "cpu_model": cpu_model(),
        "slurm_job_id": os.environ.get("SLURM_JOB_ID"), "slurm_array_task_id": os.environ.get("SLURM_ARRAY_TASK_ID"),
        "start_utc": started, "end_utc": finished, "wall_s": wall, "return_code": rc,
        "outcome": outcome, "infrastructure_failure": infra, "external_timeout": external_timeout,
        "nosol_status": nosol[0] if nosol else None,
        "nosol_time_s": float(nosol[1]) if nosol else None,
        "nosol_best_bound": float(nosol[3]) if nosol else None,
        "highs_model_status": hm.group(1) if hm else None,
        "highs_lp_iterations": int(hm.group(3)) if hm else None,
        "objetivo_post": vp.read_objective_post(vp.post_csv_path(csv_path)),
    })
    for key in FIELDS_FROM_PARSE:
        record[key] = parsed.get(key)
    for stage in ("solver", "post"):
        for key in ("max_le", "max_ge", "max_eq", "max_lb", "max_ub", "max_int", "max_viol_rel",
                    "max_viol_relact", "missing", "obj_original"):
            record[f"verif_{stage}_{key}"] = parsed.get(f"verif_{stage}_{key}")
    if record["tiempo_solver_s"] is None and nosol:
        record["tiempo_solver_s"] = float(nosol[1])
    with gzip.open(run_dir / "log.txt.gz", "wt") as fh:
        fh.write(text)
    log_path.unlink()
    for p in (csv_path, vp.post_csv_path(csv_path)):
        if p.exists():
            p.unlink()
    record_path.write_text(json.dumps(record, indent=1, default=str) + "\n")
    return outcome, False


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=Path, required=True)
    ap.add_argument("--shard", type=int, default=int(os.environ.get("SLURM_ARRAY_TASK_ID", "-1")))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--exe", type=Path, required=True)
    ap.add_argument("--campaign-id", required=True)
    ap.add_argument("--manifest-sha256", required=True)
    ap.add_argument("--git-commit", required=True)
    ap.add_argument("--binary-sha256", required=True)
    ap.add_argument("--feastol", type=float, default=1e-6)
    ap.add_argument("--inttol", type=float, default=1e-5)
    ap.add_argument("--margin", type=float, default=900.0)
    args = ap.parse_args()
    args.exe = args.exe.resolve()
    rows = [r for r in csv.DictReader(args.runs.open()) if int(r["shard"]) == args.shard]
    rows.sort(key=lambda r: int(r["order"]))
    if not rows:
        raise SystemExit(f"shard {args.shard}: no runs")
    print(f"[shard {args.shard}] {len(rows)} runs on {socket.gethostname()} at {now()}", flush=True)
    for r in rows:
        outcome, skipped = execute(r, args, args.out)
        print(f"  {r['run_id']} {outcome}{' (kept)' if skipped else ''}", flush=True)


if __name__ == "__main__":
    main()
