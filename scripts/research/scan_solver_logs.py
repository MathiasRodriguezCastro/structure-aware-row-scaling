#!/usr/bin/env python3
"""Pull the solver-reported status out of the stored run logs.

The runner records the status the C++ layer derives; the raw logs also carry the solver's own
words, including the HiGHS self-check that rejects a solution it had called optimal. This scan
keeps those in a table the analysis can join, without touching the frozen runner.
"""
import argparse
import csv
import gzip
import re
from pathlib import Path

HIGHS = re.compile(r"\[HIGHS\] model_status=(.+?) run_status=(-?\d+)")
SELFCHECK = re.compile(r"MIP solver claims optimality, but with num/max/sum primal\(([^)]*)\)")
GRB_WARN = re.compile(r"Warning: Model contains (.+)")
ROOT_LP = re.compile(r"Root relaxation: objective ([-\d.e+]+)")
GRB_FINAL = re.compile(r"Best objective ([-\d.e+]+), best bound ([-\d.e+]+)")


def scan(path):
    try:
        with gzip.open(path, "rt", errors="ignore") as fh:
            text = fh.read()
    except OSError:
        return None
    m = HIGHS.search(text)
    s = SELFCHECK.search(text)
    r = ROOT_LP.search(text)
    f = GRB_FINAL.search(text)
    return {"root_relaxation": float(r.group(1)) if r else None,
            "final_objective": float(f.group(1)) if f else None,
            "final_bound": float(f.group(2)) if f else None,
            "highs_model_status": m.group(1) if m else None,
            "highs_run_status": int(m.group(2)) if m else None,
            "solver_self_check_rejected": bool(s),
            "solver_self_check_infeasibilities": s.group(1) if s else None,
            "model_warnings": "; ".join(sorted(set(GRB_WARN.findall(text)))) or None}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    rows = []
    for log in sorted(args.runs.rglob("log.txt.gz")):
        rec = scan(log)
        if rec:
            rec["run_id"] = log.parent.name
            rows.append(rec)
    if not rows:
        raise SystemExit(f"no logs under {args.runs}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["run_id", "root_relaxation", "final_objective",
                                           "final_bound", "highs_model_status", "highs_run_status",
                                           "solver_self_check_rejected",
                                           "solver_self_check_infeasibilities", "model_warnings"])
        w.writeheader()
        w.writerows(rows)
    rejected = sum(r["solver_self_check_rejected"] for r in rows)
    print(f"{len(rows)} logs, {rejected} rejected by the solver's own check -> {args.out}")


if __name__ == "__main__":
    main()
