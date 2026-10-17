#!/usr/bin/env python3
"""Verify every refined MILP point and its global bound interval exactly."""
from fractions import Fraction
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from independent_check import reconstruct

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
F=Fraction.from_float
def load(p):
    data=p.read_bytes();return json.loads(gzip.decompress(data) if p.suffix=='.gz' else data)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')

def main():
    d=load(HERE/'repair-design.json');results=load(HERE/'repair-results.json')
    assert len(d['assignments'])==18 and set(results)==set(d['unique'])
    for p,h in d['dependencies'].items():assert sha(ROOT/p)==h,p
    bounds={r['instance']:Fraction(r['global_LP_LB_exact']) for r in load(HERE/'VALIDATION.json')['records']}
    points={};row_checks=0;conditional_products=0
    for key,record in d['unique'].items():
        folder=HERE/'repairs'/key;outcome=results[key]
        if not (folder/'rational-point.json').exists():points[key]=None;continue
        rows,lp,inequalities,base=reconstruct(record['instance'])
        q=list(map(Fraction,load(folder/'rational-point.json')));assert len(q)==lp.num_col_
        point=dict(zip(lp.col_names_,q));pattern={int(j):Fraction(v) for j,v in record['pattern'].items()}
        integer={i for i,k in enumerate(lp.integrality_) if str(k)!='HighsVarType.kContinuous'}
        assert set(pattern)==integer and all(q[i]==z and z.denominator==1 for i,z in pattern.items())
        for a,b in inequalities:assert sum((c*q[i] for i,c in a.items()),Fraction(0))<=b;row_checks+=1
        U=sum((F(float(c))*x for c,x in zip(lp.col_cost_,q)),F(float(lp.offset_)))
        assert U>=bounds[record['instance']]
        assert U==Fraction(outcome['objective_exact'])
        # The saved conditional dual is checked but never used as a global LB.
        fixed=load(folder/'lp.json.gz');pq=list(map(Fraction,load(folder/'primal.json')))
        pi={int(j):Fraction(v) for j,v in load(folder/'dual.json').items()}
        assert all(0<=j<len(fixed['rows']) and v<=0 for j,v in pi.items())
        reduced=list(map(Fraction,fixed['cost']));conditional=Fraction(fixed['offset'])
        for i,r in enumerate(fixed['rows']):
            p=pi.get(i,Fraction(0));conditional+=p*Fraction(r['rhs'])
            assert sum((Fraction(c)*pq[int(j)] for j,c in r['terms'].items()),Fraction(0))<=Fraction(r['rhs'])
            for j,c in r['terms'].items():reduced[int(j)]-=p*Fraction(c);conditional_products+=1
        assert not any(reduced) and conditional==U
        points[key]={'U':U,'point':q,'columns':list(lp.col_names_)}
    records=[]
    for a in d['assignments']:
        assert sha(ROOT/a['source'])==a['source_sha256']
        data=points[a['key']];LB=bounds[a['instance']]
        r={**a,'repaired_exact_feasible':data is not None,'global_LB_exact':str(LB),'U_exact':None,'certified_width_percent':None,'one_percent_certified':False,'exact_MILP_optimum_certified':False}
        with np.load(ROOT/a['source'],allow_pickle=False) as x:native=dict(zip(x['names'].tolist(),x['y'].tolist()))
        if data is not None:
            for j,z in d['unique'][a['key']]['pattern'].items():assert int(round(native[data['columns'][int(j)]]))==z
            U=data['U'];width=(U-LB)/abs(U) if U else None
            r.update(U_exact=str(U),certified_width_percent=None if width is None else float(100*width),
                one_percent_certified=width is not None and width<=Fraction(1,100),exact_MILP_optimum_certified=U==LB)
        records.append(r)
    with (HERE/'verified-repairs.csv').open('w',newline='') as out:
        w=csv.DictWriter(out,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    report={'native_outputs':18,'unique_repair_LP_calls':len(results),'repaired_exact_feasible_outputs':sum(r['repaired_exact_feasible'] for r in records),
        'one_percent_certified_outputs':sum(r['one_percent_certified'] for r in records),'exact_MILP_optimum_certified_outputs':sum(r['exact_MILP_optimum_certified'] for r in records),
        'original_full_inequalities_checked':row_checks,'conditional_dual_products_checked':conditional_products,
        'global_LB_source':'exact dual of full LP relaxation; no integer pattern fixed',
        'upper_bound_source':'exact feasible repaired MILP point with original integer pattern',
        'total_global_LP_seconds':sum(r['total_seconds'] for r in load(HERE/'results.json')),
        'total_repair_seconds':sum(r['total_seconds'] for r in results.values()),
        'rows':[{k:r[k] for k in ['instance','seed','key','certified_width_percent','one_percent_certified','exact_MILP_optimum_certified']} for r in records]}
    dump(HERE/'REPAIR_VALIDATION.json',report);print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2),flush=True)

if __name__=='__main__':main()
