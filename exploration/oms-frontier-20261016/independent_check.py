#!/usr/bin/env python3
"""Saved numerical replay; no runner, gurobipy, SoPlex, or optimizer invocation."""
import csv
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys
import numpy as np

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT/'scripts/research'),str(ROOT/'scripts')]
from audit_identifiability_grid import parse
from audit_fixed_basis import read_lp
from oms_dispatch_validation import physical_spec
F=Fraction.from_float
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def write(p,records):
    with p.open('w',newline='') as out:
        w=csv.DictWriter(out,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
def viol(row,x):
    r=sum((F(float(a))*x[n] for n,a in row['terms'].items()),Fraction(0))-F(float(row['rhs']))
    return abs(r) if row['sense']=='=' else max(Fraction(0),r if row['sense']=='<=' else -r)
def flags(B,C,done,U):
    if U is None:return None,None
    return bool(B is not None and F(B)>U+F(max(1e-6,8*math.ulp(B)))),bool(done and C is not None and U<F(C)-abs(F(C))/100)
def geom(v):return math.exp(statistics.mean(math.log(x) for x in v))

def main():
    d=load(HERE/'design.json');parent=load(HERE/'parent-timing.json');witnesses=load(HERE/'witness-index.json')
    assert len(d['jobs'])==len(parent)==360 and [r['job'] for r in parent]==d['jobs']
    assert all(r['returncode']==0 for r in parent)
    assert sha(HERE/'study.py')==sha(HERE/'snapshot-study.py')
    for p,h in d['dependencies'].items():assert sha(ROOT/p)==h,p
    for p,h in load(HERE/'protected-files.json').items():
        if not (ROOT/p).exists() and '--allow-absent-historical' in sys.argv:continue
        assert sha(ROOT/p)==h,p
    U={};witness_row_checks=0
    for key,r in witnesses.items():
        if 'alias' in r:continue
        if 'certificate' not in r:U[key]=None;continue
        folder=ROOT/r['folder'];cert=r['certificate'];model=ROOT/d['models'][key]['model']
        assert cert==load(folder/'independent-certificate.json')
        assert sha(model)==cert['original_model_sha256']==d['models'][key]['export_sha256']
        assert sha(folder/'exact-witness.json')==cert['witness_sha256']
        point={n:Fraction(v) for n,v in load(folder/'exact-witness.json').items()}
        rows,_=parse(model);_,lp,_=read_lp(model);assert set(point)==set(lp.col_names_)
        for n,row in rows.items():assert viol(row,point)==0,n
        for n,l,h,k in zip(lp.col_names_,lp.col_lower_,lp.col_upper_,lp.integrality_):
            if math.isfinite(l):assert point[n]>=F(float(l))
            if math.isfinite(h):assert point[n]<=F(float(h))
            if str(k)!='HighsVarType.kContinuous':assert point[n].denominator==1
        objective=sum((F(float(c))*point[n] for n,c in zip(lp.col_names_,lp.col_cost_)),F(float(lp.offset_)))
        assert objective==Fraction(cert['objective_exact_fraction']);U[key]=objective;witness_row_checks+=len(rows)
    for key,r in witnesses.items():
        if 'alias' in r:U[key]=U[r['alias']]
    records=[];physical_checks=export_checks=0;abstentions=0
    for instance in d['instances']:
        base=HERE/'models'/instance/'Base.lp';rows,_=parse(base);_,lp,_=read_lp(base)
        assert sha(base)==d['inputs'][instance]['base_sha256']
        integers={n for n,k in zip(lp.col_names_,lp.integrality_) if str(k)!='HighsVarType.kContinuous'}
        assert len(integers)==1440
        scope={}
        for n,row in rows.items():
            spec=physical_spec(n,row['terms'])
            if spec:scope[n]=spec
            elif re.fullmatch(r'a\d+_activacion_[1-4]\(\d+\)',n):scope[n]=('Volume-dependent activation','m3',1.)
        assert len(scope)==4320
        # Replay abstentions directly against original coefficients, independently
        # of the selector and its stored reason.
        for key,m in d['models'].items():
            if not key.startswith(instance+'/') or not m['incompatible_count']:continue
            assert m['model'] is None and m['budget']==10
            for blocked in m['incompatible']:
                row=rows[blocked['row']]
                E=F(1e-9)*sum((F(abs(float(a))) for n,a in row['terms'].items() if n in integers),Fraction(0))
                assert E>=F(10.),blocked['row']
        export_rows={key:parse(ROOT/m['model'])[0] for key,m in d['models'].items() if key.startswith(instance+'/') and m['model']}
        for job,timing in zip(d['jobs'],parent):
            if job['instance']!=instance:continue
            key=instance+'/'+job['key'];m=d['models'][key]
            if timing['abstained']:
                assert m['incompatible_count']>0;abstentions+=1;continue
            folder=HERE/'runs'/job['id'];r=load(folder/'result.json');assert r['job']==job
            assert sha(folder/'Base.lp')==sha(base)==r['base_sha256']
            assert sha(folder/'scaled.lp')==m['export_sha256']==r['export_sha256']
            assert not r['global_optimality_independently_verified']
            assert r['native_import']=={'rows':10080,'columns':6120,'nonzeros':22679,'matrix_rhs_objective_bounds_integer_domains_equal':True}
            params={**d['parameters'],'Seed':job['seed'],'Presolve':job['presolve']}
            if job['policy']=='L2-tight':params.update(FeasibilityTol=1e-9,IntFeasTol=1e-9)
            if job['policy']=='L2-NF3':params['NumericFocus']=3
            assert params==r['parameters']
            log=(folder/'solver.log').read_text();assert 'Gurobi Optimizer version 13.0.2' in log
            for k in ['Seed','Presolve','NumericFocus','IntegralityFocus']:assert f'Set parameter {k} to value {params[k]}' in log
            assert 'Loaded user MIP start' not in log
            assert sum(r['stages_seconds'].values())<=r['worker_internal_seconds_before_result']<=timing['total_fresh_process_seconds']
            B,G=flags(r['outcome']['bound'],r['outcome']['objective'],r['outcome']['native_completed'],U.get(key))
            assert B==r['checks']['bound_contradiction'] and G==r['checks']['completion_contradiction']
            physical={};residuals=[];exported_max=Fraction(0);exceed=0;objective=None;integer_v=None
            if r['outcome']['solutions']:
                with np.load(folder/'solution.npz',allow_pickle=False) as x:
                    names=x['names'].tolist();values=x['x'].tolist()
                assert set(names)==set(lp.col_names_) and len(names)==len(set(names)) and all(math.isfinite(v) for v in values)
                raw={n:F(v) for n,v in zip(names,values)}
                rounded={n:Fraction(round(v)) if n in integers else v for n,v in raw.items()}
                for n,(group,unit,conversion) in scope.items():
                    rv=viol(rows[n],raw)/F(conversion);zv=viol(rows[n],rounded)/F(conversion)
                    residuals.append((unit,rv,zv))
                    g=physical.setdefault((group,unit),[Fraction(0),Fraction(0)])
                    g[0]=max(g[0],rv);g[1]=max(g[1],zv);physical_checks+=2
                    ev=viol(export_rows[key][n],raw);exported_max=max(exported_max,ev);exceed+=ev>F(1e-6);export_checks+=1
                for g in r['checks']['physical']:
                    pair=physical[(g['group'],g['unit'])];assert [float(x) for x in pair]==[g['raw_max'],g['rounded_max']]
                assert float(exported_max)==r['checks']['observed_exported_physical_max_violation']
                assert exceed==r['checks']['exported_physical_rows_exceeding_epsilon']
                integer_v=max(abs(raw[n]-round(raw[n])) for n in integers)
                assert float(integer_v)==r['checks']['max_integer_violation']
                objective=sum((F(float(c))*raw[n] for n,c in zip(lp.col_names_,lp.col_cost_)),F(float(lp.offset_)))
                assert objective==Fraction(r['checks']['point_objective_exact'])
            for budget in d['volume_budgets'] if job['budget'] is None else [job['budget']]:
                ratio=None if not physical else max(pair[1]/F(.01 if unit=='MW' else float(budget)) for (group,unit),pair in physical.items())
                raw_ratio=None if not physical else max(pair[0]/F(.01 if unit=='MW' else float(budget)) for (group,unit),pair in physical.items())
                activation=physical.get(('Volume-dependent activation','m3'),[None,None])[1]
                records.append({**job,'evaluated_volume_budget':budget,'budget_pass':bool(ratio is not None and ratio<=1),
                    'rounded_max_ratio':None if ratio is None else float(ratio),'raw_max_ratio':None if raw_ratio is None else float(raw_ratio),
                    'violated_physical_rows':sum(z>F(.01 if unit=='MW' else float(budget)) for unit,raw,z in residuals),
                    'raw_violated_physical_rows':sum(raw>F(.01 if unit=='MW' else float(budget)) for unit,raw,z in residuals),
                    'activation_m3':None if activation is None else float(activation),'bound_contradiction':B,'gap_contradiction':G,
                    'objective_exact':None if objective is None else str(objective),'objective':None if objective is None else float(objective),
                    'integer_violation':None if integer_v is None else float(integer_v),
                    'exported_physical_rows_exceeding_epsilon':exceed,'observed_exported_max_violation':float(exported_max),
                    'status':r['outcome']['status'],'work':r['outcome']['work'],'native_seconds':r['outcome']['native_runtime'],
                    'total_seconds':timing['total_fresh_process_seconds'],**{k+'_seconds':v for k,v in r['stages_seconds'].items()}})
    summaries=[];qualifiers=[]
    for presolve in [-1,0]:
        for budget in d['volume_budgets']:
            for policy in ['L2','L2-tight','L2-NF3','Budget-L2']:
                rr=[r for r in records if r['presolve']==presolve and r['evaluated_volume_budget']==budget and r['policy']==policy]
                summaries.append({'presolve':presolve,'budget':budget,'policy':policy,'calls':len(rr),
                    'budgets_passed':sum(r['budget_pass'] for r in rr),'bound_flags':sum(r['bound_contradiction'] is True for r in rr),
                    'gap_flags':sum(r['gap_contradiction'] is True for r in rr),
                    'unknown_bound_checks':sum(r['bound_contradiction'] is None for r in rr),
                    'geometric_work':geom([r['work'] for r in rr]) if rr else None,
                    'median_total_seconds':statistics.median(r['total_seconds'] for r in rr) if rr else None,
                    'max_rounded_budget_ratio':max((r['rounded_max_ratio'] for r in rr if r['rounded_max_ratio'] is not None),default=None)})
            for instance in d['instances']:
                pair={p:{r['seed']:r for r in records if r['instance']==instance and r['presolve']==presolve and r['evaluated_volume_budget']==budget and r['policy']==p} for p in ['Budget-L2','L2-NF3']}
                enough=all(len(v)==3 for v in pair.values());passes=quality=no_flags=less_work=False;ratio=None
                if enough:
                    a=pair['Budget-L2'];b=pair['L2-NF3'];seeds=d['seeds']
                    passes=all(a[s]['budget_pass'] and b[s]['budget_pass'] for s in seeds)
                    no_flags=all(a[s]['bound_contradiction'] is not None and b[s]['bound_contradiction'] is not None for s in seeds) and sum(a[s]['bound_contradiction'] for s in seeds)<=sum(b[s]['bound_contradiction'] for s in seeds)
                    quality=all(a[s]['objective'] is not None and b[s]['objective'] is not None and Fraction(a[s]['objective_exact'])<=Fraction(b[s]['objective_exact'])+Fraction(1,100)*abs(Fraction(b[s]['objective_exact'])) for s in seeds)
                    ratio=geom([a[s]['work']/b[s]['work'] for s in seeds]);less_work=ratio<1
                qualifiers.append({'presolve':presolve,'budget':budget,'instance':instance,'three_pairs':enough,
                    'all_primal_pass':passes,'no_more_bound_flags':no_flags,'within_one_percent_objective':quality,
                    'work_ratio_Budget_NF3':ratio,'qualifies':bool(enough and passes and no_flags and quality and less_work)})
    write(HERE/'verified-runs.csv',records);write(HERE/'verified-summary.csv',summaries);write(HERE/'qualification.csv',qualifiers)
    regime=[]
    for p in [-1,0]:
        counts=[sum(r['qualifies'] for r in qualifiers if r['presolve']==p and r['budget']==b) for b in d['volume_budgets']]
        regime.append({'presolve':p,'qualified_models_per_budget':dict(zip(d['volume_budgets'],counts)),
            'prespecified_regime_found':any(a>=4 and b>=4 for a,b in zip(counts,counts[1:]))})
    result={'assignments':len(parent),'abstentions':abstentions,'native_MIP_calls':len(parent)-abstentions,
        'exact_witness_LP_calls':sum(r.get('lp_calls',0) for r in witnesses.values()),
        'exact_unique_witnesses':sum('certificate' in r for r in witnesses.values()),'exact_witness_row_checks':witness_row_checks,
        'physical_original_row_point_checks':physical_checks,'exported_physical_row_point_checks':export_checks,
        'regime':regime,'global_optimality_independently_verified':False,
        'distinct_export_sha256':len({m['export_sha256'] for m in d['models'].values() if m['export_sha256']}),
        'identical_export_policy_groups':[{"export_sha256":h,"model_keys":[k for k,m in d['models'].items() if m['export_sha256']==h]}
            for h in sorted({m['export_sha256'] for m in d['models'].values() if m['export_sha256']})
            if sum(m['export_sha256']==h for m in d['models'].values())>1]}
    dump(HERE/'VALIDATION.json',result);print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()
