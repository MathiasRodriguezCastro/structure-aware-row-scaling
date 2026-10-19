#!/usr/bin/env python3
"""All-run target-attainment summaries with paired whole-scenario uncertainty."""
import argparse
import json
import math
from pathlib import Path
import statistics

import numpy as np

HERE=Path(__file__).resolve().parent


def load(p):return json.loads(p.read_text())
def gm(x):return math.exp(statistics.mean(math.log(v) for v in x)) if x else None
def dump(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')


def score(r,tau,metric):
    first=r['first_qualified'][str(tau)]
    return first[metric] if first else 60.+r['solve_started_process_seconds']


def scope(records,label,seed):
    policies=sorted({r['job']['policy'] for r in records});names=sorted({r['job']['instance'] for r in records})
    lookup={(r['job']['instance'],r['job']['seed'],r['job']['policy']):r for r in records}
    assert len(records)==len(policies)*len(names)*3
    summary=[]
    for policy in policies:
        rr=[r for r in records if r['job']['policy']==policy]
        final=[r['events'][-1]['audit'] if r['events'] else {} for r in rr]
        summary.append(dict(policy=policy,runs=len(rr),candidate_events=sum(len(r['events']) for r in rr),
            targets={str(t):sum(r['first_qualified'][str(t)] is not None for r in rr) for t in [.001,.01]},
            final_physical_pass=sum(a.get('physical_pass',False) for a in final),
            final_domain_pass=sum(a.get('domain_pass',False) for a in final),
            final_other_rows_pass=sum(a.get('other_rows_pass',False) for a in final),
            detected_bound_contradictions=sum(r['bound_contradiction'] is True for r in rr),
            unknown_native_bound_contrasts=sum(r['bound_contradiction'] is None for r in rr),
            native_completed=sum(r['outcome']['completed'] for r in rr),
            median_callback_seconds=statistics.median(r['callback_seconds'] for r in rr),
            median_verification_seconds=statistics.median(r['stages_seconds']['verification'] for r in rr)))
    rng=np.random.Generator(np.random.PCG64(seed));draws=rng.integers(0,len(names),size=(100000,len(names)))
    comparisons=[]
    for control in policies:
        if control=='Budget-L2':continue
        for tau in [.001,.01]:
            common=[];cluster=[];wins=[]
            for n in names:
                logs=[]
                for s in [211,257,293]:
                    b=lookup[n,s,'Budget-L2'];c=lookup[n,s,control]
                    logs.append([math.log(score(b,tau,k)/score(c,tau,k)) for k in
                        ['process_discovery','offline_verified_available']])
                    if b['first_qualified'][str(tau)] is not None and c['first_qualified'][str(tau)] is not None:
                        common.append((b,c))
                cluster.append(np.mean(logs,axis=0))
            v=np.array(cluster);boot=v[draws].mean(axis=1)
            r=dict(control=control,tau=tau,scenarios=len(names),seed_pairs=len(names)*3,
                common_success_pairs=len(common),all_pairs_retained_in_penalized_scores=True)
            for k,key in enumerate(['process_discovery','offline_verified_available']):
                lo,hi=np.exp(np.quantile(boot[:,k],[.025,.975],method='linear'))
                r[key]=dict(PAR2_paired_geometric_ratio=float(np.exp(v[:,k].mean())),
                    lower95=float(lo),upper95=float(hi),scenarios_favor_budget=int(np.sum(v[:,k]<-1e-12)),
                    common_success_geometric_ratio=gm([b['first_qualified'][str(tau)][key]/
                        c['first_qualified'][str(tau)][key] for b,c in common]))
            r['common_success_work_ratio']=gm([b['first_qualified'][str(tau)]['work']/c['first_qualified'][str(tau)]['work']
                for b,c in common if b['first_qualified'][str(tau)]['work']>0 and c['first_qualified'][str(tau)]['work']>0])
            comparisons.append(r)
    return dict(scope=label,scenarios=len(names),seeds_per_scenario=3,policy_results=summary,comparisons=comparisons,
        bootstrap=dict(resamples=100000,seed=seed,unit='scenario; all three paired seeds retained',
            intervals='marginal percentile 95%, log scale',conditional_on_known_parent_structure=True),
        failed_target_penalty='60 seconds plus process preparation; score, not observed completion time',
        point_quality_reference_is_not_global_optimum=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--experiment-i-only',action='store_true');args=ap.parse_args()
    d=load(HERE/'design.json');rr=[]
    for j in d['jobs']:
        p=HERE/'runs'/j['id']/'result.json'
        if args.experiment_i_only and j['experiment']!='I':continue
        assert p.exists(),j['id'];r=load(p)
        repeat=HERE/'TECHNICAL_REPEAT.json'
        if repeat.exists():
            technical=load(repeat)
            if technical['standardized_timing_replacement_permitted'] and technical['job_id']==j['id']:
                r=load(HERE/'technical-repeat/runs'/j['id']/'result.json')
        if not r['abstained']:rr.append(r)
    first=scope([r for r in rr if r['job']['experiment']=='I'],'I: Gurobi automatic scaling, reference budgets',2026101906)
    dump(HERE/'EXPERIMENT_I.json',first)
    print('I:',json.dumps(first['policy_results'],indent=2),flush=True)
    if args.experiment_i_only:return
    result={'experiment_I':first}
    result['technical_repeat']=load(HERE/'TECHNICAL_REPEAT.json')
    result['CPLEX']=scope([r for r in rr if r['job']['experiment']=='III-cplex'],'III: CPLEX default scaling, traditional search',2026101908)
    result['Gurobi_internal_scaling']={}
    names={r['job']['instance'] for r in rr if r['job']['experiment']=='III-scale'}
    for scale in [-1,0,2]:
        cells=[r for r in rr if r['job']['instance'] in names and r['job']['scale']==scale and r['job']['policy'] in ['Base','L2','Budget-L2']
            and r['job']['solver']=='gurobi' and r['job']['contract']=='b100']
        result['Gurobi_internal_scaling'][str(scale)]=scope(cells,f'III: Gurobi ScaleFlag={scale}',2026101910+scale)
    dump(HERE/'COMPUTATIONAL_RESULTS.json',result)
    print('All computational scopes summarized.',flush=True)


if __name__=='__main__':main()
