"""Fixed bounded discovery pilot. The independent replay is in verify.py."""
import argparse
import copy
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import time

import method

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
F = Fraction.from_float
NAMES = ("control30-3-2-3", "neos-3421095-cinca")
SEEDS = (151, 157, 163)
BUDGETS = (1e-4, 1e-8)
POLICIES = ("Linear-L2", "Linear-NF3", "Contracted-L2", "SOS-unit", "SOS-range", "Activity-budget")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def load_probe():
    path = ROOT / "exploration/oms-budget-reformulation-20261017/probe.py"
    spec = importlib.util.spec_from_file_location("certified_bound_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build(original, contracted, targets, policy, budget):
    model = copy.deepcopy(original)
    source = contracted if policy != "Linear-L2" and policy != "Linear-NF3" else original
    model["rows"] = copy.deepcopy(source["rows"])
    selected = {t["row"]: t for t in targets}
    factors = []
    for i, row in enumerate(model["rows"]):
        reserve = method.GAMMA * sum((abs(F(float(a))) for j, a in row["terms"].items()
                                      if model["variables"][int(j)]["integer"]), Fraction(0))
        alpha = method.row_scale(list(row["terms"].values()), row["rhs"],
                                 delta=None if i in selected else F(float(row["budget"])),
                                 reserve=reserve)
        if alpha is None:
            raise ValueError(f"nonselected/common row incompatible: {i}")
        factors.append(alpha)
    metadata = {"policy": policy, "activation_budget": budget, "original_variables": len(original["variables"]),
                "original_rows": len(original["rows"]), "gates": []}
    if policy.startswith("SOS") or policy == "Activity-budget":
        complement = {}
        for target in targets:
            i, z, sign = target["row"], target["binary"], target["sense_sign"]
            M = -sign * source["rows"][i]["terms"][str(z)]
            g = {j: sign * a for j, a in source["rows"][i]["terms"].items() if int(j) != z}
            if policy == "Activity-budget":
                decision = method.select_activity(list(g.values()), M, budget)
                if decision is None:
                    raise ValueError(f"activity selector abstained: {i}")
                h, alpha, upper = decision["h"], decision["alpha"], decision["auxiliary_upper"]
            else:
                h = 1. if policy == "SOS-unit" else float(method.power(method.ceillog(F(float(M)))))
                upper = M / h
                assert F(upper) == F(float(M)) / F(h)
                alpha = method.row_scale([*g.values(), -h])
                decision = {"h": h, "alpha": alpha, "auxiliary_upper": upper,
                            "rounded_residual_bound": str(method.EPS/F(alpha)+F(h)*max(method.GAMMA,method.TAU)),
                            "budget": str(F(float(budget)))}
            if z not in complement:
                w = len(model["variables"])
                model["variables"].append({"name": f"complement_{z}", "cost": 0., "lower": 0.,
                                           "upper": 1., "integer": False, "bound_budget": 1e-6})
                c = len(model["rows"])
                model["rows"].append({"name": f"complement_{z}", "terms": {str(w): 1., str(z): 1.},
                                      "sense": "=", "rhs": 1., "budget": 1e-6, "unit": "auxiliary"})
                factors.append(1.)
                complement[z] = (w, c)
            w, c = complement[z]
            y = len(model["variables"])
            model["variables"].append({"name": f"activity_{i}", "cost": 0., "lower": 0.,
                                       "upper": upper, "integer": False, "bound_budget": 1e-6})
            model["rows"][i] = {"name": f"activity_link_{i}", "terms": {**g, str(y): -h},
                                 "sense": "<", "rhs": 0., "budget": budget, "unit": "auxiliary"}
            factors[i] = alpha
            metadata["gates"].append({"row": i, "z": z, "y": y, "w": w, "complement_row": c,
                                      "M": M, "original_M": float(target["M"]), "sign": sign, **decision})
    metadata["selected_rows"] = sorted(selected)
    metadata["factors"] = factors
    return model, metadata


def write_lp(path, model, metadata):
    def expression(terms):
        return " ".join(f'{"+" if a >= 0 else "-"} {abs(a):.17g} x{int(j):05d}'
                        for j, a in terms.items() if a) or "0"
    lines = ["Minimize", " obj: " + expression({str(j): v["cost"] for j, v in enumerate(model["variables"])}), "Subject To"]
    for i, (row, alpha) in enumerate(zip(model["rows"], metadata["factors"])):
        terms = {j: a * alpha for j, a in row["terms"].items()}
        rhs = row["rhs"] * alpha
        assert all(F(float(a)) * F(alpha) == F(float(terms[j])) for j, a in row["terms"].items())
        assert F(float(row["rhs"])) * F(alpha) == F(float(rhs))
        lines.append(f' r{i:05d}: {expression(terms)} '+{"<": "<=", ">": ">=", "=": "="}[row["sense"]]+f" {rhs:.17g}")
    lines.append("Bounds")
    integers = []
    for j, v in enumerate(model["variables"]):
        lo, hi = v["lower"], v["upper"]
        lines.append(f" {'-inf' if lo is None else format(lo, '.17g')} <= x{j:05d} <= {'+inf' if hi is None else format(hi, '.17g')}")
        if v["integer"]:
            integers.append(f" x{j:05d}")
    if integers:
        lines.extend(["Generals", *integers])
    if metadata["gates"]:
        lines.append("SOS")
        for g in metadata["gates"]:
            lines.append(f' s{g["row"]:05d}: S1:: x{g["w"]:05d}:1 x{g["y"]:05d}:2')
    lines.extend(["End", ""])
    path.write_text("\n".join(lines))


def prepare():
    output = HERE / "pilot"
    if output.exists():
        raise RuntimeError("pilot already exists; preserve the original design")
    output.mkdir()
    probe = load_probe()
    design = {"protocol_sha256": sha(HERE/"PROTOCOL.md"), "method_sha256": sha(HERE/"method.py"),
              "runner_sha256": sha(Path(__file__)), "seeds": SEEDS, "models": [], "calls": []}
    for name in NAMES:
        path = ROOT / "exploration/oms-generalization-20261014/pilot/models" / name / "original-model.json"
        original = json.loads(path.read_text())
        cpath = ROOT / "exploration/oms-budget-reformulation-20261017/diagnostic" / name / "reformulated-model.json"
        contracted = json.loads(cpath.read_text())
        targets = probe.activation_rows(original)
        assert len(targets) == 96
        folder = output / "models" / name
        folder.mkdir(parents=True)
        design["models"].append({"name": name, "source": str(path.relative_to(ROOT)), "source_sha256": sha(path),
                                 "contracted_source": str(cpath.relative_to(ROOT)), "contracted_sha256": sha(cpath)})
        for policy in POLICIES:
            for budget in (BUDGETS if policy.startswith("SOS") or policy == "Activity-budget" else (None,)):
                label = policy + (f"-{budget:.0e}" if budget is not None else "")
                model, meta = build(original, contracted, targets, policy, budget)
                arm = folder / label
                arm.mkdir()
                dump(arm/"model.json", model); dump(arm/"selection.json", meta)
                write_lp(arm/"model.lp", model, meta)
                for seed in SEEDS:
                    design["calls"].append({"name": name, "arm": label, "seed": seed,
                                            "export_sha256": sha(arm/"model.lp")})
    random.Random(17017).shuffle(design["calls"])
    assert len(design["calls"]) == 54
    dump(output/"design.json", design)
    print(json.dumps({"prepared_calls": 54, "model_exports": 18}), flush=True)


def solve():
    import gurobipy as gp
    import numpy as np
    design = json.loads((HERE/"pilot/design.json").read_text())
    assert design["protocol_sha256"] == sha(HERE/"PROTOCOL.md")
    assert design["method_sha256"] == sha(HERE/"method.py")
    assert design["runner_sha256"] == sha(Path(__file__))
    env = gp.Env(empty=True)
    env.setParam("OutputFlag", 0); env.start()
    for index, call in enumerate(design["calls"]):
        arm = HERE / "pilot/models" / call["name"] / call["arm"]
        output = HERE / "pilot/runs" / call["name"] / call["arm"] / str(call["seed"])
        if (output/"run.json").exists():
            continue
        output.mkdir(parents=True, exist_ok=True)
        assert sha(arm/"model.lp") == call["export_sha256"]
        before = time.perf_counter()
        model = gp.read(str(arm/"model.lp"), env=env)
        source = json.loads((arm/"model.json").read_text())
        meta = json.loads((arm/"selection.json").read_text())
        # Check actual solver import against every exported binary64 datum.
        variables = {v.VarName: v for v in model.getVars()}
        assert len(variables) == len(source["variables"])
        for j, v in enumerate(source["variables"]):
            got = variables[f"x{j:05d}"]
            assert F(got.Obj) == F(v["cost"])
            assert got.VType != gp.GRB.CONTINUOUS if v["integer"] else got.VType == gp.GRB.CONTINUOUS
            for actual, want in ((got.LB, v["lower"]), (got.UB, v["upper"])):
                assert abs(actual) >= 1e100 if want is None else F(actual) == F(want)
        for i, row in enumerate(source["rows"]):
            con = model.getConstrByName(f"r{i:05d}")
            expr = model.getRow(con)
            actual = {v.VarName: F(float(a)) for v, a in ((expr.getVar(k), expr.getCoeff(k)) for k in range(expr.size()))}
            want = {f"x{int(j):05d}": F(float(a))*F(meta["factors"][i]) for j, a in row["terms"].items() if a}
            assert actual == want and con.Sense == row["sense"]
            assert F(con.RHS) == F(float(row["rhs"]))*F(meta["factors"][i])
        assert model.NumSOS == len(meta["gates"])
        parameters = {"OutputFlag": 0, "LogFile": str(output/"solver.log"), "Seed": call["seed"],
                      "Threads": 4, "TimeLimit": 30., "WorkLimit": 1., "MIPGap": .01,
                      "FeasibilityTol": 1e-6, "IntFeasTol": 1e-9, "Presolve": -1,
                      "PreSOS1BigM": 0, "NumericFocus": 3 if meta["policy"] == "Linear-NF3" else 0}
        for k, v in parameters.items():
            model.setParam(k, v)
        prepare_seconds = time.perf_counter() - before
        model.optimize()
        record = {**call, "policy": meta["policy"], "activation_budget": meta["activation_budget"],
                  "parameters": {k: v for k, v in parameters.items() if k != "LogFile"},
                  "solver_version": list(gp.gurobi.version()), "status": model.Status,
                  "solution_count": model.SolCount, "has_point": model.SolCount > 0,
                  "prepare_and_import_seconds": prepare_seconds, "runtime": model.Runtime,
                  "work": model.Work, "nodes": model.NodeCount,
                  "objective": model.ObjVal if model.SolCount else None,
                  "reported_bound": model.ObjBound if math.isfinite(model.ObjBound) else None,
                  "bound_certified": False, "sos": model.NumSOS}
        if model.SolCount:
            np.savez(output/"point.npz", x=np.array([variables[f"x{j:05d}"].X for j in range(len(source["variables"]))]))
        dump(output/"run.json", record)
        print(json.dumps({"completed": index+1, **call, "status": model.Status, "point": model.SolCount > 0,
                          "work": model.Work, "runtime": model.Runtime}), flush=True)
        model.dispose()
    env.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "solve"))
    args = parser.parse_args()
    prepare() if args.action == "prepare" else solve()
