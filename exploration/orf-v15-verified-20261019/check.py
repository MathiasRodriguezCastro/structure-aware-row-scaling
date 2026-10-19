#!/usr/bin/env python3
"""License-free independent saved-candidate replay; never calls an optimizer."""
import csv
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

import numpy as np

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PARENT=ROOT/'exploration/orf-confirmatory-20261018'
sys.path[:0]=[str(ROOT/'scripts/research'),str(ROOT/'scripts')]
spec=importlib.util.spec_from_file_location('saved_parent_checker',PARENT/'check.py')
parent=importlib.util.module_from_spec(spec);sys.modules[spec.name]=parent;spec.loader.exec_module(parent)
F=Q.from_float
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(path,rows):
    with path.open('w',newline='') as out:
        w=csv.DictWriter(out,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def assess(model,point,contract):
    rows,bounds,costs,ints,scope,offset=model
    rounded={n:Q(round(v)) if n in ints else v for n,v in point.items()}
    maximum={'activation':Q(0),'water':Q(0),'power':Q(0)};nonphysical=Q(0)
    for n,r in rows.items():
        violations=[]
        for x in [point,rounded]:
            activity=sum((v*x[j] for j,v in r['terms'].items()),Q(0))-r['rhs']
            violations.append(abs(activity) if r['sense']=='=' else max(Q(0),activity if r['sense']=='<=' else -activity))
        v=max(violations)
        if n in scope:
            group,unit,conversion=scope[n]
            k='power' if unit=='MW' else 'activation' if group=='Volume-dependent activation' else 'water'
            maximum[k]=max(maximum[k],v/conversion)
        else:
            scale=max(Q(1),abs(r['rhs']),sum((abs(v*rounded[j]) for j,v in r['terms'].items()),Q(0)))
            nonphysical=max(nonphysical,v/scale)
    integer_error=max((abs(point[n]-rounded[n]) for n in ints),default=Q(0))
    bound_error=max([Q(0)]+[lo-rounded[n] for n,(lo,hi) in bounds.items() if lo is not None]+
                    [rounded[n]-hi for n,(lo,hi) in bounds.items() if hi is not None])
    objective=offset+sum((v*rounded[n] for n,v in costs.items()),Q(0))
    return dict(physical_pass=all(maximum[k]<=F(contract[k]) for k in maximum),
        domain_pass=bound_error==0 and integer_error<=F(1e-9),other_rows_pass=nonphysical<=F(1e-6),
        maximum_physical_violation={k:str(v) for k,v in maximum.items()},max_integrality=str(integer_error),
        max_bound_violation=str(bound_error),max_other_backward_error=str(nonphysical),objective_exact=str(objective))


def main():
    d=load(HERE/'design.json');timing=load(HERE/'timing.json');amend=load(HERE/'AMENDMENT_01.json')
    assert len(timing)==len(d['jobs'])==630 and [r['job'] for r in timing]==d['jobs']
    assert all(r['returncode']==0 for r in timing)
    assert sha(HERE/'design.json')==amend['original_design_sha256']
    assert sha(HERE/'original-study.py')==amend['original_runner_sha256']
    assert sha(HERE/'original-timing.json')==amend['original_timing_sha256']
    for n,h in d['dependencies'].items():
        expected=amend['corrected_runner_sha256'] if n==str((HERE/'study.py').relative_to(ROOT)) else h
        assert sha(ROOT/n)==expected,n
    assert amend['failed_before_optimization']==1 and amend['additional_MIP_calls']==0
    original=load(HERE/'original-timing.json');assert original[1]['returncode']!=0
    assert not (HERE/'failed-before-optimization'/original[1]['job']['id']/'solver.log').exists()
    models={n:parent.canonical(PARENT/'models'/n/'Base.lp') for n in d['models']}
    rows=[];events_count=0;full_audits=0;retained_hashes={}
    for count,t in enumerate(timing,1):
        j=t['job'];folder=HERE/'runs'/j['id'];r=load(folder/'result.json');assert r['job']==j
        retained_hashes[j['id']]=sha(folder/'result.json')
        if r['abstained']:
            rows.append(dict(id=j['id'],instance=j['instance'],experiment=j['experiment'],solver=j['solver'],
                scale=j['scale'],policy=j['policy'],contract=j['contract'],seed=j['seed'],abstained=True,
                events=0,hit001=False,hit01=False,bound_contradiction='',native_completed=False))
            continue
        model=models[j['instance']];ref=Q(d['references'][j['instance']+'/Base'])
        assert Q(r['reference_exact'])==ref and r['native_import']['matrix_rhs_objective_bounds_integer_domains_equal']
        with np.load(folder/'candidates.npz') as z:
            assert list(z['names'])==list(model[1]);points=z['x']
        assert len(points)==len(r['events']) and points.shape[1]==len(model[1])
        first={str(t):None for t in d['thresholds']};previous=-1.
        for i,(x,event) in enumerate(zip(points,r['events'])):
            assert np.isfinite(x).all() and event['process_discovery']>=previous
            previous=event['process_discovery'];point=dict(zip(model[1],map(lambda v:F(float(v)),x)))
            ints=model[3]
            objective=model[5]+sum((c*(Q(round(point[n])) if n in ints else point[n]) for n,c in model[2].items()),Q(0))
            assert Q(event['audit']['objective_exact'])==objective
            admissible=objective<=ref+F(max(d['thresholds']))*max(Q(1),abs(ref))
            if admissible or event['kind']=='final' or not event['audit'].get('quality_rejected_before_residual_checks'):
                audited=assess(model,point,d['contracts'][j['contract']]);full_audits+=1
                for key,value in audited.items():assert event['audit'][key]==value,(j['id'],i,key)
                passed=all(audited[k] for k in ['physical_pass','domain_pass','other_rows_pass'])
            else:passed=False
            for tau in d['thresholds']:
                if passed and objective<=ref+F(tau)*max(Q(1),abs(ref)) and first[str(tau)] is None:
                    first[str(tau)]=i
            events_count+=1
        for tau,index in first.items():
            recorded=r['first_qualified'][tau]
            assert (recorded is None)==(index is None),(j['id'],tau)
            if index is not None:
                event=r['events'][index];assert recorded['index']==index
                for key in ['solver_discovery','process_discovery','work']:assert recorded[key]==event[key]
                assert recorded['offline_verified_available']>=r['solver_finished_process_seconds']>=event['process_discovery']
        if r['known_native_export_witness']:
            rep='L2' if j['policy']=='L2-NF3' else j['policy']
            h=d['models'][j['instance']]['base_sha256'] if rep=='Base' else d['models'][j['instance']]['policies'][rep]['sha256']
            assert h==r['export_sha256']
            bound=r['outcome']['bound'];U=Q(d['references'][j['instance']+'/'+rep])
            contradiction=bound is not None and F(bound)>U+F(max(1e-6,8*math.ulp(bound)))
            assert contradiction==r['bound_contradiction']
        else:assert r['bound_contradiction'] is None
        rows.append(dict(id=j['id'],instance=j['instance'],experiment=j['experiment'],solver=j['solver'],
            scale=j['scale'],policy=j['policy'],contract=j['contract'],seed=j['seed'],abstained=False,
            events=len(points),hit001=first['0.001'] is not None,hit01=first['0.01'] is not None,
            bound_contradiction=r['bound_contradiction'],native_completed=r['outcome']['completed']))
        if count%50==0:print('Replayed',count,'/',len(timing),'assignments',flush=True)
    write(HERE/'verified-runs.csv',rows)
    technical=load(HERE/'TECHNICAL_REPEAT.json');jid=technical['job_id']
    original=load(HERE/'runs'/jid/'result.json')
    repeated=load(HERE/'technical-repeat/runs'/jid/'result.json')
    with np.load(HERE/'runs'/jid/'candidates.npz') as a,np.load(HERE/'technical-repeat/runs'/jid/'candidates.npz') as b:
        same=np.array_equal(a['x'],b['x']) and np.array_equal(a['names'],b['names'])
    endpoints=all(original['outcome'][k]==repeated['outcome'][k] for k in ['status','solutions','work','objective','bound','nodes'])
    first=all((original['first_qualified'][str(t)] or {}).get('index')==(repeated['first_qualified'][str(t)] or {}).get('index') for t in [.001,.01])
    assert technical['same_candidate_vectors']==same and technical['same_non_timing_endpoints']==endpoints
    assert technical['standardized_timing_replacement_permitted']==(same and endpoints and first)
    result=dict(status='passed',research_MIP_assignments=630,failed_worker_before_optimizer=1,
        candidate_events=events_count,full_rational_candidate_audits=full_audits,
        source_design_sha256=sha(HERE/'design.json'),additional_optimizer_calls=0,
        inherited_reference_validation_sha256=sha(PARENT/'VALIDATION.json'),
        technical_repeat_independently_compared=True,additional_technical_MIP_calls=1,
        primary_results_sha256=retained_hashes,all_candidates_retained=True)
    (HERE/'VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Passed:',events_count,'candidate events;',full_audits,'complete rational audits',flush=True)


if __name__=='__main__':main()
