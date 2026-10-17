#!/usr/bin/env python3
"""Frozen factorial IF control and independently timed full dispatch workflow."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math
import os
import platform
import random
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIOR = ROOT/'exploration/oms-followup-20261014'
sys.path[:0] = [str(PRIOR), str(ROOT/'scripts/research'), str(ROOT/'scripts')]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def dump(p, v):
    Path(p).write_text(json.dumps(v, indent=2, allow_nan=False)+'\n')


def load(p):
    return json.loads(Path(p).read_text())


def generate(folder):
    from validar_preprocesamiento import clean_instance_text
    base = folder/'Base.lp'
    commands = clean_instance_text(HERE/'input.txt')
    text = (commands+'\nconfigurarSolver --DummyLp\n'
            'preprocesar --solodiagnostico\n'
            f'grabar {base} --noConstante\nsalir\n')
    (folder/'generator-commands.txt').write_text(text)
    with (folder/'generator.log').open('w') as log:
        r = subprocess.run([str(ROOT/'code/build-audit/SistemaElectrico')],
                           input=text, text=True, cwd=ROOT/'code', stdout=log,
                           stderr=subprocess.STDOUT, timeout=60)
    assert r.returncode == 0 and base.is_file()
    return base


def prepare():
    import activation_study as old
    import measure_factor_cost as cost
    if (HERE/'design.json').exists():
        raise RuntimeError('design exists; never overwrite a frozen study')
    source = ROOT/'data/entradas/entrada-SG-Ter-Mer/instance046.txt'
    (HERE/'input.txt').write_bytes(source.read_bytes())
    d = load(PRIOR/'presolve-off-followup/design.json')
    item = d['prepared'][0]
    preflight = HERE/'preflight'; preflight.mkdir()
    base = generate(preflight)
    assert sha(base) == item['exports']['Base'], 'generator no longer reproduces Base'
    parsed, _ = old.original_rows(base)
    _, lp, _ = old.campaign.afb.read_lp(base)
    for policy in ('L2-window','Budget-L2'):
        chosen = cost.factors(parsed, lp, item['guided_gamma'], policy == 'Budget-L2')
        out = preflight/(policy+'.lp'); old.export_scaled(base, out, chosen)
        assert sha(out) == item['exports'][policy], policy
    jobs = [dict(policy=p, focus=f, seed=s, id=f'{p}-IF{f}-s{s}')
            for p in ('L2-window','Budget-L2') for f in (0,1) for s in (11,23,47)]
    random.Random(20261015).shuffle(jobs)
    dependencies = [Path(__file__), HERE/'PROTOCOL.md', PRIOR/'activation_study.py',
        PRIOR/'measure_factor_cost.py', PRIOR/'exact_dispatch_witness.py',
        ROOT/'scripts/research/budget_scaling.py',
        ROOT/'scripts/research/oms_dispatch_validation.py',
        ROOT/'scripts/research/audit_fixed_basis.py',
        ROOT/'scripts/audit_identifiability_grid.py',
        ROOT/'scripts/validar_preprocesamiento.py', ROOT/'code/build-audit/SistemaElectrico',
        HERE/'input.txt']
    # Existing witnesses, no newly optimized reference points.
    witnesses = {'L2-window': PRIOR/'exact-witnesses/instance046/L2-window',
                 'Budget-L2': PRIOR/'exact-witnesses/instance046/Budget-L2'}
    witness_info = {}
    for policy, folder in witnesses.items():
        cert = load(folder/'independent-certificate.json')
        assert cert['original_model_sha256'] == item['exports'][policy]
        witness_info[policy] = {'folder':str(folder.relative_to(ROOT)),
                               'certificate':cert}
        dependencies.extend(folder/name for name in
            ('mapping.json','rational-solution.txt','exact-witness.json','independent-certificate.json'))
    design = dict(date='2026-10-15', instance='instance046', retrospective=True,
        source_input=str(source.relative_to(ROOT)), source_input_sha256=sha(source),
        gamma=item['guided_gamma'], exports=item['exports'], jobs=jobs,
        parameters={**d['parameters'], 'IntFeasTol':item['guided_gamma']},
        budgets={'MW':.01,'m3':100.}, witnesses=witness_info,
        dependencies={str(p.relative_to(ROOT)):sha(p) for p in dependencies},
        environment={'python':sys.version,'platform':platform.platform(),
                     'gurobi':'13.0.2','numpy':'2.2.6','highspy':'1.15.1',
                     'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'},
        optimization_calls_assigned=12, preflight_optimization_calls=0,
        total_scope='fresh Python process, generator through verification and persistence',
        limitation='known case/seeds; shared machine; acquisition of old witnesses excluded')
    design['instrumentation_amendment'] = {
        'first_pass': 'first-pass', 'first_pass_calls': 12,
        'reason': 'cache LP attribute arrays once in native import checker; same mathematical checks',
        'no_changes_to_models_parameters_or_treatments': True,
        'first_pass_validation_sha256': sha(HERE/'first-pass/VALIDATION.json')}
    dump(HERE/'design.json', design)
    (HERE/'snapshot-study.py').write_bytes(Path(__file__).read_bytes())
    print('Frozen 12 assignments; generated Base and both scaled exports match historical hashes', flush=True)


def check_import(model, lp, a):
    """Check actual Gurobi import against the separately read binary64 export."""
    import numpy as np
    names = [v.VarName for v in model.getVars()]
    rows = [r.ConstrName for r in model.getConstrs()]
    assert set(names) == set(lp.col_names_) and set(rows) == set(lp.row_names_)
    ci = {n:i for i,n in enumerate(lp.col_names_)}
    ri = {n:i for i,n in enumerate(lp.row_names_)}
    # Binding properties return fresh Python arrays. Cache them once rather than
    # copying full model vectors for every individual row/column comparison.
    lower, upper, costs = lp.col_lower_, lp.col_upper_, lp.col_cost_
    kinds = lp.integrality_
    row_lower, row_upper = lp.row_lower_, lp.row_upper_
    expected = a.tocsr()[[ri[n] for n in rows],:][:,[ci[n] for n in names]]
    delta = model.getA()-expected
    assert delta.nnz == 0 or np.all(delta.data == 0)
    assert model.ModelSense == 1 and model.ObjCon == lp.offset_
    for v in model.getVars():
        j = ci[v.VarName]
        low, high = float(lower[j]), float(upper[j])
        assert (v.LB == low or math.isinf(low) and v.LB <= -1e100)
        assert (v.UB == high or math.isinf(high) and v.UB >= 1e100)
        assert v.Obj == float(costs[j])
        assert (v.VType != 'C') == (str(kinds[j]) != 'HighsVarType.kContinuous')
    for row in model.getConstrs():
        i = ri[row.ConstrName]
        lo, hi = float(row_lower[i]), float(row_upper[i])
        if lo == hi:
            assert row.Sense == '=' and row.RHS == hi
        elif math.isinf(lo):
            assert row.Sense == '<' and row.RHS == hi
        else:
            assert math.isinf(hi) and row.Sense == '>' and row.RHS == lo
    return {'rows':len(rows),'columns':len(names),'nonzeros':int(expected.nnz),
            'matrix_rhs_objective_bounds_integer_domains_equal':True}


def worker(job_id, process_started):
    from fractions import Fraction
    import numpy as np
    import gurobipy as gp
    import activation_study as old
    import measure_factor_cost as cost
    F = Fraction.from_float
    design = load(HERE/'design.json')
    job = next(j for j in design['jobs'] if j['id'] == job_id)
    folder = HERE/'runs'/job_id; folder.mkdir(parents=True)
    stages = {}
    def timed(key, f):
        start = time.perf_counter(); result = f()
        stages[key] = time.perf_counter()-start
        return result
    base = timed('generator_construction_base_export', lambda:generate(folder))
    def canonical():
        parsed, physical = old.original_rows(base)
        _, lp, a = old.campaign.afb.read_lp(base)
        return parsed, physical, lp, a
    parsed, physical, lp, a = timed('read_canonical_metadata', canonical)
    chosen = timed('factor_selection', lambda:cost.factors(parsed,lp,design['gamma'],job['policy']=='Budget-L2'))
    exported = folder/'scaled.lp'
    timed('scaled_export', lambda:old.export_scaled(base,exported,chosen))
    def integrity():
        assert sha(base) == design['exports']['Base']
        assert sha(exported) == design['exports'][job['policy']]
        _, ref_lp, ref_a = old.campaign.afb.read_lp(exported)
        return ref_lp, ref_a
    ref_lp, ref_a = timed('integrity_and_reference_read', integrity)
    env = None; model = None
    params = {**design['parameters'], 'IntegralityFocus':job['focus'], 'Seed':job['seed']}
    def native():
        nonlocal env, model
        env = gp.Env(params={'OutputFlag':0})
        model = gp.read(str(exported), env=env)
        model.setParam('OutputFlag',1);model.setParam('LogToConsole',0)
        model.setParam('LogFile',str(folder/'solver.log'))
        for k,v in params.items():model.setParam(k,v)
        return model
    timed('native_environment_import_parameters', native)
    import_check = timed('native_import_check', lambda:check_import(model,ref_lp,ref_a))
    timed('solve', model.optimize)
    def extract():
        outcome = dict(status=model.Status, solutions=model.SolCount,
            native_completed=model.Status==2, work=model.Work,nodes=model.NodeCount,
            native_runtime=model.Runtime, objective=model.ObjVal if model.SolCount else None,
            bound=model.ObjBound if math.isfinite(model.ObjBound) else None,
            gap=model.MIPGap if model.SolCount and math.isfinite(model.MIPGap) else None)
        values = None
        if model.SolCount:
            names = [v.VarName for v in model.getVars()]
            x = model.getAttr('X',model.getVars())
            np.savez_compressed(folder/'solution.npz',names=np.array(names),x=np.array(x))
            values = dict(zip(names,x))
        return outcome,values
    outcome,values = timed('extract_and_point_persistence', extract)
    def verify():
        if values is None:return {'candidate_present':False}
        assert all(math.isfinite(v) for v in values.values())
        integers = {n for n,k in zip(lp.col_names_,lp.integrality_) if str(k) != 'HighsVarType.kContinuous'}
        physical_checks = old.audit_values(physical,values,integers)
        rounded = {n:float(round(v)) if n in integers else v for n,v in values.items()}
        metrics = {'candidate_present':True,'physical':physical_checks,
            'raw_max_ratio':max(r['raw_max']/design['budgets'][r['unit']] for r in physical_checks),
            'rounded_max_ratio':max(r['rounded_max']/design['budgets'][r['unit']] for r in physical_checks),
            'max_integer_violation':max(abs(values[n]-round(values[n])) for n in integers),
            'raw_bound_violation':0.,'rounded_bound_violation':0.}
        for n,lo,hi in zip(lp.col_names_,lp.col_lower_,lp.col_upper_):
            for label,point in [('raw',values),('rounded',rounded)]:
                metrics[label+'_bound_violation'] = max(metrics[label+'_bound_violation'],max(float(lo)-point[n],point[n]-float(hi),0.))
        for label,point in [('raw',values),('rounded',rounded)]:
            x = np.array([point[n] for n in lp.col_names_]); activity = a@x
            v = np.maximum(np.maximum(np.array(lp.row_lower_)-activity,activity-np.array(lp.row_upper_)),0.)
            denom = np.maximum(1.,np.maximum(np.abs(a)@np.abs(x),np.maximum(np.where(np.isfinite(lp.row_lower_),np.abs(lp.row_lower_),0.),np.where(np.isfinite(lp.row_upper_),np.abs(lp.row_upper_),0.))))
            metrics[label+'_maximum_activity_normalized_violation'] = float(np.max(v/denom))
        objective = sum((F(float(c))*F(values[n]) for n,c in zip(lp.col_names_,lp.col_cost_)),F(float(lp.offset_)))
        metrics['original_point_objective_exact'] = str(objective)
        metrics['original_point_objective_display'] = float(objective)
        assert abs(objective-F(float(outcome['objective']))) <= F(max(1e-6,8*math.ulp(float(outcome['objective']))))
        witness = design['witnesses'][job['policy']]['certificate']
        U = Fraction(witness['objective_exact_fraction'])
        B,C = outcome['bound'],outcome['objective']
        metrics['known_witness_objective_exact'] = str(U)
        metrics['bound_contradiction'] = B is not None and F(B) > U+F(max(1e-6,8*math.ulp(B)))
        metrics['completion_contradiction'] = bool(outcome['native_completed'] and U < F(C)-Fraction(1,100)*abs(F(C)))
        metrics['audited_primal_budgets_pass'] = metrics['rounded_max_ratio'] <= 1
        return metrics
    checks = timed('verification', verify)
    result = dict(job=job,parameters=params,outcome=outcome,checks=checks,
        input_sha256=sha(HERE/'input.txt'),base_sha256=sha(base),export_sha256=sha(exported),
        native_import=import_check,timing_stages_seconds=stages,
        worker_internal_seconds_before_result=time.perf_counter()-process_started,
        native_global_optimality_independently_validated=False)
    timed('native_cleanup', lambda:(model.dispose(),env.dispose()))
    result['worker_internal_seconds_before_result'] = time.perf_counter()-process_started
    dump(folder/'result.json', result)


def run():
    design = load(HERE/'design.json')
    for name,expected in design['dependencies'].items():assert sha(ROOT/name) == expected,name
    parent_times = []
    for job in design['jobs']:
        folder = HERE/'runs'/job['id']
        if folder.exists():raise RuntimeError('refuse to overwrite '+str(folder))
        env = {**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'}
        log = HERE/(job['id']+'-execution.log')
        start = time.perf_counter()
        with log.open('w') as stream:
            r = subprocess.run([sys.executable,str(Path(__file__)),'worker',job['id']],
                cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=240)
        elapsed = time.perf_counter()-start
        record = dict(job=job,returncode=r.returncode,total_fresh_process_seconds=elapsed,
                      load_average=os.getloadavg())
        parent_times.append(record);dump(HERE/'parent-timing.json',parent_times)
        if r.returncode:
            print(log.read_text()[-4000:],flush=True)
            raise RuntimeError('worker failed; preserve all outputs: '+job['id'])
        result = load(folder/'result.json')
        print(job['id'], 'Work',result['outcome']['work'],
              'activation ratio',result['checks']['rounded_max_ratio'],
              'B flag',result['checks']['bound_contradiction'],
              'total s',round(elapsed,3),flush=True)


if __name__ == '__main__':
    started = time.perf_counter()
    p = argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','run','worker']);p.add_argument('job',nargs='?')
    args = p.parse_args()
    if args.stage == 'prepare':prepare()
    elif args.stage == 'run':run()
    else:worker(args.job,started)
