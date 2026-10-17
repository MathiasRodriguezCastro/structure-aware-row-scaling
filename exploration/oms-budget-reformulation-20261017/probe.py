"""Exact bound propagation and an opportunity gate for budget-driven reformulation.

Bound propagation and binary coefficient strengthening are established techniques.
This prototype retains an exact derivation for every bound and changes only the
research model copies. It never calls an LP or MIP optimizer.
"""
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts/research"))
from budget_scaling import dyadic_factor

F = Fraction.from_float
EPSILON, GAMMA, UPPER = F(1e-6), F(1e-9), F(1e9)


def initial_bounds(model):
    return [[None if v[k] is None else F(float(v[k])) for v in model["variables"]]
            for k in ("lower", "upper")]


def activation_rows(model):
    result = []
    for i, row in enumerate(model["rows"]):
        if row["rhs"] != 0 or row["sense"] == "=":
            continue
        sign = 1 if row["sense"] == "<" else -1
        discrete = [(int(j), sign * F(float(a))) for j, a in row["terms"].items()
                    if model["variables"][int(j)]["integer"]]
        if len(discrete) != 1:
            continue
        j, coefficient = discrete[0]
        variable = model["variables"][j]
        if coefficient >= 0 or (variable["lower"], variable["upper"]) != (0., 1.):
            continue
        cap = UPPER * F(float(row["budget"])) / (EPSILON + UPPER * GAMMA)
        if -coefficient <= cap:
            continue
        result.append({"row": i, "binary": j, "sense_sign": sign,
                       "M": -coefficient, "necessary_M_ceiling": cap,
                       "other_terms": {int(k): sign * F(float(a)) for k, a in row["terms"].items() if int(k) != j}})
    return result


def support(terms, lower, upper, references):
    total = Fraction(0)
    used = []
    for j, a in terms.items():
        side = 1 if a > 0 else 0
        bound = (lower, upper)[side][j]
        if bound is None:
            return None, []
        total += a * bound
        used.append([j, side, references[side][j]])
    return total, used


def propagate(model, targets, max_sweeps=8, seconds_limit=15):
    lower, upper = initial_bounds(model)
    references = [[None] * len(lower) for _ in range(2)]
    inequalities = []
    for i, row in enumerate(model["rows"]):
        for sign in ([1, -1] if row["sense"] == "=" else [1] if row["sense"] == "<" else [-1]):
            inequalities.append((i, sign, {int(j): sign * F(float(a)) for j, a in row["terms"].items()},
                                 sign * F(float(row["rhs"]))))
    proof = []
    started = time.perf_counter()
    reason = "maximum_sweeps"
    sweep = 0
    for sweep in range(1, max_sweeps + 1):
        changes = 0
        for index, sign, terms, rhs in inequalities:
            minimum = {}
            refs = {}
            total = Fraction(0)
            unbounded = 0
            for j, a in terms.items():
                side = 0 if a > 0 else 1
                bound = (lower, upper)[side][j]
                refs[j] = [j, side, references[side][j]]
                minimum[j] = None if bound is None else a * bound
                if bound is None:
                    unbounded += 1
                else:
                    total += a * bound
            for j, a in terms.items():
                if unbounded - int(minimum[j] is None):
                    continue
                candidate = (rhs - total + (minimum[j] or 0)) / a
                side = 1 if a > 0 else 0
                old = (lower, upper)[side][j]
                if old is not None and (candidate >= old if side else candidate <= old):
                    continue
                proof.append({"variable": j, "side": side, "value": str(candidate),
                              "row": index, "row_sign": sign,
                              "support": [refs[k] for k in terms if k != j]})
                (lower, upper)[side][j] = candidate
                references[side][j] = len(proof) - 1
                changes += 1
                if lower[j] is not None and upper[j] is not None and lower[j] > upper[j]:
                    return lower, upper, references, proof, sweep, "exact_bound_contradiction"
            if time.perf_counter() - started >= seconds_limit:
                reason = "time_limit"
                break
        if reason == "time_limit":
            break
        enough = all((lambda b: b is not None and b <= t["necessary_M_ceiling"])(
            support(t["other_terms"], lower, upper, references)[0]) for t in targets)
        if enough:
            reason = "all_target_ceilings_reached"
            break
        if not changes:
            reason = "fixed_point"
            break
    return lower, upper, references, proof, sweep, reason


def admissibility(model):
    incompatible = []
    for i, row in enumerate(model["rows"]):
        reserve = GAMMA * sum((abs(F(float(a))) for j, a in row["terms"].items()
                               if model["variables"][int(j)]["integer"]), Fraction(0))
        d = dyadic_factor(list(row["terms"].values()), row["rhs"],
                          delta=row["budget"], epsilon=1e-6, rounding_allowance=reserve)
        if d.factor is None:
            incompatible.append({"row": i, "reason": d.reason})
    return incompatible


def main():
    output = HERE / "diagnostic"
    if output.exists():
        raise RuntimeError("diagnostic already exists; keep the saved results")
    output.mkdir()
    summary = []
    for name in ("Kondili-H10", "Kondili-H12", "control30-3-2-3", "neos-3421095-cinca", "ta1-UUM"):
        source = ROOT / "exploration/oms-generalization-20261014/pilot/models" / name / "original-model.json"
        model = json.loads(source.read_text())
        before = admissibility(model)
        targets = activation_rows(model)
        started = time.perf_counter()
        lower, upper, refs, proof, sweeps, reason = propagate(model, targets) if targets else (
            *initial_bounds(model), [[None] * len(model["variables"]) for _ in range(2)], [], 0, "no_critical_activation_rows")
        contractions = []
        if reason != "exact_bound_contradiction":
            for target in targets:
                bound, used = support(target["other_terms"], lower, upper, refs)
                if bound is None:
                    continue
                value = max(Fraction(0), bound)
                if value >= target["M"]:
                    continue
                coefficient = float(value)
                if not math.isfinite(coefficient):
                    continue
                if F(coefficient) < value:
                    coefficient = math.nextafter(coefficient, math.inf)
                if F(coefficient) >= target["M"]:
                    continue
                row = model["rows"][target["row"]]
                row["terms"][str(target["binary"])] = -target["sense_sign"] * coefficient
                if not coefficient:
                    del row["terms"][str(target["binary"])]
                contractions.append({"row": target["row"], "binary": target["binary"],
                                     "sense_sign": target["sense_sign"], "original_M": str(target["M"]),
                                     "certified_global_upper": str(bound), "new_M": coefficient,
                                     "necessary_M_ceiling": str(target["necessary_M_ceiling"]), "support": used})
        after = admissibility(model)
        folder = output / name
        folder.mkdir()
        record = {"source": str(source.relative_to(ROOT)), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                  "critical_activation_rows": len(targets), "propagation_sweeps": sweeps,
                  "stop_reason": reason, "elapsed_seconds": time.perf_counter() - started,
                  "bound_derivations": proof, "contractions": contractions,
                  "incompatible_before": before, "incompatible_after": after,
                  "new_optimizer_calls": 0}
        (folder / "certificate.json").write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")
        (folder / "reformulated-model.json").write_text(json.dumps(model, indent=2, allow_nan=False) + "\n")
        item = {"instance": name, "critical_rows": len(targets), "bound_derivations": len(proof),
                "contractions": len(contractions), "incompatible_before": len(before), "incompatible_after": len(after),
                "stop_reason": reason, "seconds": record["elapsed_seconds"]}
        summary.append(item)
        print(json.dumps(item), flush=True)
    (output / "SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
