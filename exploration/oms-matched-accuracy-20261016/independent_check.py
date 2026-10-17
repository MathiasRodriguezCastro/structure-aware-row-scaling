#!/usr/bin/env python3
"""Saved-point replay: exact residuals and witnesses; no optimizer calls/imports."""
from fractions import Fraction
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import statistics as st
import sys
import time
import numpy as np

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT/'scripts/research'),str(ROOT/'scripts')]
from audit_identifiability_grid import parse
from audit_fixed_basis import read_lp
from oms_dispatch_validation import physical_spec
spec=importlib.util.spec_from_file_location('previous_independent',ROOT/'exploration/oms-if1-workflow-20261015/independent_check.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
F=Fraction.from_float


def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def csvwrite(p,data):
    with Path(p).open('w',newline='') as out:
        w=csv.DictWriter(out,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
def close(a,b):return math.isclose(a,b,rel_tol=1e-14,abs_tol=1e-15)
def geometric(values):return st.geometric_mean(values) if values and min(values)>0 else None


def main():
    d=load(HERE/'design.json');parent=load(HERE/'parent-timing.json')
    assert sha(HERE/'study.py')==sha(HERE/'snapshot-study.py')
    for p,h in d['dependencies'].items():assert sha(ROOT/p)==h,p
    protected=load(HERE/'protected-files.json')
    # Prior closed archives need not be supplied again in a self-contained replay.
    # On the working tree, any present protected file must still match.
    for p,h in protected.items():
        if (ROOT/p).exists():assert sha(ROOT/p)==h,p
    assert len(parent)==len(d['jobs'])==144
    assert [r['job'] for r in parent]==d['jobs']
    assert len({j['id'] for j in d['jobs']})==144
    assert all(r['returncode']==0 for r in parent)
    amendment=load(HERE/'RESTART_AMENDMENT.json')
    assert amendment['completed_calls_preserved']==37
    assert not amendment['model_parameter_endpoint_changes']
    assert amendment['interrupted_job']==d['jobs'][37]
    assert parent[:37]==load(HERE/'interrupted-attempt/parent-timing-before-restart.json')
    for p,h in amendment['files'].items():assert sha(HERE/p)==h,p
    partial=HERE/'interrupted-attempt'/d['jobs'][37]['id']
    assert not (partial/'result.json').exists()
    assert sha(partial/'scaled.lp')==d['models'][d['jobs'][37]['instance']]['L2-window']
    # Exact feasible witnesses belong to the actual native exports, not ideal row products.
    begin=time.perf_counter();models={};witness={}
    for n in d['instances']:
        folder=HERE/'inputs'/n
        assert sha(folder/'input.txt')==d['inputs'][n]['sha256']
        assert sha(folder/'Base.lp')==d['models'][n]['Base']
        rows,_=parse(folder/'Base.lp');_,lp,matrix=read_lp(folder/'Base.lp')
        integer={n for n,k in zip(lp.col_names_,lp.integrality_) if str(k)!='HighsVarType.kContinuous'}
        scope={}
        for name,row in rows.items():
            physical=physical_spec(name,row['terms'])
            if physical:scope[name]=physical
            elif re.fullmatch(r'a\d+_activacion_[1-4]\(\d+\)',name):
                assert row['sense']=='<='
                scope[name]=('Volume-dependent activation','m3',1.)
        assert len(rows)==10080 and len(integer)==1440 and len(scope)==4320
        models[n]=(rows,lp,matrix,integer,scope)
        for p in ('L2-window','Budget-L2'):
            model=folder/(p+'.lp');w=d['witnesses'][n+'/'+p]
            assert sha(model)==d['models'][n][p]
            witness[n+'/'+p]=prior.witness_check(model,ROOT/w['folder']/'exact-witness.json',w['certificate'])
    witness_seconds=time.perf_counter()-begin
    if not (HERE/'witness-revalidation-timing.json').exists():
        dump(HERE/'witness-revalidation-timing.json',{'witnesses':12,'seconds':witness_seconds,
            'scope':'separate reader-only revalidation of already supplied exact feasible points'})
    records=[];row_checks=0
    for job,p in zip(d['jobs'],parent):
        folder=HERE/'runs'/job['id'];r=load(folder/'result.json');checks=r['checks'];native=r['outcome']
        assert r['job']==job
        expected={**d['parameters'],'Presolve':job['presolve'],'Seed':job['seed']}
        if job['policy']=='L2-tight':expected.update(FeasibilityTol=1e-9,IntFeasTol=1e-9)
        if job['policy']=='L2-NF3':expected['NumericFocus']=3
        assert r['parameters']==expected
        source='Budget-L2' if job['policy']=='Budget-L2' else 'L2-window'
        assert r['source']==source
        assert r['input_sha256']==d['inputs'][job['instance']]['sha256']
        assert sha(folder/'Base.lp')==r['base_sha256']==d['models'][job['instance']]['Base']
        assert sha(folder/'scaled.lp')==r['export_sha256']==d['models'][job['instance']][source]
        assert r['native_import']=={'rows':10080,'columns':6120,'nonzeros':22679,
            'matrix_rhs_objective_bounds_integer_domains_equal':True}
        assert not r['native_global_optimality_independently_verified']
        log=(folder/'solver.log').read_text()
        assert 'Gurobi Optimizer version 13.0.2' in log
        assert 'Loaded user MIP start' not in log
        for key in ('Presolve','Seed','NumericFocus','IntegralityFocus','Threads','ScaleFlag'):
            assert f'Set parameter {key} to value {expected[key]}' in log
        timing=r['stages_seconds'];total=p['total_seconds']
        assert all(math.isfinite(x) and x>=0 for x in timing.values())
        assert sum(timing.values())<=r['worker_internal_seconds_before_result']<=total
        rows,lp,matrix,integer,scope=models[job['instance']]
        U=witness[job['instance']+'/'+source]
        assert Fraction(checks['known_witness_objective_exact'])==U
        bound,gap=prior.flags(native['bound'],native['objective'],native['native_completed'],U)
        assert (bound,gap)==(checks['bound_contradiction'],checks['completion_contradiction'])
        assert native['native_completed']==(native['status']==2)
        present=native['solutions']>0
        assert present==checks['candidate_present']
        raw_ratio=rounded_ratio=activation=integer_violation=None
        if present:
            with np.load(folder/'solution.npz',allow_pickle=False) as data:
                names=data['names'].tolist();x=data['x'].tolist()
            assert len(names)==len(set(names))==6120 and set(names)==set(lp.col_names_)
            assert all(math.isfinite(v) for v in x)
            point={n:F(v) for n,v in zip(names,x)}
            rounded={n:Fraction(round(v)) if n in integer else v for n,v in point.items()}
            raw_ratio=rounded_ratio=activation=Fraction(0);groups={}
            for name,(group,unit,conversion) in scope.items():
                raw=prior.violation(rows[name],point)/F(conversion)
                rnd=prior.violation(rows[name],rounded)/F(conversion)
                delta=F(d['budgets'][unit]);raw_ratio=max(raw_ratio,raw/delta)
                rounded_ratio=max(rounded_ratio,rnd/delta)
                if group=='Volume-dependent activation':activation=max(activation,rnd)
                g=groups.setdefault(group,[Fraction(0),Fraction(0)])
                g[0]=max(g[0],raw);g[1]=max(g[1],rnd);row_checks+=2
            assert close(float(raw_ratio),checks['raw_max_ratio'])
            assert close(float(rounded_ratio),checks['rounded_max_ratio'])
            assert checks['audited_budgets_pass']==(rounded_ratio<=1)
            for group in checks['physical']:
                raw,rnd=groups[group['group']]
                assert group['raw_max']==float(raw) and group['rounded_max']==float(rnd)
            objective=sum((F(float(c))*point[n] for n,c in zip(lp.col_names_,lp.col_cost_)),F(float(lp.offset_)))
            assert objective==Fraction(checks['point_objective_exact'])
            assert abs(objective-F(native['objective']))<=F(max(1e-6,8*math.ulp(native['objective'])))
            integer_violation=max(abs(point[n]-round(point[n])) for n in integer)
            assert float(integer_violation)==checks['integer_violation']
            for label,q in [('raw',point),('rounded',rounded)]:
                bound_violation=Fraction(0)
                for n,lo,hi in zip(lp.col_names_,lp.col_lower_,lp.col_upper_):
                    if math.isfinite(lo):bound_violation=max(bound_violation,F(float(lo))-q[n])
                    if math.isfinite(hi):bound_violation=max(bound_violation,q[n]-F(float(hi)))
                assert close(float(bound_violation),checks[label+'_bound_violation'])
        else:
            assert not checks['audited_budgets_pass'] and not (folder/'solution.npz').exists()
        records.append({**job,**native,'candidate_present':present,
            'raw_max_ratio':float(raw_ratio) if present else None,
            'rounded_max_ratio':float(rounded_ratio) if present else None,
            'activation_m3':float(activation) if present else None,
            'max_integer_violation':float(integer_violation) if present else None,
            'budgets_pass':checks['audited_budgets_pass'],'bound_contradiction':bound,
            'completion_contradiction':gap,'budgets_and_no_detected_flags':checks['audited_budgets_pass'] and not bound and not gap,
            'reference_witness_objective':float(U),'total_seconds':total,
            **{k+'_seconds':v for k,v in timing.items()},'other_process_seconds':total-sum(timing.values())})
    def summarize(selected,keys):
        return {**keys,'calls':len(selected),'candidates':sum(r['candidate_present'] for r in selected),
            'native_completed':sum(r['native_completed'] for r in selected),
            'time_limit':sum(r['status']==9 for r in selected),
            'budgets_pass':sum(r['budgets_pass'] for r in selected),
            'bound_contradictions':sum(r['bound_contradiction'] for r in selected),
            'completion_contradictions':sum(r['completion_contradiction'] for r in selected),
            'budgets_and_no_detected_flags':sum(r['budgets_and_no_detected_flags'] for r in selected),
            'maximum_activation_m3':max((r['activation_m3'] for r in selected if r['candidate_present']),default=None),
            'maximum_budget_ratio':max((r['rounded_max_ratio'] for r in selected if r['candidate_present']),default=None),
            'geometric_mean_work':geometric([r['work'] for r in selected]),
            'median_work':st.median(r['work'] for r in selected),
            'median_total_seconds':st.median(r['total_seconds'] for r in selected),
            'minimum_objective':min((r['objective'] for r in selected if r['candidate_present']),default=None),
            'maximum_objective':max((r['objective'] for r in selected if r['candidate_present']),default=None)}
    summary=[];by_case=[];pairs=[]
    for p in (-1,0):
        for m in ('L2','Budget-L2','L2-tight','L2-NF3'):
            selected=[r for r in records if r['presolve']==p and r['policy']==m]
            assert len(selected)==18
            summary.append(summarize(selected,{'presolve':p,'policy':m}))
            for n in d['instances']:
                by_case.append(summarize([r for r in selected if r['instance']==n],{'instance':n,'presolve':p,'policy':m}))
        for m in ('L2','L2-tight','L2-NF3'):
            for n in d['instances']:
                for seed in d['seeds']:
                    b=next(r for r in records if (r['presolve'],r['instance'],r['seed'],r['policy'])==(p,n,seed,'Budget-L2'))
                    c=next(r for r in records if (r['presolve'],r['instance'],r['seed'],r['policy'])==(p,n,seed,m))
                    pairs.append({'instance':n,'presolve':p,'seed':seed,'control':m,
                        'budget_pass':b['budgets_pass'],'control_pass':c['budgets_pass'],
                        'joint_pass':b['budgets_pass'] and c['budgets_pass'],
                        'budget_flagfree':b['budgets_and_no_detected_flags'],
                        'control_flagfree':c['budgets_and_no_detected_flags'],
                        'budget_work':b['work'],'control_work':c['work'],
                        'work_ratio':b['work']/c['work'] if c['work']>0 else None,
                        'time_ratio':b['total_seconds']/c['total_seconds'],
                        'objective_difference_budget_minus_control':b['objective']-c['objective'] if b['candidate_present'] and c['candidate_present'] else None})
    csvwrite(HERE/'verified-runs.csv',records);csvwrite(HERE/'verified-summary.csv',summary)
    csvwrite(HERE/'verified-cases.csv',by_case);csvwrite(HERE/'verified-pairs.csv',pairs)
    report={'assigned_milp_calls':144,'checked_milp_calls':len(records),'new_lp_calls':0,
        'native_milp_attempts_including_external_interruption':145,
        'externally_interrupted_attempts_retained_without_terminal_result':1,
        'completed_calls_preserved_before_reboot':37,
        'native_candidate_count':sum(r['candidate_present'] for r in records),
        'exact_feasible_native_export_witnesses_rechecked':12,'witness_rows_checked':120960,
        'witness_variables_checked':73440,'witness_integer_domains_checked':17280,
        'physical_row_point_checks':row_checks,
        'protected_file_inventory_entries':len(protected),'dependencies_match_frozen_design':True,
        'native_import_checks_match':True,'global_mip_optimality_certified':False,
        'scope':'six known models; previously used seeds; one generator; terminal budget delivery; shared machine'}
    dump(HERE/'VALIDATION.json',report)
    print(json.dumps({'validation':report,'summary':summary},indent=2))


if __name__=='__main__':main()
