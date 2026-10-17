#!/usr/bin/env python3
"""Acquire genuine global LP lower bounds, explicitly relaxing every integer."""
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT/'exploration/oms-root-attribution-20261015'),str(ROOT/'scripts/research'),str(ROOT/'scripts')]
import exact_lp as exact
from audit_identifiability_grid import parse
from audit_fixed_basis import read_lp
F=Fraction.from_float
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def data_for(instance):
    model=ROOT/'exploration/oms-matched-accuracy-20261016/inputs'/instance/'Base.lp'
    rows,_=parse(model);_,lp,_=read_lp(model);idx={n:i for i,n in enumerate(lp.col_names_)}
    variables=[{'name':n,'type':'C','lb':str(F(float(l))) if math.isfinite(l) else None,'ub':str(F(float(h))) if math.isfinite(h) else None,'obj':str(F(float(c)))} for n,c,l,h in zip(lp.col_names_,lp.col_cost_,lp.col_lower_,lp.col_upper_)]
    integer=[n for n,k in zip(lp.col_names_,lp.integrality_) if str(k)!='HighsVarType.kContinuous']
    assert len(integer)==1440
    for n in integer:assert variables[idx[n]]['lb']=='0' and variables[idx[n]]['ub']=='1'
    data={'constant':str(F(float(lp.offset_))),'variables':variables,'rows':[{'name':n,'sense':r['sense'][0],
        'rhs':str(F(float(r['rhs']))),'terms':[[idx[j],str(F(float(a)))] for j,a in r['terms'].items()]} for n,r in rows.items()]}
    return data,model

def main():
    if (HERE/'design.json').exists():raise RuntimeError('new global LP experiment already started')
    instances=['instance001','instance005','instance022','instance027','instance031','instance046']
    deps=[Path(__file__),HERE/'PROTOCOL.md',ROOT/'exploration/oms-root-attribution-20261015/exact_lp.py',ROOT/'exploration/oms-root-attribution-20261015/common.py']
    dump(HERE/'design.json',{'instances':instances,'limit_seconds':30.,'all_integer_variables_relaxed':True,'fixed_integer_variables':0,
        'dependencies':{str(p.relative_to(ROOT)):sha(p) for p in deps}})
    results=[];binary=ROOT/'exploration/oms-followup-20261014/tools/soplex-build/bin/soplex'
    for n in instances:
        data,model=data_for(n);folder=HERE/n;folder.mkdir()
        exact.dump(folder/'model.json.gz',data)
        result=exact.acquire(data,{},folder,binary,limit=30.)
        result.update(instance=n,original_model_sha256=sha(model),relaxed_integer_columns=1440,fixed_integer_columns=0)
        certificate=folder/'certificate.json'
        if certificate.exists():
            cert=json.loads(certificate.read_text());result['verified_global_LP_lower_bound']=cert['dual_value_exact'] if cert['dual_feasible'] else None
        else:result['verified_global_LP_lower_bound']=None
        results.append(result);dump(HERE/'results.json',results)
        print(n,result['outcome'],'global LB',result['verified_global_LP_lower_bound'],flush=True)

if __name__=='__main__':main()
