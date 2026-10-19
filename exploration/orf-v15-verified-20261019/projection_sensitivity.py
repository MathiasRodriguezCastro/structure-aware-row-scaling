#!/usr/bin/env python3
"""Explicitly post hoc exact-box projection; discovery times, not online latency."""
from fractions import Fraction as Q
import json
from pathlib import Path
import statistics
import sys

import numpy as np

HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import check as independent
F=Q.from_float


def main():
    d=independent.load(HERE/'design.json');models={};records=[];repairs=0;largest=Q(0)
    for j in d['jobs']:
        if j['experiment']=='II':continue
        r=independent.load(HERE/'runs'/j['id']/'result.json');name=j['instance']
        if name not in models:models[name]=independent.parent.canonical(independent.PARENT/'models'/name/'Base.lp')
        model=models[name];ref=Q(d['references'][name+'/Base']);bounds=model[1];ints=model[3]
        names=list(bounds);indices={n:i for i,n in enumerate(names)};integer_ids=[indices[n] for n in ints]
        lower=np.array([float(lo) if lo is not None else -np.inf for lo,hi in bounds.values()])
        upper=np.array([float(hi) if hi is not None else np.inf for lo,hi in bounds.values()])
        cost_entries=[(indices[n],c) for n,c in model[2].items() if c]
        with np.load(HERE/'runs'/j['id']/'candidates.npz') as z:points=z['x']
        first={str(t):None for t in [.001,.01]};delta_max=Q(0)
        for i,(event,x) in enumerate(zip(r['events'],points)):
            old=event['audit']
            rounded=x.copy();rounded[integer_ids]=np.rint(rounded[integer_ids])
            if np.max(np.abs(rounded[integer_ids]-x[integer_ids]),initial=0)>1e-9:continue
            clipped=np.minimum(np.maximum(rounded,lower),upper)
            change=F(float(np.max(np.abs(clipped-rounded),initial=0)))
            delta_max=max(delta_max,change);largest=max(largest,change)
            cost=model[5]+sum((c*F(float(clipped[j])) for j,c in cost_entries),Q(0))
            # Test the transformed objective, including candidates originally
            # rejected on objective: projection can change their cost.
            if cost>ref+F(.01)*max(Q(1),abs(ref)):continue
            if change==0 and all(old.get(k,False) for k in ['domain_pass','physical_pass','other_rows_pass']):
                audit=old;assert Q(old['objective_exact'])==cost
            else:
                point=dict(zip(bounds,map(lambda v:F(float(v)),clipped)))
                audit=independent.assess(model,point,d['contracts']['b100'])
                repairs+=change>0
            if all(audit[k] for k in ['physical_pass','domain_pass','other_rows_pass']):
                cost=Q(audit['objective_exact'])
                for t in [.001,.01]:
                    if cost<=ref+F(t)*max(Q(1),abs(ref)) and first[str(t)] is None:
                        first[str(t)]=dict(event=i,process_discovery=event['process_discovery'],
                            maximum_bound_projection=str(change),objective_exact=str(cost))
        records.append(dict(job=j,targets=first,maximum_bound_projection=str(delta_max)))
    groups={}
    for r in records:
        j=r['job'];label='I' if j['experiment']=='I' else 'CPLEX' if j['solver']=='cplex' else f"ScaleFlag={j['scale']}"
        groups.setdefault((label,j['policy']),[]).append(r)
    summary=[]
    for (label,policy),rr in groups.items():
        summary.append(dict(scope=label,policy=policy,runs=len(rr),
            targets={str(t):sum(r['targets'][str(t)] is not None for r in rr) for t in [.001,.01]},
            largest_bound_projection=float(max(Q(r['maximum_bound_projection']) for r in rr))))
    out=dict(analysis='post_hoc_exact_bound_projection_sensitivity',registered_after_observing_tiny_CPLEX_bound_errors=True,
        additional_optimizer_calls=0,primary_criterion_preserved=True,maximum_continuous_bound_projection=float(largest),
        candidate_projections_rechecked=repairs,online_verification_time_claimed=False,policy_results=summary,records=records)
    (HERE/'PROJECTION_SENSITIVITY.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
