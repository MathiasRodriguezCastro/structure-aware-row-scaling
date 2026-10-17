#!/usr/bin/env python3
"""Post-observation selective budgets with a separately frozen design."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import subprocess
import time
from build_lp import build,write
from rational_lp import verify,verify_ray
from sensitivity import HERE,ROOT,SOPLEX,load,dump,sha,parse,check_sources

F=Fraction.from_float


def prepare():
    d=check_sources();assert not (HERE/'selective-design.json').exists();queue=[]
    for task in load(HERE/'safe-design.json')['queue']:
        p=next(p for p in d['patterns'] if p['id']==task['pattern']);model=load(HERE/'inputs/models'/p['model']/'original-model.json')
        f=HERE/'characterization'/p['id']/'cost-0';lp=load(f/'model.json');dual=load(f/'dual.json');active_rows=set();active_bounds=set()
        for j,row in enumerate(lp['rows']):
            if Fraction(dual.get(str(j),'0')):
                if 'row' in row['source']:active_rows.add(row['source']['row'])
                if 'bound' in row['source']:active_bounds.add(row['source']['bound'])
        factor=Fraction(task['lambda'])
        for i,row in enumerate(model['rows']):
            if i in active_rows:
                q=F(float(row['budget']))*factor;row['budget']=float(q);assert F(row['budget'])==q
        for i,var in enumerate(model['variables']):
            if i in active_bounds:
                q=F(float(var['bound_budget']))*factor;var['bound_budget']=float(q);assert F(var['bound_budget'])==q
        folder=HERE/'selective'/p['id'];dump(folder/'budget-model.json',model)
        queue.append({'pattern':p['id'],'mode':'cost','lambda':'1','label':'selective-cost','factor':str(factor),
                      'v0':task['v0'],'epsilon':task['epsilon'],'active_rows':sorted(active_rows),'active_bound_variables':sorted(active_bounds),
                      'budget_model_sha256':sha(folder/'budget-model.json'),'v0_dual_sha256':sha(f/'dual.json')})
    dump(HERE/'selective-design.json',{'stage':'post-observation extension, frozen before selective LP calls','queue':queue,
                                     'parent_safe_design_sha256':sha(HERE/'safe-design.json'),
                                     'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__),HERE/'SELECTIVE_PROTOCOL.md')}})
    print('Frozen',len(queue),'selective budget LPs',flush=True)


def solve():
    d=check_sources();design=load(HERE/'selective-design.json');assert sha(HERE/'safe-design.json')==design['parent_safe_design_sha256']
    for name,h in design['source_hashes'].items():assert sha(ROOT/name)==h
    for task in design['queue']:
        folder=HERE/'selective'/task['pattern']
        if (folder/'result.json').exists():continue
        start=time.perf_counter();assert sha(folder/'budget-model.json')==task['budget_model_sha256'];model=load(folder/'budget-model.json')
        p=next(p for p in d['patterns'] if p['id']==task['pattern']);lp=build(model,p['integers'],'cost',Fraction(1))
        dump(folder/'model.json',lp);write(folder/'model.lp',lp)
        settings=folder/'exact.set';settings.write_text('int:syncmode = 1\nint:readmode = 1\nint:solvemode = 2\nint:checkmode = 2\nreal:feastol = 0\nreal:opttol = 0\nreal:timelimit = 2\n')
        command=[str(SOPLEX),'--loadset='+str(settings),'-X='+str(folder/'primal.txt'),'-Y='+str(folder/'dual.txt'),str(folder/'model.lp')]
        native=time.perf_counter()
        with (folder/'solver.log').open('w') as log:
            try:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=4.);code=r.returncode
            except subprocess.TimeoutExpired:code=None
        record={**task,'returncode':code,'solver_seconds':time.perf_counter()-native,'model_sha256':sha(folder/'model.json'),
                'lp_sha256':sha(folder/'model.lp'),'solver_binary_sha256':sha(SOPLEX),'outcome':'unverified'}
        begin=time.perf_counter();primal=parse(folder/'primal.txt','Primal solution (name, value):','x');dual=parse(folder/'dual.txt','Dual solution (name, value):','r')
        ray=parse(folder/'dual.txt','Dual ray (name, value):','r')
        if primal is not None and dual is not None:
            q=[primal.get(str(i),'0') for i in range(len(lp['cost']))];assert all(int(i)<len(q) for i in primal)
            dump(folder/'primal.json',q);dump(folder/'dual.json',dual);c=verify(lp,q,dual);dump(folder/'certificate.json',c)
            record['outcome']='optimum_certified' if c['optimum_certified'] else 'unverified'
        elif ray is not None:
            dump(folder/'ray.json',ray);c=verify_ray(lp,ray);dump(folder/'certificate.json',c)
            record['outcome']='infeasibility_certified' if c['infeasibility_certified'] else 'unverified'
        record.update(certificate_check_seconds=time.perf_counter()-begin,total_seconds=time.perf_counter()-start)
        dump(folder/'result.json',record);print(task['pattern'],record['outcome'],round(record['total_seconds'],3),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=('prepare','solve'));globals()[parser.parse_args().stage]()
