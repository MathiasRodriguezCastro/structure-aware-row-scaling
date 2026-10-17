#!/usr/bin/env python3
"""Frozen retrospective LP experiments; never calls a MIP optimizer."""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

import numpy as np
from build_lp import build,write
from rational_lp import verify,verify_ray

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PREVIOUS=ROOT/'exploration/oms-transfer-study-20261014'
SOPLEX=ROOT/'exploration/oms-followup-20261014/tools/soplex-build/bin/soplex'
GRID=(Fraction(0),*(Fraction(1,2**k) for k in (30,26,22,18,14,10,6)),Fraction(1))


def load(p):return json.loads(Path(p).read_text())
def dump(p,v):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def prepare():
    assert not (HERE/'design.json').exists();before=time.perf_counter()
    old=load(PREVIOUS/'confirmation/design.json');models={};patterns={};records=[]
    for m in old['models']:
        source=PREVIOUS/'confirmation/models'/m['name']/'original-model.json'
        assert sha(source)==m['model_sha256'];folder=HERE/'inputs/models'/m['name'];folder.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,folder/'original-model.json');models[m['name']]=load(source)
        raw=PREVIOUS/'sources/miplib-models'/(m['name']+'.mps.gz');shutil.copy2(raw,folder/raw.name)
    for i,t in enumerate(old['queue']):
        folder=PREVIOUS/'confirmation/runs'/t['model']/f"{t['arm']}-s{t['seed']}";r=load(folder/'run.json')
        record={**t,'order':i,'delivered':r['delivered'],'known_reference':r['known_reference'],
                'original_total_seconds':r['total_seconds'],'source_run_sha256':sha(folder/'run.json')}
        saved=HERE/'inputs/runs'/f'r{i:03d}';saved.mkdir(parents=True,exist_ok=True);shutil.copy2(folder/'run.json',saved/'run.json')
        if r['delivered']:
            with np.load(folder/'delivered-point.npz',allow_pickle=False) as z:x=z['x']
            integers={str(j):int(x[j]) for j,v in enumerate(models[t['model']]['variables']) if v['integer']}
            assert all(float(x[int(j)])==v for j,v in integers.items())
            digest=hashlib.sha256(json.dumps(integers,sort_keys=True).encode()).hexdigest()
            key=t['model']+'/'+digest[:16];patterns.setdefault(key,{'id':key,'model':t['model'],'integers':integers,'members':[]})['members'].append(i)
            shutil.copy2(folder/'delivered-point.npz',saved/'point.npz')
            record.update(pattern=key,point_sha256=sha(saved/'point.npz'))
        records.append(record)
    queue=[]
    for p in sorted(patterns.values(),key=lambda p:p['id']):
        grid=GRID if p['model']=='neos-3083784-nive' else (Fraction(0),Fraction(1))
        for lam in grid:queue.append({'pattern':p['id'],'mode':'cost','lambda':str(lam),'label':'cost-'+str(lam).replace('/','_')})
        if p['model']=='neos-3083784-nive':queue.append({'pattern':p['id'],'mode':'feasibility-threshold','lambda':'0','label':'feasibility-threshold'})
    sources={str(p.relative_to(ROOT)):sha(p) for p in (HERE/'sensitivity.py',HERE/'build_lp.py',HERE/'rational_lp.py',HERE/'PROTOCOL.md')}
    inputs={str(p.relative_to(HERE)):sha(p) for p in (HERE/'inputs').rglob('*') if p.is_file()}
    design={'stage':'post-observation sensitivity study; frozen before LP calls','records':records,'patterns':list(sorted(patterns.values(),key=lambda p:p['id'])),
            'queue':queue,'source_hashes':sources,'input_hashes':inputs,'prior_validation_sha256':sha(PREVIOUS/'VALIDATION.json'),
            'lp_limit_seconds':2.,'watchdog_seconds':4.,'shared_preparation_seconds':time.perf_counter()-before,
            'global_mip_certification':False}
    assert len(records)==80 and len(patterns)==41 and len(queue)==178
    dump(HERE/'design.json',design);shutil.copy2(Path(__file__),HERE/'source-snapshot.py')
    print('Frozen 178 LP tasks for 41 unique patterns from 72 deliveries / 80 treatments',flush=True)


def check_sources():
    d=load(HERE/'design.json')
    for name,h in d['source_hashes'].items():assert sha(ROOT/name)==h,name
    for name,h in d['input_hashes'].items():assert sha(HERE/name)==h,name
    return d


def parse(path,header,prefix):
    if not path.exists():return None
    result={};active=False;found=False
    for line in path.read_text().splitlines():
        if header in line:active=found=True;continue
        if active and (line.startswith('All other') or 'Reduced costs' in line):break
        t=line.split()
        if active and len(t)==2 and t[0].startswith(prefix) and t[0][len(prefix):].isdigit():result[str(int(t[0][len(prefix):]))]=str(Fraction(t[1]))
    return result if found else None


def solve_task(d,task,stage):
    folder=HERE/stage/task['pattern']/task['label']
    if (folder/'result.json').exists():return
    start=time.perf_counter();p=next(p for p in d['patterns'] if p['id']==task['pattern']);m=load(HERE/'inputs/models'/p['model']/'original-model.json')
    lp=build(m,p['integers'],task['mode'],Fraction(task['lambda']),Fraction(task['target']) if 'target' in task else None)
    dump(folder/'model.json',lp);write(folder/'model.lp',lp)
    settings=folder/'exact.set';settings.write_text('int:syncmode = 1\nint:readmode = 1\nint:solvemode = 2\nint:checkmode = 2\nreal:feastol = 0\nreal:opttol = 0\nreal:timelimit = 2\n')
    command=[str(SOPLEX),'--loadset='+str(settings),'-X='+str(folder/'primal.txt'),'-Y='+str(folder/'dual.txt'),str(folder/'model.lp')]
    solver_start=time.perf_counter()
    with (folder/'solver.log').open('w') as f:
        try:r=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,timeout=4.);returncode=r.returncode
        except subprocess.TimeoutExpired:returncode=None
    solver_seconds=time.perf_counter()-solver_start
    record={**task,'returncode':returncode,'solver_seconds':solver_seconds,'model_sha256':sha(folder/'model.json'),
            'lp_sha256':sha(folder/'model.lp'),'solver_binary_sha256':sha(SOPLEX),'outcome':'unverified'}
    parse_start=time.perf_counter()
    primal=parse(folder/'primal.txt','Primal solution (name, value):','x')
    dual=parse(folder/'dual.txt','Dual solution (name, value):','r')
    ray=parse(folder/'dual.txt','Dual ray (name, value):','r')
    if primal is not None and dual is not None:
        q=[primal.get(str(i),'0') for i in range(len(lp['cost']))];assert all(int(i)<len(q) for i in primal)
        dump(folder/'primal.json',q);dump(folder/'dual.json',dual);cert=verify(lp,q,dual);dump(folder/'certificate.json',cert)
        record['outcome']='optimum_certified' if cert['optimum_certified'] else 'primal_only' if cert['primal_feasible'] else 'unverified'
    elif ray is not None:
        dump(folder/'ray.json',ray);cert=verify_ray(lp,ray);dump(folder/'certificate.json',cert)
        record['outcome']='infeasibility_certified' if cert['infeasibility_certified'] else 'unverified'
    record.update(certificate_check_seconds=time.perf_counter()-parse_start,total_seconds=time.perf_counter()-start)
    dump(folder/'result.json',record)
    print(stage,p['model'],task['label'],record['outcome'],round(record['total_seconds'],3),flush=True)


def characterize():
    d=check_sources()
    for t in d['queue']:solve_task(d,t,'characterization')


def strict_dyadic_below(value):
    value=Fraction(value);assert value>0
    q=Fraction(1)
    while q>=value:q/=2
    return q


def adaptive_prepare():
    d=check_sources();assert not (HERE/'adaptive-design.json').exists();queue=[];skipped=[]
    for p in d['patterns']:
        if p['model']!='neos-3083784-nive':continue
        f=HERE/'characterization'/p['id']/'cost-0';r=load(f/'result.json')
        if r['outcome']!='optimum_certified':skipped.append({'pattern':p['id'],'reason':r['outcome']});continue
        v=Fraction(load(f/'certificate.json')['primal_value_exact']);eps=max(Fraction.from_float(1e-6),abs(v)/100)
        target=-((-((v-eps)*2**40).numerator)//((v-eps)*2**40).denominator)*Fraction(1,2**40)
        assert v-eps<=target<v
        queue.append({'pattern':p['id'],'mode':'cost-threshold','lambda':'0','label':'cost-threshold','target':str(target),
                      'v0':str(v),'epsilon':str(eps),'v0_certificate_sha256':sha(f/'certificate.json')})
    dump(HERE/'adaptive-design.json',{'stage':'conditional design after characterization; thresholds fixed before their LP calls','queue':queue,'skipped':skipped,
                                     'parent_design_sha256':sha(HERE/'design.json')})
    print('Frozen',len(queue),'cost-threshold LPs; skipped',len(skipped),flush=True)


def adaptive():
    d=check_sources();a=load(HERE/'adaptive-design.json');assert sha(HERE/'design.json')==a['parent_design_sha256']
    for t in a['queue']:solve_task(d,t,'adaptive')


def safe_prepare():
    check_sources();assert not (HERE/'safe-design.json').exists();a=load(HERE/'adaptive-design.json');queue=[];skipped=[]
    for t in a['queue']:
        folder=HERE/'adaptive'/t['pattern']/t['label'];r=load(folder/'result.json');c=load(folder/'certificate.json') if (folder/'certificate.json').exists() else {}
        if r['outcome']=='optimum_certified':
            threshold=Fraction(c['primal_value_exact']);assert threshold>0;factor=strict_dyadic_below(threshold)
        elif r['outcome']=='infeasibility_certified':threshold=None;factor=Fraction(1)
        else:skipped.append({'pattern':t['pattern'],'reason':r['outcome']});continue
        queue.append({'pattern':t['pattern'],'mode':'cost','lambda':str(factor),'label':'safe-cost','target':t['target'],
                      'v0':t['v0'],'epsilon':t['epsilon'],'cost_threshold':str(threshold) if threshold is not None else None,
                      'threshold_certificate_sha256':sha(folder/'certificate.json')})
    dump(HERE/'safe-design.json',{'stage':'dyadic safe factors fixed from threshold certificates before validation LPs','queue':queue,'skipped':skipped,
                                'parent_design_sha256':sha(HERE/'adaptive-design.json')})
    print('Frozen',len(queue),'safe-factor LP checks',flush=True)


def safe():
    d=check_sources();a=load(HERE/'safe-design.json');assert sha(HERE/'adaptive-design.json')==a['parent_design_sha256']
    for t in a['queue']:solve_task(d,t,'safe')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=('prepare','characterize','adaptive_prepare','adaptive','safe_prepare','safe'))
    globals()[parser.parse_args().stage]()
