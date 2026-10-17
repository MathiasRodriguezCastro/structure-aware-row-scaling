#!/usr/bin/env python3
"""A fixed 2x2 mechanism follow-up, with export aliases declared before solves."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import joint
import solve as shared
import study as diagnostic

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(p):return json.loads(p.read_text())
def dump(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
POLICIES=['Row-contract','Row-uncontracted','Joint-contract','Joint-uncontracted']

def prepare():
    if (HERE/'ablation-design.json').exists():raise RuntimeError('ablation design exists')
    original=load(HERE/'solve-design.json');models={};canonical={};assignments=[];jobs=[]
    for instance in diagnostic.INSTANCES:
        for policy in POLICIES:
            model,base=diagnostic.model_for(instance,100)
            if policy.endswith('uncontracted'):model['delta']={};model['E']={}
            start=time.perf_counter();r=joint.minimize(model,policy.startswith('Joint'));assert r['feasible']
            u,v=joint.exponents(model,r);folder=HERE/'ablation'/policy/'solve-models'/instance;folder.mkdir(parents=True)
            path=folder/'Joint.lp';shared.export(model,u,v,path);dump(folder/'exponents.json',{'u':u,'v':v})
            record={'export':str(path.relative_to(ROOT)),'export_sha256':sha(path),'Base':str(base.relative_to(ROOT)),
                'Base_sha256':sha(base),'exponents_sha256':sha(folder/'exponents.json'),'selection_seconds':time.perf_counter()-start,'t':r['t']}
            key=instance+'/'+policy;h=record['export_sha256']
            if policy=='Joint-contract':assert h==original['models'][instance]['export_sha256'];record['borrowed_pilot']=True
            if (instance,h) in canonical:record['alias']=canonical[instance,h]
            else:canonical[instance,h]=key
            models[key]=record
    # Prefer the pre-existing pilot for its exact representation, irrespective
    # of enumeration order. Every alias is frozen before additional solves.
    for instance in diagnostic.INSTANCES:
        oldhash=original['models'][instance]['export_sha256']
        for policy in POLICIES:
            key=instance+'/'+policy
            if models[key]['export_sha256']==oldhash:
                if policy!='Joint-contract':models[key]['alias']=instance+'/Joint-contract'
                else:models[key].pop('alias',None)
    for policy in POLICIES:
        phase=HERE/'ablation'/policy
        ms={n:models[n+'/'+policy] for n in diagnostic.INSTANCES}
        phasejobs=[{'instance':n,'seed':s,'id':n+'-s'+str(s)} for n in diagnostic.INSTANCES for s in [59,71,89]]
        dump(phase/'solve-design.json',{'models':ms,'jobs':phasejobs,'parameters':original['parameters'],'dependencies':{},'known_model_pilot':True})
        dump(phase/'base-witness-index.json',load(HERE/'base-witness-index.json'))
        for j in phasejobs:
            m=ms[j['instance']];assignment={**j,'policy':policy,'key':j['instance']+'/'+policy}
            if m.get('borrowed_pilot') or 'alias' in m:assignment['native_call_required']=False
            else:assignment['native_call_required']=True;jobs.append(assignment)
            assignments.append(assignment)
    random.Random(2026101604).shuffle(jobs)
    deps=[Path(__file__),HERE/'joint.py',HERE/'solve.py',HERE/'study.py',HERE/'ABLATION_PROTOCOL.md',HERE/'solve-design.json',HERE/'solve-timings.json']
    dump(HERE/'ablation-design.json',{'assignments':assignments,'new_jobs':jobs,'models':models,
        'dependencies':{str(p.relative_to(ROOT)):sha(p) for p in deps},'borrowed_calls':18,
        'prior_joint_results_observed':True,'no_new_exact_LP_calls':True})
    print('Frozen',len(assignments),'arms;',len(jobs),'new MIP calls; 18 pilot calls reused',flush=True)

def worker(policy,job):
    shared.HERE=HERE/'ablation'/policy
    shared.worker(job)

def run():
    d=load(HERE/'ablation-design.json')
    for p,h in d['dependencies'].items():assert sha(ROOT/p)==h
    assert not (HERE/'ablation-timings.json').exists();records=[]
    for i,j in enumerate(d['new_jobs']):
        start=time.perf_counter()
        with (HERE/('ablation-'+j['policy']+'-'+j['id']+'.log')).open('w') as log:
            p=subprocess.run([sys.executable,str(Path(__file__)),'worker',j['policy'],j['id']],cwd=ROOT,
                env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'},stdout=log,stderr=subprocess.STDOUT,timeout=240)
        records.append({'job':j,'returncode':p.returncode,'process_seconds':time.perf_counter()-start});dump(HERE/'ablation-timings.json',records)
        assert p.returncode==0
        print(i+1,'/',len(d['new_jobs']),j['policy'],j['id'],round(records[-1]['process_seconds'],2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','run','worker']);p.add_argument('args',nargs='*');a=p.parse_args()
    if a.stage=='worker':worker(*a.args)
    else:globals()[a.stage]()
