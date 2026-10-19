#!/usr/bin/env python3
"""Frozen prospective scenarios; original generator and Budget-L2 unchanged."""
import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT/'exploration/oms-followup-20261014'),str(ROOT/'scripts/research'),str(ROOT/'scripts')]
F=Q.from_float
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_text())
def dump(p,d):
    p=Path(p);tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n');tmp.replace(p)
def library(p,name):
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def modules():
    import activation_study as a
    front=library(ROOT/'exploration/oms-frontier-20261016/study.py','frozen_frontier')
    return a,front

def generate(name,folder):
    from validar_preprocesamiento import clean_instance_text
    base=folder/'Base.lp'
    text=clean_instance_text(HERE/'models'/name/'input.txt')+'\nconfigurarSolver --DummyLp\npreprocesar --solodiagnostico\n'+f'grabar {base} --noConstante\nsalir\n'
    (folder/'generator-commands.txt').write_text(text)
    with (folder/'generator.log').open('w') as out:
        p=subprocess.run([str(ROOT/'code/build-audit/SistemaElectrico')],input=text,text=True,
            cwd=ROOT/'code',stdout=out,stderr=subprocess.STDOUT,timeout=60)
    assert p.returncode==0 and base.is_file()
    return base

def prepare():
    assert not (HERE/'design.json').exists(),'immutable design already exists'
    import gurobipy as gp
    assert gp.gurobi.version()==(13,0,2)
    a,front=modules();rng=random.Random(2026101811)
    parents=front.INSTANCES;models={};hashes=set()
    for hi,horizon in enumerate([24,72,168]):
        for k in range(8):
            name=f'new-h{horizon:03d}-{k+1:02d}';parent=parents[(8*hi+k)%6]
            source=ROOT/'exploration/oms-frontier-20261016/models'/parent/'input.txt'
            lines=source.read_text().splitlines();start=rng.randrange(361-horizon)
            positions={}
            for i,line in enumerate(lines):
                if line.startswith('inicializar '):lines[i]=f'inicializar --t {horizon}'
                if line.startswith('agregarAgente --SaltoGrande'):positions['inflow']=i+3
                if line.startswith('agregarAgente --DemandaFija'):positions['local']=i+1
                if line.startswith('crearDespacho --mercado'):positions['total']=i+4
            demand=[rng.uniform(.9,1.1) for _ in range(horizon)]
            inflow=[rng.uniform(.9,1.1) for _ in range(horizon)]
            for key,i in positions.items():
                values=list(map(float,lines[i].split()))[start:start+horizon]
                weights=inflow if key=='inflow' else demand
                lines[i]=' '.join(f'{v*w:.8f}' for v,w in zip(values,weights))
            folder=HERE/'models'/name;folder.mkdir(parents=True)
            (folder/'input.txt').write_text('\n'.join(lines)+'\n')
            assert not a.scan([folder/'input.txt'])['defective']
            base=generate(name,folder);parsed,physical=a.original_rows(base)
            _,lp,_=a.campaign.afb.read_lp(base)
            nint=sum(str(t)!='HighsVarType.kContinuous' for t in lp.integrality_)
            assert nint==4*horizon and len(parsed)==28*horizon and lp.num_col_==17*horizon
            assert sha(base) not in hashes;hashes.add(sha(base))
            info={}
            unscaled,plain=front.choose(parsed,lp,None)
            for key,budget in [('L2',None),('Budget-L2',100)]:
                factors,decisions=front.choose(parsed,lp,budget)
                ratios=[factors[n]/unscaled[n] for n in factors if factors[n]!=unscaled[n]]
                item=dict(**decisions,changed_from_L2=len(ratios),
                    max_factor_ratio_to_L2=max(ratios,default=1.),min_factor_ratio_to_L2=min(ratios,default=1.))
                dump(folder/(key+'-factors.json'),factors)
                if not decisions['incompatible_count']:
                    path=folder/(key+'.lp');a.export_scaled(base,path,factors);item['sha256']=sha(path)
                info[key]=item
            models[name]=dict(horizon=horizon,parent=parent,parent_input=str(source.relative_to(ROOT)),
                parent_input_sha256=sha(source),window_start=start,input_sha256=sha(folder/'input.txt'),
                base_sha256=sha(base),rows=len(parsed),columns=lp.num_col_,integer_columns=nint,
                physical_rows=len(physical),policies=info)
            print('Prepared',name,'changed',info['Budget-L2']['changed_from_L2'],flush=True)
    jobs=[dict(instance=n,seed=s,policy=p,id=f'{n}-s{s}-{p}') for n in models
        for s in [101,137,173] for p in ['Base','Base-tight','L2','L2-NF3','Budget-L2']]
    random.Random(2026101812).shuffle(jobs)
    deps=[Path(__file__),HERE/'PROTOCOL.md',ROOT/'exploration/oms-frontier-20261016/study.py',
        ROOT/'exploration/oms-followup-20261014/activation_study.py',ROOT/'scripts/research/budget_scaling.py',
        ROOT/'scripts/research/oms_dispatch_validation.py',ROOT/'exploration/oms-if1-workflow-20261015/study.py']
    dump(HERE/'design.json',dict(date='2026-10-18',models=models,jobs=jobs,parameters=dict(Threads=4,
        TimeLimit=120.,MIPGap=.01,Presolve=-1,FeasibilityTol=1e-6,IntFeasTol=1e-9,ScaleFlag=-1,
        IntegralityFocus=0,NumericFocus=0),dependencies={str(p.relative_to(ROOT)):sha(p) for p in deps},
        generator_binary_sha256=sha(ROOT/'code/build-audit/SistemaElectrico'),solver_version=list(gp.gurobi.version()),
        shared_machine=True,hostname=os.uname().nodename,external_family=False,previously_known_parents=True))
    print('Frozen 24 scenarios and',len(jobs),'assignments; no optimization calls',flush=True)

def worker(job_id,started):
    import numpy as np
    import gurobipy as gp
    a,front=modules();d=load(HERE/'design.json');job=next(j for j in d['jobs'] if j['id']==job_id)
    wf=library(ROOT/'exploration/oms-if1-workflow-20261015/study.py','native_import_check')
    folder=HERE/'runs'/job_id;folder.mkdir(parents=True);stages={}
    def timed(key,fn):
        t=time.perf_counter();v=fn();stages[key]=time.perf_counter()-t;return v
    meta=d['models'][job['instance']]
    base=timed('generation',lambda:generate(job['instance'],folder));assert sha(base)==meta['base_sha256']
    parsed,physical=timed('parse',lambda:a.original_rows(base))
    _,lp,_=timed('metadata',lambda:a.campaign.afb.read_lp(base))
    key='Base' if job['policy'].startswith('Base') else 'Budget-L2' if job['policy']=='Budget-L2' else 'L2'
    info={}
    if key!='Base':
        factors,info=timed('selection',lambda:front.choose(parsed,lp,100 if key=='Budget-L2' else None))
        if info['incompatible_count']:
            dump(folder/'result.json',dict(job=job,abstained=True,factor_info=info));return
        export=folder/'scaled.lp';timed('export',lambda:a.export_scaled(base,export,factors))
        assert sha(export)==meta['policies'][key]['sha256']
    else:export=base
    _,elp,ea=timed('export_metadata',lambda:a.campaign.afb.read_lp(export))
    params={**d['parameters'],'Seed':job['seed']}
    if job['policy']=='Base-tight':params['FeasibilityTol']=1e-9
    if job['policy']=='L2-NF3':params['NumericFocus']=3
    def native():
        env=gp.Env(params={'OutputFlag':0});m=gp.read(str(export),env=env)
        m.setParam('LogToConsole',0);m.setParam('LogFile',str(folder/'solver.log'))
        for k,v in params.items():m.setParam(k,v)
        return env,m
    env,m=timed('native_import',native)
    equality=timed('import_check',lambda:wf.check_import(m,elp,ea))
    timed('solve',m.optimize)
    outcome=dict(status=m.Status,solutions=m.SolCount,work=m.Work,nodes=m.NodeCount,
        runtime=m.Runtime,objective=m.ObjVal if m.SolCount else None,
        bound=m.ObjBound if math.isfinite(m.ObjBound) else None)
    checks={}
    if m.SolCount:
        values=dict(zip(lp.col_names_,[m.getVarByName(n).X for n in lp.col_names_]))
        np.savez_compressed(folder/'solution.npz',names=np.array(list(values)),x=np.array(list(values.values())))
        def check():
            ints={n for n,t in zip(lp.col_names_,lp.integrality_) if str(t)!='HighsVarType.kContinuous'}
            groups=a.audit_values(physical,values,ints)
            return dict(physical=groups,max_integer_violation=max(abs(values[n]-round(values[n])) for n in ints),
                point_objective_exact=str(sum((F(float(c))*F(values[n]) for n,c in zip(lp.col_names_,lp.col_cost_)),F(float(lp.offset_)))))
        checks=timed('verification',check)
    dump(folder/'result.json',dict(job=job,abstained=False,parameters=params,representation=key,
        base_sha256=sha(base),export_sha256=sha(export),native_import=equality,outcome=outcome,
        checks=checks,stages_seconds=stages,global_optimality_independently_verified=False))
    m.dispose();env.dispose()
    if export!=base:export.unlink()
    base.unlink() # Identical immutable exports are preserved once under models/.

def run():
    d=load(HERE/'design.json')
    for p,h in d['dependencies'].items():assert sha(ROOT/p)==h,p
    assert sha(ROOT/'code/build-audit/SistemaElectrico')==d['generator_binary_sha256']
    records=load(HERE/'timing.json') if (HERE/'timing.json').exists() else []
    assert all(r['returncode']==0 for r in records),'failure retained; amendment required'
    assert [r['job'] for r in records]==d['jobs'][:len(records)]
    for job in d['jobs'][len(records):]:
        assert not (HERE/'runs'/job['id']).exists(),'unrecorded attempt retained'
        t=time.perf_counter()
        with (HERE/(job['id']+'-execution.log')).open('w') as log:
            try:
                p=subprocess.run([sys.executable,str(Path(__file__)),'worker',job['id']],cwd=ROOT,
                    env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'},stdout=log,stderr=subprocess.STDOUT,timeout=240)
                rc=p.returncode
            except subprocess.TimeoutExpired:rc=124
        records.append(dict(job=job,returncode=rc,total_seconds=time.perf_counter()-t))
        dump(HERE/'timing.json',records)
        print(len(records),'/',len(d['jobs']),job['id'],'rc',rc,'seconds',round(records[-1]['total_seconds'],2),flush=True)
        if rc:raise RuntimeError('failed attempt retained')

if __name__=='__main__':
    started=time.perf_counter();ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['prepare','run','worker']);ap.add_argument('job',nargs='?');args=ap.parse_args()
    if args.stage=='worker':worker(args.job,started)
    else:globals()[args.stage]()
