"""Secondary, solver-free audit of robustness and external transfer evidence."""
import csv
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import statistics

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FRONT = ROOT / "exploration/oms-frontier-20261016/verified-runs.csv"
EXTERNAL = ROOT / "exploration/oms-followup-20261017/external/verified-runs.csv"
TOLERANCE = ROOT / "exploration/oms-followup-20261017/tolerance/verified-summary.csv"


def read(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def gm(xs):
    xs = list(xs)
    assert xs and all(math.isfinite(x) and x > 0 for x in xs)
    return math.exp(statistics.fmean(math.log(x) for x in xs))


def write(name, rows):
    with (HERE / name).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def flags(rows, field):
    return sum(r[field] == "True" for r in rows)


def subset_record(rows):
    return {
        "pairs": len(rows),
        "work_ratio": gm(r["work_ratio"] for r in rows),
        "full_time_ratio": gm(r["full_time_ratio"] for r in rows),
        "work_wins": sum(r["work_ratio"] < 1 for r in rows),
        "full_time_wins": sum(r["full_time_ratio"] < 1 for r in rows),
        "budget_passes": sum(r["budget_pass"] for r in rows),
        "bound_flags": sum(r["bound_flag"] for r in rows),
        "gap_flags": sum(r["gap_flag"] for r in rows),
        "maximum_candidate_cost_deterioration_percent": max(
            r["candidate_cost_deterioration_percent"] for r in rows
        ),
    }


def main():
    frontier = read(FRONT)
    assert len(frontier) == 978 and len({r["id"] for r in frontier}) == 330
    index = {}
    for r in frontier:
        key = (int(r["presolve"]), int(r["evaluated_volume_budget"]),
               r["instance"], int(r["seed"]), r["policy"])
        assert key not in index
        index[key] = r
    paired = []
    for key, r in sorted(index.items()):
        if r["policy"] != "Budget-L2":
            continue
        p, b, instance, seed, _ = key
        nf = index[p, b, instance, seed, "L2-NF3"]
        assert r["bound_contradiction"] in ("True", "False")
        assert nf["bound_contradiction"] in ("True", "False")
        c, cnf = Fraction(r["objective_exact"]), Fraction(nf["objective_exact"])
        assert cnf != 0
        paired.append({
            "presolve": p, "budget": b, "instance": instance, "seed": seed,
            "id": r["id"], "control_id": nf["id"],
            "work_ratio": float(r["work"]) / float(nf["work"]),
            "full_time_ratio": float(r["total_seconds"]) / float(nf["total_seconds"]),
            "budget_pass": r["budget_pass"] == "True",
            "bound_flag": r["bound_contradiction"] == "True",
            "gap_flag": r["gap_contradiction"] == "True",
            "candidate_cost_deterioration_percent": float(100 * (c - cnf) / abs(cnf)),
        })
    assert len(paired) == 222 and len({r["id"] for r in paired}) == 222
    groups, deletions, summary = [], [], []
    for p in (-1, 0):
        for b in (10, 30, 100, 300, 1000, 3000, 10000):
            rr = [r for r in paired if r["presolve"] == p and r["budget"] == b]
            models = sorted({r["instance"] for r in rr})
            seeds = sorted({r["seed"] for r in rr})
            assert len(rr) == (3 if b == 10 else 18)
            out = {"presolve": p, "budget": b, "models": len(models),
                   "abstentions": 18 - len(rr), **subset_record(rr)}
            for field, values in (("instance", models), ("seed", seeds)):
                for value in values:
                    subset = [r for r in rr if r[field] == value]
                    groups.append({"presolve": p, "budget": b,
                                   "group_by": field, "group": value, **subset_record(subset)})
                    remaining = [r for r in rr if r[field] != value]
                    if remaining:
                        deletions.append({"presolve": p, "budget": b,
                                          "removed_by": field, "removed": value,
                                          **subset_record(remaining)})
            for field in ("instance", "seed"):
                dd = [r for r in deletions if r["presolve"] == p
                      and r["budget"] == b and r["removed_by"] == field]
                for metric in ("work_ratio", "full_time_ratio"):
                    out[f"delete_{field}_{metric}_min"] = min(
                        (r[metric] for r in dd), default=None)
                    out[f"delete_{field}_{metric}_max"] = max(
                        (r[metric] for r in dd), default=None)
            summary.append(out)
    write("dispatch-pairs.csv", paired)
    write("dispatch-groups.csv", groups)
    write("dispatch-deletions.csv", deletions)
    write("dispatch-summary.csv", summary)

    external = read(EXTERNAL)
    assert len(external) == 96 and len({r["id"] for r in external}) == 96
    extindex = {(r["instance"], int(r["seed"]), r["policy"]): r for r in external}
    assert len(extindex) == 96
    external_summary = []
    for scope in ("all_eight_horizons", "six_nonanchor_horizons"):
        selected = [r for r in external if scope == "all_eight_horizons"
                    or r["known_pilot_anchor"] == "False"]
        for policy in ("L2", "Budget-L2", "L2-tight", "L2-NF3"):
            rr = [r for r in selected if r["policy"] == policy]
            assert len(rr) == (24 if scope == "all_eight_horizons" else 18)
            out = {"scope": scope, "policy": policy,
                   "models": len({r["instance"] for r in rr}), "calls": len(rr),
                   "budget_passes": flags(rr, "budget_pass"),
                   "known_bound_checks": sum(r["bound_flag"] in ("True", "False") for r in rr),
                   "unknown_bound_checks": sum(r["bound_flag"] == "" for r in rr),
                   "bound_flags": flags(rr, "bound_flag"), "gap_flags": flags(rr, "gap_flag")}
            assert out["known_bound_checks"] + out["unknown_bound_checks"] == len(rr)
            for control in ("L2", "L2-NF3"):
                for metric in ("work", "total_seconds"):
                    out[f"{metric}_ratio_to_{control}"] = gm(
                        float(r[metric]) / float(extindex[r["instance"], int(r["seed"]), control][metric])
                        for r in rr)
            external_summary.append(out)
    write("external-summary.csv", external_summary)
    result = {
        "analysis": "Secondary descriptive audit of already observed results",
        "new_optimizer_calls": 0,
        "independent_dispatch_models": 6,
        "seed_repetitions_are_independent_models": False,
        "deletion_ranges_are_confidence_intervals": False,
        "internal_solver_cause_identified": False,
        "external_computational_superiority_established": False,
        "inputs": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in (FRONT, EXTERNAL, TOLERANCE, HERE / "PROTOCOL.md")},
        "dispatch_summary": summary,
        "external_summary": external_summary,
        "integer_tolerance_sensitivity": read(TOLERANCE),
    }
    (HERE / "RESULTS.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    for r in summary:
        if r["presolve"] == -1 and r["budget"] in (30, 100):
            print(json.dumps(r, indent=2))
    for r in external_summary:
        if r["scope"] == "all_eight_horizons":
            print(json.dumps(r, indent=2))


if __name__ == "__main__":
    main()
