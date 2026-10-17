#!/usr/bin/env python3
"""Bounded common-incumbent intervention on frozen, known row scalings."""
import argparse
from datetime import datetime,timezone
from fractions import Fraction as Q
import hashlib
import json
import math
from pathlib import Path
import random
import time
import numpy as np
from common import load,dump,sha,build,exact_feasibility,ExactData,pow2
import exact_lp

HERE=Path(__file__).resolve().parent


def freeze(name,names):
    hs={n:sha(HERE/n) for n in names};p=HERE/name
    if p.exists():assert load(p)==hs
    else:
        dump(p,hs)
        for n in names:(HERE/('snapshot-'+n)).write_bytes((HERE/n).read_bytes())


def prepare():
    d=load(HERE/'design.json')
    for n,h in d['inputs'].items():assert sha(HERE/n)==h
    assert sha(HERE/'PROTOCOL.md')==d['protocol_sha256']
    freeze('sources-before-reference.json',['study.py','common.py','exact_lp.py','PROTOCOL.md'])
    refs={};binary=(HERE/d['soplex_relative_path']).resolve()
    for name in d['instances']:
        inp=HERE/'inputs'/name;data=load(inp/'canonical.json.gz');parent=load(inp/'Algebraic-archived.json.gz')
        pattern={str(j):str(round(parent['point'][j])) for j,v in enumerate(data['variables']) if v['type']!='C'}
        result=exact_lp.acquire(data,pattern,HERE/'references'/name,binary,15.)
        refs[name]=result
        if result.get('exact_feasible'):
            point=load(HERE/'references'/name/'rational-point.json');floating=[float(Q(q)) for q in point]
            dump(HERE/'references'/name/'start.json',floating)
            prep=load(inp/'preparation.json');checks={}
            for policy in ['Base','GM']:
                ex=prep['policy_exponents']['Base' if policy=='Base' else 'Algebraic']
                checks[policy]=start_check(data,floating,ex)
            dump(HERE/'references'/name/'start-check.json',checks)
        print(name,'reference',result['outcome'],'cost',result.get('objective'),flush=True)
    schedule=[dict(instance=n,policy=p,start=s,seed=k) for n in d['instances'] if refs[n].get('exact_feasible')
              for p in d['policies'] for s in d['starts'] for k in d['seeds']]
    random.Random(20261015).shuffle(schedule)
    dump(HERE/'run-design.json',dict(frozen_utc=datetime.now(timezone.utc).isoformat(),references=refs,schedule=schedule,
        inputs={str(p.relative_to(HERE)):sha(p) for p in sorted((HERE/'references').rglob('*')) if p.is_file()}))


def start_check(data,point,ex):
    xs=list(map(Q,point));raw=Q(0);scaled=Q(0);bounds=Q(0)
    for r,k in zip(data['rows'],ex):
        v=sum(Q(a)*xs[j] for j,a in r['terms'])-Q(r['rhs'])
        v=abs(v) if r['sense']=='=' else max(Q(0),v if r['sense']=='<' else -v)
        raw=max(raw,v);scaled=max(scaled,v*pow2(k))
    for v,x in zip(data['variables'],xs):
        if v['lb'] is not None:bounds=max(bounds,Q(v['lb'])-x)
        if v['ub'] is not None:bounds=max(bounds,x-Q(v['ub']))
    cost=Q(data['constant'])+sum(Q(v['obj'])*x for v,x in zip(data['variables'],xs))
    return dict(max_raw_residual_exact=str(raw),max_exported_residual_exact=str(scaled),
        max_bound_residual_exact=str(bounds),objective_exact=str(cost),
        integers_exact=all(v['type']=='C' or x.denominator==1 for v,x in zip(data['variables'],xs)))


def run():
    import gurobipy as gp
    d=load(HERE/'design.json');rd=load(HERE/'run-design.json')
    for n,h in load(HERE/'sources-before-reference.json').items():assert sha(HERE/n)==h
    for n,h in rd['inputs'].items():assert sha(HERE/n)==h
    freeze('sources-before-mip.json',['study.py','common.py','exact_lp.py','PROTOCOL.md'])
    with gp.Env(empty=True) as env:
        env.setParam('OutputFlag',0);env.start()
        for j,job in enumerate(rd['schedule']):
            out=HERE/'runs'/('{instance}-{policy}-{start}-s{seed}'.format(**job));out.mkdir(parents=True,exist_ok=True)
            if (out/'run.json').exists():continue
            inp=HERE/'inputs'/job['instance'];data=load(inp/'canonical.json.gz');prep=load(inp/'preparation.json')
            ex=prep['policy_exponents']['Base' if job['policy']=='Base' else 'Algebraic']
            for r,k in zip(data['rows'],ex):
                for z in [r['rhs']]+[a for _,a in r['terms']]:assert Q(math.ldexp(z,k))==Q(z)*pow2(k)
            t=time.perf_counter();m=build(data,ex,env);construction=time.perf_counter()-t
            params={**d['parameters'],'Seed':job['seed']}
            for p,v in params.items():m.setParam(p,v)
            m.Params.LogFile=str(out/'solver.log');m.Params.OutputFlag=1;m.Params.LogToConsole=0
            variables=m.getVars()
            if job['start']=='CommonStart':m.setAttr('Start',variables,load(HERE/'references'/job['instance']/'start.json'))
            points=[];events=[];progress=[];last=[None,None];capture=0.
            def cb(model,where):
                nonlocal capture
                if where==gp.GRB.Callback.MIPSOL:
                    t=time.perf_counter();points.append(np.array(model.cbGetSolution(variables)))
                    events.append(dict(kind='MIPSOL',work=model.cbGet(gp.GRB.Callback.WORK),
                        runtime=model.cbGet(gp.GRB.Callback.RUNTIME),nodes=model.cbGet(gp.GRB.Callback.MIPSOL_NODCNT),
                        reported_objective=model.cbGet(gp.GRB.Callback.MIPSOL_OBJ)))
                    capture+=time.perf_counter()-t
                if where==gp.GRB.Callback.MIP:
                    u=model.cbGet(gp.GRB.Callback.MIP_OBJBST);b=model.cbGet(gp.GRB.Callback.MIP_OBJBND)
                    if [u,b]!=last:
                        progress.append(dict(work=model.cbGet(gp.GRB.Callback.WORK),runtime=model.cbGet(gp.GRB.Callback.RUNTIME),
                            nodes=model.cbGet(gp.GRB.Callback.MIP_NODCNT),incumbent=u if abs(u)<1e99 else None,
                            bound=b if abs(b)<1e99 else None));last[:]=[u,b]
            t=time.perf_counter();m.optimize(cb);elapsed=time.perf_counter()-t
            if m.SolCount:
                points.append(np.array(m.getAttr('X')));events.append(dict(kind='final',work=m.Work,runtime=m.Runtime,nodes=m.NodeCount,reported_objective=m.ObjVal))
            np.savez_compressed(out/'candidates.npz',x=np.stack(points) if points else np.empty((0,len(variables))))
            result=dict(job=job,parameters=params,status=m.Status,work=m.Work,runtime=m.Runtime,wall_seconds=elapsed,
                construction_seconds=construction,capture_seconds=capture,nodes=m.NodeCount,iterations=m.IterCount,
                objective=m.ObjVal if m.SolCount else None,bound=m.ObjBound,gap=m.MIPGap if m.SolCount else None,
                events=events,progress=progress,solver_version=list(gp.gurobi.version()))
            dump(out/'run.json',result);m.dispose()
            print(j+1,'/',len(rd['schedule']),out.name,'status',result['status'],'work',round(result['work'],4),'U',result['objective'],flush=True)


def certify():
    d=load(HERE/'design.json');rd=load(HERE/'run-design.json');queue={};assignments={}
    for job in rd['schedule']:
        key='{instance}-{policy}-{start}-s{seed}'.format(**job);out=HERE/'runs'/key;r=load(out/'run.json')
        if not r['events']:continue
        data=load(HERE/'inputs'/job['instance']/'canonical.json.gz');x=np.load(out/'candidates.npz')['x'][-1]
        pattern={str(j):str(round(float(x[j]))) for j,v in enumerate(data['variables']) if v['type']!='C'}
        h=hashlib.sha256(json.dumps(pattern,sort_keys=True).encode()).hexdigest()[:20];k=job['instance']+'/'+h
        queue[k]=pattern;assignments[key]=k
    target=HERE/'posthoc-design.json';plan=dict(queue=queue,assignments=assignments,limit=5.)
    if target.exists():assert load(target)==plan
    else:dump(target,plan)
    for k,pattern in queue.items():
        out=HERE/'certificates'/k
        if (out/'result.json').exists():continue
        data=load(HERE/'inputs'/k.split('/')[0]/'canonical.json.gz')
        r=exact_lp.acquire(data,pattern,out,(HERE/d['soplex_relative_path']).resolve(),5.)
        print('Certificate',k,r['outcome'],flush=True)


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('action',choices=['prepare','run','certify']);args=a.parse_args()
    {'prepare':prepare,'run':run,'certify':certify}[args.action]()
