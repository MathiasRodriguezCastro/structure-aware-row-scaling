#!/usr/bin/env python3
"""Replay all joint native points and the exact primal witnesses; no solvers."""
import csv
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
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def power(k):return Fraction(2)**k
def viol(row,x):
    r=sum((F(float(a))*x[j] for j,a in row['terms'].items()),Fraction(0))-F(float(row['rhs']))
    return abs(r) if row['sense']=='=' else max(Fraction(0),r if row['sense']=='<=' else -r)

def main():
    d=load(HERE/'solve-design.json');timings=load(HERE/'solve-timings.json');witnesses=load(HERE/'base-witness-index.json')
    assert len(timings)==len(d['jobs'])==18 and [t['job'] for t in timings]==d['jobs']
    assert all(t['returncode']==0 for t in timings)
    for p,h in d['dependencies'].items():assert sha(ROOT/p)==h,p
    records=[];point_rows=0;witness_rows=0;data_checks=0
    for instance,m in d['models'].items():
        base=ROOT/m['Base'];native=ROOT/m['export'];assert sha(base)==m['Base_sha256'] and sha(native)==m['export_sha256']
        rows,_=parse(base);native_rows,_=parse(native);_,lp,_=read_lp(base);_,nlp,_=read_lp(native)
        assert lp.offset_==nlp.offset_==0
        exfile=HERE/'solve-models'/instance/'exponents.json';assert sha(exfile)==m['exponents_sha256'];ex=load(exfile)
        integer={n for n,k in zip(lp.col_names_,lp.integrality_) if str(k)!='HighsVarType.kContinuous'}
        U=None;scope={}
        assert set(rows)==set(native_rows) and set(lp.col_names_)==set(nlp.col_names_)
        for n,row in rows.items():
            assert F(float(native_rows[n]['rhs']))==F(float(row['rhs']))*power(ex['u'][n])
            assert row['sense']==native_rows[n]['sense'] and set(row['terms'])==set(native_rows[n]['terms'])
            for j,a in row['terms'].items():
                assert F(float(native_rows[n]['terms'][j]))==F(float(a))*power(ex['u'][n]+ex['v'][j]);data_checks+=1
            spec=physical_spec(n,row['terms'])
            if spec:scope[n]=spec
            elif re.fullmatch(r'a\d+_activacion_[1-4]\(\d+\)',n):scope[n]=('Volume-dependent activation','m3',1.)
        assert len(scope)==4320 and len(integer)==1440
        nd={n:(float(c),float(l),float(h),str(k)) for n,c,l,h,k in zip(nlp.col_names_,nlp.col_cost_,nlp.col_lower_,nlp.col_upper_,nlp.integrality_)}
        for n,c,l,h,k in zip(lp.col_names_,lp.col_cost_,lp.col_lower_,lp.col_upper_,lp.integrality_):
            cc,ll,hh,kk=nd[n];assert F(cc)==F(float(c))*power(ex['v'][n]) and kk==str(k)
            if n in integer:assert ex['v'][n]==0
            for original,scaled in zip([l,h],[ll,hh]):
                if math.isfinite(original):assert F(scaled)==F(float(original))/power(ex['v'][n])
                else:assert scaled==original
        wr=witnesses[instance]
        if 'certificate' in wr:
            folder=HERE/'base-witnesses'/instance;cert=load(folder/'independent-certificate.json');assert cert==wr['certificate'] and cert['original_model_sha256']==sha(base)
            original={n:Fraction(x) for n,x in load(folder/'exact-witness.json').items()}
            y={n:Fraction(x) for n,x in load(folder/'joint-witness.json').items()}
            assert set(original)==set(y)==set(lp.col_names_)
            for n in original:assert y[n]*power(ex['v'][n])==original[n]
            for n,row in rows.items():assert viol(row,original)==viol(native_rows[n],y)==0;witness_rows+=2
            for n,c,l,h,k in zip(lp.col_names_,lp.col_cost_,lp.col_lower_,lp.col_upper_,lp.integrality_):
                if math.isfinite(l):assert original[n]>=F(float(l))
                if math.isfinite(h):assert original[n]<=F(float(h))
                if n in integer:assert original[n].denominator==y[n].denominator==1
            U=sum((F(float(c))*original[n] for n,c in zip(lp.col_names_,lp.col_cost_)),Fraction(0))
            assert U==Fraction(cert['objective_exact_fraction'])
            assert U==sum((F(float(c))*y[n] for n,c in zip(nlp.col_names_,nlp.col_cost_)),Fraction(0))
        for j,timing in zip(d['jobs'],timings):
            if j['instance']!=instance:continue
            folder=HERE/'solve-runs'/j['id'];r=load(folder/'result.json');assert r['job']==j
            assert r['parameters']=={**d['parameters'],'Seed':j['seed']}
            assert r['export_sha256']==sha(native) and not r['global_optimality_independently_verified']
            assert r['native_import']['matrix_rhs_objective_bounds_integer_domains_equal']
            out=r['outcome'];assert out['solve_seconds']<=timing['process_seconds']
            log=(folder/'solver.log').read_text();assert 'Gurobi Optimizer version 13.0.2' in log
            assert 'Set parameter Presolve to value -1' in log and 'Loaded user MIP start' not in log
            with np.load(folder/'solution.npz',allow_pickle=False) as s:names=s['names'].tolist();values=s['y'].tolist()
            assert set(names)==set(lp.col_names_) and len(names)==len(set(names)) and all(math.isfinite(x) for x in values)
            y={n:F(x) for n,x in zip(names,values)}
            mapped={n:y[n]*power(ex['v'][n]) for n in names}
            delivered={n:F(math.ldexp(x,ex['v'][n])) for n,x in zip(names,values)}
            rounded={n:Fraction(round(x)) if n in integer else x for n,x in delivered.items()}
            assert all(mapped[n]==delivered[n] for n in names)==r['checks']['mapping_binary64_exact']
            ratio=Fraction(0);groups={};export_bad=0;maximum=Fraction(0);violated=0
            for n,(group,unit,conversion) in scope.items():
                a=viol(rows[n],delivered)/F(conversion);b=viol(rows[n],rounded)/F(conversion)
                g=groups.setdefault(group,[Fraction(0),Fraction(0)]);g[0]=max(g[0],a);g[1]=max(g[1],b)
                delta=F(.01 if unit=='MW' else 100.);ratio=max(ratio,b/delta);violated+=b>delta
                z=viol(native_rows[n],y);export_bad+=z>F(1e-6);maximum=max(maximum,z);point_rows+=3
                assert viol(rows[n],mapped)*power(ex['u'][n])==z
            for g in r['checks']['physical_delivered']:assert [float(x) for x in groups[g['group']]]==[g['raw_max'],g['rounded_max']]
            objective=sum((F(float(c))*mapped[n] for n,c in zip(lp.col_names_,lp.col_cost_)),Fraction(0))
            assert objective==sum((F(float(c))*y[n] for n,c in zip(nlp.col_names_,nlp.col_cost_)),Fraction(0))
            B=out['bound'];C=out['objective'];bf=None if U is None else bool(B is not None and F(B)>U+F(max(1e-6,8*math.ulp(B))))
            gf=None if U is None else bool(out['native_completed'] and U<F(C)-abs(F(C))/100)
            assert bf==r['checks']['bound_contradiction'] and gf==r['checks']['gap_contradiction']
            records.append({**j,**out,'objective_exact':str(objective),'physical_budget_pass':ratio<=1,
                'max_rounded_ratio':float(ratio),'violated_physical_rows':violated,'bound_contradiction':bf,'gap_contradiction':gf,
                'exported_rows_exceeding_epsilon':export_bad,'max_exported_physical_violation':float(maximum),
                'mapping_binary64_exact':r['checks']['mapping_binary64_exact'],'process_seconds':timing['process_seconds']})
    with (HERE/'verified-solves.csv').open('w',newline='') as out:
        w=csv.DictWriter(out,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    result={'native_calls':18,'verified_candidates':len(records),'physical_budgets_passed':sum(r['physical_budget_pass'] for r in records),
        'bound_flags':sum(r['bound_contradiction'] is True for r in records),'gap_flags':sum(r['gap_contradiction'] is True for r in records),
        'point_row_checks':point_rows,'witness_row_checks':witness_rows,'exact_matrix_coefficient_checks':data_checks,
        'all_mapped_points_exact_binary64':all(r['mapping_binary64_exact'] for r in records),
        'preparation_cost_in_process_seconds':False,'factor_acquisition_cost_reported_in_diagnostic':True,
        'global_MIP_optimality_verified':False}
    dump(HERE/'SOLVE_VALIDATION.json',result);print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()
