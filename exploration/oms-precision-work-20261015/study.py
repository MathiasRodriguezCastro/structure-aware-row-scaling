#!/usr/bin/env python3
"""Fixed-target precision/work exploration. All timed MILP calls sequential."""
import argparse
from datetime import datetime,timezone
from fractions import Fraction as Q
import hashlib
import json
import math
from pathlib import Path
import random
import shutil
import time

import numpy as np
from common import SCENARIOS,GAMMA,sha,load,dump,choose,gcd_audit,canonical,build,ExactData,pow2,units
import exact_lp

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
OLD=ROOT/'exploration/oms-followup-20261014'
SOPLEX=OLD/'tools/soplex-build/bin/soplex'
INSTANCES=['instance001','instance022','instance046'];SEEDS=[401,409,419]
POLICIES=['Base','Tight','GM','Ruiz','L2','NumericFocus','GCD']+['Budget-'+s for s in SCENARIOS]
PARAMS=dict(Threads=4,TimeLimit=15.,WorkLimit=16.,MIPGap=.001,FeasibilityTol=1e-6,
            IntFeasTol=GAMMA,IntegralityFocus=1,Presolve=-1,ScaleFlag=-1)


def prepare():
    import gurobipy as gp
    if (HERE/'design.json').exists():raise RuntimeError('already frozen')
    protected={str(p):sha(p) for p in (ROOT/'paper/submission/oms/releases/v1.3.5-oms-submission').rglob('*') if p.is_file()}
    protected.update({str(p):sha(p) for p in (ROOT/'exploration').glob('*/*-artifact.zip')})
    dump(HERE/'protected-files.json',protected)
    (HERE/'inputs').mkdir(exist_ok=True)
    refs={};preparations={}
    with gp.Env(empty=True) as env:
        env.setParam('OutputFlag',0);env.start()
        for instance in INSTANCES:
            folder=HERE/'inputs'/instance;folder.mkdir(exist_ok=True)
            source=OLD/'confirmation-bank/models'/instance/'Base.lp';shutil.copyfile(source,folder/'Base.lp')
            m=gp.read(str(source),env=env);data=canonical(m);m.write(str(folder/'Base.mps'));m.dispose()
            m=gp.read(str(folder/'Base.mps'),env=env);assert canonical(m)==data;m.dispose()
            dump(folder/'canonical.json.gz',data)
            prep=dict(source=str(source.relative_to(ROOT)),source_sha256=sha(source),gcd=gcd_audit(data),policies={})
            for policy in POLICIES:
                t=time.perf_counter();ex,bad=choose(data,policy)
                prep['policies'][policy]=dict(exponents=ex,incompatible=bad,selection_seconds=time.perf_counter()-t)
                if bad:continue
                for r,k in zip(data['rows'],ex):
                    for a in [r['rhs']]+[a for _,a in r['terms']]:assert Q(math.ldexp(a,k))==Q(a)*pow2(k)
            witness=load(OLD/'exact-witnesses'/instance/'GM/exact-witness.json')
            pattern={str(j):str(Q(witness[v['name']])) for j,v in enumerate(data['variables']) if v['type']!='C'}
            reference=exact_lp.acquire(data,pattern,HERE/'references'/instance,SOPLEX,limit=15.)
            assert reference['outcome'] in ('optimum_certified','exact_primal_only'),reference
            u=Q(reference['objective_exact']);cap=u+Q(1,100)*max(Q(1),abs(u))
            refs[instance]=dict(objective_exact=str(u),objective_cap_exact=str(cap),source_pattern='archived GM witness; no Start',
                                acquisition_seconds=reference['total_seconds'],global_optimum_certified=False)
            dump(folder/'preparation.json',prep);preparations[instance]=prep
            print('Prepared',instance,'reference',float(u),'cap',float(cap),'GCD',prep['gcd'],
                  'changed',{s:sum(x!=y for x,y in zip(prep['policies']['L2']['exponents'],prep['policies']['Budget-'+s]['exponents'])) for s in SCENARIOS},flush=True)
    schedule=[dict(instance=i,policy=p,seed=s) for i in INSTANCES for p in POLICIES for s in SEEDS]
    random.Random(20261015).shuffle(schedule)
    for name in ('PROTOCOL.md','common.py','study.py','exact_lp.py'):
        shutil.copyfile(HERE/name,HERE/('snapshot-'+name))
    design=dict(frozen_utc=datetime.now(timezone.utc).isoformat(),instances=INSTANCES,policies=POLICIES,seeds=SEEDS,
                parameters=PARAMS,solver_version=gp.gurobi.version(),references=refs,schedule=schedule,
                sources={n:sha(HERE/n) for n in ('PROTOCOL.md','common.py','study.py','exact_lp.py')},
                posthoc_lp_limit=5.,reference_lp_limit=15.,quality_information='offline feasible aspiration, not optimum or a free algorithmic input',
                instances_are_known=True)
    dump(HERE/'design.json',design)


def run():
    import gurobipy as gp
    design=load(HERE/'design.json')
    for n,h in design['sources'].items():assert sha(HERE/n)==h,n
    folder=HERE/'runs';folder.mkdir(exist_ok=True);cache={}
    with gp.Env(empty=True) as env:
        env.setParam('OutputFlag',0);env.start()
        for order,job in enumerate(design['schedule']):
            name='{instance}-{policy}-s{seed}'.format(**job);out=folder/name
            out.mkdir(exist_ok=True)
            if (out/'run.json').exists():
                r=load(out/'run.json')
                if not r.get('alias_of') and r.get('cache_key'):cache[tuple(r['cache_key'])]=out
                continue
            data=load(HERE/'inputs'/job['instance']/'canonical.json.gz');frozen=load(HERE/'inputs'/job['instance']/'preparation.json')
            t=time.perf_counter();ex,bad=choose(data,job['policy']);selection=time.perf_counter()-t
            assert ex==frozen['policies'][job['policy']]['exponents'] and bad==frozen['policies'][job['policy']]['incompatible']
            params={**PARAMS,'Seed':job['seed']}
            if job['policy']=='Tight':params['FeasibilityTol']=1e-9
            if job['policy']=='NumericFocus':params['NumericFocus']=3
            ck=(job['instance'],hashlib.sha256(json.dumps(ex).encode()).hexdigest(),job['seed'],params['FeasibilityTol'],params.get('NumericFocus',0))
            if ck in cache:
                dump(out/'run.json',dict(job=job,alias_of=str(cache[ck].relative_to(HERE)),selection_seconds=selection,parameters=params))
                print(order+1,'Alias',name,flush=True);continue
            if bad:
                dump(out/'run.json',dict(job=job,alias_of=None,incompatible=bad,parameters=params));print(order+1,'Abstain',name,flush=True);continue
            t=time.perf_counter();m=build(data,ex,env);construction=time.perf_counter()-t
            for p,v in params.items():m.setParam(p,v)
            m.Params.LogFile=str(out/'solver.log');m.Params.OutputFlag=1;m.Params.LogToConsole=0
            points=[];events=[];capture_seconds=0.
            def cb(model,where):
                nonlocal capture_seconds
                if where==gp.GRB.Callback.MIPSOL:
                    t=time.perf_counter();work=model.cbGet(gp.GRB.Callback.WORK);runtime=model.cbGet(gp.GRB.Callback.RUNTIME)
                    point=np.asarray(model.cbGetSolution(model.getVars()),dtype=np.float64)
                    points.append(point);events.append(dict(kind='MIPSOL',work=work,runtime=runtime,reported_objective=model.cbGet(gp.GRB.Callback.MIPSOL_OBJ)))
                    capture_seconds+=time.perf_counter()-t
            start=time.perf_counter();m.optimize(cb);wall=time.perf_counter()-start
            if m.SolCount:
                points.append(np.asarray(m.getAttr('X'),dtype=np.float64))
                events.append(dict(kind='final',work=m.Work,runtime=m.Runtime,reported_objective=m.ObjVal))
            t=time.perf_counter()
            np.savez_compressed(out/'candidates.npz',x=np.stack(points) if points else np.empty((0,len(data['variables']))))
            persistence=time.perf_counter()-t
            record=dict(job=job,alias_of=None,cache_key=list(ck),parameters=params,status=m.Status,
                        work=m.Work,runtime=m.Runtime,optimizer_wall_seconds=wall,capture_seconds=capture_seconds,
                        selection_seconds=selection,construction_seconds=construction,persistence_seconds=persistence,
                        objective=m.ObjVal if m.SolCount else None,bound=m.ObjBound,
                        gap=m.MIPGap if m.SolCount else None,events=events)
            dump(out/'run.json',record);cache[ck]=out;m.dispose()
            print(order+1,'/',len(design['schedule']),name,'status',record['status'],'W',round(record['work'],4),'candidates',len(events),flush=True)


def evaluate():
    design=load(HERE/'design.json');cache={};outcomes=[];point_checks=[]
    for instance in INSTANCES:cache[instance]=ExactData(load(HERE/'inputs'/instance/'canonical.json.gz'))
    for out in sorted((HERE/'runs').iterdir()):
        record=load(out/'run.json');job=record['job']
        source=HERE/record['alias_of'] if record.get('alias_of') else out
        native=load(source/'run.json')
        if native.get('incompatible'):
            outcomes.append(dict(job=job,alias_of=record.get('alias_of'),incompatible=native['incompatible']));continue
        saved=source/'checks.json.gz'
        if not saved.exists():
            with np.load(source/'candidates.npz',allow_pickle=False) as f:points=f['x']
            checks=[]
            for point in points:
                t=time.perf_counter();check=cache[job['instance']].check(point)
                check['verification_seconds']=time.perf_counter()-t;checks.append(check)
            dump(saved,checks)
        else:checks=load(saved)
        cap=Q(design['references'][job['instance']]['objective_cap_exact'])
        first={};precision_only={}
        for i,(event,check) in enumerate(zip(native['events'],checks)):
            for j,s in enumerate(SCENARIOS):
                passed=check['auxiliary_pass'] and check['bounds_pass'] and Q(check['physical_ratios_exact'][j])<=1
                if passed and s not in precision_only:precision_only[s]=i
                if passed and Q(check['objective_exact'])<=cap and s not in first:first[s]=i
        outcomes.append(dict(job=job,alias_of=record.get('alias_of'),status=native['status'],final_work=native['work'],
                             candidate_count=len(checks),first_hit={s:dict(candidate=i,**native['events'][i],check=checks[i]) for s,i in first.items()},
                             precision_only_first={s:dict(candidate=i,**native['events'][i],check=checks[i]) for s,i in precision_only.items()},
                             selection_seconds=record.get('selection_seconds',native['selection_seconds']),construction_seconds=native['construction_seconds'],
                             optimizer_seconds=native['runtime'],verification_seconds=sum(c['verification_seconds'] for c in checks),
                             source=str(source.relative_to(HERE))))
        print('Evaluated',out.name,'hits',list(first),flush=True)
    dump(HERE/'outcomes.json',outcomes)


def certify():
    design=load(HERE/'design.json');outcomes=load(HERE/'outcomes.json');queue={};assignments=[]
    for outcome in outcomes:
        if not outcome.get('first_hit'):continue
        job=outcome['job'];data=load(HERE/'inputs'/job['instance']/'canonical.json.gz')
        with np.load(HERE/outcome['source']/'candidates.npz',allow_pickle=False) as f:points=f['x']
        for scenario,hit in outcome['first_hit'].items():
            point=points[hit['candidate']]
            pattern={str(j):str(round(float(point[j]))) for j,v in enumerate(data['variables']) if v['type']!='C'}
            h=hashlib.sha256(json.dumps(pattern,sort_keys=True).encode()).hexdigest()
            key=job['instance']+'/'+h[:20];queue.setdefault(key,dict(instance=job['instance'],pattern=pattern))
            assignments.append(dict(job=job,scenario=scenario,candidate=hit['candidate'],pattern_key=key,
                                    nominal_cost_exact=hit['check']['objective_exact']))
    dump(HERE/'posthoc-design.json',dict(frozen_utc=datetime.now(timezone.utc).isoformat(),queue=queue,assignments=assignments,
                                        role='posthoc validation, no extra MILP and no credit in native work frontier'))
    for key,task in sorted(queue.items()):
        out=HERE/'certificates'/key
        if not (out/'result.json').exists():
            data=load(HERE/'inputs'/task['instance']/'canonical.json.gz')
            result=exact_lp.acquire(data,task['pattern'],out,SOPLEX,limit=5.)
            print('Certified',key,result['outcome'],round(result['total_seconds'],3),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run','evaluate','certify']);args=p.parse_args()
    globals()[args.action]()
