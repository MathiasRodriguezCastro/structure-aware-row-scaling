#!/usr/bin/env python3
"""Read-only numerical replay; imports neither study.py nor a commercial solver."""
from collections import Counter
from fractions import Fraction
from pathlib import Path
import csv
import hashlib
import json
import math
import re
import statistics
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT/'scripts/research'),str(ROOT/'scripts')]
from audit_identifiability_grid import parse
from audit_fixed_basis import read_lp
from oms_dispatch_validation import physical_spec

F = Fraction.from_float


def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')


def violation(row, values):
    residual = sum((F(float(a))*values[n] for n,a in row['terms'].items()),Fraction(0))-F(float(row['rhs']))
    if row['sense'] == '=':return abs(residual)
    return max(Fraction(0), residual if row['sense']=='<=' else -residual)


def flags(bound, objective, completed, witness):
    bound_flag = bound is not None and F(bound)>witness+F(max(1e-6,8*math.ulp(bound)))
    gap_flag = bool(completed and objective is not None and witness<F(objective)-Fraction(1,100)*abs(F(objective)))
    return bound_flag,gap_flag


def witness_check(model, point_file, certificate):
    rows,_ = parse(model)
    _,lp,_ = read_lp(model)
    point = {n:Fraction(v) for n,v in load(point_file).items()}
    assert set(point) == set(lp.col_names_)
    for name,row in rows.items():assert violation(row,point)==0,name
    integer_count = 0
    for n,lo,hi,kind in zip(lp.col_names_,lp.col_lower_,lp.col_upper_,lp.integrality_):
        if math.isfinite(lo):assert point[n]>=F(float(lo)),n
        if math.isfinite(hi):assert point[n]<=F(float(hi)),n
        if str(kind)!='HighsVarType.kContinuous':
            integer_count+=1;assert point[n].denominator==1,n
    objective = sum((F(float(c))*point[n] for n,c in zip(lp.col_names_,lp.col_cost_)),F(float(lp.offset_)))
    assert objective==Fraction(certificate['objective_exact_fraction'])
    assert sha(model)==certificate['original_model_sha256']
    assert len(rows)==certificate['original_rows_checked']==10080
    assert len(point)==certificate['variables_checked']==6120
    assert integer_count==certificate['integer_variables_checked']==1440
    return objective


def main():
    design=load(HERE/'design.json')
    assert sha(HERE/'study.py')==sha(HERE/'snapshot-study.py')
    for rel,expected in design['dependencies'].items():
        # The recorded offline C++ executable is not needed for saved-point replay.
        if rel!='code/build-audit/SistemaElectrico':assert sha(ROOT/rel)==expected,rel
    parent=load(HERE/'parent-timing.json')
    assert len(design['jobs'])==len(parent)==12
    assert [p['job'] for p in parent]==design['jobs']
    assert all(p['returncode']==0 for p in parent)
    first=HERE/'first-pass'
    assert sha(first/'VALIDATION.json')==design['instrumentation_amendment']['first_pass_validation_sha256']
    assert load(first/'design.json')['jobs']==design['jobs']
    assert sha(first/'study.py')==sha(first/'snapshot-study.py')
    assert sha(first/'study.py')==load(first/'design.json')['dependencies'][str((HERE/'study.py').relative_to(ROOT))]
    # Check the full old exact feasible witnesses, not only stored certificate labels.
    begin=time.perf_counter(); witness_values={}
    for policy,data in design['witnesses'].items():
        witness_values[policy]=witness_check(HERE/'preflight'/(policy+'.lp'),
            ROOT/data['folder']/'exact-witness.json',data['certificate'])
    witness_seconds=time.perf_counter()-begin
    rows,_=parse(HERE/'preflight/Base.lp')
    _,lp,_=read_lp(HERE/'preflight/Base.lp')
    integer={n for n,k in zip(lp.col_names_,lp.integrality_) if str(k)!='HighsVarType.kContinuous'}
    scope={}
    for name,row in rows.items():
        spec=physical_spec(name,row['terms'])
        if spec:scope[name]=spec
        elif re.fullmatch(r'a\d+_activacion_[1-4]\(\d+\)',name):
            assert row['sense']=='<='
            scope[name]=('Volume-dependent activation','m3',1.)
    assert len(scope)==4320
    records=[];checked_rows=0
    for job,p in zip(design['jobs'],parent):
        folder=HERE/'runs'/job['id']; r=load(folder/'result.json')
        previous=load(first/'runs'/job['id']/'result.json')
        for field in ('status','solutions','native_completed','work','nodes','objective','bound','gap'):
            assert r['outcome'][field]==previous['outcome'][field],(job['id'],field)
        assert r['checks']==previous['checks'],job['id']
        with np.load(folder/'solution.npz',allow_pickle=False) as x, np.load(first/'runs'/job['id']/'solution.npz',allow_pickle=False) as y:
            assert np.array_equal(x['names'],y['names']) and np.array_equal(x['x'],y['x'])
        assert r['job']==job
        expected={**design['parameters'],'IntegralityFocus':job['focus'],'Seed':job['seed']}
        assert r['parameters']==expected
        assert r['base_sha256']==sha(folder/'Base.lp')==design['exports']['Base']
        assert r['export_sha256']==sha(folder/'scaled.lp')==design['exports'][job['policy']]
        assert r['native_import']=={'rows':10080,'columns':6120,'nonzeros':22679,
            'matrix_rhs_objective_bounds_integer_domains_equal':True}
        assert not r['native_global_optimality_independently_validated']
        log=(folder/'solver.log').read_text()
        assert 'Gurobi Optimizer version 13.0.2' in log
        assert f'Set parameter IntegralityFocus to value {job["focus"]}' in log
        assert 'Set parameter Presolve to value 0' in log
        assert 'Loaded user MIP start' not in log
        t=r['timing_stages_seconds'];total=p['total_fresh_process_seconds']
        assert all(math.isfinite(v) and v>=0 for v in t.values())
        assert sum(t.values())<=r['worker_internal_seconds_before_result']<=total
        assert r['outcome']['solutions']>0
        with np.load(folder/'solution.npz',allow_pickle=False) as a:
            names=a['names'].tolist(); x=a['x'].tolist()
        assert set(names)==set(lp.col_names_) and len(names)==len(set(names))
        assert all(math.isfinite(v) for v in x)
        point={n:F(v) for n,v in zip(names,x)}
        rounded={n:Fraction(round(v)) if n in integer else v for n,v in point.items()}
        raw_ratio=Fraction(0);rounded_ratio=Fraction(0);activation=Fraction(0)
        groups={}
        for name,(group,unit,conversion) in scope.items():
            raw=violation(rows[name],point)/F(conversion)
            rnd=violation(rows[name],rounded)/F(conversion)
            delta=F(design['budgets'][unit])
            raw_ratio=max(raw_ratio,raw/delta);rounded_ratio=max(rounded_ratio,rnd/delta)
            if group=='Volume-dependent activation':activation=max(activation,rnd)
            entry=groups.setdefault(group,[Fraction(0),Fraction(0)])
            entry[0]=max(entry[0],raw);entry[1]=max(entry[1],rnd)
            checked_rows+=2
        check=r['checks']
        assert math.isclose(float(raw_ratio),check['raw_max_ratio'],rel_tol=1e-14,abs_tol=1e-15)
        assert math.isclose(float(rounded_ratio),check['rounded_max_ratio'],rel_tol=1e-14,abs_tol=1e-15)
        assert check['audited_primal_budgets_pass']==(rounded_ratio<=1)
        for entry in check['physical']:
            g=groups[entry['group']]
            assert entry['raw_max']==float(g[0]) and entry['rounded_max']==float(g[1])
        objective=sum((F(float(c))*point[n] for n,c in zip(lp.col_names_,lp.col_cost_)),F(float(lp.offset_)))
        assert objective==Fraction(check['original_point_objective_exact'])
        observed_gamma=max(abs(point[n]-round(point[n])) for n in integer)
        assert float(observed_gamma)==check['max_integer_violation']
        U=witness_values[job['policy']]
        assert Fraction(check['known_witness_objective_exact'])==U
        bound_flag,gap_flag=flags(r['outcome']['bound'],r['outcome']['objective'],r['outcome']['native_completed'],U)
        assert bound_flag==check['bound_contradiction'] and gap_flag==check['completion_contradiction']
        record={**job,**r['outcome'],'raw_max_ratio':float(raw_ratio),
            'rounded_max_ratio':float(rounded_ratio),'activation_m3':float(activation),
            'primal_budgets_pass':rounded_ratio<=1,'bound_contradiction':bound_flag,
            'completion_contradiction':gap_flag,'total_seconds':total,
            **{k+'_seconds':v for k,v in t.items()},
            'other_process_seconds':total-sum(t.values())}
        records.append(record)
    summary=[]
    for policy in ('L2-window','Budget-L2'):
        for focus in (0,1):
            selected=[r for r in records if r['policy']==policy and r['focus']==focus]
            assert sorted(r['seed'] for r in selected)==[11,23,47]
            s=dict(policy=policy,focus=focus,runs=len(selected),
                native_completed=sum(r['native_completed'] for r in selected),
                budgets_passed=sum(r['primal_budgets_pass'] for r in selected),
                bound_contradictions=sum(r['bound_contradiction'] for r in selected),
                completion_contradictions=sum(r['completion_contradiction'] for r in selected),
                maximum_activation_m3=max(r['activation_m3'] for r in selected),
                median_work=statistics.median(r['work'] for r in selected))
            for field in ['total_seconds']+[k for k in selected[0] if k.endswith('_seconds') and k!='total_seconds']:
                s['median_'+field]=statistics.median(r[field] for r in selected)
            summary.append(s)
    for filename,data in [('verified-runs.csv',records),('verified-summary.csv',summary)]:
        with (HERE/filename).open('w',newline='') as out:
            w=csv.DictWriter(out,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    report=dict(assigned_calls=12,checked_calls=len(records),exact_reference_witnesses=2,
        first_pass_calls_retained=12,total_new_milp_calls=24,
        first_pass_native_outcomes_and_points_identical=True,
        reference_rows_checked=20160,reference_variables_checked=12240,
        reference_integer_domains_checked=2880,
        physical_row_point_checks=checked_rows,
        native_global_optimality_verified=False,
        scope='binary64 data, original-unit residuals and refutations; one retrospective case',
        replay_source_dependencies_verified=True,
        offline_generator_executable_hash_recorded=True)
    dump(HERE/'VALIDATION.json',report)
    print(json.dumps({'summary':summary,'validation':report},indent=2),flush=True)


if __name__=='__main__':main()
