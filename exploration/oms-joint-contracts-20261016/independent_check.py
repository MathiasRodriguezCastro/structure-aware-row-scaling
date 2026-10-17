#!/usr/bin/env python3
"""Rebuild exponent intervals by enumerating actual ldexp representability.

Does not import joint.py, study.py, solve.py, or optimize a model. Verifies integer
potentials/cycles against independently reconstructed difference inequalities.
"""
from functools import lru_cache
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import numpy as np

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT/'scripts/research'),str(ROOT/'scripts')]
from audit_identifiability_grid import parse
from audit_fixed_basis import read_lp
from oms_dispatch_validation import physical_spec
F=Fraction.from_float
def load(p):return json.loads(p.read_text())
def dump(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pow2(k):return Fraction(2)**k

@lru_cache(None)
def allowed(value,minimum,maximum):
    valid=[];q=F(abs(value))
    for k in range(-2200,2201):
        try:z=math.ldexp(abs(value),k)
        except OverflowError:continue
        if not z or not math.isfinite(z):continue
        if F(z)!=q*pow2(k):continue
        if minimum is not None and F(z)<minimum:continue
        if maximum is not None and F(z)>maximum:continue
        valid.append(k)
    assert valid and valid==list(range(valid[0],valid[-1]+1))
    return valid[0],valid[-1]

@lru_cache(None)
def ceil_accuracy(delta,E):
    if delta<=E:return None
    # Independent direct rational search, no logarithm/exponent bit formula.
    for k in range(-1200,1201):
        if F(1e-6)/pow2(k)+E<=delta:return k
    raise ValueError('outside declared search')

def model(instance,budget):
    p=ROOT/'exploration/oms-matched-accuracy-20261016/inputs'/instance/'Base.lp'
    rows,_=parse(p);_,lp,_=read_lp(p)
    integer={n for n,k in zip(lp.col_names_,lp.integrality_) if str(k)!='HighsVarType.kContinuous'}
    delta={};reserve={}
    for n,row in rows.items():
        spec=physical_spec(n,row['terms'])
        if spec:_,unit,conv=spec
        elif re.fullmatch(r'a\d+_activacion_[1-4]\(\d+\)',n):unit,conv='m3',1.
        else:continue
        delta[n]=F(.01 if unit=='MW' else float(budget))*F(conv)
        reserve[n]=F(1e-9)*sum((F(abs(float(a))) for j,a in row['terms'].items() if j in integer),Fraction(0))
    return rows,lp,integer,delta,reserve,p

def edges_for(data,t,columns):
    rows,lp,integer,delta,E,_=data;edges=[]
    ri={n:i+1 for i,n in enumerate(rows)};ci={n:len(rows)+i+1 for i,n in enumerate(lp.col_names_)}
    def interval(a,b,lo,hi):edges.extend([(a,b,hi),(b,a,-lo)])
    for n,row in rows.items():
        i=ri[n];interval(0,i,-1074,1023)
        if n in delta:
            k=ceil_accuracy(delta[n],E[n])
            if k is None:edges.append((0,0,-1))
            else:edges.append((i,0,-k))
        if float(row['rhs']):
            lo,hi=allowed(float(row['rhs']),None,F(1e19));interval(0,i,lo,hi)
        for j,a in row['terms'].items():
            if not a:continue
            # Individual component ranges permit an empty intersection.
            exactlo,exacthi=allowed(float(a),None,None)
            winlo,winhi=allowed(float(a),F(1e-9),F(1e9))
            tlo,thi=allowed(float(a),pow2(-t),pow2(t))
            interval(ci[j],i,max(exactlo,winlo,tlo),min(exacthi,winhi,thi))
    for n,c,l,h in zip(lp.col_names_,lp.col_cost_,lp.col_lower_,lp.col_upper_):
        i=ci[n];interval(0,i,-1023,1074)
        if not columns or n in integer:interval(0,i,0,0)
        if c:
            lo,hi=allowed(float(c),None,None);interval(0,i,-hi,-lo)
        for b in [l,h]:
            if b and math.isfinite(b):
                lo,hi=allowed(float(b),None,F(1e19));interval(0,i,lo,hi)
    return edges

def check_certificate(edges,result,n):
    if 'potential' in result:
        p=result['potential'];assert len(p)==n and p[0]==0 and all(isinstance(v,int) for v in p)
        assert all(p[b]-p[a]<=c for a,b,c in edges)
    else:
        cycle=[edges[i] for i in result['negative_cycle']];assert cycle
        assert all(cycle[i][1]==cycle[(i+1)%len(cycle)][0] for i in range(len(cycle)))
        assert sum(c for a,b,c in cycle)<0

def violation(row,x):
    r=sum((F(float(a))*x[j] for j,a in row['terms'].items()),Fraction(0))-F(float(row['rhs']))
    return abs(r) if row['sense']=='=' else max(Fraction(0),r if row['sense']=='<=' else -r)

def main():
    records=load(HERE/'results.json');design=load(HERE/'design.json');assert len(records)==84
    amend=load(HERE/'bibliographic-amendment.json')
    for f,h in design['source_sha256'].items():
        if f=='PROTOCOL.md':assert h==amend['original_protocol_sha256'] and sha(HERE/f)==amend['corrected_protocol_sha256']
        else:assert sha(HERE/f)==h,f
    for p,h in load(HERE/'protected-files.json').items():
        if not (ROOT/p).exists() and '--allow-absent-historical' in sys.argv:continue
        assert sha(ROOT/p)==h,p
    constraints=0;feasible=0;negative=0;bycase=[]
    for r in records:
        data=model(r['instance'],r['volume_budget']);rows,lp,integer,delta,E,path=data
        assert sha(path)==r['input_model_sha256']
        edges=edges_for(data,r['t'],r['columns_free']);constraints+=len(edges)
        check_certificate(edges,r['result'],len(rows)+lp.num_col_+1)
        if r['feasible']:
            assert 'potential' in r['result'];feasible+=1
            if r['t']:
                lower=edges_for(data,r['t']-1,r['columns_free']);check_certificate(lower,r['lower_certificate'],len(rows)+lp.num_col_+1)
                assert 'negative_cycle' in r['lower_certificate'];constraints+=len(lower);negative+=1
        else:assert 'negative_cycle' in r['result'];negative+=1
        bycase.append({k:r[k] for k in ['instance','volume_budget','columns_free','feasible','t']})
    report={'diagnostic_cells':84,'feasible_cells':feasible,'negative_cycles_checked':negative,'integer_constraints_checked':constraints,
        'intervals_independently_enumerated':allowed.cache_info().currsize,'new_optimizer_calls':0,'global_optimality_certified_for_MIP':False}
    dump(HERE/'DIAGNOSTIC_VALIDATION.json',report);print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()
