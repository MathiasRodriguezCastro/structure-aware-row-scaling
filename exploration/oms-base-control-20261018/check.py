#!/usr/bin/env python3
"""Independent saved-point replay. No runner or optimizer import/invocation."""
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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FRONT = ROOT/'exploration/oms-frontier-20261016'
sys.path[:0] = [str(ROOT/'scripts/research'),str(ROOT/'scripts')]
from audit_identifiability_grid import parse
from audit_fixed_basis import read_lp
from oms_dispatch_validation import physical_spec
F = Fraction.from_float
INPUTS = {}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    path = Path(path)
    INPUTS[str(path.relative_to(ROOT))] = sha(path)
    return json.loads(path.read_text())


def dump(path, data):
    path.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')


def write(path, data):
    with path.open('w',newline='') as out:
        w = csv.DictWriter(out,fieldnames=list(data[0]))
        w.writeheader()
        w.writerows(data)


def gm(values):
    return math.exp(statistics.mean(math.log(v) for v in values))


def violation(row, point):
    residual = sum((a*point[n] for n,a in row['terms'].items()),Fraction(0))-row['rhs']
    return abs(residual) if row['sense']=='=' else max(Fraction(0),residual if row['sense']=='<=' else -residual)


def canonical(path):
    INPUTS[str(path.relative_to(ROOT))] = sha(path)
    rows,_ = parse(path)
    _,lp,_ = read_lp(path)
    exact = {n:dict(sense=r['sense'],rhs=F(float(r['rhs'])),
              terms={j:F(float(a)) for j,a in r['terms'].items()}) for n,r in rows.items()}
    bounds = {n:(F(float(l)) if math.isfinite(l) else None,F(float(h)) if math.isfinite(h) else None)
              for n,l,h in zip(lp.col_names_,lp.col_lower_,lp.col_upper_)}
    costs = {n:F(float(c)) for n,c in zip(lp.col_names_,lp.col_cost_)}
    integers = {n for n,k in zip(lp.col_names_,lp.integrality_) if str(k)!='HighsVarType.kContinuous'}
    scope = {}
    for n,r in rows.items():
        spec = physical_spec(n,r['terms'])
        if spec:
            scope[n] = spec[0],spec[1],F(float(spec[2]))
        elif re.fullmatch(r'a\d+_activacion_[1-4]\(\d+\)',n):
            scope[n] = 'Volume-dependent activation','m3',Fraction(1)
    assert len(scope)==4320 and len(exact)==10080 and len(integers)==1440
    return exact,bounds,costs,integers,scope,F(float(lp.offset_))


def check_witness(folder, model_path):
    cert = load(folder/'independent-certificate.json')
    point_path = folder/'exact-witness.json'
    point = {n:Fraction(v) for n,v in load(point_path).items()}
    rows,bounds,costs,integers,scope,offset = canonical(model_path)
    assert sha(model_path)==cert['original_model_sha256']
    assert sha(point_path)==cert['witness_sha256']
    assert set(point)==set(bounds)
    for n,r in rows.items():
        assert violation(r,point)==0,n
    for n,(l,h) in bounds.items():
        assert l is None or point[n]>=l,n
        assert h is None or point[n]<=h,n
    assert all(point[n].denominator==1 for n in integers)
    objective = offset+sum((costs[n]*point[n] for n in point),Fraction(0))
    assert objective==Fraction(cert['objective_exact_fraction'])
    return objective


def audit(folder, model, U, is_historical):
    r = load(folder/'result.json')
    job = r['job']
    source = folder/'solver.log'
    log = source.read_text()
    INPUTS[str(source.relative_to(ROOT))] = sha(source)
    assert 'Gurobi Optimizer version 13.0.2' in log
    assert 'Loaded user MIP start' not in log
    d = load(HERE/'design.json')
    params = {**d['parameters'],'Seed':job['seed']}
    if job['policy']=='Base-tight':
        params['FeasibilityTol']=1e-9
    assert r['parameters']==params
    for k in ['Seed','Presolve','NumericFocus','IntegralityFocus']:
        assert f'Set parameter {k} to value {params[k]}' in log
    assert r['native_import']==dict(rows=10080,columns=6120,nonzeros=22679,
        matrix_rhs_objective_bounds_integer_domains_equal=True)
    base = FRONT/'models'/job['instance']/'Base.lp'
    assert sha(folder/'Base.lp')==sha(base)==r['base_sha256']
    if is_historical:
        assert sha(folder/'scaled.lp')==sha(model)==r['export_sha256']
    B,C = r['outcome']['bound'],r['outcome']['objective']
    bf = bool(B is not None and F(B)>U+F(max(1e-6,8*math.ulp(B))))
    gf = bool(r['outcome']['native_completed'] and C is not None and U<F(C)-abs(F(C))/100)
    assert bf==r['checks']['bound_contradiction']
    assert gf==r['checks']['completion_contradiction']
    assert U==Fraction(r['checks']['known_witness_objective_exact'])
    assert not r['global_optimality_independently_verified']
    rows,bounds,costs,integers,scope,offset = canonical(base)
    exported = canonical(model)[0] if is_historical else rows
    group_stats = {}
    extras = dict(candidate_present=False,objective_exact=None,max_integer_violation=None,
        integer_hypothesis_holds=None,raw_bound_max=None,rounded_bound_max=None,
        nonphysical_raw_max=None,nonphysical_rounded_max=None,nonphysical_positive_rows=None,
        exported_physical_max=None,exported_physical_rows_over_epsilon=None)
    if r['outcome']['solutions']:
        point_path = folder/'solution.npz'
        INPUTS[str(point_path.relative_to(ROOT))] = sha(point_path)
        with np.load(point_path,allow_pickle=False) as point:
            names = point['names'].tolist()
            values = point['x'].tolist()
        assert len(set(names))==len(names) and set(names)==set(bounds)
        assert all(math.isfinite(v) for v in values)
        raw = {n:F(v) for n,v in zip(names,values)}
        rounded = {n:Fraction(round(v)) if n in integers else v for n,v in raw.items()}
        raw_bound = rounded_bound = Fraction(0)
        for n,(lo,hi) in bounds.items():
            for p,mode in [(raw,'raw'),(rounded,'rounded')]:
                v = max(Fraction(0),lo-p[n] if lo is not None else Fraction(0),p[n]-hi if hi is not None else Fraction(0))
                if mode=='raw': raw_bound=max(raw_bound,v)
                else: rounded_bound=max(rounded_bound,v)
        nonphysical_raw = nonphysical_round = exp_max = Fraction(0)
        nonphysical_count = exp_over = 0
        physical_rows = []
        for n,row in rows.items():
            vr,vz = violation(row,raw),violation(row,rounded)
            if n not in scope:
                nonphysical_raw=max(nonphysical_raw,vr)
                nonphysical_round=max(nonphysical_round,vz)
                nonphysical_count+=vz>0
                continue
            group,unit,conversion = scope[n]
            vr,vz = vr/conversion,vz/conversion
            physical_rows.append((unit,vr,vz))
            stats = group_stats.setdefault((group,unit),[Fraction(0),Fraction(0)])
            stats[0],stats[1] = max(stats[0],vr),max(stats[1],vz)
            ev = violation(exported[n],raw)
            exp_max=max(exp_max,ev)
            exp_over+=ev>F(1e-6)
        for g in r['checks']['physical']:
            assert [float(x) for x in group_stats[g['group'],g['unit']]]==[g['raw_max'],g['rounded_max']]
        objective = offset+sum((costs[n]*raw[n] for n in raw),Fraction(0))
        assert objective==Fraction(r['checks']['point_objective_exact'])
        assert C is not None and abs(objective-F(C))<=F(max(1e-6,8*math.ulp(C)))
        iv=max(abs(raw[n]-round(raw[n])) for n in integers)
        extras.update(candidate_present=True,objective_exact=str(objective),max_integer_violation=float(iv),
            integer_hypothesis_holds=iv<=F(params['IntFeasTol']),raw_bound_max=float(raw_bound),
            rounded_bound_max=float(rounded_bound),nonphysical_raw_max=float(nonphysical_raw),
            nonphysical_rounded_max=float(nonphysical_round),nonphysical_positive_rows=nonphysical_count,
            exported_physical_max=float(exp_max),exported_physical_rows_over_epsilon=exp_over)
    records = []
    for budget in [job['budget']] if is_historical else d['volume_budgets']:
        ratios = [v[1]/F(.01 if unit=='MW' else float(budget)) for (group,unit),v in group_stats.items()]
        raw_ratios = [v[0]/F(.01 if unit=='MW' else float(budget)) for (group,unit),v in group_stats.items()]
        record = dict(instance=job['instance'],seed=job['seed'],policy=job['policy'],budget=budget,
            status=r['outcome']['status'],work=r['outcome']['work'],native_seconds=r['outcome']['native_runtime'],
            physical_budgets_pass=bool(ratios and max(ratios)<=1),rounded_max_ratio=float(max(ratios)) if ratios else None,
            raw_max_ratio=float(max(raw_ratios)) if raw_ratios else None,
            bound_contradiction=bf,completion_contradiction=gf,**extras,
            rounded_volume_max_m3=max((float(v[1]) for (g,u),v in group_stats.items() if u=='m3'),default=None),
            rounded_power_max_MW=max((float(v[1]) for (g,u),v in group_stats.items() if u=='MW'),default=None),
            violated_physical_rows=sum(vz>F(.01 if unit=='MW' else float(budget)) for unit,vr,vz in physical_rows) if ratios else None)
        records.append(record)
    return records


def main():
    d = load(HERE/'design.json')
    for p,h in d['dependencies'].items():
        assert sha(ROOT/p)==h,p
    for p,h in d['frozen_pdfs'].items():
        if not (ROOT/p).exists() and '--allow-absent-historical' in sys.argv:
            continue
        assert sha(ROOT/p)==h,p
    timings = load(HERE/'parent-timing.json')
    assert len(timings)==len(d['jobs'])==36
    assert [r['job'] for r in timings]==d['jobs']
    assert all(r['returncode']==0 for r in timings)
    old = load(FRONT/'design.json')
    wi = load(FRONT/'witness-index.json')
    witnessed = {}
    for n in d['instances']:
        base = FRONT/'models'/n/'Base.lp'
        assert sha(base)==d['input_hashes'][n]['base_sha256']
        witnessed[n+'/Base'] = check_witness(ROOT/d['base_witnesses'][n],base)
        for b in d['volume_budgets']:
            key = n+'/B'+str(b)
            w = wi[key]
            while 'alias' in w:
                w = wi[w['alias']]
            witnessed[key] = check_witness(ROOT/w['folder'],ROOT/old['models'][key]['model'])
        print('Exact witnesses checked',n,flush=True)
    records = []
    for timing in timings:
        job = timing['job']
        folder = HERE/'runs'/job['id']
        r = load(folder/'result.json')
        assert r['job']==job
        assert sum(r['stages_seconds'].values())<=r['worker_internal_seconds_before_result']<=timing['total_fresh_process_seconds']
        new = audit(folder,FRONT/'models'/job['instance']/'Base.lp',witnessed[job['instance']+'/Base'],False)
        for v in new:
            v['new_total_seconds'] = timing['total_fresh_process_seconds']
        records.extend(new)
    for p in d['historical_budget_references']:
        folder=ROOT/p
        j=load(folder/'result.json')['job']
        assert j in old['jobs'] and j['presolve']==-1
        new = audit(folder,FRONT/'models'/j['instance']/f"B{j['budget']}.lp",witnessed[j['instance']+'/B'+str(j['budget'])],True)
        for v in new:
            v['new_total_seconds']=None
        records.extend(new)
    assert len(records)==108
    write(HERE/'verified-runs.csv',records)
    summaries=[]
    pairs=[]
    model_pairs=[]
    lookup={(r['instance'],r['seed'],r['policy'],r['budget']):r for r in records}
    for b in d['volume_budgets']:
        for policy in ['Base','Base-tight','Budget-L2']:
            rr=[r for r in records if r['policy']==policy and r['budget']==b]
            summaries.append(dict(budget=b,policy=policy,calls=len(rr),
                candidates=sum(r['candidate_present'] for r in rr),budgets_passed=sum(r['physical_budgets_pass'] for r in rr),
                bound_flags=sum(r['bound_contradiction'] for r in rr),completion_flags=sum(r['completion_contradiction'] for r in rr),
                time_limits=sum(r['status']==9 for r in rr),gm_work=gm([r['work'] for r in rr]),
                max_volume_m3=max(r['rounded_volume_max_m3'] for r in rr),max_power_MW=max(r['rounded_power_max_MW'] for r in rr),
                max_original_bound_violation=max(r['rounded_bound_max'] for r in rr)))
        for control in ['Base','Base-tight']:
            for n in d['instances']:
                new_pairs=[]
                for s in d['seeds']:
                    a=lookup[n,s,'Budget-L2',b]
                    c=lookup[n,s,control,b]
                    cost=100*(Fraction(a['objective_exact'])-Fraction(c['objective_exact']))/abs(Fraction(c['objective_exact']))
                    pair=dict(budget=b,control=control,instance=n,seed=s,work_ratio=a['work']/c['work'],
                        objective_deterioration_percent=float(cost),both_budgets_pass=a['physical_budgets_pass'] and c['physical_budgets_pass'],
                        budget_bound_flag=a['bound_contradiction'],control_bound_flag=c['bound_contradiction'],
                        budget_completion_flag=a['completion_contradiction'],control_completion_flag=c['completion_contradiction'],
                        budget_status=a['status'],control_status=c['status'])
                    pairs.append(pair);new_pairs.append(pair)
                model_pairs.append(dict(budget=b,control=control,instance=n,work_ratio=gm([p['work_ratio'] for p in new_pairs]),
                    max_cost_deterioration_percent=max(p['objective_deterioration_percent'] for p in new_pairs),
                    both_budgets_all=all(p['both_budgets_pass'] for p in new_pairs)))
    write(HERE/'verified-summary.csv',summaries)
    write(HERE/'paired-work.csv',pairs)
    write(HERE/'per-model.csv',model_pairs)
    aggregate=[]
    for b in d['volume_budgets']:
        for control in ['Base','Base-tight']:
            pp=[p for p in pairs if p['budget']==b and p['control']==control]
            mm=[p for p in model_pairs if p['budget']==b and p['control']==control]
            aggregate.append(dict(budget=b,control=control,gm_work_ratio=gm([p['work_ratio'] for p in pp]),
                cheaper_pairs=sum(p['work_ratio']<1 for p in pp),cheaper_models=sum(p['work_ratio']<1 for p in mm),
                both_budgets_pass=sum(p['both_budgets_pass'] for p in pp),
                max_cost_deterioration_percent=max(p['objective_deterioration_percent'] for p in pp),
                model_ratio_min=min(p['work_ratio'] for p in mm),model_ratio_max=max(p['work_ratio'] for p in mm),
                control_bound_flags=sum(p['control_bound_flag'] for p in pp),control_completion_flags=sum(p['control_completion_flag'] for p in pp)))
    gate = {b:all(a['gm_work_ratio']<1 and a['cheaper_models']>=4 and a['both_budgets_pass']==18
                  and a['max_cost_deterioration_percent']<=1
                  and sum(p['budget_bound_flag'] for p in pairs if p['budget']==b and p['control']==a['control'])<=a['control_bound_flags']
                  and sum(p['budget_completion_flag'] for p in pairs if p['budget']==b and p['control']==a['control'])<=a['control_completion_flags']
                  for a in aggregate if a['budget']==b) for b in d['volume_budgets']}
    result=dict(new_native_MIP_calls=36,reused_historical_Budget_calls=36,new_LP_calls=0,
        verified_exact_witnesses=len(witnessed),saved_points=72,original_row_point_checks=72*10080*2,
        physical_original_row_point_checks=72*4320*2,exported_physical_row_point_checks=72*4320,
        results=summaries,paired_comparisons=aggregate,temporal_confirmation_gate=gate,
        time_ratios_to_historical_runs_not_computed=True,global_MILP_optimality_not_certified=True)
    dump(HERE/'VALIDATION.json',result)
    dump(HERE/'replay-inputs.json',INPUTS)
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':
    main()
