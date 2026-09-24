#!/usr/bin/env python3
"""Performance-independent split and cost model for the robustness campaign.

Instances are ordered by sha256(salt | family | instance file hash). The first
k per family form the calibration set, the remainder the evaluation set, and
the first m evaluation instances per family the multi-seed subset. Expected
cost uses the historical one-thread Gurobi Base times as a proxy for every
policy; worst case assumes every run reaches its cap.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "results-revision/solver-robustness"
FAMILIES = ("Simple", "SG-Ter-Mer", "Full")


def order_key(salt, family, digest):
    return hashlib.sha256(f"{salt}|{family}|{digest}".encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=BASE / "inventory/instance-manifest.csv")
    ap.add_argument("--history", type=Path, default=BASE / "inventory/historical-base-times.csv")
    ap.add_argument("--out", type=Path, default=BASE / "design")
    ap.add_argument("--salt", default="solver-robustness-v1")
    ap.add_argument("--calibration", default="Simple=10,SG-Ter-Mer=10,Full=30")
    ap.add_argument("--multiseed", default="Simple=50,SG-Ter-Mer=50,Full=50")
    ap.add_argument("--full-evaluation", type=int, default=0, help="0 = all remaining Full instances")
    ap.add_argument("--caps", default="Simple=1800,SG-Ter-Mer=1800,Full=3600")
    ap.add_argument("--overhead", default="Simple=10,SG-Ter-Mer=10,Full=30")
    ap.add_argument("--policies", type=int, default=4)
    ap.add_argument("--gaps", type=int, default=2)
    ap.add_argument("--extra-seeds", type=int, default=4)
    args = ap.parse_args()
    parse = lambda s, f=int: {k: f(v) for k, v in (x.split("=") for x in s.split(","))}
    ncal, nms, caps, over = parse(args.calibration), parse(args.multiseed), parse(args.caps, float), parse(args.overhead, float)
    rows = list(csv.DictReader(args.manifest.open()))
    hist = {}
    for r in csv.DictReader(args.history.open()):
        if r["pool_version"] in ("sealed release", "corrected pool"):
            hist[(r["family"], r["instance"])] = r
    args.out.mkdir(parents=True, exist_ok=True)
    split, cost = [], {}
    for fam in FAMILIES:
        sub = sorted((r for r in rows if r["family"] == fam),
                     key=lambda r: order_key(args.salt, fam, r["sha256"]))
        cal, ev = sub[:ncal[fam]], sub[ncal[fam]:]
        if fam == "Full" and args.full_evaluation:
            ev = ev[:args.full_evaluation]
        ms = {r["instance"] for r in ev[:nms[fam]]}
        for rank, r in enumerate(sub):
            role = "calibration" if r in cal else ("evaluation" if r in ev else "unused")
            split.append({"family": fam, "instance": r["instance"], "sha256": r["sha256"],
                          "order": rank, "role": role, "multiseed": r["instance"] in ms})
        cap = caps[fam]
        per = []
        for r in ev:
            h = hist[(fam, r["instance"])]
            t1, t01 = float(h["t_gap1"]), float(h["t_gap01"])
            per.append((min(t1, cap), min(t01, cap), t1 <= cap, t01 <= cap))
        exp_pair = sum(a + b + 2 * over[fam] for a, b, _, _ in per)
        ms_pair = sum(a + b + 2 * over[fam] for (a, b, _, _), r in zip(per, ev) if r["instance"] in ms)
        runs = len(ev) * args.policies * args.gaps
        cost[fam] = {
            "cap_s": cap, "calibration": len(cal), "evaluation": len(ev), "multiseed": len(ms),
            "base_completion_at_cap_gap_1pct": round(sum(c for _, _, c, _ in per) / len(per), 3),
            "base_completion_at_cap_gap_0.1pct": round(sum(c for _, _, _, c in per) / len(per), 3),
            "primary_runs_per_solver": runs,
            "primary_expected_cpu_h_per_solver": round(exp_pair * args.policies / 3600, 1),
            "primary_worst_cpu_h_per_solver": round(runs * (cap + over[fam]) / 3600, 1),
            "multiseed_runs_per_solver": len(ms) * args.policies * args.gaps * args.extra_seeds,
            "multiseed_expected_cpu_h_per_solver": round(ms_pair * args.policies * args.extra_seeds / 3600, 1),
            "multiseed_worst_cpu_h_per_solver": round(len(ms) * args.policies * args.gaps * args.extra_seeds
                                                      * (cap + over[fam]) / 3600, 1),
        }
    with (args.out / "instance-split.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(split[0]))
        w.writeheader()
        w.writerows(split)
    total = {k: round(sum(c[k] for c in cost.values()), 1) for k in cost["Full"] if "cpu_h" in k or "runs" in k}
    out = {"salt": args.salt, "families": cost, "totals_per_solver": total,
           "assumption": "every policy and solver costs like historical one-thread Gurobi Base; overhead per run added"}
    (args.out / "cost-model.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
