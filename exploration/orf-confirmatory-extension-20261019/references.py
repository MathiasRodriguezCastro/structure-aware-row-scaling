#!/usr/bin/env python3
"""Common Base acquisition followed by an exact, independently checked LP repair."""
import argparse
import json
from pathlib import Path
import sys
import time
import numpy as np
from runner import HERE,ROOT,load,save,sha,library,native,witness_feasible


def acquire(index):
    plan=load(HERE/'PILOT_PLAN.json');item=plan['blocks'][index];name=item['instance']
    for n,h in plan['dependencies'].items():assert sha(ROOT/n)==h,'Frozen dependency changed: '+n
    folder=HERE/'reference-acquisition'/name;folder.mkdir(parents=True,exist_ok=False)
    follow=library(ROOT/'exploration/orf-v15-verified-20261019/study.py','reference_frozen_helpers')
    a,_=follow.old.modules();base=HERE/'models'/name/'Base.lp'
    metadata=load(HERE/'MODEL_PREPARATION.json')['models'][name]
    assert sha(base)==metadata['base_sha256']
    _,lp,matrix=a.campaign.afb.read_lp(base);rows,_=follow.checker.parse(base)
    started=time.perf_counter();job=dict(policy='Base',solver='gurobi',seed=389,time_limit=120.)
    result=dict(instance=name,procedure='Base gap 0.001, 120 seconds; fixed-pattern exact LP repair',
        acquisition_cost_separate=True,reference_is_certified_optimum=False)
    try:
        outcome,points,events,parameters,imported,errors=native(base,folder,job,started,lp,rows,follow,matrix)
        np.savez_compressed(folder/'candidates.npz',names=np.array(lp.col_names_),
            x=np.array(points,dtype=float).reshape(-1,len(lp.col_names_)))
        save(folder/'native-result.json',dict(outcome=outcome,parameters=parameters,native_import=imported,
            events=events,callback_errors=errors,optimization_calls=1))
        if not points:
            result.update(status='unknown_no_incumbent');return
        # Common rule uses the final Base candidate, never a preferred scaled policy.
        solution=folder/'solution.npz';np.savez_compressed(solution,names=np.array(lp.col_names_),x=np.array(points[-1]))
        exact=library(ROOT/'exploration/oms-followup-20261014/exact_dispatch_witness.py','new_reference_repair')
        out=HERE/'references'/name;assert not out.exists()
        exact.prepare(out,base,solution)
        exact.solve(out,ROOT/'exploration/oms-followup-20261014/tools/soplex-build/bin/soplex')
        exact.check(out)
        from fractions import Fraction as Q
        point={n:Q(v) for n,v in load(out/'exact-witness.json').items()}
        assert witness_feasible(follow.checker.canonical(base),point)
        result.update(status='verified_feasible',objective_exact=load(out/'independent-certificate.json')['objective_exact_fraction'])
    except Exception as e:
        result.update(status='unknown_retained_failure',error=type(e).__name__+': '+str(e))
    finally:
        result['total_seconds']=time.perf_counter()-started
        save(folder/'result.json',result)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('index',type=int);args=ap.parse_args();acquire(args.index)
