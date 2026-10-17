#!/usr/bin/env python3
"""Small prespecified pilot of the certified joint transformation."""
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import joint
import study as diagnostic

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
F=Fraction.from_float
def load(p):return json.loads(p.read_text())
def dump(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def library(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def export(model,u,v,path):
    lines=['min\nobj:\n']
    for n,c in model['costs'].items():
        if c:lines.append(f'  {math.ldexp(float(c),v[n]):+.17g} {n}\n')
    lines.append('\ns.t.\n')
    for n,row in model['rows'].items():
        lines.append(n+':\n')
        for j,a in row['terms'].items():lines.append(f'  {math.ldexp(float(a),u[n]+v[j]):+.17g} {j}\n')
        lines.append(f'  {row["sense"]} {math.ldexp(float(row["rhs"]),u[n]):.17g}\n')
    lines.append('\nbounds\n')
    for n,(l,h) in model['bounds'].items():
        if math.isinf(l) and math.isinf(h):lines.append(f' {n} free\n')
        elif math.isinf(l):lines.extend([f' {n} free\n',f' {n} <= {math.ldexp(h,-v[n]):.17g}\n'])
        elif math.isinf(h):lines.append(f' {n} >= {math.ldexp(l,-v[n]):.17g}\n')
        else:lines.append(f' {math.ldexp(l,-v[n]):.17g} <= {n} <= {math.ldexp(h,-v[n]):.17g}\n')
    # All discrete variables in this bank are binary, checked in prepare.
    lines.append('\nbinary\n');lines.extend(' '+n+'\n' for n in model['columns'] if n in model['integers']);lines.append('end\n')
    path.write_text(''.join(lines))

def prepare():
    if (HERE/'solve-design.json').exists():raise RuntimeError('solve design exists')
    data=load(HERE/'results.json');models={}
    for instance in diagnostic.INSTANCES:
        model,base=diagnostic.model_for(instance,100)
        r=next(r for r in data if r['instance']==instance and r['volume_budget']==100 and r['columns_free'])
        assert r['feasible'];graph=joint.construct(model,r['t'],True);graph.check(r['result'])
        u,v=joint.exponents(model,{'feasible':True,'graph':graph,'result':r['result']})
        for n in model['integers']:assert model['bounds'][n]==(0.,1.)
        folder=HERE/'solve-models'/instance;folder.mkdir(parents=True)
        path=folder/'Joint.lp';export(model,u,v,path)
        # Verify actual file values, not only the candidate arithmetic.
        rows,_=diagnostic.a.parse(path);_,lp,_=diagnostic.a.campaign.afb.read_lp(path)
        assert set(rows)==set(model['rows']) and set(lp.col_names_)==set(model['columns'])
        for n,row in rows.items():
            assert row['sense']==model['rows'][n]['sense']
            assert F(float(row['rhs']))==F(float(model['rows'][n]['rhs']))*joint.power(u[n])
            for j,a in row['terms'].items():assert F(float(a))==F(float(model['rows'][n]['terms'][j]))*joint.power(u[n]+v[j])
        for n,c,l,h,k in zip(lp.col_names_,lp.col_cost_,lp.col_lower_,lp.col_upper_,lp.integrality_):
            assert F(float(c))==F(float(model['costs'][n]))*joint.power(v[n])
            for a,b in zip([l,h],model['bounds'][n]):
                if math.isfinite(b):assert F(float(a))==F(b)/joint.power(v[n])
                else:assert a==b
            assert (str(k)!='HighsVarType.kContinuous')==(n in model['integers'])
        dump(folder/'exponents.json',{'u':u,'v':v})
        models[instance]={'export':str(path.relative_to(ROOT)),'export_sha256':sha(path),'Base':str(base.relative_to(ROOT)),'Base_sha256':sha(base),'exponents_sha256':sha(folder/'exponents.json')}
    jobs=[{'instance':n,'seed':s,'id':n+'-s'+str(s)} for n in diagnostic.INSTANCES for s in [59,71,89]];random.Random(2026101603).shuffle(jobs)
    deps=[Path(__file__),HERE/'joint.py',HERE/'study.py',HERE/'SOLVE_PROTOCOL.md',HERE/'results.json']
    dump(HERE/'solve-design.json',{'jobs':jobs,'models':models,'parameters':{'Threads':4,'TimeLimit':120.,'MIPGap':.01,'FeasibilityTol':1e-6,'IntFeasTol':1e-9,'Presolve':-1,'ScaleFlag':-1,'IntegralityFocus':0,'NumericFocus':0},'dependencies':{str(p.relative_to(ROOT)):sha(p) for p in deps},'known_model_pilot':True})

def witnesses():
    import exact_dispatch_witness as e
    d=load(HERE/'solve-design.json');index={}
    old=ROOT/'exploration/oms-followup-20261014'
    for instance,m in d['models'].items():
        folder=HERE/'base-witnesses'/instance
        source=ROOT/load(old/'exact-witnesses'/instance/'Budget-L2/mapping.json')['saved_solution']
        start=time.perf_counter()
        try:
            e.prepare(folder,ROOT/m['Base'],source);e.solve(folder,old/'tools/soplex-build/bin/soplex');e.check(folder)
            ex=load(HERE/'solve-models'/instance/'exponents.json')
            point={n:Fraction(x)/joint.power(ex['v'][n]) for n,x in load(folder/'exact-witness.json').items()}
            rows,_=diagnostic.a.parse(ROOT/m['export'])
            for n,row in rows.items():
                z=sum((F(float(a))*point[j] for j,a in row['terms'].items()),Fraction(0))-F(float(row['rhs']))
                assert (z==0 if row['sense']=='=' else z<=0 if row['sense']=='<=' else z>=0),n
            dump(folder/'joint-witness.json',{n:str(x) for n,x in point.items()})
            index[instance]={'certificate':load(folder/'independent-certificate.json'),'seconds':time.perf_counter()-start}
        except Exception as error:index[instance]={'error':str(error),'seconds':time.perf_counter()-start}
        dump(HERE/'base-witness-index.json',index)

def worker(job_id):
    import numpy as np
    import gurobipy as gp
    from oms_dispatch_validation import exact_violation
    wf=library(ROOT/'exploration/oms-if1-workflow-20261015/study.py','joint_native_check')
    d=load(HERE/'solve-design.json');j=next(j for j in d['jobs'] if j['id']==job_id);m=d['models'][j['instance']]
    folder=HERE/'solve-runs'/job_id;folder.mkdir(parents=True)
    ex=load(HERE/'solve-models'/j['instance']/'exponents.json');assert sha(HERE/'solve-models'/j['instance']/'exponents.json')==m['exponents_sha256']
    path=ROOT/m['export'];assert sha(path)==m['export_sha256']
    _,lp,A=diagnostic.a.campaign.afb.read_lp(path)
    env=gp.Env(params={'OutputFlag':0});native=gp.read(str(path),env=env)
    native.setParam('OutputFlag',1);native.setParam('LogToConsole',0);native.setParam('LogFile',str(folder/'solver.log'))
    params={**d['parameters'],'Seed':j['seed']}
    for k,v in params.items():native.setParam(k,v)
    equality=wf.check_import(native,lp,A);start=time.perf_counter();native.optimize();seconds=time.perf_counter()-start
    outcome={'status':native.Status,'solutions':native.SolCount,'work':native.Work,'runtime':native.Runtime,'solve_seconds':seconds,'bound':native.ObjBound if math.isfinite(native.ObjBound) else None,'objective':native.ObjVal if native.SolCount else None,'native_completed':native.Status==2}
    checks={}
    if native.SolCount:
        names=[v.VarName for v in native.getVars()];y=native.getAttr('X',native.getVars())
        np.savez_compressed(folder/'solution.npz',names=np.array(names),y=np.array(y))
        # Mathematical mapped point and its binary64 delivered representation differ
        # if ldexp underflows; both paths are retained and audited.
        mapped={n:F(float(value))*joint.power(ex['v'][n]) for n,value in zip(names,y)}
        delivered={n:math.ldexp(float(value),ex['v'][n]) for n,value in zip(names,y)}
        _,physical=diagnostic.a.original_rows(ROOT/m['Base']);integer=set(diagnostic.model_for(j['instance'],100)[0]['integers'])
        checks['physical_delivered']=diagnostic.a.audit_values(physical,delivered,integer)
        checks['mapping_binary64_exact']=all(F(delivered[n])==mapped[n] for n in names)
        witness=load(HERE/'base-witness-index.json')[j['instance']]
        if 'certificate' in witness:
            U=Fraction(witness['certificate']['objective_exact_fraction']);B=outcome['bound'];C=outcome['objective']
            checks.update(known_U=str(U),bound_contradiction=B is not None and F(B)>U+F(max(1e-6,8*math.ulp(B))),gap_contradiction=bool(outcome['native_completed'] and U<F(C)-abs(F(C))/100))
        else:checks.update(known_U=None,bound_contradiction=None,gap_contradiction=None)
    native.dispose();env.dispose()
    dump(folder/'result.json',{'job':j,'parameters':params,'native_import':equality,'export_sha256':sha(path),'outcome':outcome,'checks':checks,'global_optimality_independently_verified':False})

def run():
    d=load(HERE/'solve-design.json')
    for p,h in d['dependencies'].items():assert sha(ROOT/p)==h,p
    assert not (HERE/'solve-timings.json').exists();records=[]
    for i,j in enumerate(d['jobs']):
        start=time.perf_counter()
        with (HERE/(j['id']+'-execution.log')).open('w') as log:
            p=subprocess.run([sys.executable,str(Path(__file__)),'worker',j['id']],cwd=ROOT,env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'},stdout=log,stderr=subprocess.STDOUT,timeout=240)
        records.append({'job':j,'returncode':p.returncode,'process_seconds':time.perf_counter()-start});dump(HERE/'solve-timings.json',records)
        assert p.returncode==0
        print(i+1,'/18',j['id'],round(records[-1]['process_seconds'],2),flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','witnesses','run','worker']);p.add_argument('job',nargs='?');a=p.parse_args()
    if a.stage=='worker':worker(a.job)
    else:globals()[a.stage]()
