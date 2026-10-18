#!/usr/bin/env python3
"""Matched unscaled controls; immutable inputs, native logs and saved points."""
import argparse
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import random
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FRONT = ROOT / 'exploration/oms-frontier-20261016'
PRIOR = ROOT / 'exploration/oms-followup-20261014'
sys.path[:0] = [str(PRIOR), str(ROOT/'scripts/research'), str(ROOT/'scripts')]
F = Fraction.from_float


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def dump(path, data):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2, allow_nan=False)+'\n')
    tmp.replace(path)


def library(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def prepare():
    import gurobipy as gp
    if (HERE/'design.json').exists():
        raise RuntimeError('design exists; do not overwrite')
    old = load(FRONT/'design.json')
    assert gp.gurobi.version() == (13, 0, 2)
    assert os.uname().nodename == old['hostname']
    jobs = [dict(instance=n, seed=s, policy=p, id=f'{n}-s{s}-{p}')
            for n in old['instances'] for s in old['seeds']
            for p in ['Base', 'Base-tight']]
    random.Random(2026101807).shuffle(jobs)
    deps = [HERE/'study.py', HERE/'PROTOCOL.md', FRONT/'design.json', FRONT/'study.py',
            ROOT/'exploration/oms-if1-workflow-20261015/study.py',
            PRIOR/'activation_study.py', ROOT/'scripts/research/budget_scaling.py',
            ROOT/'scripts/research/oms_dispatch_validation.py',
            ROOT/'scripts/research/audit_fixed_basis.py',
            ROOT/'scripts/audit_identifiability_grid.py',
            ROOT/'scripts/validar_preprocesamiento.py']
    references = []
    for n in old['instances']:
        deps.extend([FRONT/'models'/n/'Base.lp', FRONT/'models'/n/'input.txt'])
        for b in [30, 100]:
            deps.append(FRONT/'models'/n/f'B{b}.lp')
            for s in old['seeds']:
                folder = FRONT/'runs'/f'{n}-P-1-s{s}-Budget-L2{b}'
                references.append(str(folder.relative_to(ROOT)))
                deps.extend(folder/f for f in ['result.json', 'solution.npz', 'solver.log'])
    witnesses = {}
    for n in old['instances']:
        folder = ROOT/'exploration/oms-joint-contracts-20261016/base-witnesses'/n
        cert = load(folder/'independent-certificate.json')
        assert cert['original_model_sha256'] == old['inputs'][n]['base_sha256']
        witnesses[n] = str(folder.relative_to(ROOT))
        deps.extend(folder/f for f in ['exact-witness.json', 'independent-certificate.json'])
    # Protect every existing release PDF used for the editorial comparison.
    release = ROOT/'paper/submission/oms/releases/v1.3.14-oms-submission'
    frozen = {str(p.relative_to(ROOT)):sha(p) for p in release.glob('*.pdf')}
    dump(HERE/'design.json', dict(date='2026-10-18', retrospective=True,
        question='Budget-L2 versus no external scaling in the main favorable experiment',
        jobs=jobs, historical_budget_references=references, base_witnesses=witnesses,
        parameters={**old['parameters'], 'Presolve':-1},
        instances=old['instances'], seeds=old['seeds'], volume_budgets=[30,100],
        power_budget_MW=.01, input_hashes=old['inputs'],
        dependencies={str(p.relative_to(ROOT)):sha(p) for p in deps},
        generator_binary_sha256=sha(ROOT/'code/build-audit/SistemaElectrico'),
        frozen_pdfs=frozen, native_MIP_calls_assigned=36,
        new_LP_calls_assigned=0, environment=dict(hostname=os.uname().nodename,
            platform=platform.platform(), python=sys.version, gurobi=list(gp.gurobi.version()),
            cpu=next(line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),
            shared_machine=True), historical_time_comparison_authorized=False))
    print('Frozen 36 Base controls; no optimizer called', flush=True)


def worker(job_id, started):
    import numpy as np
    import gurobipy as gp
    import activation_study as a
    front = library(FRONT/'study.py', 'frontier_control_generator')
    wf = library(ROOT/'exploration/oms-if1-workflow-20261015/study.py', 'native_control_check')
    d = load(HERE/'design.json')
    job = next(j for j in d['jobs'] if j['id'] == job_id)
    folder = HERE/'runs'/job_id
    folder.mkdir(parents=True)
    stages = {}
    def timed(key, fun):
        t = time.perf_counter()
        val = fun()
        stages[key] = time.perf_counter()-t
        return val
    base = timed('generator', lambda:front.generate(job['instance'], folder))
    assert sha(base) == d['input_hashes'][job['instance']]['base_sha256']
    parsed, physical = timed('parse_original', lambda:a.original_rows(base))
    _, lp, matrix = timed('matrix_metadata', lambda:a.campaign.afb.read_lp(base))
    params = {**d['parameters'], 'Seed':job['seed']}
    if job['policy'] == 'Base-tight':
        params['FeasibilityTol'] = 1e-9
    def native():
        env = gp.Env(params={'OutputFlag':0})
        model = gp.read(str(base), env=env)
        model.setParam('OutputFlag', 1)
        model.setParam('LogToConsole', 0)
        model.setParam('LogFile', str(folder/'solver.log'))
        for k, v in params.items():
            model.setParam(k, v)
        return env, model
    env, model = timed('native_import', native)
    equality = timed('native_equality_check', lambda:wf.check_import(model, lp, matrix))
    timed('solve', model.optimize)
    def extract():
        outcome = dict(status=model.Status, solutions=model.SolCount,
            native_completed=model.Status == 2, work=model.Work, nodes=model.NodeCount,
            native_runtime=model.Runtime, objective=model.ObjVal if model.SolCount else None,
            bound=model.ObjBound if math.isfinite(model.ObjBound) else None)
        values = None
        if model.SolCount:
            names = [v.VarName for v in model.getVars()]
            xs = model.getAttr('X', model.getVars())
            np.savez_compressed(folder/'solution.npz', names=np.array(names), x=np.array(xs))
            values = dict(zip(names, xs))
        return outcome, values
    outcome, values = timed('extraction', extract)
    def check():
        cert = load(ROOT/d['base_witnesses'][job['instance']]/'independent-certificate.json')
        U = Fraction(cert['objective_exact_fraction'])
        B, C = outcome['bound'], outcome['objective']
        result = dict(known_witness_objective_exact=str(U),
            bound_contradiction=bool(B is not None and F(B)>U+F(max(1e-6,8*math.ulp(B)))),
            completion_contradiction=bool(outcome['native_completed'] and C is not None and U<F(C)-abs(F(C))/100),
            physical=None, point_objective_exact=None)
        if values is not None:
            integers = {n for n,k in zip(lp.col_names_,lp.integrality_) if str(k)!='HighsVarType.kContinuous'}
            result['physical'] = a.audit_values(physical, values, integers)
            result['point_objective_exact'] = str(sum((F(float(c))*F(values[n]) for n,c in zip(lp.col_names_,lp.col_cost_)),F(float(lp.offset_))))
        return result
    checks = timed('verification', check)
    timed('cleanup', lambda:(model.dispose(),env.dispose()))
    dump(folder/'result.json', dict(job=job, parameters=params, base_sha256=sha(base),
        native_import=equality, outcome=outcome, checks=checks, stages_seconds=stages,
        worker_internal_seconds_before_result=time.perf_counter()-started,
        global_optimality_independently_verified=False))


def run():
    d = load(HERE/'design.json')
    for p,h in {**d['dependencies'],**d['frozen_pdfs']}.items():
        assert sha(ROOT/p) == h, p
    assert sha(ROOT/'code/build-audit/SistemaElectrico') == d['generator_binary_sha256']
    timing_path = HERE/'parent-timing.json'
    records = load(timing_path) if timing_path.exists() else []
    assert [r['job'] for r in records] == d['jobs'][:len(records)]
    assert all(r['returncode']==0 for r in records), 'failed attempt retained'
    for i,job in enumerate(d['jobs'][len(records):],len(records)+1):
        assert not (HERE/'runs'/job['id']).exists(), 'unrecorded attempt; amendment required'
        start = time.perf_counter()
        with (HERE/(job['id']+'-execution.log')).open('w') as log:
            try:
                p = subprocess.run([sys.executable,str(Path(__file__)),'worker',job['id']],
                    cwd=ROOT, env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'},
                    stdout=log,stderr=subprocess.STDOUT,timeout=240)
                rc = p.returncode
            except subprocess.TimeoutExpired:
                rc = 124
        records.append(dict(job=job,returncode=rc,total_fresh_process_seconds=time.perf_counter()-start))
        dump(timing_path,records)
        print(i,'/36',job['id'],'rc',rc,'seconds',round(records[-1]['total_fresh_process_seconds'],2),flush=True)
        if rc:
            raise RuntimeError('failed attempt retained; inspect before resuming')


if __name__ == '__main__':
    started = time.perf_counter()
    ap = argparse.ArgumentParser()
    ap.add_argument('stage',choices=['prepare','run','worker'])
    ap.add_argument('job',nargs='?')
    args = ap.parse_args()
    if args.stage == 'worker':
        worker(args.job,started)
    else:
        globals()[args.stage]()
