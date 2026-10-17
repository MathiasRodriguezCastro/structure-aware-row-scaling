"""Independent checks of actual exports and the negative cycles in this pilot.

Does not import the new selector or invoke a solver. LP input readers are used
only for the retained dispatch files. This pilot has radius zero in all feasible
real cases; positive-radius constructed examples are checked by enumeration.
"""
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
F = Fraction.from_float


def pow2(k):
    return Fraction(2) ** k


def logceil(q):
    guess = q.numerator.bit_length() - q.denominator.bit_length()
    while pow2(guess) < q:
        guess += 1
    while pow2(guess - 1) >= q:
        guess -= 1
    return guess


def model_from_source(record):
    source = ROOT / record["source"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == record["source_sha256"]
    if source.suffix == ".json":
        data = json.loads(source.read_text())
        names = [f"x{i:05d}" for i in range(len(data["variables"]))]
        integers = {n for n, d in zip(names, data["variables"]) if d["integer"]}
        rows = {f"r{i:05d}": {"rhs": r["rhs"], "terms": {names[int(j)]: a for j, a in r["terms"].items()}}
                for i, r in enumerate(data["rows"])}
        delta = {n: F(float(d["budget"])) for n, d in zip(rows, data["rows"])}
        gamma = F(1e-9) if record["scope"].startswith("rounded") else Fraction(0)
        bounds = {n: (d["lower"], d["upper"]) for n, d in zip(names, data["variables"])}
        costs = {n: d["cost"] for n, d in zip(names, data["variables"])}
    else:
        sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "scripts/research")]
        from audit_identifiability_grid import parse
        from audit_fixed_basis import read_lp
        from oms_dispatch_validation import physical_spec
        rows, _ = parse(source)
        _, lp, _ = read_lp(source)
        names = list(lp.col_names_)
        integers = {n for n, k in zip(names, lp.integrality_) if str(k) != "HighsVarType.kContinuous"}
        bounds = {n: tuple(None if not math.isfinite(x) else float(x) for x in pair)
                  for n, pair in zip(names, zip(lp.col_lower_, lp.col_upper_))}
        costs = dict(zip(names, lp.col_cost_))
        delta = {}
        for n, row in rows.items():
            scope = physical_spec(n, row["terms"])
            if scope:
                _, unit, conversion = scope
                delta[n] = F(.01 if unit == "MW" else float(record["volume_budget"])) * F(float(conversion))
            elif re.fullmatch(r"a\d+_activacion_[1-4]\(\d+\)", n):
                delta[n] = F(float(record["volume_budget"]))
        assert len(delta) == 4320
        gamma = F(1e-9)
    reserve = {n: gamma * sum((abs(F(float(a))) for j, a in row["terms"].items() if j in integers), Fraction(0))
               for n, row in rows.items()}
    return rows, integers, delta, reserve, bounds, costs


def check_cycle(record, model):
    rows, integers, delta, reserve, bounds, costs = model
    cycle = record["negative_cycle"]
    assert cycle and sum(e[2] for e in cycle) < 0
    assert all(cycle[i][1] == cycle[(i + 1) % len(cycle)][0] for i in range(len(cycle)))
    for source, target, cap, reason in cycle:
        if reason.startswith("rounding reserve exhausts budget "):
            row = reason.removeprefix("rounding reserve exhausts budget ")
            assert source == target == "anchor" and cap == -1 and reserve[row] >= delta[row]
        elif reason.startswith("fixed integer/control column "):
            name = reason.removeprefix("fixed integer/control column ").removesuffix(" upper")
            assert name in integers and source == "anchor" and target == "col:" + name and cap == 0
        elif reason.startswith("coefficient "):
            assert reason.endswith(" upper")
            row, column = reason.removeprefix("coefficient ").removesuffix(" upper").split(" / ")
            a = abs(F(float(rows[row]["terms"][column])))
            # In these negative cycles the active upper limit is the declared window.
            assert source == "col:" + column and target == "row:" + row
            assert a * pow2(cap) <= F(1e9) < a * pow2(cap + 1)
        elif reason.startswith("accuracy "):
            row = reason.removeprefix("accuracy ")
            assert delta[row] > reserve[row]
            assert source == "row:" + row and target == "anchor"
            assert cap == -logceil(F(1e-6) / (delta[row] - reserve[row]))
        else:
            raise AssertionError("cycle edge type not covered by this pilot verifier: " + reason)


def main():
    checked_rows = checked_data = checked_cycles = 0
    summary = json.loads((HERE / "diagnostic/SUMMARY.json").read_text())
    assert len(summary) == 27
    for item in summary:
        path = HERE / item["certificate"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        r = json.loads(path.read_text())
        model = model_from_source(r)
        if not r["compatible"]:
            check_cycle(r, model)
            checked_cycles += 1
            continue
        assert r["radius"] == 0 and all(v == 0 for v in r["v"].values())
        rows, integers, delta, reserve, bounds, costs = model
        for n, row in rows.items():
            alpha = pow2(r["u"][n])
            assert -1074 <= r["u"][n] <= 1023
            for j, a in row["terms"].items():
                value = math.ldexp(float(a), r["u"][n] + r["v"][j])
                assert math.isfinite(value) and F(value) == F(float(a)) * alpha * pow2(r["v"][j])
                assert F(1e-9) <= abs(F(value)) <= F(1e9)
                checked_data += 1
            value = math.ldexp(float(row["rhs"]), r["u"][n])
            assert math.isfinite(value) and abs(value) <= 1e19 and F(value) == F(float(row["rhs"])) * alpha
            if n in delta:
                assert F(1e-6) / alpha + reserve[n] <= delta[n]
            checked_rows += 1
        for name, exponent in r["v"].items():
            if name in integers:
                assert exponent == 0
            value = math.ldexp(float(costs[name]), exponent)
            assert math.isfinite(value) and F(value) == F(float(costs[name])) * pow2(exponent)
            for bound in bounds[name]:
                if bound is not None:
                    value = math.ldexp(float(bound), -exponent)
                    assert math.isfinite(value) and abs(value) <= 1e19
                    assert F(value) == F(float(bound)) / pow2(exponent)
            if name in r.get("bound_budgets", {}):
                assert F(r["epsilon_bound"]) * pow2(exponent) <= F(r["bound_budgets"][name])
    proof = {"diagnostic_cases": len(summary), "compatible_zero_radius_cases": len(summary) - checked_cycles,
             "independently_checked_negative_cycles": checked_cycles,
             "original_rows_checked": checked_rows, "coefficient_exports_checked": checked_data,
             "new_optimizer_calls": 0, "positive_radius_real_cases": 0,
             "new_selector_imported": False}
    (HERE / "VALIDATION.json").write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
