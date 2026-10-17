#!/usr/bin/env python3
"""Prospective, compact OMS comparison and application-unit budget audit.

prepare: solver-free C++ exports, pure row-only Ruiz control, named invariants,
fixed reference bases, and three declared precision scenarios.
run: sequential matched Gurobi calls, preserved incumbents and original-unit checks.
summarize: complete-case work ratios, all-instance PAR10, budget verification.
The historical 1,800-second operational experiment remains a separate experiment.
"""
import argparse
import csv
from datetime import datetime, timezone
from fractions import Fraction
import gzip
import hashlib
import json
import math
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import time

import numpy as np
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scripts"))
import audit_fixed_basis as afb
from audit_identifiability_grid import parse
from budget_scaling import select_factor
from solver_scaling_bridge import equilibrate, kappa1
from validar_preprocesamiento import clean_instance_text

OUT = ROOT / "results-revision/research-audit/oms-close-20261013"
REFERENCE = ROOT / "results-revision/research-audit/fixed-basis-final-20260914/fresh"
POLICIES = {"Base": "--solodiagnostico", "Flat-GM": "--local-matricial --plano",
            "Ruiz-R4": None, "Role-Hybrid": "--local-matricial --acoplamiento-l2"}
ABLATION = {"Local-only": "--local-matricial --acoplamiento-l2 --solo-local",
            "Coupling-only": "--local-matricial --acoplamiento-l2 --solo-acoplamiento"}
SCENARIOS = {"Demanding": (0.01, 100.), "Reference": (0.1, 1000.),
             "Permissive": (1., 10000.)}
EPSILON, FLOOR, CEILING = 1e-6, 1e-9, 1e9


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def csvwrite(path, rows):
    if not rows:
        raise ValueError("empty output: " + str(path))
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "wt", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def ruiz_row_factor(coefficients, iterations=4):
    """Ruiz half-step iteration with column factors fixed to one.

    Only A enters the infinity norm. Apply the cumulative candidate once,
    with the final policies' closed identity band and coefficient-window veto.
    This deliberately is not the historical C++ mixed Ruiz/block procedure.
    """
    nz = np.abs(np.asarray(coefficients, dtype=float))
    nz = nz[nz != 0]
    if not len(nz):
        return 1., 1., "constant_row"
    if iterations < 1 or not np.isfinite(nz).all():
        raise ValueError("positive iteration count and finite coefficients required")
    factor, maximum = 1., float(nz.max())
    for _ in range(iterations):
        step = 1. / math.sqrt(maximum)
        factor *= step
        maximum *= step
    if .5 <= factor <= 2.:
        return factor, 1., "identity_band"
    scaled = nz * factor
    if scaled.min() < FLOOR or scaled.max() > CEILING:
        return factor, 1., "coefficient_veto"
    return factor, factor, "applied"


def physical_spec(name, terms):
    """Return (family group, physical unit, algebraic units per physical unit).

    Conversion is read from the named power/storage variable, not assumed
    from the row name. Unknown or ambiguous rows are outside this audit.
    """
    family = name.split("(")[0]
    if family in ("gh_total", "gen_menor_demanda") or re.fullmatch(r"a\d+_gen_rio_negro", family):
        group, unit = "Power identities and demand cap", "MW"
        candidates = [abs(float(v)) for k, v in terms.items()
                      if re.fullmatch(r"g\d*\(\d+\)", k)]
        # The aggregate generation on the LHS defines the row's MW units.
        first = next((abs(float(v)) for k,v in terms.items()
                      if k.split("(")[0] == ("g" if family in ("gh_total", "gen_menor_demanda")
                                              else "g" + family.split("_")[0][1:])), None)
        if first is None or not candidates:
            raise ValueError("missing aggregate generation: " + name)
        return group, unit, first
    if re.fullmatch(r"a\d+_g[1-4]h_def", family):
        coefficients = [abs(float(v)) for k, v in terms.items()
                        if re.fullmatch(r"g\d+\(\d+\)", k)]
        if len(coefficients) != 1:
            raise ValueError("ambiguous generation definition: " + name)
        return "Plant generation definitions", "MW", coefficients[0]
    if re.fullmatch(r"a\d+_(?:bonete|baygorria|palmar|salto_grande)_tangente_\d+", family):
        coefficients = [abs(float(v)) for k, v in terms.items()
                        if re.fullmatch(r"a\d+_z[1-4]h\(\d+\)", k)]
        if len(coefficients) != 1:
            raise ValueError("ambiguous production envelope: " + name)
        return "Production envelopes", "MW", coefficients[0]
    if re.fullmatch(r"a\d+_v[1-3]h_din", family) or re.fullmatch(r"a\d+_balance", family):
        agent = family.split('_')[0]
        plant = '4' if family.endswith('_balance') else family.split('_')[1][1]
        coefficients = [abs(float(v)) for k,v in terms.items()
                        if k.split('(')[0] == f'{agent}_v{plant}h']
        # Baygorria has no storage variable: its hourly flow balance uses 3600 s.
        if not coefficients and plant == '2':
            coefficients = [abs(float(v))/3600. for k,v in terms.items()
                            if k.split('(')[0] == f'{agent}_x2h']
        if not coefficients or len(set(coefficients)) != 1:
            raise ValueError("ambiguous water balance: " + name)
        return "Water balances", "m3", coefficients[0]
    return None


def project_proposal(coefficients, proposed, budget):
    # select_factor computes exact rational interval endpoints, rounded inward.
    decision = select_factor(coefficients, budget, epsilon=EPSILON,
                             coefficient_floor=FLOOR, coefficient_ceiling=CEILING)
    if decision.factor is None:
        return decision.lower, decision.upper, None, "incompatible"
    applied = min(max(proposed, decision.lower), decision.upper)
    return decision.lower, decision.upper, applied, "unchanged" if applied == proposed else "modified"


def ruiz_export(source, target):
    parsed, _ = parse(source)
    factors, decisions = {}, []
    for name, row in parsed.items():
        proposed, applied, reason = ruiz_row_factor(list(row["terms"].values()))
        factors[name] = applied
        decisions.append({"row_name": name, "proposed": proposed, "applied": applied, "reason": reason})
    # Preserve every non-constraint byte and the term/name order of the generator.
    lines, in_rows, name = [], False, None
    from audit_identifiability_grid import TERM, SENSE
    for line in source.read_text().splitlines(keepends=True):
        stripped = line.strip()
        if stripped == "s.t.":
            in_rows = True
        elif stripped.lower() in ("bounds", "binary", "binaries", "generals", "end"):
            in_rows = False
        if in_rows and stripped.endswith(":"):
            name = stripped[:-1]
        elif in_rows and (match := TERM.fullmatch(stripped)):
            value, column = match.groups()
            lines.append(f"  {float(value)*factors[name]:+.17g} {column}\n"); continue
        elif in_rows and (match := SENSE.fullmatch(stripped)):
            sense, value = match.groups()
            lines.append(f"  {sense} {float(value)*factors[name]:.17g}\n"); continue
        lines.append(line)
    target.write_text("".join(lines))
    return decisions


def bank():
    result = []
    for cls, filename in (("simple", "instances_simple.txt"), ("sgtm", "instances_sgtm.txt")):
        paths = (ROOT / "results-revision/final-variants" / filename).read_text().splitlines()
        assert len(paths) == 15
        for position, path in enumerate(paths):
            result.append({"class": cls, "instance": Path(path).stem, "input": path,
                           "ablation": position in (0, 7, 14)})
    return result


def prepare(out):
    if (out / "design.json").exists():
        raise RuntimeError("frozen design exists; use a new output directory")
    out.mkdir(parents=True, exist_ok=True)
    exe = ROOT / "code/build-audit/SistemaElectrico"
    selected = bank()
    import gurobipy as gp
    design = {"frozen_utc": datetime.now(timezone.utc).isoformat(),
              "selection": "same 30 archived operational inputs; no exclusions or input repairs",
              "ablation_selection": "positions 1, 8, 15 in each archived 15-instance list (six instances)",
              "instances": selected, "policies": POLICIES, "ablation": ABLATION,
              "ruiz": {"iterations": 4, "norm": "coefficient-only infinity norm",
                       "column_factors": 1, "identity_band": [.5, 2.],
                       "coefficient_window": [FLOOR, CEILING], "guards": "once on cumulative factor",
                       "reference": "Ruiz, RAL-TR-2001-034, Algorithm 2.1 with column factors fixed to one"},
              "solver": {"name": "Gurobi", "version": list(gp.gurobi.version()),
                         "parameters": {"Threads": 4, "Seed": 42, "TimeLimit": 120.,
                                        "MIPGap": .01, "FeasibilityTol": EPSILON,
                                        "IntFeasTol": 1e-5, "ScaleFlag": -1, "Presolve": -1}},
              "pilot": "separate six-call, 60-second pilot; excluded from all comparisons",
              "timing": "fresh C++ generation/export + Ruiz transformation where applicable + Gurobi load + optimize; checking excluded; sequential solver calls",
              "endpoints": "paired work and total time on all-policy completed subset; completions and total-time PAR10 on all 15 per class; original-row residuals, bounds and integrality",
              "par10": "total measured time when status OPTIMAL at declared gap; 10 times 120 otherwise",
              "conditioning": "same stored named Base LP basis; unit slack columns; max of onenormest(t=4) seeds 0,1,2, before/after 10 documented power-of-two row/column passes",
              "physical_budgets": {k: {"power_MW": p, "water_m3": v} for k,(p,v) in SCENARIOS.items()},
              "budget_basis": "declared study precision objectives, not UTE operating tolerances; reference 0.1 MW/0.001 hm3; one decade tighter/looser sensitivity; no tuning to induce active contracts",
              "residual_hypothesis": EPSILON, "coefficient_window": [FLOOR, CEILING],
              "contract_scope": "named power identities, generation definitions, production envelopes, water balances; other rows remain outside physical budgets",
              "contract_rounding_allowance": "zero for algebraic interval audit; actual original-data checks and pointwise coefficient/RHS rounding defects reported separately, no unconditional solver guarantee",
              "hardware": {"platform": platform.platform(), "processor": subprocess.check_output(['lscpu'],text=True)},
              "python": platform.python_version(), "exe_sha256": sha(exe),
              "source_sha256": sha(__file__),
              "inputs": [{"path": item["input"], "sha256": sha(ROOT/item["input"])} for item in selected]}
    dump(out / "design.json", design)
    (out / "source-snapshot").mkdir()
    (out / "source-snapshot/oms_dispatch_validation.py").write_bytes(Path(__file__).read_bytes())
    exports, conditions, decisions, budget_rows, manifest = [], [], [], [], []
    for item in selected:
        cls, name = item["class"], item["instance"]
        folder = out / "exports" / cls / name
        folder.mkdir(parents=True)
        commands = clean_instance_text(ROOT/item["input"])
        variants = {**POLICIES, **(ABLATION if item["ablation"] else {})}
        basis_path = REFERENCE / cls / name / "reference-basis.json"
        (folder / "reference-basis.json").write_bytes(basis_path.read_bytes())
        for policy, flags in variants.items():
            lp_path = folder / (policy + ".lp")
            started = time.perf_counter()
            if policy == "Ruiz-R4":
                # Include the cost of obtaining the same unscaled generator output.
                prep = next(r["prepare_seconds"] for r in exports if r["class"]==cls and r["instance"]==name and r["policy"]=="Base")
                ruiz = ruiz_export(folder/"Base.lp", lp_path)
                csvwrite(folder/"Ruiz-R4-decisions.csv", ruiz)
                elapsed = prep + time.perf_counter()-started
            else:
                command = f"{commands}\n\nconfigurarSolver --DummyLp\npreprocesar {flags}\ngrabar {lp_path} --noConstante\nsalir\n"
                (folder/(policy+"-commands.txt")).write_text(command)
                with (folder/(policy+"-export.log")).open("w") as log:
                    result = subprocess.run([str(exe)], input=command, text=True, cwd=ROOT/"code", stdout=log, stderr=subprocess.STDOUT, timeout=60)
                assert result.returncode == 0 and lp_path.exists()
                elapsed = time.perf_counter()-started
            exports.append({"class":cls,"instance":name,"policy":policy,"prepare_seconds":elapsed,"lp_sha256":sha(lp_path)})
        assert sha(folder/"Base.lp") == sha(REFERENCE/cls/name/"Base.lp"), "reference basis export differs"
        base = afb.read_lp(folder/"Base.lp")
        _, lp, matrix = base
        basis = json.loads(basis_path.read_text())
        colmap, rowmap = {n:i for i,n in enumerate(lp.col_names_)}, {n:i for i,n in enumerate(lp.row_names_)}
        columns = [colmap[n] for n in basis["basic_variables"]]
        slackrows = [rowmap[n] for n in basis["basic_slack_rows"]]
        unit = sp.csc_matrix((np.ones(len(slackrows)),(slackrows,range(len(slackrows)))), shape=(lp.num_row_,len(slackrows)))
        parsed, _ = parse(folder/"Base.lp")
        for policy in variants:
            scaled, check = afb.check_scaling(base, afb.read_lp(folder/(policy+".lp")), folder/(policy+"-row-factors.csv"))
            factors = {r["row_name"]: float(r["factor"]) for r in csv.DictReader((folder/(policy+"-row-factors.csv")).open())}
            for rowname, row in parsed.items():
                physical = physical_spec(rowname,row["terms"])
                if physical is None:
                    continue
                group, unit_name, conversion = physical
                for scenario,(power,water) in SCENARIOS.items():
                    delta_physical = power if unit_name=="MW" else water
                    proposed = factors[rowname]
                    lower,upper,applied,reason = project_proposal(list(row["terms"].values()), proposed,delta_physical*conversion)
                    budget_rows.append({"class":cls,"instance":name,"policy":policy,"scenario":scenario,
                        "row_name":rowname,"group":group,"unit":unit_name,"units_per_physical":conversion,
                        "physical_budget":delta_physical,"algebraic_budget":delta_physical*conversion,
                        "epsilon_exported":EPSILON,"proposed":proposed,"lower":lower,"upper":upper,
                        "applied":applied,"decision":reason,"budget_binding":int(applied is not None and applied==lower and lower>=EPSILON/(delta_physical*conversion))})
            if policy in POLICIES:
                b = sp.hstack([scaled[:,columns],unit],format="csc")
                raw, eq = kappa1(b), kappa1(equilibrate(b,10))
                assert raw is not None and eq is not None
                conditions.append({"class":cls,"instance":name,"policy":policy,"rows":b.shape[0],"kappa1":raw,"kappa1_equilibrated10":eq,**check})
            manifest.append({"class":cls,"instance":name,"policy":policy,
                             "lp_sha256":sha(folder/(policy+".lp")), "named_row_equivalence":check})
        if item["ablation"]:
            f = {p: np.array([float(r["factor"]) for r in csv.DictReader((folder/(p+"-row-factors.csv")).open())]) for p in ("Role-Hybrid",*ABLATION)}
            assert np.allclose(f["Role-Hybrid"],f["Local-only"]*f["Coupling-only"],rtol=2e-13,atol=0)
            assert not np.any((f["Local-only"]!=1)&(f["Coupling-only"]!=1)), "stage supports overlap"
        # Compress LPs after all checks. The artifact retains all new exports.
        for policy in variants:
            path = folder/(policy+".lp")
            with (folder/(policy+".lp.gz")).open("wb") as fh:
                fh.write(gzip.compress(path.read_bytes(),compresslevel=9,mtime=0))
            path.unlink()
        print("prepared",cls,name,"budget rows",sum(physical_spec(n,r["terms"]) is not None for n,r in parsed.items()),flush=True)
    csvwrite(out/"exports.csv",exports); csvwrite(out/"conditioning.csv",conditions)
    csvwrite(out/"factor-contracts.csv.gz",budget_rows)
    dump(out/"export-invariants.json",manifest)
    dump(out/"prepared.json",{"models":len(selected),"exports":len(exports),"conditioning_records":len(conditions),"factor_contract_records":len(budget_rows),"completed_utc":datetime.now(timezone.utc).isoformat()})


def exact_violation(terms, rhs, values, sense):
    # Verify original binary64 generator coefficients and the stored binary64 point.
    f = Fraction.from_float
    residual = sum((f(float(v))*f(float(values[n])) for n,v in terms.items()),Fraction(0))-f(float(rhs))
    return abs(residual) if sense=="=" else max(Fraction(0),residual if sense=="<=" else -residual)


def verify_point(base_path, scaled_path, values, policy, cls, instance):
    parsed, _ = parse(base_path); scaled, _ = parse(scaled_path)
    _, lp, a = afb.read_lp(base_path)
    x = np.array([values[n] for n in lp.col_names_]); activity = a@x
    lower,upper = np.array(lp.row_lower_),np.array(lp.row_upper_)
    violation = np.maximum(np.maximum(lower-activity,activity-upper),0)
    abs_activity = abs(a)@abs(x)
    normalized = violation/np.maximum(1,abs_activity)
    bound_violation = float(np.max(np.maximum(np.maximum(np.array(lp.col_lower_)-x,x-np.array(lp.col_upper_)),0)))
    integer_columns = [i for i,k in enumerate(lp.integrality_) if str(k)!="HighsVarType.kContinuous"]
    integer_violation = float(max((abs(x[i]-round(x[i])) for i in integer_columns),default=0.))
    groups = {}
    for name,row in parsed.items():
        physical = physical_spec(name,row["terms"])
        if physical is None: continue
        group,unit,conversion = physical
        residual = float(exact_violation(row["terms"],row["rhs"],values,row["sense"]))/conversion
        sr = scaled[name]
        exported = float(exact_violation(sr["terms"],sr["rhs"],values,sr["sense"]))
        pivot = max(row["terms"],key=lambda n:abs(row["terms"][n]))
        alpha = float(sr["terms"][pivot])/float(row["terms"][pivot])
        f = Fraction.from_float
        # Pointwise forward defect of coefficient/RHS export relative to alpha.
        defect = abs(sum(((f(float(sr["terms"][n]))/f(alpha)-f(float(c)))*f(values[n])
                          for n,c in row["terms"].items()),Fraction(0))
                     -(f(float(sr["rhs"]))/f(alpha)-f(float(row["rhs"]))))
        key=(group,unit)
        g=groups.setdefault(key,{"rows":0,"max_original_physical_residual":0.,"max_exported_row_violation":0.,"exported_hypothesis_failures":0,"max_pointwise_export_defect_physical":0.})
        g["rows"]+=1
        g["max_original_physical_residual"]=max(g["max_original_physical_residual"],residual)
        g["max_exported_row_violation"]=max(g["max_exported_row_violation"],exported)
        g["exported_hypothesis_failures"]+=int(exported>EPSILON)
        g["max_pointwise_export_defect_physical"]=max(g["max_pointwise_export_defect_physical"],float(defect)/conversion)
    common={"class":cls,"instance":instance,"policy":policy}
    return {**common,"max_absolute_row_residual":float(violation.max()),"max_activity_normalized_residual":float(normalized.max()),"max_bound_violation":bound_violation,"max_integrality_violation":integer_violation}, [{**common,"group":group,"unit":unit,**v} for (group,unit),v in groups.items()]


def run(out):
    import gurobipy as gp
    design=json.loads((out/"design.json").read_text())
    assert (out/"prepared.json").exists()
    records=[]; physical=[]
    if (out/"runs.csv").exists():
        records=list(csv.DictReader((out/"runs.csv").open()))
        physical=list(csv.DictReader((out/"physical-verification.csv").open()))
    done={(r["class"],r["instance"],r["policy"]) for r in records}
    exports=list(csv.DictReader((out/"exports.csv").open()))
    # Fixed random ordering within each paired instance reduces policy-order bias.
    rng=np.random.default_rng(20261013)
    queue=[]
    for item in design["instances"]:
        selected=[r for r in exports if r["class"]==item["class"] and r["instance"]==item["instance"]]
        queue.extend(selected[i] for i in rng.permutation(len(selected)))
    env=gp.Env(params={"OutputFlag":0})
    for rec in queue:
        cls,name,policy=rec["class"],rec["instance"],rec["policy"]
        if (cls,name,policy) in done:continue
        folder=out/"exports"/cls/name
        logs=out/"runs"/cls/name;logs.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="oms-dispatch-") as temp:
            temp=Path(temp)
            for p in {"Base",policy}:
                (temp/(p+".lp")).write_bytes(gzip.decompress((folder/(p+".lp.gz")).read_bytes()))
            t=time.perf_counter();model=gp.read(str(temp/(policy+".lp")),env=env)
            load=time.perf_counter()-t
            model.setParam("LogToConsole",0);model.setParam("OutputFlag",1)
            model.setParam("LogFile",str(logs/(policy+".log")))
            for k,v in design["solver"]["parameters"].items():model.setParam(k,v)
            t=time.perf_counter();model.optimize();optimize=time.perf_counter()-t
            total=float(rec["prepare_seconds"])+load+optimize
            completed=int(model.Status==gp.GRB.OPTIMAL)
            row={"class":cls,"instance":name,"policy":policy,"status":model.Status,"completed":completed,
                 "sol_count":model.SolCount,"prepare_seconds":float(rec["prepare_seconds"]),"load_seconds":load,
                 "optimizer_seconds":optimize,"total_seconds":total,"runtime":model.Runtime,"work":model.Work,
                 "nodes":model.NodeCount,"par10_seconds":total if completed else 10*design["solver"]["parameters"]["TimeLimit"],
                 "objective":model.ObjVal if model.SolCount else None,"bound":model.ObjBound if math.isfinite(model.ObjBound) else None,
                 "gap":model.MIPGap if model.SolCount and math.isfinite(model.MIPGap) else None,
                 "max_absolute_row_residual":None,"max_activity_normalized_residual":None,"max_bound_violation":None,"max_integrality_violation":None}
            if model.SolCount:
                names=[v.VarName for v in model.getVars()];x=np.array(model.getAttr("X",model.getVars()))
                np.savez_compressed(logs/(policy+"-solution.npz"),names=np.array(names),x=x)
                checked,groups=verify_point(temp/"Base.lp",temp/(policy+".lp"),dict(zip(names,x)),policy,cls,name)
                row.update(checked);physical.extend(groups)
            model.dispose()
        records.append(row)
        csvwrite(out/"runs.csv",records);csvwrite(out/"physical-verification.csv",physical)
        print(len(records),"/",len(queue),cls,name,policy,"status",row["status"],"work",row["work"],"seconds",total,flush=True)
    env.dispose()
    dump(out/"completed.json",{"runs":len(records),"physical_groups":len(physical),"completed_utc":datetime.now(timezone.utc).isoformat()})


def summarize(out):
    runs=list(csv.DictReader((out/"runs.csv").open()))
    physical=list(csv.DictReader((out/"physical-verification.csv").open()))
    with gzip.open(out/"factor-contracts.csv.gz","rt") as fh:
        contracts=list(csv.DictReader(fh))
    cond=list(csv.DictReader((out/"conditioning.csv").open()))
    summary=[]
    for cls in ("simple","sgtm"):
        members=[r for r in runs if r["class"]==cls and r["policy"] in POLICIES]
        common=sorted(n for n in {r["instance"] for r in members} if all(any(r["instance"]==n and r["policy"]==p and int(r["completed"]) for r in members) for p in POLICIES))
        base={r["instance"]:r for r in members if r["policy"]=="Base"}
        for p in POLICIES:
            selected=[r for r in members if r["policy"]==p];complete=[r for r in selected if r["instance"] in common]
            geo=lambda key:math.exp(np.mean([math.log(float(r[key])/float(base[r["instance"]][key])) for r in complete])) if complete else None
            matrices=[r for r in cond if r["class"]==cls and r["policy"]==p]
            cb={r["instance"]:r for r in cond if r["class"]==cls and r["policy"]=="Base"}
            summary.append({"class":cls,"policy":p,"instances":len(selected),"completed":sum(int(r["completed"]) for r in selected),"common_completed":len(common),
                "geomean_work_ratio":geo("work"),"geomean_total_time_ratio":geo("total_seconds"),"mean_par10_seconds":float(np.mean([float(r["par10_seconds"]) for r in selected])),
                "median_kappa_ratio":float(np.median([float(r["kappa1"])/float(cb[r["instance"]]["kappa1"]) for r in matrices])),
                "median_equilibrated_kappa_ratio":float(np.median([float(r["kappa1_equilibrated10"])/float(cb[r["instance"]]["kappa1_equilibrated10"]) for r in matrices])),
                "max_activity_normalized_residual":max(float(r["max_activity_normalized_residual"]) for r in selected if r["sol_count"]!="0"),
                "max_bound_violation":max(float(r["max_bound_violation"]) for r in selected if r["sol_count"]!="0"),
                "max_integrality_violation":max(float(r["max_integrality_violation"]) for r in selected if r["sol_count"]!="0")})
    csvwrite(out/"comparison-summary.csv",summary)
    ablation=[]
    for cls in ("simple","sgtm"):
        names=[i["instance"] for i in bank() if i["class"]==cls and i["ablation"]]
        members=[r for r in runs if r["class"]==cls and r["instance"] in names and r["policy"] in ("Base",*ABLATION,"Role-Hybrid")]
        base={r["instance"]:r for r in members if r["policy"]=="Base"}
        common=[n for n in names if all(any(r["instance"]==n and r["policy"]==p and int(r["completed"]) for r in members) for p in ("Base",*ABLATION,"Role-Hybrid"))]
        for p in ("Base",*ABLATION,"Role-Hybrid"):
            selected=[r for r in members if r["policy"]==p];good=[r for r in selected if r["instance"] in common]
            ablation.append({"class":cls,"policy":p,"instances":len(selected),"completed":sum(int(r["completed"]) for r in selected),"common_completed":len(common),
                "geomean_work_ratio":math.exp(np.mean([math.log(float(r["work"])/float(base[r["instance"]]["work"])) for r in good])),
                "geomean_total_time_ratio":math.exp(np.mean([math.log(float(r["total_seconds"])/float(base[r["instance"]]["total_seconds"])) for r in good])),
                "mean_par10_seconds":float(np.mean([float(r["par10_seconds"]) for r in selected]))})
    csvwrite(out/"ablation-summary.csv",ablation)
    budget_summary=[]
    for scenario,(power,water) in SCENARIOS.items():
        for p in POLICIES:
            chosen=[r for r in contracts if r["scenario"]==scenario and r["policy"]==p]
            verified=[r for r in physical if r["policy"]==p]
            ratios=[float(r["max_original_physical_residual"])/(power if r["unit"]=="MW" else water) for r in verified]
            budget_summary.append({"scenario":scenario,"policy":p,"rows":len(chosen),"admissible":sum(r["decision"]=="unchanged" for r in chosen),"modified":sum(r["decision"]=="modified" for r in chosen),"incompatible":sum(r["decision"]=="incompatible" for r in chosen),"binding":sum(int(r["budget_binding"]) for r in chosen),"verified_solutions":len({(r["class"],r["instance"]) for r in verified}),"max_observed_budget_ratio":max(ratios),"physical_groups_over_budget":sum(v>1 for v in ratios),"exported_hypothesis_failures":sum(int(r["exported_hypothesis_failures"]) for r in verified),"max_export_defect_MW":max(float(r["max_pointwise_export_defect_physical"]) for r in verified if r["unit"]=="MW"),"max_export_defect_m3":max(float(r["max_pointwise_export_defect_physical"]) for r in verified if r["unit"]=="m3")})
    csvwrite(out/"budget-summary.csv",budget_summary)
    dump(out/"summary.json",{"comparison":summary,"ablation":ablation,"budgets":budget_summary})
    print(json.dumps({"comparison":summary,"ablation":ablation,"budgets":budget_summary},indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",choices=("prepare","run","summarize"))
    parser.add_argument("--out",type=Path,default=OUT)
    args=parser.parse_args()
    globals()[args.stage](args.out.resolve())


if __name__=="__main__":main()
