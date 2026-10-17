#!/usr/bin/env python3
"""Independently verify global LP duals and complete integer upper witnesses."""
import csv
from fractions import Fraction
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT/'scripts/research'),str(ROOT/'scripts')]
from audit_identifiability_grid import parse
from audit_fixed_basis import read_lp
F=Fraction.from_float
def load(p):
    b=p.read_bytes();return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')

def reconstruct(instance):
    base=ROOT/'exploration/oms-matched-accuracy-20261016/inputs'/instance/'Base.lp'
    rows,_=parse(base);_,lp,_=read_lp(base);indices={n:i for i,n in enumerate(lp.col_names_)}
    inequalities=[]
    for n,row in rows.items():
        for sign in ([1,-1] if row['sense']=='=' else [1] if row['sense']=='<=' else [-1]):
            inequalities.append(({indices[j]:sign*F(float(a)) for j,a in row['terms'].items()},sign*F(float(row['rhs']))))
    for j,(l,h) in enumerate(zip(lp.col_lower_,lp.col_upper_)):
        if math.isfinite(l):inequalities.append(({j:Fraction(-1)},-F(float(l))))
        if math.isfinite(h):inequalities.append(({j:Fraction(1)},F(float(h))))
    return rows,lp,inequalities,base

def main():
    design=load(HERE/'design.json');outcomes=load(HERE/'results.json');assert len(outcomes)==6
    for p,h in design['dependencies'].items():assert sha(ROOT/p)==h,p
    saved=load(ROOT/'exploration/oms-joint-contracts-20261016/base-witness-index.json')
    records=[];products=0;upper_rows=0
    for result in outcomes:
        instance=result['instance'];folder=HERE/instance
        rows,lp,inequalities,base=reconstruct(instance);assert sha(base)==result['original_model_sha256']
        assert result['fixed_integer_columns']==0 and result['relaxed_integer_columns']==1440
        stored=load(folder/'lp.json.gz');assert len(stored['rows'])==len(inequalities) and stored['integers']=={}
        assert len(stored['cost'])==lp.num_col_==6120
        for (a,b),r in zip(inequalities,stored['rows']):
            assert a=={int(j):Fraction(c) for j,c in r['terms'].items()} and b==Fraction(r['rhs'])
        assert [Fraction(v) for v in stored['cost']]==[F(float(c)) for c in lp.col_cost_]
        assert Fraction(stored['offset'])==F(float(lp.offset_))
        dual=load(folder/'dual.json');q=list(map(Fraction,load(folder/'primal.json')))
        pi={int(i):Fraction(v) for i,v in dual.items()};assert all(0<=i<len(inequalities) and v<=0 for i,v in pi.items())
        reduced=[F(float(c)) for c in lp.col_cost_];LB=F(float(lp.offset_))
        for i,(a,b) in enumerate(inequalities):
            assert sum((c*q[j] for j,c in a.items()),Fraction(0))<=b
            p=pi.get(i,Fraction(0));LB+=p*b
            for j,c in a.items():reduced[j]-=p*c;products+=1
        assert not any(reduced)
        lp_objective=sum((F(float(c))*x for c,x in zip(lp.col_cost_,q)),F(float(lp.offset_)))
        assert lp_objective==LB==Fraction(result['verified_global_LP_lower_bound'])
        wf=ROOT/'exploration/oms-joint-contracts-20261016/base-witnesses'/instance
        point={n:Fraction(v) for n,v in load(wf/'exact-witness.json').items()}
        assert set(point)==set(lp.col_names_)
        for n,row in rows.items():
            activity=sum((F(float(c))*point[j] for j,c in row['terms'].items()),Fraction(0))
            b=F(float(row['rhs']));assert activity==b if row['sense']=='=' else activity<=b if row['sense']=='<=' else activity>=b
            upper_rows+=1
        integer=0
        for n,l,h,k in zip(lp.col_names_,lp.col_lower_,lp.col_upper_,lp.integrality_):
            if math.isfinite(l):assert point[n]>=F(float(l))
            if math.isfinite(h):assert point[n]<=F(float(h))
            if str(k)!='HighsVarType.kContinuous':assert point[n].denominator==1;integer+=1
        U=sum((F(float(c))*point[n] for n,c in zip(lp.col_names_,lp.col_cost_)),F(float(lp.offset_)))
        assert U==Fraction(saved[instance]['certificate']['objective_exact_fraction']) and LB<=U and integer==1440
        width=(U-LB)/abs(U) if U else None
        records.append({'instance':instance,'global_LP_LB_exact':str(LB),'integer_U_exact':str(U),
            'LB_display':float(LB),'U_display':float(U),'relative_interval_width_percent':None if width is None else float(width*100),
            'MILP_one_percent_certified':width is not None and width<=Fraction(1,100),
            'MILP_optimum_certified':U==LB,'fractional_LP_integer_coordinates':sum(x.denominator!=1 for x,k in zip(q,lp.integrality_) if str(k)!='HighsVarType.kContinuous')})
    with (HERE/'verified-intervals.csv').open('w',newline='') as out:
        w=csv.DictWriter(out,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    report={'global_LP_calls':6,'global_exact_duals_verified':6,'exact_integer_witnesses_verified':6,
        'dual_coefficient_products':products,'integer_witness_rows_checked':upper_rows,
        'MILP_one_percent_certified_cases':[r['instance'] for r in records if r['MILP_one_percent_certified']],
        'MILP_exact_optimum_certified_cases':[r['instance'] for r in records if r['MILP_optimum_certified']],
        'MILP_lower_bounds_from_fixed_patterns':False,'records':records}
    dump(HERE/'VALIDATION.json',report);print(json.dumps({k:v for k,v in report.items() if k!='records'},indent=2),flush=True)

if __name__=='__main__':main()
