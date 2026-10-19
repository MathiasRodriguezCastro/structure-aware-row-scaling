#!/usr/bin/env python3
"""Replay every saved point and rational certificate without optimizer calls."""
import argparse
import csv
from fractions import Fraction as Q
import gzip
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
F=Q.from_float
def load(p):
    b=p.read_bytes();return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def write(p,rows):
    if not rows:return
    with p.open('w',newline='') as out:
        w=csv.DictWriter(out,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def gm(values):return math.exp(statistics.mean(math.log(x) for x in values)) if values else None
def residual(row,x):
    v=sum((a*x[n] for n,a in row['terms'].items()),Q(0))-row['rhs']
    return abs(v) if row['sense']=='=' else max(Q(0),v if row['sense']=='<=' else -v)
def canonical(path):
    parsed,_=parse(path);_,lp,_=read_lp(path)
    rows={n:dict(sense=r['sense'],rhs=F(float(r['rhs'])),terms={j:F(float(a)) for j,a in r['terms'].items()}) for n,r in parsed.items()}
    bounds={n:(F(float(l)) if math.isfinite(l) else None,F(float(u)) if math.isfinite(u) else None) for n,l,u in zip(lp.col_names_,lp.col_lower_,lp.col_upper_)}
    costs={n:F(float(c)) for n,c in zip(lp.col_names_,lp.col_cost_)}
    integers={n for n,t in zip(lp.col_names_,lp.integrality_) if str(t)!='HighsVarType.kContinuous'}
    scope={}
    for n,r in parsed.items():
        s=physical_spec(n,r['terms'])
        if s:scope[n]=(s[0],s[1],F(float(s[2])))
        elif re.fullmatch(r'a\d+_activacion_[1-4]\(\d+\)',n):scope[n]=('Volume-dependent activation','m3',Q(1))
    return rows,bounds,costs,integers,scope,F(float(lp.offset_))

def certificate(model,folder,global_lp):
    rows,bounds,costs,integers,scope,offset=model;names=list(bounds);index={n:j for j,n in enumerate(names)}
    if not (folder/'certificate.json').exists():return dict(verified_lower=None,verified_upper=None)
    lp=load(folder/'lp.json.gz');fixed={names[int(j)]:Q(v) for j,v in lp['integers'].items()}
    assert not fixed if global_lp else set(fixed)==integers
    assert all(v.denominator==1 for v in fixed.values())
    continuous=[n for n in names if n not in fixed];ci={n:j for j,n in enumerate(continuous)}
    inequalities=[]
    for n,r in rows.items():
        rhs=r['rhs']-sum((a*fixed[j] for j,a in r['terms'].items() if j in fixed),Q(0))
        terms={ci[j]:a for j,a in r['terms'].items() if j not in fixed}
        for sign in ([1,-1] if r['sense']=='=' else [1] if r['sense']=='<=' else [-1]):
            inequalities.append(({j:sign*a for j,a in terms.items()},sign*rhs))
    for n in continuous:
        lo,hi=bounds[n]
        if lo is not None:inequalities.append(({ci[n]:Q(-1)},-lo))
        if hi is not None:inequalities.append(({ci[n]:Q(1)},hi))
    assert len(lp['rows'])==len(inequalities)
    for (a,b),saved in zip(inequalities,lp['rows']):
        assert a=={int(j):Q(v) for j,v in saved['terms'].items()} and b==Q(saved['rhs'])
    c=[costs[n] for n in continuous];constant=offset+sum((costs[n]*x for n,x in fixed.items()),Q(0))
    assert list(map(Q,lp['cost']))==c and Q(lp['offset'])==constant
    q=list(map(Q,load(folder/'primal.json')));assert len(q)==len(continuous)
    primal_ok=all(sum((a*q[j] for j,a in terms.items()),Q(0))<=rhs for terms,rhs in inequalities)
    if not primal_ok:return dict(verified_lower=None,verified_upper=None,primal_rows_verified=len(rows),point_integer_feasible=False)
    point={**fixed,**dict(zip(continuous,q))}
    assert set(point)==set(bounds)
    for r in rows.values():assert residual(r,point)==0
    for n,(lo,hi) in bounds.items():assert (lo is None or point[n]>=lo) and (hi is None or point[n]<=hi)
    U=constant+sum((a*x for a,x in zip(c,q)),Q(0));LB=None
    dual=load(folder/'dual.json')
    if dual is not None:
        pi={int(j):Q(v) for j,v in dual.items()}
        assert all(0<=j<len(inequalities) for j in pi)
        reduced=c.copy();L=constant
        for j,(terms,rhs) in enumerate(inequalities):
            p=pi.get(j,Q(0));L+=p*rhs
            for k,a in terms.items():reduced[k]-=p*a
        dual_ok=all(v<=0 for v in pi.values()) and not any(reduced)
        if dual_ok:
            assert L<=U
            if global_lp:LB=L
    integer_feasible=all(point[n].denominator==1 for n in integers)
    return dict(verified_lower=None if LB is None else str(LB),
        verified_upper=str(U) if integer_feasible else None,primal_rows_verified=len(rows),
        point_integer_feasible=integer_feasible)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--logging-confirmation',action='store_true')
    args=parser.parse_args()
    run_root=HERE/'logging-confirmation' if args.logging_confirmation else HERE
    d=load(HERE/'design.json');timing=load(run_root/'timing.json');certs=load(HERE/'certificate-results.json')
    if args.logging_confirmation:
        amendment=load(HERE/'LOGGING_AMENDMENT.json')
        assert sha(HERE/'design.json')==amendment['first_campaign_design_sha256']
        assert sha(run_root/'study.py')==amendment['logging_runner_sha256']
        for name,h in amendment['original_results_sha256'].items():assert sha(HERE/name)==h
        expected=(HERE/'study.py').read_text().replace('ROOT=HERE.parents[1]','ROOT=HERE.parents[2]').replace(
            "m.setParam('LogToConsole',0);m.setParam('LogFile',str(folder/'solver.log'))",
            "m.setParam('OutputFlag',1);m.setParam('LogToConsole',0);m.setParam('LogFile',str(folder/'solver.log'))")
        assert (run_root/'study.py').read_text()==expected
    assert len(timing)==len(d['jobs'])==360 and all(t['returncode']==0 for t in timing)
    assert [t['job'] for t in timing]==d['jobs']
    for p,h in d['dependencies'].items():assert sha(ROOT/p)==h,p
    plan=load(HERE/'certificate-plan.json');assert sha(HERE/'design.json')==plan['design_sha256']
    for p,h in plan['dependencies'].items():assert sha(ROOT/p)==h,p
    assert len(certs)==len(plan['plan'])==96 and [r['assignment'] for r in certs]==plan['plan']
    models={};references={};factor_records=[];certificate_records=[]
    for name,meta in d['models'].items():
        folder=HERE/'models'/name;assert sha(folder/'input.txt')==meta['input_sha256']
        for rep in ['Base','L2','Budget-L2']:
            path=folder/(rep+'.lp');expected=meta['base_sha256'] if rep=='Base' else meta['policies'][rep]['sha256']
            assert sha(path)==expected;models[name,rep]=canonical(path)
            if args.logging_confirmation:assert sha(run_root/'models'/name/(rep+'.lp'))==sha(path)
        base=models[name,'Base'];assert len(base[0])==meta['rows'] and len(base[3])==4*meta['horizon']
        l2=load(folder/'L2-factors.json');budget=load(folder/'Budget-L2-factors.json')
        changed=[n for n in l2 if budget[n]!=l2[n]]
        assert len(changed)==meta['policies']['Budget-L2']['changed_from_L2']
        assert all(re.fullmatch(r'a\d+_activacion_[1-4]\(\d+\)',n) for n in changed)
        for rep in ['L2','Budget-L2']:
            assert models[name,rep][1:4]==base[1:4] and models[name,rep][5]==base[5], 'bounds, objective or domains changed'
            factors=l2 if rep=='L2' else budget
            assert set(factors)==set(base[0])
            for n,row in base[0].items():
                actual=models[name,rep][0][n];alpha=F(factors[n]);assert alpha>0
                assert actual['sense']==row['sense'] and set(actual['terms'])==set(row['terms'])
                assert all(float(actual['terms'][j])==float(alpha*a) for j,a in row['terms'].items())
                assert float(actual['rhs'])==float(alpha*row['rhs'])
        factor_records.append(dict(instance=name,horizon=meta['horizon'],rows=meta['rows'],
            changed_rows=len(changed),changed_percent=100*len(changed)/len(base[0]),
            max_ratio=max(budget[n]/l2[n] for n in changed),incompatible=meta['policies']['Budget-L2']['incompatible_count']))
    for r in certs:
        item=r['assignment'];key=item['instance'],item['representation']
        assert sha(HERE/'models'/key[0]/(key[1]+'.lp'))==r['model_sha256']
        folder=HERE/'certificates'/key[0]/(item['kind']+'-'+key[1])
        c=certificate(models[key],folder,item['kind']=='global-LP')
        certificate_records.append(dict(**item,**c))
        ref=references.setdefault(key,dict(lower=None,upper=None))
        if c['verified_lower'] is not None:ref['lower']=Q(c['verified_lower'])
        if c['verified_upper'] is not None:
            U=Q(c['verified_upper']);ref['upper']=min(U,ref['upper']) if ref['upper'] is not None else U
    records=[];row_checks=0;complete_logs=0;replication=[]
    for t in timing:
        job=t['job'];folder=run_root/'runs'/job['id'];r=load(folder/'result.json');assert r['job']==job and not r['abstained']
        log=(folder/'solver.log').read_text()
        log_complete='Gurobi Optimizer version 13.0.2' in log and 'Best objective' in log
        complete_logs+=log_complete
        if args.logging_confirmation:
            assert log_complete,job['id']
            match=re.search(r'Best objective ([-+\d.e]+), best bound ([-+\d.e]+)',log)
            assert match
            for value,key in zip(match.groups(),['objective','bound']):
                assert math.isclose(float(value),r['outcome'][key],rel_tol=1e-10,abs_tol=1e-7)
            old=load(HERE/'runs'/job['id']/'result.json')
            with np.load(HERE/'runs'/job['id']/'solution.npz',allow_pickle=False) as a,np.load(folder/'solution.npz',allow_pickle=False) as b:
                samepoint=np.array_equal(a['names'],b['names']) and np.array_equal(a['x'],b['x'])
            replication.append(dict(id=job['id'],point_identical=bool(samepoint),
                endpoints_identical=all(old['outcome'][k]==r['outcome'][k] for k in ['status','work','nodes','objective','bound']),
                work_identical=old['outcome']['work']==r['outcome']['work']))
        params={**d['parameters'],'Seed':job['seed']}
        if job['policy']=='Base-tight':params['FeasibilityTol']=1e-9
        if job['policy']=='L2-NF3':params['NumericFocus']=3
        assert r['parameters']==params
        out=r['outcome'];base=models[job['instance'],'Base'];export=models[job['instance'],r['representation']]
        item=dict(instance=job['instance'],horizon=d['models'][job['instance']]['horizon'],seed=job['seed'],
            policy=job['policy'],candidate=bool(out['solutions']),status=out['status'],work=out['work'],
            total_seconds=t['total_seconds'],budgets_passed=False,max_budget_ratio=None,objective=None,
            exported_hypothesis=False,bound_contradiction=None,completion_contradiction=None,
            max_original_row_violation=None,max_bound_violation=None,max_integrality=None)
        if out['solutions']:
            with np.load(folder/'solution.npz',allow_pickle=False) as saved:
                point={n:F(float(x)) for n,x in zip(saved['names'].tolist(),saved['x'].tolist())}
            assert set(point)==set(base[1]);rounded={n:Q(round(x)) if n in base[3] else x for n,x in point.items()}
            maximum=Q(0);exported=Q(0);original=Q(0)
            for n,row in base[0].items():
                raw=residual(row,point);v=residual(row,rounded);original=max(original,raw,v);row_checks+=2
                if n in base[4]:
                    _,unit,conv=base[4][n];delta=F(.01) if unit=='MW' else Q(100)
                    maximum=max(maximum,raw/conv/delta,v/conv/delta)
                    exported=max(exported,residual(export[0][n],point))
            bv=max([Q(0)]+[max(Q(0),lo-point[n]) for n,(lo,hi) in base[1].items() if lo is not None]+
                [max(Q(0),point[n]-hi) for n,(lo,hi) in base[1].items() if hi is not None])
            iv=max(abs(point[n]-round(point[n])) for n in base[3])
            objective=base[5]+sum((a*point[n] for n,a in base[2].items()),Q(0))
            assert objective==Q(r['checks']['point_objective_exact'])
            item.update(budgets_passed=maximum<=1,max_budget_ratio=float(maximum),objective=float(objective),
                exported_hypothesis=exported<=F(1e-6),max_original_row_violation=float(original),
                max_bound_violation=float(bv),max_integrality=float(iv))
        U=references[job['instance'],r['representation']]['upper']
        if U is not None:
            B=out['bound'];C=out['objective']
            item['bound_contradiction']=bool(B is not None and F(B)>U+F(max(1e-6,8*math.ulp(B))))
            item['completion_contradiction']=bool(out['status']==2 and C is not None and U<F(C)-abs(F(C))/100)
        records.append(item)
    summaries=[];pairs=[]
    for control in ['Base','Base-tight','L2','L2-NF3']:
        lookup={(r['instance'],r['seed']):r for r in records if r['policy']==control}
        for r in records:
            if r['policy']!='Budget-L2':continue
            c=lookup[r['instance'],r['seed']]
            valid=all(x['candidate'] and x['budgets_passed'] and x['status']==2 and
                x['bound_contradiction'] is False and x['completion_contradiction'] is False for x in [r,c])
            pairs.append(dict(instance=r['instance'],horizon=r['horizon'],seed=r['seed'],control=control,
                work_ratio=r['work']/c['work'],time_ratio=r['total_seconds']/c['total_seconds'],
                both_completed_verified_accuracy_without_detected_contradiction=valid,
                candidate_deterioration_percent=None if r['objective'] is None or c['objective'] in (None,0) else
                100*(r['objective']-c['objective'])/abs(c['objective'])))
        for horizon in [None,24,72,168]:
            pp=[p for p in pairs if p['control']==control and (horizon is None or p['horizon']==horizon)]
            vv=[p for p in pp if p['both_completed_verified_accuracy_without_detected_contradiction']]
            summaries.append(dict(control=control,horizon=horizon,pairs=len(pp),
                work_ratio=gm([p['work_ratio'] for p in pp]),time_ratio=gm([p['time_ratio'] for p in pp]),
                work_wins=sum(p['work_ratio']<1 for p in pp),time_wins=sum(p['time_ratio']<1 for p in pp),
                screened_pairs=len(vv),screened_work_ratio=gm([p['work_ratio'] for p in vv]),
                screened_time_ratio=gm([p['time_ratio'] for p in vv]),
                max_candidate_deterioration_percent=max([p['candidate_deterioration_percent'] for p in pp if p['candidate_deterioration_percent'] is not None],default=None)))
    policy=[]
    for p in ['Base','Base-tight','L2','L2-NF3','Budget-L2']:
        rr=[r for r in records if r['policy']==p]
        policy.append(dict(policy=p,runs=len(rr),candidates=sum(r['candidate'] for r in rr),
            native_completed=sum(r['status']==2 for r in rr),budgets_passed=sum(r['budgets_passed'] for r in rr),
            exported_hypothesis_passed=sum(r['exported_hypothesis'] for r in rr),
            bound_flags=sum(r['bound_contradiction'] is True for r in rr),
            completion_flags=sum(r['completion_contradiction'] is True for r in rr),
            bound_contrasts_unknown=sum(r['bound_contradiction'] is None for r in rr),
            checked_completion_PAR10_seconds=statistics.mean(r['total_seconds'] if
                r['candidate'] and r['budgets_passed'] and r['status']==2 and
                r['bound_contradiction'] is False and r['completion_contradiction'] is False else 1200.
                for r in rr),
            max_budget_ratio=max([r['max_budget_ratio'] for r in rr if r['max_budget_ratio'] is not None],default=None)))
    intervals=[]
    for name in d['models']:
        ref=references[name,'Base'];L,U=ref['lower'],ref['upper']
        assert L is None or U is None or L<=U
        intervals.append(dict(instance=name,LB=None if L is None else str(L),U=None if U is None else str(U),
            relative_width_percent=None if L is None or U in (None,0) else float(100*(U-L)/abs(U)),
            exact_optimum=L is not None and U is not None and L==U))
    for filename,rows in [('verified-runs.csv',records),('verified-pairs.csv',pairs),('verified-factors.csv',factor_records),
        ('verified-certificates.csv',certificate_records),('verified-intervals.csv',intervals)]:write(run_root/filename,rows)
    summary=dict(status='passed',models=24,MIP_calls=360,rational_row_residual_checks=row_checks,
        external_validation=False,global_LP_lower_bounds=sum(i['LB'] is not None for i in intervals),
        exact_original_MILP_optima=sum(i['exact_optimum'] for i in intervals),policies=policy,paired_comparisons=summaries,
        exact_native_export_witnesses=sum(v['upper'] is not None for v in references.values()),
        certificate_acquisition_seconds=sum(r['result']['total_seconds'] for r in certs),
        design_sha256=sha(HERE/'design.json'),no_global_MIP_gap_claim_from_saved_float_candidates=True)
    summary['complete_native_logs']=complete_logs
    summary['logging_confirmation']=args.logging_confirmation
    if args.logging_confirmation:
        summary['replication']={'assignments':len(replication),
            'identical_saved_points':sum(r['point_identical'] for r in replication),
            'identical_work':sum(r['work_identical'] for r in replication),
            'identical_endpoints':sum(r['endpoints_identical'] for r in replication),
            'additional_LP_calls':0}
        write(run_root/'verified-replication.csv',replication)
    dump(run_root/'VALIDATION.json',summary);print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':main()
