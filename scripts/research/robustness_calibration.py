#!/usr/bin/env python3
"""Apply the pre-registered cap rules R1 and R2 to the pilot and the history.

R1 picks, per family, the smallest cap in {1800, 3600, 7200} for which Base
completes at least 80% at gap 1% and 70% at gap 0.1%, for Gurobi (historical
one-thread logs) and for CPLEX (pilot). R2 decides the HiGHS scope. The rules
and thresholds were registered in campaign-manifest.json before the pilot ran.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "results-revision/solver-robustness"
CAPS = [1800.0, 3600.0, 7200.0]
THRESHOLD = {"0.01": 0.80, "0.001": 0.70}
FAMILY_KEY = {"Simple": "Simple", "SG-Ter-Mer": "SG-Ter-Mer", "Full": "Full"}


def pilot_completion(runs):
    rows = [json.loads(p.read_text()) for p in sorted(Path(runs).rglob("run.json"))]
    d = pd.DataFrame(rows)
    if d.empty:
        return d
    d["t"] = pd.to_numeric(d.tiempo_solver_s, errors="coerce")
    d["completed"] = d.outcome.eq("COMPLETED")
    out = []
    for (fam, solver, gap), g in d.groupby(["family", "solver", "gap"]):
        rec = {"family": fam, "solver": solver, "gap": str(gap), "n": len(g),
               "completed_at_cap_7200": round(float(g.completed.mean()), 4)}
        for cap in CAPS:
            rec[f"completed_by_{int(cap)}s"] = round(float((g.completed & (g.t <= cap)).mean()), 4)
        out.append(rec)
    return pd.DataFrame(out)


def history_completion(path, calibration=None, label="gurobi"):
    """Historical one-thread Gurobi Base: time to 1% from the log trajectory, to 0.1% from
    termination. Runs censored at the historical 3600 s limit count as not completed, so the
    7200 s column is unknown and left empty."""
    h = pd.read_csv(path)
    h = h[h.pool_version.isin(["sealed release", "corrected pool"])]
    h = h[~((h.family == "SG-Ter-Mer") & (h.pool_version == "sealed release"))]
    if calibration is not None:
        h = h[h.instance.isin(calibration)]
    rows = []
    for fam, g in h.groupby("family"):
        for gap, col in (("0.01", "t_gap1"), ("0.001", "t_gap01")):
            t = pd.to_numeric(g[col], errors="coerce").fillna(np.inf).to_numpy()
            rec = {"family": fam, "solver": label, "gap": gap, "n": len(g)}
            for cap in CAPS:
                rec[f"completed_by_{int(cap)}s"] = round(float((t <= cap).mean()), 4) if cap <= 3600 else None
            rows.append(rec)
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pilot-runs", type=Path, default=BASE / "runs-raw/pilot")
    ap.add_argument("--history", type=Path, default=BASE / "inventory/historical-base-times.csv")
    ap.add_argument("--split", type=Path, default=BASE / "design/instance-split.csv")
    ap.add_argument("--out", type=Path, default=BASE / "design/calibration-decision.json")
    args = ap.parse_args()
    pilot = pilot_completion(args.pilot_runs)
    hist = history_completion(args.history)
    # Diagnostic only, never read by the rule: is the calibration subset as hard as its pool?
    split = pd.read_csv(args.split)
    calib = set(split.query("role == 'calibration'").instance)
    subset = history_completion(args.history, calibration=calib, label="gurobi-calibration-subset")
    table = pd.concat([hist, pilot, subset], ignore_index=True)
    decision = {}
    for fam in FAMILY_KEY:
        chosen, reason = None, []
        for cap in CAPS:
            ok = True
            for solver in ("gurobi", "cplex"):
                for gap, need in THRESHOLD.items():
                    sel = table[(table.family == fam) & (table.solver == solver) & (table.gap == gap)]
                    if sel.empty:
                        ok = False; reason.append(f"{solver} {gap}: no data at {int(cap)}s"); continue
                    val = sel.iloc[0].get(f"completed_by_{int(cap)}s")
                    if val is None or np.isnan(val) or val < need:
                        ok = False
                        reason.append(f"{solver} gap {gap} at {int(cap)}s: {val} < {need}")
            if ok:
                chosen = cap
                break
        decision[fam] = {"cap_s": chosen if chosen else 7200.0,
                         "rule": "R1", "fallback_used": chosen is None, "checks": reason}
        highs = table[(table.family == fam) & (table.solver == "highs") & (table.gap == "0.01")]
        cap = decision[fam]["cap_s"]
        expected = int(split[(split.family == fam) & (split.role == "calibration")].shape[0])
        got = int(highs.iloc[0]["n"]) if not highs.empty else 0
        rate = float(highs.iloc[0][f"completed_by_{int(cap)}s"]) if not highs.empty else None
        decision[fam]["highs_base_completion_at_cap_gap_1pct"] = rate
        decision[fam]["highs_pilot_runs"] = f"{got}/{expected}"
        # An unfinished HiGHS pilot must not be read as a failure to complete.
        decision[fam]["highs_scope"] = ("undecided: HiGHS pilot incomplete" if got < expected else
                                        "full evaluation set" if rate >= 0.5 else
                                        "multiseed subset only (rule R2)")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.out.with_name("calibration-completion.csv"), index=False)
    args.out.write_text(json.dumps({"thresholds": THRESHOLD, "caps_considered": CAPS,
                                    "decision": decision}, indent=2) + "\n")
    print(table.to_string(index=False))
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
