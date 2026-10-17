#!/usr/bin/env python3
"""Exact saved-point activation audit and prospective comparison of remedies.

Original numerical inputs remain untouched. New solver calls are sequential and
use separate output directories, atomic point storage, native logs and hashes.
"""
import argparse
import csv
from fractions import Fraction
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import tempfile
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OLD = ROOT / "results-revision/research-audit/oms-close-20261013"
sys.path.insert(0, str(ROOT / "scripts/research"))
import oms_dispatch_validation as campaign
from audit_identifiability_grid import parse, TERM, SENSE
from budget_scaling import select_factor, dyadic_factor
from check_sgtm_demand import scan

ACT = re.compile(r"a\d+_activacion_[1-4]\(\d+\)")
F = Fraction.from_float
POLICIES = ("GM", "L2-window", "L2-matched-int", "Budget-L2", "L2-global-tight",
            "GM-IntFocus", "GM-tight-M", "GM-indicators")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def csvwrite(path, rows):
    if not rows:
        return
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def activation_spec(name, row):
    if not ACT.fullmatch(name):
        return None
    assert row["sense"] == "<=" and len(row["terms"]) == 2
    binary = next(k for k in row["terms"] if "_varphi4" in k)
    storage = next(k for k in row["terms"] if "_v4h(" in k)
    assert float(row["terms"][storage]) == -1
    m = float(row["terms"][binary])
    assert m > 0
    threshold = F(m) - F(float(row["rhs"]))
    return binary, storage, m, threshold


def original_rows(path):
    parsed, _ = parse(path)
    result = {}
    for name, row in parsed.items():
        spec = campaign.physical_spec(name, row["terms"])
        if spec:
            group, unit, conversion = spec
        elif activation_spec(name, row):
            group, unit, conversion = "Volume-dependent activation", "m3", 1.0
        else:
            continue
        result[name] = {**row, "group": group, "unit": unit, "conversion": conversion}
    return parsed, result


def audit_values(rows, values, integers):
    rounded = {name: float(round(value)) if name in integers else value
               for name, value in values.items()}
    groups = {}
    for name, row in rows.items():
        key = row["group"], row["unit"]
        g = groups.setdefault(key, {"group": key[0], "unit": key[1], "rows": 0,
            "raw_max": 0., "rounded_max": 0., "rounded_limiting_row": ""})
        raw = campaign.exact_violation(row["terms"], row["rhs"], values, row["sense"]) / F(row["conversion"])
        new = campaign.exact_violation(row["terms"], row["rhs"], rounded, row["sense"]) / F(row["conversion"])
        g["rows"] += 1
        g["raw_max"] = max(g["raw_max"], float(raw))
        if float(new) > g["rounded_max"]:
            g["rounded_max"] = float(new); g["rounded_limiting_row"] = name
    return list(groups.values())


def saved_audit(out):
    out.mkdir(parents=True, exist_ok=True)
    design = json.loads((OLD / "design.json").read_text())
    runs = list(csv.DictReader((OLD / "runs.csv").open()))
    results, model_summary, inputs = [], [], {}
    with tempfile.TemporaryDirectory(prefix="activation-saved-") as temp:
        path = Path(temp) / "Base.lp"
        for item in design["instances"]:
            cls, instance = item["class"], item["instance"]
            source = OLD / "exports" / cls / instance / "Base.lp.gz"
            inputs[str(source.relative_to(ROOT))] = sha(source)
            path.write_bytes(gzip.decompress(source.read_bytes()))
            parsed, rows = original_rows(path)
            _, lp, _ = campaign.afb.read_lp(path)
            integers = {name for name, kind in zip(lp.col_names_, lp.integrality_)
                        if str(kind) != "HighsVarType.kContinuous"}
            demand = scan([ROOT / item["input"]]) if cls == "sgtm" else None
            count = sum(ACT.fullmatch(name) is not None for name in parsed)
            model_summary.append({"class": cls, "instance": instance, "activation_rows": count,
                "physical_rows_with_integer_terms": sum(bool(set(r["terms"]) & integers)
                    for r in rows.values() if r["group"] != "Volume-dependent activation"),
                "demand_inversion": bool(demand and demand["defective"])})
            for run in (r for r in runs if r["class"] == cls and r["instance"] == instance):
                source = OLD / "runs" / cls / instance / (run["policy"] + "-solution.npz")
                inputs[str(source.relative_to(ROOT))] = sha(source)
                with np.load(source, allow_pickle=False) as sol:
                    values = dict(zip(sol["names"].tolist(), sol["x"].tolist()))
                for r in audit_values(rows, values, integers):
                    results.append({"class": cls, "instance": instance, "policy": run["policy"],
                                    "demand_inversion": bool(demand and demand["defective"]), **r})
            print("saved audit", cls, instance, flush=True)
    csvwrite(out / "saved-point-audit.csv", results)
    csvwrite(out / "model-scope.csv", model_summary)
    dump(out / "input-hashes.json", inputs)
    selected = [r for r in results if r["group"] == "Volume-dependent activation"]
    summary = {"models": len(model_summary), "solutions": len(runs),
        "activation_points": len(selected),
        "positive_rounded_activation_points": sum(r["rounded_max"] > 0 for r in selected),
        "clean_models_with_positive_rounding": sorted({r["instance"] for r in selected
            if r["rounded_max"] > 0 and not r["demand_inversion"]}),
        "maximum_rounded_activation_violation_m3": max(r["rounded_max"] for r in selected),
        "maximum_original_physical_integer_support": max(r["physical_rows_with_integer_terms"] for r in model_summary),
        "scope": "exact rational residuals of binary64 inputs and stored points; no optimality certificate",
        "optimization_calls": 0}
    dump(out / "saved-audit-summary.json", summary)
    print(json.dumps(summary, indent=2), flush=True)


def export_scaled(path, destination, factors):
    lines, in_rows, name = [], False, None
    for line in path.read_text().splitlines(keepends=True):
        stripped = line.strip()
        if stripped == "s.t.": in_rows = True
        elif stripped.lower() in ("bounds", "binary", "binaries", "generals", "end"): in_rows = False
        if in_rows and stripped.endswith(":"):
            name = stripped[:-1]
        elif in_rows and (match := TERM.fullmatch(stripped)):
            value, column = match.groups()
            lines.append(f"  {float(value)*factors[name]:+.17g} {column}\n"); continue
        elif in_rows and (match := SENSE.fullmatch(stripped)):
            sense, value = match.groups()
            lines.append(f"  {sense} {float(value)*factors[name]:.17g}\n"); continue
        lines.append(line)
    destination.write_text("".join(lines))


def prepare(out, phase):
    if (out / "design.json").exists():
        raise RuntimeError("frozen design exists; choose a new directory")
    out.mkdir(parents=True, exist_ok=True)
    old = json.loads((OLD / "design.json").read_text())
    inputs = [item for item in old["instances"] if item["class"] == "sgtm"]
    clean = [item for item in inputs if not scan([ROOT/item["input"]])["defective"]]
    assert len(clean) == 6
    selected = [item for item in clean if item["instance"] == "instance046"] if phase == "pilot" else clean
    seeds = [17] if phase == "pilot" else [1, 7, 42]
    params = {"Threads": 4, "TimeLimit": 60. if phase == "pilot" else 120.,
              "MIPGap": .01, "FeasibilityTol": 1e-6, "IntFeasTol": 1e-5,
              "ScaleFlag": -1, "Presolve": -1}
    design = {"date": "2026-10-14", "phase": phase, "instances": selected, "seeds": seeds,
        "policies": list(POLICIES), "parameters": params,
        "budget_scenario": "Demanding, declared before this exploration: 0.01 MW/100 m3",
        "activation_budget_meaning": "study numerical consistency target on the volume threshold of a binary activation, not an operator standard; new row scope explicitly separated from water balances",
        "coefficient_window": [1e-9, 1e9],
        "l2_control": "pure coefficient row L2 factor projected onto the coefficient window; no identity-band veto",
        "guided_integrality": "per model, largest dyadic gamma no greater than 100/(2*max_activation_M), capped by default 1e-5; minimum supported Gurobi gamma 1e-9",
        "budgets": {"MW": .01, "m3": 100.},
        "exact_verification": "raw and integer-rounded original binary64 rows, including activation rows; whole-model diagnostics are separate",
        "no_optimality_certificate": True,
        "comparison": "L2-matched-int isolates factor selection using identical guided integer tolerance; L2-global-tight uses both primal and integer tolerance 1e-9; GM controls assess existing alternative remedies",
        "pilot_excluded_from_confirmatory_results": True,
        "source_sha256": sha(Path(__file__)), "prepared": []}
    for item in selected:
        instance = item["instance"]
        folder = out / "models" / instance; folder.mkdir(parents=True)
        base = folder / "Base.lp"
        base.write_bytes(gzip.decompress((OLD/"exports/sgtm"/instance/"Base.lp.gz").read_bytes()))
        parsed, physical = original_rows(base)
        original = campaign.afb.read_lp(base)
        _, lp, _ = original
        integers = {name for name, kind in zip(lp.col_names_, lp.integrality_)
                    if str(kind) != "HighsVarType.kContinuous"}
        max_m = max(activation_spec(n,r)[2] for n,r in parsed.items() if ACT.fullmatch(n))
        target = 100. / (2. * max_m)
        gamma = min(1e-5, math.ldexp(1., math.floor(math.log2(target))))
        assert 1e-9 <= gamma <= target
        factors, decisions = {}, []
        for name, row in parsed.items():
            coefficients = [float(v) for v in row["terms"].values()]
            nz = np.abs(coefficients); nz = nz[nz != 0]
            # Use exactly the selector's L2 kernel and inward coefficient bounds
            # for both policies. A dormant residual bound disables budget action
            # in the control; different floating-point norm formulas must not be
            # counted as contract-induced factor changes.
            assert F(1e-6)/F(1e100) < F(1e-9)/F(float(nz.min()))
            conventional = select_factor(coefficients, 1e100, kernel="l2")
            assert conventional.factor is not None
            factors[name] = conventional.factor
            decisions.append({"row": name, "l2_window_factor": factors[name],
                "budget_factor": factors[name], "scope": "none", "rounding_reserve": 0.,
                "default_gamma_contract_reason": "outside_scope", "changed_by_budget": False})
        budget_factors = factors.copy()
        for record in decisions:
            name = record["row"]
            if name not in physical: continue
            row = physical[name]
            delta = design["budgets"][row["unit"]] * row["conversion"]
            int_sum = sum(abs(float(v)) for n,v in row["terms"].items() if n in integers)
            reserve = float(np.nextafter(float(F(gamma)*sum((F(abs(float(v))) for n,v in row["terms"].items() if n in integers),Fraction(0))), math.inf)) if int_sum else 0.
            default = select_factor(list(row["terms"].values()), delta,
                kernel="l2", rounding_allowance=1e-5*int_sum)
            decision = select_factor(list(row["terms"].values()), delta,
                kernel="l2", rounding_allowance=reserve)
            assert decision.factor is not None
            budget_factors[name] = decision.factor
            record.update(budget_factor=decision.factor, scope=row["group"],
                rounding_reserve=reserve, default_gamma_contract_reason=default.reason,
                changed_by_budget=decision.factor != factors[name])
        csvwrite(folder / "decisions.csv", decisions)
        export_scaled(base, folder / "L2-window.lp", factors)
        export_scaled(base, folder / "Budget-L2.lp", budget_factors)
        (folder / "GM.lp").write_bytes(gzip.decompress((OLD/"exports/sgtm"/instance/"Flat-GM.lp.gz").read_bytes()))
        for policy in ("L2-window", "Budget-L2", "GM"):
            campaign.afb.check_scaling(original, campaign.afb.read_lp(folder/(policy+".lp")), folder/(policy+"-factors.csv"))
        design["prepared"].append({"instance": instance, "guided_gamma": gamma,
            "max_activation_M": max_m, "budget_changed_rows": sum(r["changed_by_budget"] for r in decisions),
            "default_rounding_exhausted_rows": sum(r["default_gamma_contract_reason"] == "rounding_budget_exhausted" for r in decisions),
            "inputs": {"original_input": {"path": item["input"],"sha256":sha(ROOT/item["input"])}},
            "exports": {p: sha(folder/(p+".lp")) for p in ("Base","GM","L2-window","Budget-L2")}})
        print("prepared",instance,"gamma",gamma,"changed",sum(r["changed_by_budget"] for r in decisions),flush=True)
    dump(out / "design.json", design)
    (out / "source-snapshot.py").write_bytes(Path(__file__).read_bytes())


def solve(out):
    import gurobipy as gp
    design = json.loads((out / "design.json").read_text())
    assert sha(Path(__file__)) == design["source_sha256"], "source changed after design freeze"
    results = list(csv.DictReader((out/"runs.csv").open())) if (out/"runs.csv").exists() else []
    done = {(r["instance"],r["policy"],int(r["seed"])) for r in results}
    diagnostics = list(csv.DictReader((out/"physical.csv").open())) if (out/"physical.csv").exists() else []
    queue = [(item["instance"],policy,seed) for item in design["instances"] for seed in design["seeds"] for policy in design["policies"]]
    rng = np.random.default_rng(20261014)
    queue = [queue[i] for i in rng.permutation(len(queue))]
    env = gp.Env(params={"OutputFlag":0})
    for instance,policy,seed in queue:
        if (instance,policy,seed) in done: continue
        folder = out / "models" / instance
        run_dir = out / "runs" / instance / (policy+f"-s{seed}"); run_dir.mkdir(parents=True,exist_ok=True)
        parsed, rows = original_rows(folder/"Base.lp")
        prep = next(r for r in design["prepared"] if r["instance"] == instance)
        source = policy if policy in ("GM","Budget-L2") else "L2-window" if policy.startswith("L2-") else "GM"
        started = time.perf_counter()
        model = gp.read(str(folder/(source+".lp")),env=env)
        model.setParam("OutputFlag",1); model.setParam("LogToConsole",0)
        model.setParam("LogFile",str(run_dir/"solver.log"))
        params = {**design["parameters"], "Seed":seed}
        if policy in ("L2-matched-int","Budget-L2"):params["IntFeasTol"] = prep["guided_gamma"]
        if policy == "L2-global-tight":params.update(FeasibilityTol=1e-9,IntFeasTol=1e-9)
        if policy == "GM-IntFocus":params["IntegralityFocus"] = 1
        for key,value in params.items():model.setParam(key,value)
        reforms = []
        if policy in ("GM-tight-M","GM-indicators"):
            for name,row in parsed.items():
                spec = activation_spec(name,row)
                if spec is None: continue
                binary,storage,m,threshold = spec
                b,v = model.getVarByName(binary),model.getVarByName(storage)
                oldrow = model.getConstrByName(name)
                alpha = -model.getCoeff(oldrow,v)
                assert alpha > 0 and b.VType == gp.GRB.BINARY
                lower = F(v.LB)
                assert F(m) >= max(Fraction(0),threshold-lower)
                model.remove(oldrow)
                # The original row is redundant at b=0 because v>=LB and M>=V-LB.
                # At b=1 it is exactly v>=V. No other formulation is changed.
                if policy == "GM-indicators":
                    assert F(float(threshold)) == threshold
                    model.addGenConstrIndicator(b,1,v>=float(threshold),name=name)
                else:
                    new_m = max(Fraction(0),threshold-lower)
                    assert F(float(new_m)) == new_m and F(float(new_m-threshold)) == new_m-threshold
                    model.addConstr(alpha*float(new_m)*b-alpha*v<=alpha*float(new_m-threshold),name=name)
                reforms.append({"row":name,"original_M":m,"threshold":str(threshold),
                                "storage_lower_bound":float(lower),"type":policy})
            model.update()
        load_transform = time.perf_counter()-started
        dump(run_dir/"parameters.json",params)
        if reforms:dump(run_dir/"reformulations.json",reforms)
        started = time.perf_counter();model.optimize();elapsed = time.perf_counter()-started
        result = {"instance":instance,"policy":policy,"seed":seed,"status":model.Status,
            "solutions":model.SolCount,"completed":int(model.Status==gp.GRB.OPTIMAL),
            "load_transform_seconds":load_transform,"optimize_seconds":elapsed,"total_seconds":load_transform+elapsed,
            "work":model.Work,"nodes":model.NodeCount,"objective":model.ObjVal if model.SolCount else None,
            "bound":model.ObjBound if math.isfinite(model.ObjBound) else None,
            "gap":model.MIPGap if model.SolCount and math.isfinite(model.MIPGap) else None,
            "raw_activation_m3":None,"rounded_activation_m3":None,
            "raw_physical_max_ratio":None,"rounded_physical_max_ratio":None}
        if model.SolCount:
            names = [v.VarName for v in model.getVars()]
            values = model.getAttr("X",model.getVars())
            pending=run_dir/"solution.pending.npz"
            np.savez_compressed(pending,names=np.array(names),x=np.array(values));pending.replace(run_dir/"solution.npz")
            integers = {v.VarName for v in model.getVars() if v.VType != gp.GRB.CONTINUOUS}
            audited = audit_values(rows,dict(zip(names,values)),integers)
            for r in audited:diagnostics.append({"instance":instance,"policy":policy,"seed":seed,**r})
            activation = next(r for r in audited if r["group"]=="Volume-dependent activation")
            result.update(raw_activation_m3=activation["raw_max"],rounded_activation_m3=activation["rounded_max"],
                raw_physical_max_ratio=max(r["raw_max"]/design["budgets"][r["unit"]] for r in audited),
                rounded_physical_max_ratio=max(r["rounded_max"]/design["budgets"][r["unit"]] for r in audited))
        model.dispose()
        results.append(result)
        csvwrite(out/"runs.csv",results);csvwrite(out/"physical.csv",diagnostics)
        print(len(results),"/",len(queue),instance,policy,seed,"status",result["status"],
              "work",round(result["work"],4),"rounded activation",result["rounded_activation_m3"],flush=True)
    env.dispose()
    dump(out/"completed.json",{"runs":len(results),"assigned":len(queue),"phase":design["phase"]})


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("stage",choices=("audit","prepare","solve"))
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--phase",choices=("pilot","confirmatory"),default="pilot")
    args=ap.parse_args();out=args.out.resolve()
    if args.stage=="audit":saved_audit(out)
    elif args.stage=="prepare":prepare(out,args.phase)
    else:solve(out)


if __name__=="__main__":main()
