"""Prespecified structural opportunity gate; does not invoke an optimizer."""
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import time

import selector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def external_model(path, rounded):
    data = json.loads(path.read_text())
    names = [f"x{i:05d}" for i in range(len(data["variables"]))]
    rows = {f"r{i:05d}": {"terms": {names[int(j)]: a for j, a in r["terms"].items()},
                           "rhs": r["rhs"], "sense": {"<": "<=", ">": ">=", "=": "="}[r["sense"]]}
            for i, r in enumerate(data["rows"])}
    integers = {n for n, v in zip(names, data["variables"]) if v["integer"]}
    gamma = Fraction.from_float(1e-9) if rounded else Fraction(0)
    model = {"rows": rows, "columns": names, "integers": integers,
             "costs": {n: v["cost"] for n, v in zip(names, data["variables"])},
             "bounds": {n: (v["lower"] if v["lower"] is not None else -math.inf,
                            v["upper"] if v["upper"] is not None else math.inf)
                        for n, v in zip(names, data["variables"])},
             "delta": {n: Fraction.from_float(float(r["budget"])) for n, r in zip(rows, data["rows"])},
             "E": {n: gamma * sum((abs(Fraction.from_float(float(a))) for j, a in r["terms"].items()
                                    if j in integers), Fraction(0)) for n, r in rows.items()}}
    budgets = {n: float(v["bound_budget"]) for n, v in zip(names, data["variables"])
               if not v["integer"] and (v["lower"] is not None or v["upper"] is not None)}
    return model, budgets


def negative_cycle(cert):
    if cert is None:
        return None
    labels, edges = cert["labels"], cert["edges"]
    return [[labels[edges[i][0]], labels[edges[i][1]], edges[i][2], edges[i][3]]
            for i in cert["result"]["negative_cycle"]]


def compact(result):
    if not result["compatible"]:
        return {"compatible": False, "negative_cycle": negative_cycle(result["certificate"])}
    return {"compatible": True, "radius": result["radius"], "u": result["u"], "v": result["v"],
            "lower_negative_cycle": negative_cycle(result["lower_certificate"])}


def main():
    output = HERE / "diagnostic"
    if output.exists():
        raise RuntimeError("diagnostic exists; preserve it and choose a new run directory")
    output.mkdir()
    inputs = ROOT / "exploration/oms-generalization-20261014/pilot/models"
    names = ["Kondili-H10", "Kondili-H12", "control30-3-2-3", "neos-3421095-cinca", "ta1-UUM"]
    summary = []
    for name in names:
        source = inputs / name / "original-model.json"
        for scope in ("raw_rows", "raw_rows_and_bounds", "rounded_rows_and_bounds"):
            model, bound_budgets = external_model(source, scope.startswith("rounded"))
            if scope == "raw_rows":
                bound_budgets = {}
            start = time.perf_counter()
            result = selector.select(model, bound_budgets)
            seconds = time.perf_counter() - start
            record = {"instance": name, "scope": scope, "source": str(source.relative_to(ROOT)),
                      "source_sha256": digest(source), "selection_seconds": seconds,
                      "epsilon_bound": 1e-6, "bound_budgets": bound_budgets, **compact(result)}
            path = output / (name + "-" + scope + ".json")
            path.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")
            summary.append({"instance": name, "scope": scope, "compatible": result["compatible"],
                            "radius": result.get("radius"), "selection_seconds": seconds,
                            "certificate": str(path.relative_to(HERE)), "sha256": digest(path)})
            print(json.dumps(summary[-1]), flush=True)
    # Dispatch data preparation is read-only and uses the prior frozen adapter.
    import sys
    sys.path[:0] = [str(ROOT / "exploration/oms-joint-contracts-20261016"), str(ROOT / "scripts/research"), str(ROOT / "scripts")]
    spec = importlib.util.spec_from_file_location("saved_dispatch_adapter", ROOT / "exploration/oms-joint-contracts-20261016/study.py")
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    for name in adapter.INSTANCES:
        for budget in (30, 100):
            model, source = adapter.model_for(name, budget)
            start = time.perf_counter()
            result = selector.select(model)
            seconds = time.perf_counter() - start
            record = {"instance": name, "scope": "dispatch_rows_only", "volume_budget": budget,
                      "source": str(source.relative_to(ROOT)), "source_sha256": digest(source),
                      "continuous_bound_budgets_specified": False,
                      "selection_seconds": seconds, **compact(result)}
            path = output / (name + "-" + str(budget) + ".json")
            path.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")
            summary.append({"instance": name, "scope": "dispatch_rows_only", "volume_budget": budget,
                            "compatible": result["compatible"], "radius": result.get("radius"),
                            "selection_seconds": seconds, "certificate": str(path.relative_to(HERE)), "sha256": digest(path)})
            print(json.dumps(summary[-1]), flush=True)
    (output / "SUMMARY.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
