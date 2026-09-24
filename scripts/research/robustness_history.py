#!/usr/bin/env python3
"""Reconstruct historical Base time-to-gap profiles from native Gurobi logs.

The historical runs (Gurobi 13.0.1, one thread, seed 1, MIPGap 1e-3, 3600 s)
predate this campaign. The time at which the logged relative gap first reaches
1% is read from the branch-and-bound table; completion at 0.1% is the solver's
own termination. Log lines are printed every few seconds, so time-to-1% is an
upper bound at that resolution. No policy other than Base is used.
"""
import argparse
import csv
import json
import math
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
TABLE = re.compile(r"(-|[\d.]+%)\s+\S+\s+(\d+)s\s*$")
EXPLORED = re.compile(r"^Explored \d+ nodes .* in ([\d.]+) seconds(?: \(([\d.]+) work units\))?")
FINAL = re.compile(r"^Best objective .*gap ([\d.]+|-)%?")
CAPS = (600, 1800, 3600)


def parse(path):
    lines = path.read_text(errors="replace").splitlines()
    out = {"threads": None, "mipgap": None, "timelimit": None, "status": "UNKNOWN",
           "time": math.nan, "work": math.nan, "final_gap_pct": math.nan, "t_gap1": math.inf,
           "integer_vars": None}
    in_mip = False
    for line in lines:
        if line.startswith("Set parameter MIPGap"):
            out["mipgap"] = float(line.split()[-1])
        elif line.startswith("Set parameter TimeLimit"):
            out["timelimit"] = float(line.split()[-1])
        elif "using up to" in line:
            out["threads"] = int(line.split("using up to")[1].split()[0])
        elif line.startswith("Variable types") and out["integer_vars"] is None:
            out["integer_vars"] = int(line.split(",")[1].split()[0])
        elif line.startswith("Root relaxation"):
            in_mip = True
        elif in_mip and (m := TABLE.search(line)) and m.group(1) != "-":
            gap = float(m.group(1)[:-1])
            if gap <= 1.0 and math.isinf(out["t_gap1"]):
                out["t_gap1"] = float(m.group(2))
        elif (m := EXPLORED.match(line)):
            out["time"] = float(m.group(1))
            out["work"] = float(m.group(2)) if m.group(2) else math.nan
            in_mip = False
        elif line.startswith("Optimal solution found"):
            out["status"] = "OPTIMAL"
        elif line.startswith("Time limit reached"):
            out["status"] = "TIME_LIMIT"
        elif (m := FINAL.match(line)) and m.group(1) != "-" and math.isnan(out["final_gap_pct"]):
            out["final_gap_pct"] = float(m.group(1))
    if out["status"] == "OPTIMAL":
        out["t_gap1"] = min(out["t_gap1"], out["time"])
    out["t_gap01"] = out["time"] if out["status"] == "OPTIMAL" else math.inf
    return out


def summarize(rows):
    res = {"n": len(rows), "statuses": {}}
    for r in rows:
        res["statuses"][r["status"]] = res["statuses"].get(r["status"], 0) + 1
    for key, label in (("t_gap1", "gap_1pct"), ("t_gap01", "gap_0.1pct")):
        t = np.array([r[key] for r in rows], dtype=float)
        res[label] = {f"completed_by_{c}s": round(float(np.mean(t <= c)), 4) for c in CAPS}
        done = t[np.isfinite(t)]
        res[label]["completed_time_quantiles_s"] = {q: round(float(np.quantile(done, q)), 1)
                                                    for q in (0.5, 0.8, 0.9, 0.95)} if done.size else {}
        for c in (1800, 3600):
            res[label][f"mean_cpu_s_at_cap_{c}"] = round(float(np.mean(np.minimum(t, c))), 1)
    cens = [r["final_gap_pct"] for r in rows if r["status"] == "TIME_LIMIT"]
    if cens:
        res["censored_final_gap_pct"] = {"n": len(cens), "median": float(np.median(cens)),
                                         "max": float(np.max(cens)),
                                         "at_most_0.2pct": int(sum(g <= 0.2 for g in cens)),
                                         "at_most_0.5pct": int(sum(g <= 0.5 for g in cens))}
    return res


def main():
    base = ROOT / "results-revision/solver-robustness/inventory"
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=Path, default=base / "raw")
    ap.add_argument("--out", type=Path, default=base)
    args = ap.parse_args()
    sources = {("Simple", "sealed release"): ("hist_banco_base/simple", "*_base.log"),
               ("SG-Ter-Mer", "sealed release, defective total demand"): ("hist_banco_base/sgtm", "*_base.log"),
               ("SG-Ter-Mer", "corrected pool"): ("hist_sgtm_fixed", "*_base.log"),
               ("Full", "sealed release"): ("hist_banco_base/completo", "*_base.log")}
    rows, summary = [], {}
    for (fam, version), (folder, pattern) in sources.items():
        logs = sorted((args.raw / folder).rglob(pattern))
        parsed = []
        for log in logs:
            r = {"family": fam, "pool_version": version, "instance": log.name.replace("_base.log", ""),
                 "log": str(log.relative_to(args.raw))} | parse(log)
            parsed.append(r)
        rows += parsed
        summary[f"{fam} ({version})"] = summarize(parsed) | {
            "settings": sorted({(r["threads"], r["mipgap"], r["timelimit"]) for r in parsed})}
    with (args.out / "historical-base-times.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    (args.out / "historical-base-summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
