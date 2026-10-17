#!/usr/bin/env python3
"""A fixed, local 6 x 2 x 3 x 4 comparison; preserve original data and models."""
import argparse
import csv
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

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
OLD=ROOT/'exploration/oms-followup-20261014'
WORKFLOW=ROOT/'exploration/oms-if1-workflow-20261015'
sys.path[:0]=[str(OLD),str(ROOT/'scripts/research'),str(ROOT/'scripts')]


def load(p):return json.loads(Path(p).read_text())
def dump(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def bound_flags(bound,objective,completed,witness):
    from fractions import Fraction
    F=Fraction.from_float
    return (bool(bound is not None and F(bound)>witness+F(max(1e-6,8*math.ulp(bound)))),
        bool(completed and objective is not None and witness<F(objective)-Fraction(1,100)*abs(F(objective))))


def library(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def generate(instance,folder):
    from validar_preprocesamiento import clean_instance_text
    base=folder/'Base.lp'
    commands=clean_instance_text(HERE/'inputs'/instance/'input.txt')
    text=(commands+'\nconfigurarSolver --DummyLp\npreprocesar --solodiagnostico\n'
          f'grabar {base} --noConstante\nsalir\n')
    (folder/'generator-commands.txt').write_text(text)
    with (folder/'generator.log').open('w') as log:
        p=subprocess.run([str(ROOT/'code/build-audit/SistemaElectrico')],input=text,text=True,
            cwd=ROOT/'code',stdout=log,stderr=subprocess.STDOUT,timeout=60)
    assert p.returncode==0 and base.is_file()
    return base


def prepare():
    import activation_study as a
    import measure_factor_cost as c
    from check_sgtm_demand import scan
    import gurobipy as gp
    assert gp.gurobi.version()==(13,0,2)
    with gp.Env(params={'OutputFlag':0}):pass
    if (HERE/'design.json').exists():raise RuntimeError('frozen design exists')
    bank=load(OLD/'confirmation-bank/design.json')
    selected=['instance001','instance005','instance022','instance027','instance031','instance046']
    items={r['instance']:r for r in bank['prepared']}
    instances={r['instance']:r for r in bank['instances']}
    inputs={};models={};witnesses={}
    deps=[Path(__file__),HERE/'PROTOCOL.md',OLD/'activation_study.py',OLD/'measure_factor_cost.py',
        WORKFLOW/'study.py',ROOT/'scripts/research/budget_scaling.py',
        ROOT/'scripts/research/oms_dispatch_validation.py',ROOT/'scripts/validar_preprocesamiento.py',
        ROOT/'scripts/research/audit_fixed_basis.py',ROOT/'scripts/audit_identifiability_grid.py',
        HERE/'test_endpoints.py']
    for name in selected:
        folder=HERE/'inputs'/name;folder.mkdir(parents=True)
        source=ROOT/instances[name]['input'];assert not scan([source])['defective']
        (folder/'input.txt').write_bytes(source.read_bytes())
        inputs[name]={'source':str(source.relative_to(ROOT)),'sha256':sha(source)}
        base=generate(name,folder)
        item=items[name];assert item['guided_gamma']==2.**-28
        assert sha(base)==item['exports']['Base']
        parsed,physical=a.original_rows(base);_,lp,_=a.campaign.afb.read_lp(base)
        assert len(parsed)==10080 and lp.num_col_==6120 and len(physical)==4320
        models[name]={'Base':sha(base)}
        for policy in ['L2-window','Budget-L2']:
            chosen=c.factors(parsed,lp,item['guided_gamma'],policy=='Budget-L2')
            dest=folder/(policy+'.lp');a.export_scaled(base,dest,chosen)
            assert sha(dest)==item['exports'][policy]
            models[name][policy]=sha(dest)
            wfolder=OLD/'exact-witnesses'/name/policy
            cert=load(wfolder/'independent-certificate.json')
            assert cert['original_model_sha256']==sha(dest)
            witnesses[name+'/'+policy]={'folder':str(wfolder.relative_to(ROOT)),'certificate':cert}
            deps.extend(wfolder/f for f in ['independent-certificate.json','exact-witness.json'])
        models[name]['changed_activation_rows']=item['budget_changed_rows']
        assert item['budget_changed_rows']==1440
        deps.extend([folder/'input.txt',base,folder/'L2-window.lp',folder/'Budget-L2.lp'])
        print('Prepared',name,'two native exports matched; no solves',flush=True)
    jobs=[{'instance':n,'presolve':p,'seed':s,'policy':m,
           'id':f'{n}-P{p}-s{s}-{m}'}
          for n in selected for p in [-1,0] for s in [11,23,47]
          for m in ['L2','Budget-L2','L2-tight','L2-NF3']]
    random.Random(20261016).shuffle(jobs)
    design={'date':'2026-10-16','retrospective_models':True,'instances':selected,'seeds':[11,23,47],
        'jobs':jobs,'inputs':inputs,'models':models,'witnesses':witnesses,
        'parameters':{'Threads':4,'TimeLimit':120.,'MIPGap':.01,'FeasibilityTol':1e-6,
            'IntFeasTol':2.**-28,'ScaleFlag':-1,'IntegralityFocus':0,'NumericFocus':0},
        'budgets':{'MW':.01,'m3':100.},'native_mip_calls_assigned':144,'new_lp_calls':0,
        'dependencies':{str(p.relative_to(ROOT)):sha(p) for p in deps},
        'generator_binary_sha256':sha(ROOT/'code/build-audit/SistemaElectrico'),
        'local_hostname':os.uname().nodename,'shared_machine':True,
        'total_time_scope':'complete fresh Python process; generator through verification and persistence'}
    protected={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'paper/submission/oms/releases').rglob('*') if p.is_file()}
    protected.update({str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'exploration').rglob('*.zip')})
    dump(HERE/'protected-files.json',protected)
    dump(HERE/'design.json',design)
    (HERE/'snapshot-study.py').write_bytes(Path(__file__).read_bytes())
    print('Frozen 144 assignments; no MILP optimized',flush=True)


def worker(job_id,started):
    from fractions import Fraction
    import numpy as np
    import gurobipy as gp
    import activation_study as a
    import measure_factor_cost as c
    wf=library(WORKFLOW/'study.py','archived_workflow')
    F=Fraction.from_float
    d=load(HERE/'design.json');job=next(j for j in d['jobs'] if j['id']==job_id)
    folder=HERE/'runs'/job_id;folder.mkdir(parents=True)
    stages={}
    def timed(key,f):
        t=time.perf_counter();result=f();stages[key]=time.perf_counter()-t;return result
    base=timed('generator',lambda:generate(job['instance'],folder))
    def metadata():
        parsed,physical=a.original_rows(base);_,lp,matrix=a.campaign.afb.read_lp(base)
        return parsed,physical,lp,matrix
    parsed,physical,lp,matrix=timed('metadata',metadata)
    factors=timed('factor_selection',lambda:c.factors(parsed,lp,2.**-28,job['policy']=='Budget-L2'))
    source='Budget-L2' if job['policy']=='Budget-L2' else 'L2-window'
    export=folder/'scaled.lp'
    timed('scaled_export',lambda:a.export_scaled(base,export,factors))
    def integrity():
        assert sha(base)==d['models'][job['instance']]['Base']
        assert sha(export)==d['models'][job['instance']][source]
        _,native_lp,native_a=a.campaign.afb.read_lp(export)
        return native_lp,native_a
    native_lp,native_a=timed('integrity',integrity)
    params={**d['parameters'],'Presolve':job['presolve'],'Seed':job['seed']}
    if job['policy']=='L2-tight':params.update(FeasibilityTol=1e-9,IntFeasTol=1e-9)
    if job['policy']=='L2-NF3':params['NumericFocus']=3
    def native():
        env=gp.Env(params={'OutputFlag':0});model=gp.read(str(export),env=env)
        model.setParam('OutputFlag',1);model.setParam('LogToConsole',0)
        model.setParam('LogFile',str(folder/'solver.log'))
        for key,value in params.items():model.setParam(key,value)
        return env,model
    env,model=timed('native_import',native)
    imported=timed('native_equality_check',lambda:wf.check_import(model,native_lp,native_a))
    timed('solve',model.optimize)
    def extraction():
        result={'status':model.Status,'solutions':model.SolCount,'native_completed':model.Status==2,
            'work':model.Work,'nodes':model.NodeCount,'native_runtime':model.Runtime,
            'objective':model.ObjVal if model.SolCount else None,
            'bound':model.ObjBound if math.isfinite(model.ObjBound) else None,
            'gap':model.MIPGap if model.SolCount and math.isfinite(model.MIPGap) else None}
        values=None
        if model.SolCount:
            names=[v.VarName for v in model.getVars()];x=model.getAttr('X',model.getVars())
            np.savez_compressed(folder/'solution.npz',names=np.array(names),x=np.array(x))
            values=dict(zip(names,x))
        return result,values
    result,values=timed('extraction',extraction)
    def verification():
        U=Fraction(d['witnesses'][job['instance']+'/'+source]['certificate']['objective_exact_fraction'])
        bound_flag,gap_flag=bound_flags(result['bound'],result['objective'],result['native_completed'],U)
        if values is None:return {'candidate_present':False,'audited_budgets_pass':False,
            'known_witness_objective_exact':str(U),
            'bound_contradiction':bound_flag,'completion_contradiction':gap_flag}
        assert all(math.isfinite(v) for v in values.values())
        integers={n for n,k in zip(lp.col_names_,lp.integrality_) if str(k)!='HighsVarType.kContinuous'}
        checked=a.audit_values(physical,values,integers)
        outcome={'candidate_present':True,'physical':checked,
            'raw_max_ratio':max(r['raw_max']/d['budgets'][r['unit']] for r in checked),
            'rounded_max_ratio':max(r['rounded_max']/d['budgets'][r['unit']] for r in checked),
            'integer_violation':max(abs(values[n]-round(values[n])) for n in integers)}
        point=np.array([values[n] for n in lp.col_names_]);rounded=point.copy()
        for i,n in enumerate(lp.col_names_):
            if n in integers:rounded[i]=round(point[i])
        lower,upper=np.array(lp.col_lower_),np.array(lp.col_upper_)
        for label,x in [('raw',point),('rounded',rounded)]:
            outcome[label+'_bound_violation']=float(np.max(np.maximum(np.maximum(lower-x,x-upper),0.)))
            activity=matrix@x;row_l=np.array(lp.row_lower_);row_u=np.array(lp.row_upper_)
            violation=np.maximum(np.maximum(row_l-activity,activity-row_u),0.)
            scale=np.maximum(1.,np.maximum(abs(matrix)@abs(x),np.maximum(np.where(np.isfinite(row_l),abs(row_l),0.),np.where(np.isfinite(row_u),abs(row_u),0.))))
            outcome[label+'_max_activity_normalized_violation']=float(np.max(violation/scale))
        objective=sum((F(float(cost))*F(values[n]) for n,cost in zip(lp.col_names_,lp.col_cost_)),F(float(lp.offset_)))
        assert abs(objective-F(result['objective']))<=F(max(1e-6,8*math.ulp(result['objective'])))
        outcome['point_objective_exact']=str(objective)
        outcome.update(audited_budgets_pass=outcome['rounded_max_ratio']<=1,
            known_witness_objective_exact=str(U),
            bound_contradiction=bound_flag,completion_contradiction=gap_flag)
        return outcome
    checked=timed('verification',verification)
    timed('native_cleanup',lambda:(model.dispose(),env.dispose()))
    dump(folder/'result.json',{'job':job,'parameters':params,'source':source,
        'input_sha256':sha(HERE/'inputs'/job['instance']/'input.txt'),
        'base_sha256':sha(base),'export_sha256':sha(export),'native_import':imported,
        'outcome':result,'checks':checked,'stages_seconds':stages,
        'worker_internal_seconds_before_result':time.perf_counter()-started,
        'native_global_optimality_independently_verified':False})


def run():
    d=load(HERE/'design.json')
    for path,h in d['dependencies'].items():assert sha(ROOT/path)==h,path
    assert sha(ROOT/'code/build-audit/SistemaElectrico')==d['generator_binary_sha256']
    recorded=load(HERE/'parent-timing.json') if (HERE/'parent-timing.json').exists() else []
    done={r['job']['id'] for r in recorded if r['returncode']==0}
    assert len(done)==len(recorded),'a failed assignment is preserved; do not silently rerun it'
    for index,job in enumerate(d['jobs']):
        if job['id'] in done:continue
        assert not (HERE/'runs'/job['id']).exists(),'unrecorded previous output; inspect before resuming'
        env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'}
        start=time.perf_counter()
        with (HERE/(job['id']+'-execution.log')).open('w') as log:
            try:
                p=subprocess.run([sys.executable,str(Path(__file__)),'worker',job['id']],cwd=ROOT,
                    env=env,stdout=log,stderr=subprocess.STDOUT,timeout=240)
                returncode=p.returncode
            except subprocess.TimeoutExpired:
                returncode=124
        record={'job':job,'returncode':returncode,'total_seconds':time.perf_counter()-start,
                'load_average':os.getloadavg()}
        recorded.append(record);dump(HERE/'parent-timing.json',recorded)
        if returncode:raise RuntimeError('preserved failed worker '+job['id'])
        r=load(HERE/'runs'/job['id']/'result.json')
        print(index+1,'/144',job['id'],'Work',round(r['outcome']['work'],4),
            'budgets',r['checks']['audited_budgets_pass'],'B flag',r['checks']['bound_contradiction'],
            'seconds',round(record['total_seconds'],2),flush=True)


if __name__=='__main__':
    started=time.perf_counter()
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','run','worker']);p.add_argument('job',nargs='?')
    args=p.parse_args()
    if args.stage=='prepare':prepare()
    elif args.stage=='run':run()
    else:worker(args.job,started)
