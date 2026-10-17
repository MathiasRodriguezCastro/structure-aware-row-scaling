#!/usr/bin/env python3
"""Finite paired feedback experiment with matched restarts and strong controls."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import shutil
import time
import traceback
import numpy as np
from infra import (HERE,ROOT,OBJECTIVE,PILOT,ARITH,TARGET,F,load,dump,sha,point,save,native,audit,proof,arithmetic)
from cuts import project,export
from verify_cuts import check as check_cut


def prepare():
    assert not (HERE/'design.json').exists();t=time.perf_counter();source=OBJECTIVE/'inputs/models/neos-3083784-nive'
    folder=HERE/'inputs';folder.mkdir(exist_ok=True)
    for name in ('original-model.json','neos-3083784-nive.mps.gz'):shutil.copy2(source/name,folder/name)
    factors=ROOT/'exploration/oms-transfer-study-20261014/confirmation/models/neos-3083784-nive/factors.json';shutil.copy2(factors,folder/'factors.json')
    jobs=[{'solver':solver,'seed':seed,'kind':kind} for solver in ('gurobi','highs') for seed in (109,127,149)
          for kind in ('L2-direct','Base-direct','Base-tight','prefix')]
    branches=[{'solver':solver,'seed':seed,'kind':kind} for solver in ('gurobi','highs') for seed in (109,127,149)
              for kind in ('B-restart','C-aggregate','C-guard')]
    rng=np.random.default_rng(20261014);jobs=[jobs[i] for i in rng.permutation(len(jobs))];branches=[branches[i] for i in rng.permutation(len(branches))]
    sources=[HERE/name for name in ('run_feedback.py','infra.py','cuts.py','PROTOCOL.md','verify_cuts.py')]
    sources += [OBJECTIVE/'build_lp.py',OBJECTIVE/'rational_lp.py',ARITH/'independent_check.py',PILOT/'generalization_study.py',ROOT/'scripts/research/budget_scaling.py']
    d={'stage':'fixed before any new MIP optimization','seeds':[109,127,149],'solvers':['gurobi','highs'],'strategy_results':42,
       'initial_jobs':jobs,'branch_jobs':branches,'maximum_native_mip_calls':60,'mip_budget_seconds':30.,'phase_budget_seconds':10.,
       'cycle_reference_seconds':45.,'target_exact':str(TARGET),'reference_cost':27851,
       'shared_preparation_seconds':time.perf_counter()-t,'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in sources},
       'input_hashes':{str(p.relative_to(HERE)):sha(p) for p in folder.iterdir() if p.is_file()},
       'preflight_verification_sha256':sha(HERE/'preflight-verification.json'),
       'scope':'one previously selected numerical model; exact-certificate feedback; no global optimality or novelty claim'}
    dump(HERE/'design.json',d)
    for p in sources[:5]:shutil.copy2(p,HERE/('snapshot-'+p.name))
    print('Frozen 42 strategy results, at most 60 new native MIP calls',flush=True)


def checked_design():
    d=load(HERE/'design.json')
    for path,h in d['source_hashes'].items():assert sha(ROOT/path)==h,path
    for path,h in d['input_hashes'].items():assert sha(HERE/path)==h,path
    return d


def phase(model,factors,solver,seed,tight,folder,limit,deadline,cache,start=None,exported=None):
    began=time.perf_counter();extended=json.loads(json.dumps(model));alphas=list(factors)
    for c in exported or []:
        e=c['export'];extended['rows'].append({'name':'feedback-'+c['exact']['signature'],'terms':e['terms'],'sense':'>','rhs':e['rhs'],
                                              'budget':float(Fraction(e['alpha_exact'])*Fraction(e['unscaled_residual_budget'])),'unit':'exported cut units'})
        alphas.append(1.)
    dump(folder/'active-cuts.json',exported or [])
    n,x=native(extended,alphas,solver,tight,folder,seed,limit,deadline,start)
    if x is not None:save(folder/'source-point.npz',x)
    result={'native':n,'has_source':x is not None,'active_cuts':len(exported or []),'native_elapsed_seconds':time.perf_counter()-began}
    a=audit(model,x,folder/'audit',cache,deadline);pf,p=proof(folder/'audit')
    result.update(audit_path=str((folder/'audit').relative_to(HERE)),audit=a,proof_path=str(pf.relative_to(HERE)),proof_outcome=p['outcome'],
                  exact_upper=p.get('exact_upper'),float_deliverable=p.get('float_deliverable',False),target_met=p.get('target_met',False),
                  total_seconds=time.perf_counter()-began)
    dump(folder/'phase.json',result);return result


def witness(p):
    if p.get('float_deliverable') and p.get('exact_upper') is not None:return Fraction(p['exact_upper']),p['proof_path']
    return None


def better(old,new):
    value=witness(new)
    return value if value is not None and (old is None or value[0]<old[0]) else old


def initial():
    d=checked_design();model=load(HERE/'inputs/original-model.json');factors=load(HERE/'inputs/factors.json')
    for job in d['initial_jobs']:
        label=f"{job['solver']}-s{job['seed']}-{job['kind']}";folder=HERE/'initial'/label
        if (folder/'result.json').exists():continue
        folder.mkdir(parents=True,exist_ok=True);began=time.perf_counter();cache={};result={**job,'label':label}
        try:
            policy='Dyadic-L2' if job['kind'] in ('prefix','L2-direct') else 'Base'
            p=phase(model,factors[policy],job['solver'],job['seed'],job['kind']=='Base-tight',folder/'phase-0',
                    10. if job['kind']=='prefix' else 30.,began+45.,cache)
            result.update(phases=[str((folder/'phase-0/phase.json').relative_to(HERE))],cache=cache,exact_upper=p.get('exact_upper'),
                          best_proof_path=p['proof_path'] if witness(p) else None,target_met=p['target_met'])
        except Exception as e:result.update(error_type=type(e).__name__,error=str(e),traceback=traceback.format_exc())
        result['total_seconds']=time.perf_counter()-began;dump(folder/'result.json',result)
        print(label,'U',result.get('exact_upper'),'target',result.get('target_met'),'seconds',round(result['total_seconds'],3),'error',result.get('error'),flush=True)


def learn(model,p,kind,folder):
    before=time.perf_counter();pf,a=proof(HERE/p['audit_path'])
    if not (pf/'model.json').exists():return {'generated':False,'reason':'no_dual_or_ray','total_seconds':time.perf_counter()-before}
    lp=load(pf/'model.json');cert=load(pf/'certificate.json') if (pf/'certificate.json').exists() else {}
    if cert.get('dual_feasible'):
        multipliers=load(pf/'dual.json');proof_kind='cost'
    elif cert.get('infeasibility_certified'):
        multipliers={i:str(Fraction(v)*cert['orientation']) for i,v in load(pf/'ray.json').items()};proof_kind='ray'
    else:return {'generated':False,'reason':'no_valid_dual_or_ray','total_seconds':time.perf_counter()-before}
    z=load(pf/'pattern.json');aggregate,guard=project(model,lp,multipliers,proof_kind,z)
    exact=aggregate if kind=='C-aggregate' else guard;exported=export(model,exact)
    verification=check_cut(model,lp,z,multipliers,proof_kind,exact,exported)
    result={'generated':True,'proof_path':str(pf.relative_to(HERE)),'proof_kind':proof_kind,'exact':exact,'export':exported,
            'verification':verification,'total_seconds':time.perf_counter()-before};dump(folder/'learned-cut.json',result);return result


def branches():
    d=checked_design();model=load(HERE/'inputs/original-model.json');factors=load(HERE/'inputs/factors.json')['Dyadic-L2']
    for job in d['branch_jobs']:
        label=f"{job['solver']}-s{job['seed']}-{job['kind']}";folder=HERE/'branches'/label
        if (folder/'result.json').exists():continue
        folder.mkdir(parents=True,exist_ok=True);prefixfolder=HERE/'initial'/f"{job['solver']}-s{job['seed']}-prefix"
        prefix=load(prefixfolder/'result.json');began=time.perf_counter();result={**job,'label':label,'shared_prefix':str((prefixfolder/'result.json').relative_to(HERE)),
                                                                                 'prefix_seconds':prefix['total_seconds']}
        try:
            assert 'error' not in prefix;cache=dict(prefix['cache']);phases=list(prefix['phases']);last=load(HERE/phases[-1]);best=better(None,last)
            cuts=[];learned=[];deadline=began+max(0.,45.-prefix['total_seconds']);source_pattern_cache_hits=0
            for iteration in (1,2):
                if best is not None and best[0]<=TARGET:break
                if time.perf_counter()+.2>=deadline:break
                if job['kind'].startswith('C-'):
                    learnfolder=folder/f'learn-{iteration}';learnfolder.mkdir(exist_ok=True);new=learn(model,last,job['kind'],learnfolder);learned.append(new)
                    if new['generated'] and new['export']['exported'] and all(c['exact']['signature']!=new['exact']['signature'] for c in cuts):cuts.append(new)
                start=point(HERE/best[1]/'witness-float.npz') if best is not None else None
                last=phase(model,factors,job['solver'],job['seed'],False,folder/f'phase-{iteration}',10.,deadline,cache,start,cuts)
                phases.append(str((folder/f'phase-{iteration}/phase.json').relative_to(HERE)));best=better(best,last)
                source_pattern_cache_hits+=last['audit'].get('cache_hit',False)
            result.update(phases=phases,learned=learned,applied_distinct_cuts=len(cuts),cache=cache,
                          exact_upper=str(best[0]) if best is not None else None,best_proof_path=best[1] if best else None,
                          target_met=best is not None and best[0]<=TARGET,cache_hits_after_prefix=source_pattern_cache_hits)
        except Exception as e:result.update(error_type=type(e).__name__,error=str(e),traceback=traceback.format_exc())
        result.update(branch_seconds=time.perf_counter()-began,total_seconds=prefix['total_seconds']+time.perf_counter()-began)
        dump(folder/'result.json',result)
        print(label,'U',result.get('exact_upper'),'target',result.get('target_met'),'cuts',result.get('applied_distinct_cuts'),
              'seconds',round(result['total_seconds'],3),'error',result.get('error'),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=('prepare','initial','branches'));globals()[parser.parse_args().stage]()
