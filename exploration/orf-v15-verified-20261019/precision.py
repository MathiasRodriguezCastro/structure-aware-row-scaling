#!/usr/bin/env python3
"""Independent actual-export reserves, numerical-envelope controls and margins."""
import csv
from fractions import Fraction as Q
import json
import math
from pathlib import Path
import statistics
import sys

import numpy as np

HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import check as independent
from check import parent,F


def load(p):return json.loads(p.read_text())
def write(p,rows):
    with p.open('w',newline='') as out:
        w=csv.DictWriter(out,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def key(group,unit):return 'power' if unit=='MW' else 'activation' if group=='Volume-dependent activation' else 'water'


def main():
    d=load(HERE/'design.json');exports=load(HERE/'EXPORTS.json')['records']
    models={n:parent.canonical(independent.PARENT/'models'/n/'Base.lp') for n in d['models']}
    selection=[];incompatible=[];observations=[];cache={};certificates=0
    for n,model in models.items():
        rows,bounds,costs,ints,scope,offset=model
        boxes={j:None if lo is None or hi is None else max(abs(lo),abs(hi)) for j,(lo,hi) in bounds.items()}
        blocked=[]
        for rowname,(group,unit,conversion) in scope.items():
            if key(group,unit)!='activation':continue
            E=F(1e-9)*sum((abs(v) for j,v in rows[rowname]['terms'].items() if j in ints),Q(0))
            if E>=F(1.)*conversion:blocked.append((rowname,E/conversion))
        incompatible.append(dict(instance=n,horizon=d['models'][n]['horizon'],activation_budget_m3=1.,
            rounding_contract_incompatible_rows=len(blocked),example_row=blocked[0][0] if blocked else '',
            largest_E_m3=float(max((v for _,v in blocked),default=Q(0))),
            model_infeasibility_claimed=False))
        l2=load(independent.PARENT/'models'/n/'L2-factors.json')
        for tag,info in exports.items():
            name,policy,contract_name=tag.split('/')
            if name!=n or info['abstained']:continue
            contract=d['contracts'][contract_name]
            factors=load(HERE/info['factors']);written=parent.canonical(HERE/info['export'])[0]
            known=certified=ideal=0;worst=Q(0);clone_mismatch=0;reserves=[]
            for rn,(group,unit,conversion) in scope.items():
                a=rows[rn];w=written[rn];alpha=F(factors[rn]);delta=F(contract[key(group,unit)])*conversion
                assert set(a['terms'])==set(w['terms']) and a['sense']==w['sense']
                assert all(F(1e-9)<=abs(v)<=F(1e9) for v in w['terms'].values() if v)
                for j,v in a['terms'].items():assert F(float(float(alpha)*float(v)))==w['terms'][j]
                assert F(float(float(alpha)*float(a['rhs'])))==w['rhs']
                E=F(1e-9)*sum((abs(v) for j,v in a['terms'].items() if j in ints),Q(0))
                B=abs(w['rhs']-alpha*a['rhs']);unknown=False
                for j,v in a['terms'].items():
                    error=w['terms'][j]-alpha*v
                    if error and boxes[j] is None:unknown=True
                    elif error:B+=abs(error)*boxes[j]
                ideal+=F(1e-6)/alpha+E<=delta
                if not unknown:
                    known+=1;ratio=((F(1e-6)+B)/alpha+E)/delta;worst=max(worst,ratio)
                    certified+=ratio<=1;certificates+=1
                reserves.append((key(group,unit),None if unknown else ((F(1e-6)+B)/alpha+E)/conversion,
                    (F(1e-6)/alpha+E)/conversion))
                if policy=='Budget-L2':
                    # Consume an already compiled numerical interval, with no
                    # unit labels or family names passed to the projector.
                    rho=Q(0)
                    if key(group,unit)=='activation':
                        rho=F(2.**-52)*(sum((abs(v)*boxes[j] for j,v in a['terms'].items()),Q(0))+abs(a['rhs']))
                    reserve=float(E+rho)
                    if F(reserve)<E+rho:reserve=math.nextafter(reserve,math.inf)
                    numeric_delta=F(contract[key(group,unit)]*float(conversion))
                    nz=[abs(v) for v in a['terms'].values() if v]
                    lower=max(F(1e-6)/(numeric_delta-F(reserve)),F(1e-9)/min(nz));upper=F(1e9)/max(nz)
                    lo=float(lower);hi=float(upper)
                    if F(lo)<lower:lo=math.nextafter(lo,math.inf)
                    if F(hi)>upper:hi=math.nextafter(hi,0.)
                    numeric_factor=min(max(l2[rn],lo),hi)
                    clone_mismatch+=numeric_factor!=factors[rn]
            if policy=='Export-Budget-L2':assert known==certified==len(scope),(tag,known,certified,len(scope))
            if policy=='Budget-L2':assert clone_mismatch==0,(tag,clone_mismatch)
            selection.append(dict(instance=n,policy=policy,contract=contract_name,physical_rows=len(scope),
                factors_changed_from_L2=sum(factors[r]!=l2[r] for r in factors),
                rows_meeting_ideal_residual_and_integer_condition=ideal,rows_with_uniform_export_bound=known,
                rows_certified_by_actual_export_reserve=certified,worst_known_sufficient_bound_over_budget=float(worst),
                numeric_envelope_factor_mismatches=clone_mismatch,all_rows_uniformly_certified=certified==len(scope)))
            if policy=='L2':
                for cname,c in d['contracts'].items():
                    if cname==contract_name:continue
                    rr=[r/F(c[k]) for k,r,_ in reserves if r is not None]
                    selection.append(dict(instance=n,policy=policy,contract=cname,physical_rows=len(scope),
                        factors_changed_from_L2=0,rows_meeting_ideal_residual_and_integer_condition=sum(v<=F(c[k]) for k,_,v in reserves),
                        rows_with_uniform_export_bound=known,rows_certified_by_actual_export_reserve=sum(v<=1 for v in rr),
                        worst_known_sufficient_bound_over_budget=float(max(rr,default=Q(0))),
                        numeric_envelope_factor_mismatches=0,all_rows_uniformly_certified=len(rr)==len(scope) and all(v<=1 for v in rr)))
    subset=[n for n in models if n.endswith(('-01','-08'))]
    timing=load(HERE/'timing.json')
    # Compare original points for conventional L2 with all four requirements;
    # these are rechecks of existing vectors, not new MIP experiments.
    jobs={j['id']:j for j in d['jobs']}
    for t in timing:
        j=t['job']
        if j['instance'] not in subset or not (j['experiment']=='II' or j['experiment']=='I' and j['policy'] in ['L2','Budget-L2']):continue
        r=load(HERE/'runs'/j['id']/'result.json')
        if r['abstained']:continue
        model=models[j['instance']];rows,bounds,costs,ints,scope,offset=model
        with np.load(HERE/'runs'/j['id']/'candidates.npz') as z:x=z['x'][-1]
        point=dict(zip(bounds,map(lambda v:F(float(v)),x)))
        rounded={n:Q(round(v)) if n in ints else v for n,v in point.items()}
        groups={}
        for rn,(group,unit,conversion) in scope.items():
            row=rows[rn];violation=Q(0)
            for xx in [point,rounded]:
                v=sum((a*xx[n] for n,a in row['terms'].items()),Q(0))-row['rhs']
                v=abs(v) if row['sense']=='=' else max(Q(0),v if row['sense']=='<=' else -v)
                violation=max(violation,v/conversion)
            groups.setdefault((group,unit),[]).append(violation)
        contracts=d['contracts'] if j['experiment']=='I' else {j['contract']:d['contracts'][j['contract']]}
        for cname,contract in contracts.items():
            for (group,unit),vv in groups.items():
                ratios=[float(v/F(contract[key(group,unit)])) for v in vv]
                policy=j['policy'] if j['policy']=='L2' or cname==j['contract'] else 'Budget100-reused'
                observations.append(dict(instance=j['instance'],horizon=d['models'][j['instance']]['horizon'],seed=j['seed'],
                    policy=policy,contract=cname,group=group,unit=unit,rows=len(ratios),
                    median_q=float(np.median(ratios)),p95_q=float(np.quantile(ratios,.95)),p99_q=float(np.quantile(ratios,.99)),
                    max_q=max(ratios),rows_near_limit=sum(.5<=v<=1 for v in ratios),rows_over_budget=sum(v>1 for v in ratios)))
    write(HERE/'selection-certificates.csv',selection);write(HERE/'incompatible-contracts.csv',incompatible)
    write(HERE/'precision-by-family.csv',observations)
    summary=[]
    for cname in d['contracts']:
        policies=sorted({r['policy'] for r in observations if r['contract']==cname})
        for p in policies:
            rr=[r for r in observations if r['contract']==cname and r['policy']==p]
            per_run={}
            for r in rr:per_run.setdefault((r['instance'],r['seed']),[]).append(r)
            summary.append(dict(contract=cname,policy=p,runs=len(per_run),
                final_physical_budget_pass=sum(all(v['max_q']<=1 for v in rows) for rows in per_run.values()),
                max_q=max(r['max_q'] for r in rr),violating_rows=sum(r['rows_over_budget'] for r in rr),
                near_limit_rows=sum(r['rows_near_limit'] for r in rr)))
    result=dict(status='passed',uniform_reserves_independently_computed=certificates,
        export_aware_physical_rows_certified=sum(r['rows_certified_by_actual_export_reserve'] for r in selection if r['policy']=='Export-Budget-L2'),
        legacy_numeric_envelope_mismatches=sum(r['numeric_envelope_factor_mismatches'] for r in selection),
        incompatible_models_at_1m3=sum(r['rounding_contract_incompatible_rows']>0 for r in incompatible),
        incompatible_rows_at_1m3=sum(r['rounding_contract_incompatible_rows'] for r in incompatible),
        incompatibility_is_not_model_infeasibility=True,observed_final_precision=summary,
        additional_optimizer_calls=0)
    (HERE/'PRECISION_RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
