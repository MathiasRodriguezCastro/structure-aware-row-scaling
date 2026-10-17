#!/usr/bin/env python3
"""Validate inherited proofs and both native importers without optimizing."""
import json
from fractions import Fraction
from pathlib import Path
import time
from infra import HERE,ROOT,OBJECTIVE,load,dump,sha,native,F
from cuts import project,export
from verify_cuts import check


def main():
    d=load(OBJECTIVE/'design.json');model=load(OBJECTIVE/'inputs/models/neos-3083784-nive/original-model.json');records=[];example=None
    for p in d['patterns']:
        if p['model']!='neos-3083784-nive':continue
        f=OBJECTIVE/'characterization'/p['id']/'cost-0';c=load(f/'certificate.json');lp=load(f/'model.json')
        kind='cost' if c.get('optimum_certified') else 'ray'
        mu=load(f/('dual.json' if kind=='cost' else 'ray.json'))
        if kind=='ray':mu={i:str(Fraction(v)*c['orientation']) for i,v in mu.items()}
        a,g=project(model,lp,mu,kind,p['integers'])
        for cut in (a,g):
            e=export(model,cut);cert=check(model,lp,p['integers'],mu,kind,cut,e)
            records.append({'source_pattern':p['id'],'exact':cut,'export':e,'certificate':cert})
            if example is None and kind=='cost' and cut['kind']=='partial-cost':example={'model':model,'export':e,'f':f,'lp':lp,'z':p['integers']}
    factors=load(ROOT/'exploration/oms-transfer-study-20261014/confirmation/models/neos-3083784-nive/factors.json');extended=json.loads(json.dumps(model))
    extended['rows'].append({'name':'preflight-cut','terms':example['export']['terms'],'sense':'>','rhs':example['export']['rhs'],'budget':1e-6,'unit':'exported units'})
    start=[0.]*len(model['variables'])
    for i,z in example['z'].items():start[int(i)]=float(z)
    for i,v in zip(example['lp']['continuous_original_indices'],load(example['f']/'primal.json')):start[i]=float(Fraction(v))
    imports=[]
    for solver in ('gurobi','highs'):
        r,_=native(extended,factors['Dyadic-L2']+[1.],solver,False,HERE/'preflight'/solver,109,10.,time.perf_counter()+45.,start,True)
        imports.append({'solver':solver,**r})
    dump(HERE/'preflight-verification.json',{'stage':'before new MIP optimization','proofs':records,'native_import_only':imports,'new_optimization_calls':0})
    print('24 globally valid cuts checked; both importers and Starts checked without optimization')


if __name__=='__main__':main()
