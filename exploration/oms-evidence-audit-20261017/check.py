"""Check secondary aggregates against raw saved outcomes and parent process timings."""
import csv
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FRONT = ROOT / "exploration/oms-frontier-20261016"
EXT = ROOT / "exploration/oms-followup-20261017/external"


def load(path):
    return json.loads(path.read_text())


def read(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def geometric(values):
    with localcontext() as ctx:
        ctx.prec = 80
        product, count = Decimal(1), 0
        for value in values:
            product *= Decimal.from_float(value)
            count += 1
        assert count > 0
        return float(product ** (Decimal(1) / Decimal(count)))


def same(actual, expected):
    assert math.isclose(float(actual), expected, rel_tol=2e-12, abs_tol=1e-13), (actual, expected)


def main():
    result = load(HERE / "RESULTS.json")
    for rel, digest in result["inputs"].items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == digest
    timing = {r["job"]["id"]: r for r in load(FRONT / "parent-timing.json")}
    native = {}
    for name, r in timing.items():
        if not r["abstained"]:
            native[name] = load(FRONT / "runs" / name / "result.json")
    assert len(native) == 330 and len(timing) == 360
    pairs = read(HERE / "dispatch-pairs.csv")
    assert len(pairs) == 222 and len({r["id"] for r in pairs}) == 222
    for r in pairs:
        a, b = native[r["id"]], native[r["control_id"]]
        assert a["job"]["policy"] == "Budget-L2" and b["job"]["policy"] == "L2-NF3"
        for key in ("instance", "seed", "presolve"):
            assert a["job"][key] == b["job"][key]
        same(r["work_ratio"], a["outcome"]["work"] / b["outcome"]["work"])
        same(r["full_time_ratio"], timing[r["id"]]["total_fresh_process_seconds"] /
             timing[r["control_id"]]["total_fresh_process_seconds"])
        qa, qb = Fraction(a["checks"]["point_objective_exact"]), Fraction(b["checks"]["point_objective_exact"])
        same(r["candidate_cost_deterioration_percent"], float(100 * (qa - qb) / abs(qb)))
        assert (r["bound_flag"] == "True") == a["checks"]["bound_contradiction"]
        assert (r["gap_flag"] == "True") == a["checks"]["completion_contradiction"]
    aggregate_count = 0
    for name in ("dispatch-groups.csv", "dispatch-deletions.csv", "dispatch-summary.csv"):
        for r in read(HERE / name):
            subset = [v for v in pairs if (v["presolve"], v["budget"]) == (r["presolve"], r["budget"])]
            if "group_by" in r:
                subset = [v for v in subset if v[r["group_by"]] == r["group"]]
            if "removed_by" in r:
                subset = [v for v in subset if v[r["removed_by"]] != r["removed"]]
            assert len(subset) == int(r["pairs"])
            for key in ("work_ratio", "full_time_ratio"):
                same(r[key], geometric(float(v[key]) for v in subset))
                assert int(r["work_wins" if key == "work_ratio" else "full_time_wins"]) == sum(float(v[key]) < 1 for v in subset)
            same(r["maximum_candidate_cost_deterioration_percent"],
                 max(float(v["candidate_cost_deterioration_percent"]) for v in subset))
            for field, output in (("budget_pass", "budget_passes"), ("bound_flag", "bound_flags"), ("gap_flag", "gap_flags")):
                assert int(r[output]) == sum(v[field] == "True" for v in subset)
            aggregate_count += 1
    for r in result["dispatch_summary"]:
        dd = [v for v in read(HERE / "dispatch-deletions.csv") if int(v["presolve"]) == r["presolve"] and int(v["budget"]) == r["budget"]]
        for field in ("instance", "seed"):
            ss = [v for v in dd if v["removed_by"] == field]
            for metric in ("work_ratio", "full_time_ratio"):
                for mode, fn in (("min", min), ("max", max)):
                    value = r[f"delete_{field}_{metric}_{mode}"]
                    if ss:
                        same(value, fn(float(v[metric]) for v in ss))
                    else:
                        assert value is None

    etiming = {r["job"]["id"]: r for r in load(EXT / "jobs-timing.json")}
    enative = {name: load(EXT / "runs" / name / "result.json") for name in etiming}
    eindex = {(r["job"]["instance"], r["job"]["seed"], r["job"]["policy"]): name for name, r in enative.items()}
    design = load(EXT / "design.json")
    for r in result["external_summary"]:
        names = [name for name, a in enative.items() if a["job"]["policy"] == r["policy"] and
                 (r["scope"] == "all_eight_horizons" or not design["models"][a["job"]["instance"]]["known_pilot_anchor"])]
        assert len(names) == r["calls"]
        assert r["budget_passes"] == sum(enative[name]["verification"]["primal_accepted"] for name in names)
        assert r["unknown_bound_checks"] == sum(enative[name]["flags"]["bound_contradiction"] is None for name in names)
        assert r["bound_flags"] == sum(enative[name]["flags"]["bound_contradiction"] is True for name in names)
        assert r["gap_flags"] == sum(enative[name]["flags"]["completion_contradiction"] is True for name in names)
        for control in ("L2", "L2-NF3"):
            wr, tr = [], []
            for name in names:
                a = enative[name]
                peer = eindex[a["job"]["instance"], a["job"]["seed"], control]
                wr.append(a["outcome"]["work"] / enative[peer]["outcome"]["work"])
                tr.append(etiming[name]["total_fresh_process_seconds"] / etiming[peer]["total_fresh_process_seconds"])
            same(r[f"work_ratio_to_{control}"], geometric(wr))
            same(r[f"total_seconds_ratio_to_{control}"], geometric(tr))
    proof = {"raw_frontier_terminal_calls": len(native), "raw_frontier_abstentions": 30,
             "checked_dispatch_pairs": len(pairs), "checked_aggregate_rows": aggregate_count,
             "raw_external_terminal_calls": len(enative), "checked_external_summary_rows": 8,
             "geometric_mean_check": "80-digit Decimal products against logarithmic means",
             "new_optimizer_calls": 0,
             "raw_outcomes_and_parent_timings_used": True,
             "results_sha256": hashlib.sha256((HERE / "RESULTS.json").read_bytes()).hexdigest()}
    (HERE / "VALIDATION.json").write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
