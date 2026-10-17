#!/usr/bin/env python3
"""Posthoc 16-pattern cost audit, with rational primal/dual replay."""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import numpy as np
from cost_certificate import verify

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PREVIOUS=ROOT/'exploration/oms-decision-study-20261014'


def load(p):return json.loads(Path(p).read_text())
def dump(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def point(p):
    with np.load(p,allow_pickle=False) as z:return list(z['x'])


def parse(path,header,prefix):
    values={};active=False;found=False
    if not path.exists():return None
    for line in path.read_text().splitlines():
        if header in line:active=found=True;continue
        if active and (line.startswith('All other') or 'Reduced costs' in line):break
        t=line.split()
        if active and len(t)==2 and t[0].startswith(prefix) and t[0][len(prefix):].isdigit():
            values[t[0][len(prefix):]]=str(Fraction(t[1]))
    return values if found else None


def prepare():
    out=HERE/'cost-audit';assert not (out/'design.json').exists();out.mkdir(exist_ok=True)
    folder=HERE/'confirmation/models/neos-3083784-nive';model=load(folder/'original-model.json')
    d=load(HERE/'confirmation/design.json');queue=[]
    for task in d['queue']:
        if task['model']!='neos-3083784-nive':continue
        run=HERE/'confirmation/runs'/task['model']/f"{task['arm']}-s{task['seed']}"
        record=load(run/'run.json')
        queue.append({**task,'source_path':str(run.relative_to(HERE)),'delivered':record['delivered'],
                      'delivered_sha256':sha(run/'delivered-point.npz') if record['delivered'] else None})
    assert len(queue)==16
    design={'stage':'post-observation cost audit; no new MILP and not a prospective treatment endpoint',
            'assigned_patterns':16,'queue':queue,'model_sha256':sha(folder/'original-model.json'),
            'lp_limit_seconds':2.,'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in
              (Path(__file__),HERE/'cost_certificate.py',HERE/'COST_AUDIT_PROTOCOL.md',PREVIOUS/'repair.py')}}
    dump(out/'design.json',design);shutil.copy2(Path(__file__),out/'source-snapshot.py')
    print('Frozen all 16 nive delivery patterns before additional LP calls',flush=True)


def solve():
    sys.path.insert(0,str(PREVIOUS));from repair import fixed_subproblem,write_fixed_lp,SOPLEX
    out=HERE/'cost-audit';design=load(out/'design.json')
    for path,digest in design['source_hashes'].items():assert sha(ROOT/path)==digest
    modelpath=HERE/'confirmation/models/neos-3083784-nive/original-model.json';assert sha(modelpath)==design['model_sha256']
    model=load(modelpath)
    for task in design['queue']:
        folder=out/'runs'/f"{task['arm']}-s{task['seed']}"
        if (folder/'result.json').exists():continue
        folder.mkdir(parents=True,exist_ok=True);began=time.perf_counter()
        result={**task,'primal_dual_certificate':False}
        if not task['delivered']:
            result.update(outcome='no_original_delivery',total_seconds=time.perf_counter()-began);dump(folder/'result.json',result);continue
        source=HERE/task['source_path']/'delivered-point.npz';assert sha(source)==task['delivered_sha256']
        delivered=point(source);fixed=fixed_subproblem(model,delivered)
        if 'failure' in fixed:
            dump(folder/'obstruction.json',fixed);result.update(outcome=fixed['failure'],total_seconds=time.perf_counter()-began)
            dump(folder/'result.json',result);continue
        dump(folder/'fixed-pattern.json',fixed['integers']);lp=folder/'fixed.lp';write_fixed_lp(lp,model,fixed,True)
        settings=folder/'exact.set';settings.write_text('int:syncmode = 1\nint:readmode = 1\nint:solvemode = 2\nint:checkmode = 2\nreal:feastol = 0\nreal:opttol = 0\nreal:timelimit = 2\n')
        command=[str(SOPLEX),'--loadset='+str(settings),'-X='+str(folder/'primal.txt'),'-Y='+str(folder/'dual.txt'),str(lp)]
        with (folder/'solver.log').open('w') as stream:
            try:p=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=4.)
            except subprocess.TimeoutExpired:p=None
        result.update(lp_sha256=sha(lp),solver_binary_sha256=sha(SOPLEX),returncode=p.returncode if p else None)
        primal=parse(folder/'primal.txt','Primal solution (name, value):','y')
        dual=parse(folder/'dual.txt','Dual solution (name, value):','r')
        if primal is not None and dual is not None:
            q=[Fraction(0)]*len(model['variables'])
            for i,z in fixed['integers'].items():q[int(i)]=Fraction(z)
            for i,v in primal.items():q[int(i)]=Fraction(v)
            dump(folder/'primal-point.json',[str(x) for x in q]);dump(folder/'dual-multipliers.json',dual)
            certificate=verify(model,delivered,q,dual);dump(folder/'certificate.json',certificate)
            result.update(primal_dual_certificate=certificate.get('pattern_optimum_certified',False),
                          outcome='verified_certificate' if certificate.get('pattern_optimum_certified') else 'no_verified_optimum_certificate')
        else:result['outcome']='missing_rational_primal_or_dual'
        result['total_seconds']=time.perf_counter()-began;dump(folder/'result.json',result)
        print(task['arm'],task['seed'],result['outcome'],'seconds',round(result['total_seconds'],3),flush=True)


def replay():
    out=HERE/'cost-audit';design=load(out/'design.json')
    for path,digest in design['source_hashes'].items():assert sha(ROOT/path)==digest
    assert sha(out/'source-snapshot.py')==sha(Path(__file__))
    modelpath=HERE/'confirmation/models/neos-3083784-nive/original-model.json';assert sha(modelpath)==design['model_sha256']
    model=load(modelpath);records=[];certificates=[]
    for task in design['queue']:
        folder=out/'runs'/f"{task['arm']}-s{task['seed']}";r=load(folder/'result.json');assert all(r[k]==v for k,v in task.items())
        if task['delivered']:
            path=HERE/task['source_path']/'delivered-point.npz';assert sha(path)==task['delivered_sha256'];delivered=point(path)
            if (folder/'certificate.json').exists():
                q=[Fraction(v) for v in load(folder/'primal-point.json')];dual=load(folder/'dual-multipliers.json')
                c=verify(model,delivered,q,dual);assert c==load(folder/'certificate.json')
                assert c.get('pattern_optimum_certified',False)==r['primal_dual_certificate']
                assert sha(folder/'fixed.lp')==r['lp_sha256']
                certificates.append({**{k:task[k] for k in ('arm','seed')},**c})
            elif (folder/'obstruction.json').exists():
                obstruction=load(folder/'obstruction.json');integers=obstruction['integers']
                assert integers=={str(i):round(float(x)) for i,(x,v) in enumerate(zip(delivered,model['variables'])) if v['integer']}
                assert obstruction['failure']=='fixed_integer_contradicts_constant_row'
                row=model['rows'][obstruction['row']];assert all(i in integers or not a for i,a in row['terms'].items())
                b=Fraction.from_float(float(row['rhs']))-sum((Fraction.from_float(float(a))*integers[i] for i,a in row['terms'].items()),Fraction(0))
                assert str(b)==obstruction['rhs_exact'] and not (b==0 if row['sense']=='=' else b>=0 if row['sense']=='<' else b<=0)
        records.append(r)
    dump(out/'certificates.json',certificates)
    summary={'assigned_patterns':len(records),'primal_dual_optimum_certificates':sum(r['primal_dual_certificate'] for r in records),
             'numeric_budget_compliant_points_checked':sum(c.get('numeric_point_meets_original_budgets',False) for c in certificates),
             'material_cost_understatements':sum(c.get('understatement_exceeds_one_percent',False) for c in certificates),
             'weighted_budget_inequalities_verified':sum(c.get('budget_inequality_verified',False) for c in certificates),
             'fixed_pattern_obstructions':sum(r['outcome']=='fixed_integer_contradicts_constant_row' for r in records),
             'audit_seconds':sum(r['total_seconds'] for r in records),'solver_calls_during_replay':0,
             'global_mip_optima_or_lower_bounds_certified':False,'scope':'posthoc fixed-pattern LP optimality and budget-weighted cost understatement'}
    dump(out/'independent-verification.json',summary);print(json.dumps(summary,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('prepare','solve','replay'));globals()[p.parse_args().stage]()
