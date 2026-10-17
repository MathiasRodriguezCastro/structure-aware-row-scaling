#!/usr/bin/env python3
"""Compare complete fresh preparation processes on the same isolated binary."""
import argparse
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'scripts/research'),str(ROOT/'exploration/oms-followup-20261014')]
INSTANCES=['instance001','instance005','instance022','instance027','instance031','instance046']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def load(p):return json.loads(p.read_text())
def frontier():
    spec=importlib.util.spec_from_file_location('frontier_source',ROOT/'exploration/oms-frontier-20261016/study.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def worker(instance,policy,backend,folder):
    from validar_preprocesamiento import clean_instance_text
    folder.mkdir(parents=True);export=folder/'scaled.lp';base=folder/'Base.lp'
    source=ROOT/'exploration/oms-matched-accuracy-20261016/inputs'/instance/'input.txt'
    env={**os.environ}
    env.pop('OMS_NATIVE_POLICY',None);env.pop('OMS_NATIVE_FACTORS',None)
    if backend=='cpp':env.update(OMS_NATIVE_POLICY=policy,OMS_NATIVE_FACTORS=str(folder/'factors.csv'))
    destination=export if backend=='cpp' else base
    commands=clean_instance_text(source)+'\nconfigurarSolver --DummyLp\npreprocesar --solodiagnostico\n'+f'grabar {destination} --noConstante\nsalir\n'
    (folder/'commands.txt').write_text(commands)
    start=time.perf_counter()
    with (folder/'generator.log').open('w') as log:
        p=subprocess.run([str(HERE/'source/build/SistemaElectrico')],cwd=ROOT/'code',input=commands,text=True,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=60)
    generator=time.perf_counter()-start;assert p.returncode==0 and destination.is_file()
    t={};factors=None
    if backend=='python':
        # Includes module startup and all metadata reconstruction in full parent time.
        a=frontier();start=time.perf_counter()
        parsed,_=a.library(ROOT/'exploration/oms-followup-20261014/activation_study.py','native_benchmark_activation').original_rows(base)
        import activation_study as act
        _,lp,_=act.campaign.afb.read_lp(base);t['parse_seconds']=time.perf_counter()-start
        start=time.perf_counter();factors,info=a.choose(parsed,lp,100 if policy=='Budget-L2' else None);t['select_seconds']=time.perf_counter()-start
        assert not info['incompatible_count'];start=time.perf_counter();act.export_scaled(base,export,factors);t['export_seconds']=time.perf_counter()-start
        with (folder/'factors.csv').open('w',newline='') as out:
            w=csv.writer(out);w.writerow(['row','factor']);w.writerows(factors.items())
    dump(folder/'result.json',{'instance':instance,'policy':policy,'backend':backend,'generator_seconds':generator,
        'stages':t,'export_sha256':sha(export)})

def compare(instance,policy,cpp,python):
    # Equality against the prespecified Python mathematical reference, beyond formatting.
    from audit_identifiability_grid import parse
    from audit_fixed_basis import read_lp
    import numpy as np
    a,_=parse(cpp);b,_=parse(python)
    assert list(a)==list(b)
    diffs=[]
    for n,r in a.items():
        assert r['sense']==b[n]['sense'] and set(r['terms'])==set(b[n]['terms'])
        for j,v in r['terms'].items():
            if float(v)!=float(b[n]['terms'][j]):diffs.append((n,j,float(v),float(b[n]['terms'][j])))
        if float(r['rhs'])!=float(b[n]['rhs']):diffs.append((n,'RHS',float(r['rhs']),float(b[n]['rhs'])))
    _,x,_=read_lp(cpp);_,y,_=read_lp(python)
    assert set(x.col_names_)==set(y.col_names_)
    xm={n:(c,l,h,str(k)) for n,c,l,h,k in zip(x.col_names_,x.col_cost_,x.col_lower_,x.col_upper_,x.integrality_)}
    ym={n:(c,l,h,str(k)) for n,c,l,h,k in zip(y.col_names_,y.col_cost_,y.col_lower_,y.col_upper_,y.integrality_)}
    assert xm==ym and x.offset_==y.offset_
    return {'instance':instance,'policy':policy,'row_data_differences':len(diffs),'sample_differences':diffs[:5],
        'objective_bounds_domains_equal':True,'bitwise_model_equal':not diffs}

def prepare():
    if (HERE/'design.json').exists():raise RuntimeError('design exists')
    records=[]
    for n in INSTANCES:
        for p in ['L2','Budget-L2']:
            for b in ['python','cpp']:worker(n,p,b,HERE/'preflight'/n/p/b)
            records.append(compare(n,p,HERE/'preflight'/n/p/'cpp/scaled.lp',HERE/'preflight'/n/p/'python/scaled.lp'))
            print(n,p,records[-1]['bitwise_model_equal'],records[-1]['row_data_differences'],flush=True)
    dump(HERE/'preflight.json',records)
    jobs=[{'instance':n,'policy':p,'backend':b,'repeat':r,'id':n+'-'+p+'-'+b+'-'+str(r)} for n in INSTANCES for p in ['L2','Budget-L2'] for b in ['python','cpp'] for r in range(7)]
    random.Random(2026101602).shuffle(jobs)
    deps={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),HERE/'NativeContracts.h',HERE/'PROTOCOL.md',HERE/'prepare_build.py',HERE/'source/build/SistemaElectrico',ROOT/'exploration/oms-frontier-20261016/study.py']}
    dump(HERE/'design.json',{'jobs':jobs,'dependencies':deps,'preflight_all_bitwise_equal':all(r['bitwise_model_equal'] for r in records),
        'parameters':{'power_MW':.01,'water_m3':100.,'gamma':1e-9},'compiler':'g++ 11.4.0 -O2 -DNDEBUG, no fast-math',
        'native_policy_disabled_in_python_arm':True,'timing_scope':'whole fresh Python preparation process including all imports, generator, metadata, selection, export, factor recording and result persistence; excludes experiment equality checker'})

def run():
    d=load(HERE/'design.json')
    for p,h in d['dependencies'].items():assert sha(ROOT/p)==h
    assert not (HERE/'timings.json').exists()
    records=[]
    for i,j in enumerate(d['jobs']):
        start=time.perf_counter();folder=HERE/'runs'/j['id']
        with (HERE/(j['id']+'-execution.log')).open('w') as log:
            p=subprocess.run([sys.executable,str(Path(__file__)),'worker',j['instance'],j['policy'],j['backend'],str(folder)],
                cwd=ROOT,env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'},stdout=log,stderr=subprocess.STDOUT,timeout=120)
        record={**j,'returncode':p.returncode,'total_seconds':time.perf_counter()-start};records.append(record);dump(HERE/'timings.json',records)
        assert p.returncode==0
        print(i+1,'/168',j['id'],round(record['total_seconds'],3),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','run','worker']);p.add_argument('args',nargs='*');a=p.parse_args()
    if a.stage=='worker':worker(*a.args[:3],Path(a.args[3]))
    else:globals()[a.stage]()
