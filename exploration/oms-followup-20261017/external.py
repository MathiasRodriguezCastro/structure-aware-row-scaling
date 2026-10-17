"""Prospective, bounded STN transfer validation, retaining previous negative evidence."""
import argparse
import csv
from fractions import Fraction
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import time
from common import HERE,ROOT,F,load,dump,sha,module,exact_witness

OUT=HERE/'external'
SOURCE=ROOT/'exploration/oms-generalization-20261014'
HORIZONS=[8,10,12,16,20,24,32,40]
POLICIES=['L2','Budget-L2','L2-tight','L2-NF3']
GAMMA=1e-9

def source():return module(SOURCE/'generalization_study.py','archived_STN_adapter')

def choose(model,budget):
    from budget_scaling import dyadic_factor
    result=[];decisions=[]
    for j,r in enumerate(model['rows']):
        coefficients=[float(v) for v in r['terms'].values()]
        E=F(GAMMA)*sum((abs(F(float(v))) for i,v in r['terms'].items() if model['variables'][int(i)]['integer']),Fraction(0)) if budget else Fraction(0)
        reserve=float(E)
        if F(reserve)<E:reserve=math.nextafter(reserve,math.inf)
        decision=dyadic_factor(coefficients,r['rhs'],delta=r['budget'] if budget else None,epsilon=1e-6,rounding_allowance=reserve)
        alpha=None
        if decision.factor is not None:
            z=math.log2(1./math.sqrt(sum(c*c for c in coefficients)))
            lo,hi=round(math.log2(decision.lower)),round(math.log2(decision.upper))
            ks={min(hi,max(lo,math.floor(z))),min(hi,max(lo,math.ceil(z)))}
            k=min(ks,key=lambda k:(abs(k-z),-k));alpha=math.ldexp(1.,k)
            if budget:assert F(1e-6)/F(alpha)+E<=F(r['budget'])
        result.append(alpha);decisions.append({'row':j,'source_row':r['name'],'unit':r['unit'],'budget':r['budget'],
            'factor':alpha,'integer_reserve_exact':str(E),'reason':decision.reason})
    return result,decisions

def export(path,model,factors):
    lines=['Minimize\n obj:\n']
    for i,v in enumerate(model['variables']):
        if v['cost']:lines.append(f'  {v["cost"]:+.17g} x{i:05d}\n')
    lines.append('s.t.\n')
    for j,(r,alpha) in enumerate(zip(model['rows'],factors)):
        lines.append(f' r{j:05d}:\n')
        for i,c in r['terms'].items():
            value=alpha*c;assert F(value)==F(alpha)*F(c)
            lines.append(f'  {value:+.17g} x{int(i):05d}\n')
        rhs=alpha*r['rhs'];assert F(rhs)==F(alpha)*F(r['rhs'])
        lines.append('  '+{'=':'=','<':'<=','>':'>='}[r['sense']]+f' {rhs:.17g}\n')
    lines.append('Bounds\n')
    for i,v in enumerate(model['variables']):
        n=f'x{i:05d}';lo,hi=v['lower'],v['upper']
        if lo is None:
            lines.append(f' {n} free\n')
            if hi is not None:lines.append(f' {n} <= {hi:.17g}\n')
        elif hi is None:lines.append(f' {n} >= {lo:.17g}\n')
        else:lines.append(f' {lo:.17g} <= {n} <= {hi:.17g}\n')
    lines.append('Generals\n '+' '.join(f'x{i:05d}' for i,v in enumerate(model['variables']) if v['integer'])+'\nEnd\n')
    path.write_text(''.join(lines))

def prepare():
    assert not (OUT/'design.json').exists();OUT.mkdir(exist_ok=True)
    g=source();models={}
    for horizon in HORIZONS:
        model=g.scheduling_model(horizon)
        model['source_suggested_gamma']=model['guided_gamma'];model['guided_gamma']=GAMMA
        folder=OUT/'models'/model['name'];folder.mkdir(parents=True)
        dump(folder/'original-model.json',model)
        factors={};exports={}
        for key in ['Base','L2','Budget-L2']:
            fs,records=([1.]*len(model['rows']),[]) if key=='Base' else choose(model,key=='Budget-L2')
            factors[key]=fs
            if all(a is not None for a in fs):
                p=folder/(key+'.lp');export(p,model,fs);exports[key]=sha(p)
            if records:dump(folder/(key+'-decisions.json'),records)
        dump(folder/'factors.json',factors)
        models[model['name']]={'horizon':horizon,'known_pilot_anchor':horizon in [10,12],
            'rows':len(model['rows']),'variables':len(model['variables']),'exports':exports,
            'changed_factors':sum(a!=b for a,b in zip(factors['L2'],factors['Budget-L2'])),
            'incompatible_rows':sum(a is None for a in factors['Budget-L2']),
            'original_model_sha256':sha(folder/'original-model.json')}
        print(model['name'],models[model['name']]['rows'],'rows; changed',models[model['name']]['changed_factors'],flush=True)
    refs=[{'instance':n,'horizon':v['horizon'],'policy':'Reference-NF3','seed':127,'id':n+'-reference-127'} for n,v in models.items()]
    jobs=[{'instance':n,'horizon':v['horizon'],'policy':p,'seed':s,'id':f'{n}-{p}-{s}'} for n,v in models.items() for p in POLICIES for s in [131,137,149]]
    random.Random(2026101702).shuffle(refs);random.Random(2026101703).shuffle(jobs)
    deps=[Path(__file__),HERE/'common.py',HERE/'PROTOCOL.md',SOURCE/'generalization_study.py',SOURCE/'independent_check.py',
        SOURCE/'sources/STN-Scheduler/STN/STN.py',SOURCE/'sources/STN-Scheduler/STN/kondili.py',ROOT/'scripts/research/budget_scaling.py']
    dump(OUT/'design.json',{'date':'2026-10-17','models':models,'references':refs,'jobs':jobs,
        'parameters':{'Threads':4,'TimeLimit':30.,'MIPGap':.01,'Presolve':-1,'ScaleFlag':-1,'FeasibilityTol':1e-6,'IntFeasTol':GAMMA,'IntegralityFocus':0,'NumericFocus':0},
        'budgets':{'mass_kg':1e-5,'logical':1e-5,'source_monetary_units':1e-3},
        'dependencies':{str(p.relative_to(ROOT)):sha(p) for p in deps},
        'prior_pilot_no_added_primal_acceptance_advantage':True,'new_horizons':[h for h in HORIZONS if h not in [10,12]],
        'source_commit':'3b1d5f3adfb1165c06ca496775047d683886ab52','source_url':'https://github.com/jckantor/STN-Scheduler',
        'comparison_seeds':[131,137,149],'reference_seed':127,'no_external_population_generality_claim':True})

def worker(jobid,start):
    import gurobipy as gp
    import numpy as np
    d=load(OUT/'design.json');job=next(j for j in d['references']+d['jobs'] if j['id']==jobid)
    ref=job['policy']=='Reference-NF3';folder=OUT/('references' if ref else 'runs')/jobid;folder.mkdir(parents=True)
    stages={}
    def timed(key,fn):
        t=time.perf_counter();v=fn();stages[key]=time.perf_counter()-t;return v
    g=source()
    model=timed('generation',lambda:g.scheduling_model(job['horizon']))
    model['source_suggested_gamma']=model['guided_gamma'];model['guided_gamma']=GAMMA
    prepared=OUT/'models'/job['instance'];fixed=load(prepared/'original-model.json')
    # The upstream ConstraintList follows Python sets. Recover the frozen row
    # order only after checking the entire mathematical multiset, with duplicates.
    import json
    def row_multiset(rows):
        return sorted(json.dumps({k:v for k,v in r.items() if k!='name'},sort_keys=True) for r in rows)
    assert row_multiset(model['rows'])==row_multiset(fixed['rows'])
    model['rows']=fixed['rows']
    assert model==fixed
    key='Base' if ref else 'Budget-L2' if job['policy']=='Budget-L2' else 'L2'
    fs=timed('selection',lambda:[1.]*len(model['rows']) if ref else choose(model,key=='Budget-L2')[0])
    assert fs==load(prepared/'factors.json')[key]
    if any(a is None for a in fs):
        dump(folder/'result.json',{'job':job,'abstained':True,'stages_seconds':stages});return
    path=folder/'scaled.lp';timed('export',lambda:export(path,model,fs))
    assert sha(path)==d['models'][job['instance']]['exports'][key]
    params={**d['parameters'],'Seed':job['seed']}
    if job['policy']=='L2-tight':params['FeasibilityTol']=1e-9
    if job['policy'] in ['L2-NF3','Reference-NF3']:params['NumericFocus']=3
    def native():
        env=gp.Env(params={'OutputFlag':0});m=gp.read(str(path),env=env)
        m.Params.OutputFlag=1;m.Params.LogToConsole=0;m.Params.LogFile=str(folder/'solver.log')
        for k,v in params.items():m.setParam(k,v)
        return env,m
    env,m=timed('native_import',native)
    def equality():
        rows=[]
        for c in m.getConstrs():
            e=m.getRow(c);rows.append((c.ConstrName,{e.getVar(k).VarName:float(e.getCoeff(k)) for k in range(e.size())},c.Sense,float(c.RHS)))
        variables=m.getVars();names=[v.VarName for v in variables]
        data=[(v.VarName,g.finite(v.LB) if abs(v.LB)<1e100 else None,g.finite(v.UB) if abs(v.UB)<1e100 else None,v.VType!='C',float(v.Obj)) for v in variables]
        g.check_import(model,fs,names,rows,data)
        assert m.ModelSense==1 and m.ObjCon==0
        return {'rows':len(rows),'variables':len(variables),'all_data_equal':True}
    equality_result=timed('native_equality',equality)
    timed('solve',m.optimize)
    outcome={'status':m.Status,'solutions':m.SolCount,'native_completed':m.Status==2,'work':m.Work,'native_runtime':m.Runtime,
        'objective':m.ObjVal if m.SolCount else None,'bound':float(m.ObjBound) if math.isfinite(m.ObjBound) else None}
    def extract():
        if not m.SolCount:return None
        xs=np.array([m.getVarByName(f'x{i:05d}').X for i in range(len(model['variables']))])
        np.savez_compressed(folder/'solution.npz',names=np.array([f'x{i:05d}' for i in range(len(xs))]),x=xs)
        return xs
    x=timed('extraction',extract)
    checked=timed('original_unit_verification',lambda:g.verify_point(model,x)) if x is not None else None
    index=load(OUT/'witness-index.json') if (OUT/'witness-index.json').exists() else {}
    record=index.get(job['instance'],{});U=Fraction(record['certificate']['objective_exact_fraction']) if record.get('certificate') else None
    flags={'witness_objective_exact':str(U) if U is not None else None,
        'bound_contradiction':bool(F(outcome['bound'])>U+F(max(1e-6,8*math.ulp(outcome['bound'])))) if U is not None and outcome['bound'] is not None else None,
        'completion_contradiction':bool(outcome['native_completed'] and U<F(outcome['objective'])-Fraction(1,100)*abs(F(outcome['objective']))) if U is not None and outcome['objective'] is not None else None}
    timed('cleanup',lambda:(m.dispose(),env.dispose()))
    dump(folder/'result.json',{'job':job,'abstained':False,'parameters':params,'stages_seconds':stages,
        'export_sha256':sha(path),'model_key':key,'native_import':equality_result,'outcome':outcome,'verification':checked,'flags':flags,
        'worker_seconds_before_persistence':time.perf_counter()-start,'global_optimality_independently_verified':False})

def execute(which):
    d=load(OUT/'design.json')
    for p,h in d['dependencies'].items():assert sha(ROOT/p)==h,p
    timing=OUT/(which+'-timing.json');assert not timing.exists()
    records=[]
    for i,job in enumerate(d[which]):
        start=time.perf_counter()
        with (OUT/(job['id']+'-execution.log')).open('w') as log:
            p=subprocess.run([sys.executable,str(Path(__file__)),'worker',job['id']],cwd=ROOT,
                env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'},stdout=log,stderr=subprocess.STDOUT,timeout=90)
        records.append({'job':job,'returncode':p.returncode,'total_fresh_process_seconds':time.perf_counter()-start,'system_load_after':os.getloadavg()})
        dump(timing,records);print(i+1,'/',len(d[which]),job['id'],round(records[-1]['total_fresh_process_seconds'],3),flush=True)
        assert p.returncode==0,'Failed attempt retained; no automatic retry'

def witnesses():
    d=load(OUT/'design.json');index={}
    for j in d['references']:
        folder=OUT/'references'/j['id'];model=OUT/'models'/j['instance']/'Base.lp'
        try:index[j['instance']]=exact_witness(OUT/'witnesses'/j['instance'],model,folder/'solution.npz',10)
        except Exception as ex:index[j['instance']]={'error':str(ex),'lp_calls':int((OUT/'witnesses'/j['instance']/'solver-provenance.json').exists())}
        dump(OUT/'witness-index.json',index)
    print('Exactly feasible reference witnesses:',sum(bool(r.get('certificate')) for r in index.values()),'/',len(index),flush=True)

if __name__=='__main__':
    started=time.perf_counter();p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','references','witnesses','run','worker']);p.add_argument('job',nargs='?');a=p.parse_args()
    if a.stage=='worker':worker(a.job,started)
    elif a.stage in ['references','run']:execute('references' if a.stage=='references' else 'jobs')
    else:globals()[a.stage]()
