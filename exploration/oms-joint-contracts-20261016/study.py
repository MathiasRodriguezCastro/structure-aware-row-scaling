#!/usr/bin/env python3
"""Opportunity diagnostic. No MIP solve and no edit to the model generator."""
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import joint

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT/'exploration/oms-followup-20261014'),str(ROOT/'scripts/research'),str(ROOT/'scripts')]
import activation_study as a
F=Fraction.from_float
INSTANCES=['instance001','instance005','instance022','instance027','instance031','instance046']
def dump(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def model_for(instance,budget):
    path=ROOT/'exploration/oms-matched-accuracy-20261016/inputs'/instance/'Base.lp'
    rows,physical=a.original_rows(path);_,lp,_=a.campaign.afb.read_lp(path)
    integers={n for n,k in zip(lp.col_names_,lp.integrality_) if str(k)!='HighsVarType.kContinuous'}
    delta={n:F(.01 if r['unit']=='MW' else float(budget))*F(float(r['conversion'])) for n,r in physical.items()}
    E={n:F(1e-9)*sum((F(abs(float(v))) for j,v in r['terms'].items() if j in integers),Fraction(0)) for n,r in physical.items()}
    return {'rows':rows,'columns':list(lp.col_names_),'integers':integers,'delta':delta,'E':E,
        'costs':dict(zip(lp.col_names_,lp.col_cost_)),'bounds':dict(zip(lp.col_names_,zip(lp.col_lower_,lp.col_upper_)))},path

def check_export(model,u,v):
    """Exact rational checks independent of exponent construction formulas."""
    count=0
    def transformed(value,k):
        nonlocal count
        z=math.ldexp(float(value),k)
        assert math.isfinite(z) and F(z)==F(float(value))*joint.power(k)
        count+=1;return z
    for n,row in model['rows'].items():
        transformed(row['rhs'],u[n])
        for j,value in row['terms'].items():
            z=transformed(value,u[n]+v[j]);assert 1e-9<=abs(z)<=1e9
        if n in model['delta']:assert F(1e-6)/joint.power(u[n])+model['E'][n]<=model['delta'][n]
    for j in model['columns']:
        transformed(model['costs'][j],v[j])
        for b in model['bounds'][j]:
            if math.isfinite(b):assert abs(transformed(b,-v[j]))<=1e19
        if j in model['integers']:assert v[j]==0
    return count

def main():
    if (HERE/'results.json').exists():raise RuntimeError('results already exist')
    protected={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'paper/submission/oms/releases').rglob('*') if p.is_file()}
    protected.update({str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'exploration').rglob('*.zip')})
    dump(HERE/'protected-files.json',protected)
    dump(HERE/'design.json',{'instances':INSTANCES,'budgets':[10,30,100,300,1000,3000,10000],
        'power_MW':.01,'gamma':1e-9,'epsilon':1e-6,'backend_cap':1e19,
        'source_sha256':{p.name:sha(p) for p in [HERE/'joint.py',Path(__file__),HERE/'PROTOCOL.md']},
        'no_native_solver_calls':True})
    records=[]
    for instance in INSTANCES:
        for budget in [10,30,100,300,1000,3000,10000]:
            model,path=model_for(instance,budget)
            for columns in [False,True]:
                start=time.perf_counter();r=joint.minimize(model,columns)
                record={'instance':instance,'volume_budget':budget,'columns_free':columns,
                    'feasible':r['feasible'],'t':r['t'],'seconds':time.perf_counter()-start,
                    'input_model_sha256':sha(path),'result':r['result']}
                if r['feasible']:
                    u,v=joint.exponents(model,r);record['exact_data_checks']=check_export(model,u,v)
                    record['changed_continuous_columns']=sum(e!=0 for e in v.values())
                    record['row_exponent_range']=[min(u.values()),max(u.values())]
                    record['column_exponent_range']=[min(v.values()),max(v.values())]
                    lower=r['lower_certificate']
                    record['lower_certificate']=None if lower is None else lower['result']
                else:
                    record['negative_cycle_labels']=[r['graph'].edges[i][3] for i in r['result']['negative_cycle']]
                records.append(record);dump(HERE/'results.json',records)
                print(instance,budget,'joint' if columns else 'rows',r['feasible'],r['t'],round(record['seconds'],3),flush=True)
    for p,h in protected.items():assert sha(ROOT/p)==h,p

if __name__=='__main__':main()
