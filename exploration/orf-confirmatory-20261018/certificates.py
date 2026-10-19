#!/usr/bin/env python3
"""Acquire separate rational reference intervals; never promote MIP solver gaps."""
from fractions import Fraction as Q
import json
import math
from pathlib import Path
import sys
import time
import numpy as np

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT/'exploration/oms-root-attribution-20261015'),str(ROOT/'scripts/research'),str(ROOT/'scripts')]
import exact_lp as exact
from audit_identifiability_grid import parse
from audit_fixed_basis import read_lp
from study import load,dump,sha
F=Q.from_float

def data(path,relax=False):
    rows,_=parse(path);_,lp,_=read_lp(path);indices={n:i for i,n in enumerate(lp.col_names_)}
    variables=[dict(name=n,type='C' if relax or str(k)=='HighsVarType.kContinuous' else 'B',
        lb=str(F(float(l))) if math.isfinite(l) else None,
        ub=str(F(float(u))) if math.isfinite(u) else None,obj=str(F(float(c))))
        for n,k,l,u,c in zip(lp.col_names_,lp.integrality_,lp.col_lower_,lp.col_upper_,lp.col_cost_)]
    return dict(constant=str(F(float(lp.offset_))),variables=variables,
        rows=[dict(name=n,sense=r['sense'][0],rhs=str(F(float(r['rhs']))),
            terms=[[indices[j],str(F(float(a)))] for j,a in r['terms'].items()]) for n,r in rows.items()])

def main():
    d=load(HERE/'design.json');timing=load(HERE/'timing.json')
    assert len(timing)==len(d['jobs']) and all(r['returncode']==0 for r in timing)
    plan=[]
    for name in d['models']:
        plan.append(dict(instance=name,representation='Base',kind='global-LP',source=None))
        for representation in ['Base','L2','Budget-L2']:
            candidates=[]
            for job in d['jobs']:
                if job['instance']!=name:continue
                r=load(HERE/'runs'/job['id']/'result.json')
                if not r.get('abstained') and r['representation']==representation and r['outcome']['solutions']:
                    candidates.append((Q(r['checks']['point_objective_exact']),job['id']))
            plan.append(dict(instance=name,representation=representation,kind='integer-pattern',
                source=min(candidates)[1] if candidates else None))
    dependencies=[Path(__file__),ROOT/'exploration/oms-root-attribution-20261015/exact_lp.py',
        ROOT/'exploration/oms-root-attribution-20261015/common.py']
    manifest=dict(design_sha256=sha(HERE/'design.json'),plan=plan,time_limit_seconds=30,
        dependencies={str(p.relative_to(ROOT)):sha(p) for p in dependencies})
    target=HERE/'certificate-plan.json'
    if target.exists():assert manifest==load(target)
    else:dump(target,manifest)
    binary=ROOT/'exploration/oms-followup-20261014/tools/soplex-build/bin/soplex'
    outcomes=load(HERE/'certificate-results.json') if (HERE/'certificate-results.json').exists() else []
    assert [r['assignment'] for r in outcomes]==plan[:len(outcomes)]
    for item in plan[len(outcomes):]:
        folder=HERE/'certificates'/item['instance']/(item['kind']+'-'+item['representation'])
        assert not folder.exists(),'unrecorded attempt retained'
        base=HERE/'models'/item['instance']/(item['representation']+'.lp')
        if item['kind']=='integer-pattern' and not item['source']:
            result=dict(outcome='no_candidate',total_seconds=0.)
        else:
            original=data(base,relax=item['kind']=='global-LP');pattern={}
            if item['kind']=='integer-pattern':
                with np.load(HERE/'runs'/item['source']/'solution.npz',allow_pickle=False) as sol:
                    point=dict(zip(sol['names'].tolist(),sol['x'].tolist()))
                pattern={str(j):str(round(point[v['name']])) for j,v in enumerate(original['variables']) if v['type']!='C'}
            result=exact.acquire(original,pattern,folder,binary,limit=30.)
        outcomes.append(dict(assignment=item,model_sha256=sha(base),result=result))
        dump(HERE/'certificate-results.json',outcomes)
        print(len(outcomes),'/',len(plan),item['instance'],item['kind'],item['representation'],result['outcome'],flush=True)

if __name__=='__main__':main()
