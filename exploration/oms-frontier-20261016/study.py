#!/usr/bin/env python3
"""Prespecified multi-budget study. All new outputs stay in this directory."""
import argparse
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

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
OLD=ROOT/'exploration/oms-followup-20261014'
MATCHED=ROOT/'exploration/oms-matched-accuracy-20261016'
sys.path[:0]=[str(OLD),str(ROOT/'scripts/research'),str(ROOT/'scripts')]
F=Fraction.from_float
BUDGETS=[10,30,100,300,1000,3000,10000]
INSTANCES=['instance001','instance005','instance022','instance027','instance031','instance046']

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def dump(p,d):Path(p).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def library(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def choose(parsed,lp,budget):
    import activation_study as a
    integers={n for n,k in zip(lp.col_names_,lp.integrality_) if str(k)!='HighsVarType.kContinuous'}
    boxes={n:max(abs(float(l)),abs(float(u))) for n,l,u in zip(lp.col_names_,lp.col_lower_,lp.col_upper_)}
    factors={};blocked=[];active=0;reserves=[]
    for name,row in parsed.items():
        delta=1e100;reserve=0.
        if budget is not None:
            spec=a.campaign.physical_spec(name,row['terms'])
            if spec:_,unit,conversion=spec
            elif a.activation_spec(name,row):unit,conversion='m3',1.
            else:unit=None
            if unit:
                delta=(.01 if unit=='MW' else budget)*conversion
                e=F(1e-9)*sum((F(abs(float(v))) for n,v in row['terms'].items() if n in integers),Fraction(0))
                rho=Fraction(0)
                if a.ACT.fullmatch(name):
                    rho=F(2.**-52)*(sum((F(abs(float(v)))*F(boxes[n]) for n,v in row['terms'].items()),Fraction(0))+F(abs(float(row['rhs']))))
                    reserves.append(float(e))
                reserve=float(e+rho)
                if F(reserve)<e+rho:reserve=math.nextafter(reserve,math.inf)
        result=a.select_factor(list(row['terms'].values()),delta,kernel='l2',rounding_allowance=reserve)
        if result.factor is None:
            blocked.append({'row':name,'reason':result.reason,'delta':delta,'reserve':reserve})
        else:
            factors[name]=result.factor
            active+=result.reason=='projected'
    return factors,{'incompatible':blocked,'incompatible_count':len(blocked),
        'projected_rows':active,'max_integer_rounding_reserve_m3':max(reserves,default=0.)}

def generate(instance,folder):
    from validar_preprocesamiento import clean_instance_text
    base=folder/'Base.lp'
    text=clean_instance_text(HERE/'models'/instance/'input.txt')+'\nconfigurarSolver --DummyLp\npreprocesar --solodiagnostico\n'+f'grabar {base} --noConstante\nsalir\n'
    (folder/'generator-commands.txt').write_text(text)
    with (folder/'generator.log').open('w') as log:
        p=subprocess.run([str(ROOT/'code/build-audit/SistemaElectrico')],input=text,text=True,cwd=ROOT/'code',stdout=log,stderr=subprocess.STDOUT,timeout=60)
    assert p.returncode==0 and base.is_file();return base

def prepare():
    import activation_study as a
    if (HERE/'design.json').exists():raise RuntimeError('design already frozen')
    protected={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'paper/submission/oms/releases').rglob('*') if p.is_file()}
    protected.update({str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'exploration').rglob('*.zip')})
    dump(HERE/'protected-files.json',protected)
    models={};inputs={}
    for name in INSTANCES:
        folder=HERE/'models'/name;folder.mkdir(parents=True)
        for filename in ['Base.lp','input.txt']:(folder/filename).write_bytes((MATCHED/'inputs'/name/filename).read_bytes())
        parsed,physical=a.original_rows(folder/'Base.lp');_,lp,_=a.campaign.afb.read_lp(folder/'Base.lp')
        assert len(parsed)==10080 and lp.num_col_==6120 and len(physical)==4320
        inputs[name]={'base_sha256':sha(folder/'Base.lp'),'input_sha256':sha(folder/'input.txt')}
        for budget in [None,*BUDGETS]:
            key='L2' if budget is None else 'B'+str(budget)
            factors,info=choose(parsed,lp,budget)
            record={**info,'budget':budget,'model':None,'export_sha256':None}
            if not info['incompatible_count']:
                path=folder/(key+'.lp');a.export_scaled(folder/'Base.lp',path,factors)
                record.update(model=str(path.relative_to(ROOT)),export_sha256=sha(path))
            models[name+'/'+key]=record
        print('Prepared',name,flush=True)
    jobs=[{'instance':n,'presolve':p,'seed':s,'policy':policy,'budget':b,
           'key':'B'+str(b) if b is not None else 'L2',
           'id':f'{n}-P{p}-s{s}-{policy}'+('' if b is None else str(b))}
          for n in INSTANCES for p in [-1,0] for s in [59,71,89]
          for policy,b in [('L2',None),('L2-tight',None),('L2-NF3',None),*[('Budget-L2',b) for b in BUDGETS]]]
    random.Random(2026101601).shuffle(jobs)
    dependencies=[Path(__file__),HERE/'PROTOCOL.md',OLD/'activation_study.py',OLD/'exact_dispatch_witness.py',
        ROOT/'scripts/research/budget_scaling.py',ROOT/'scripts/research/oms_dispatch_validation.py',
        ROOT/'scripts/validar_preprocesamiento.py',ROOT/'scripts/research/audit_fixed_basis.py',ROOT/'scripts/audit_identifiability_grid.py',
        ROOT/'exploration/oms-if1-workflow-20261015/study.py']
    for name in INSTANCES:
        meta=load(OLD/'exact-witnesses'/name/'Budget-L2/mapping.json')
        dependencies.append(ROOT/meta['saved_solution'])
    dump(HERE/'design.json',{'date':'2026-10-16','jobs':jobs,'models':models,'inputs':inputs,
        'instances':INSTANCES,'seeds':[59,71,89],'volume_budgets':BUDGETS,'power_budget_MW':.01,
        'parameters':{'Threads':4,'TimeLimit':120.,'MIPGap':.01,'FeasibilityTol':1e-6,'IntFeasTol':1e-9,'ScaleFlag':-1,'IntegralityFocus':0,'NumericFocus':0},
        'dependencies':{str(p.relative_to(ROOT)):sha(p) for p in dependencies},
        'generator_binary_sha256':sha(ROOT/'code/build-audit/SistemaElectrico'),
        'shared_machine':True,'hostname':os.uname().nodename,'prior_known_models':True})
    (HERE/'snapshot-study.py').write_bytes(Path(__file__).read_bytes())
    print('Frozen',len(jobs),'assignments;',sum(bool(models[j['instance']+'/'+j['key']]['incompatible_count']) for j in jobs),'abstentions before solves',flush=True)

def witnesses():
    import exact_dispatch_witness as e
    d=load(HERE/'design.json');records={};byhash={}
    binary=OLD/'tools/soplex-build/bin/soplex'
    for key,model in d['models'].items():
        if model['model'] is None:continue
        start=time.perf_counter();h=model['export_sha256']
        if h in byhash:
            records[key]={'alias':byhash[h]};continue
        out=HERE/'witnesses'/key;source=load(OLD/'exact-witnesses'/key.split('/')[0]/'Budget-L2/mapping.json')['saved_solution']
        try:
            e.prepare(out,ROOT/model['model'],ROOT/source);e.solve(out,binary);e.check(out)
            records[key]={'folder':str(out.relative_to(ROOT)),'certificate':load(out/'independent-certificate.json'),'seconds':time.perf_counter()-start,'lp_calls':1}
        except Exception as error:
            records[key]={'error':type(error).__name__+': '+str(error),'seconds':time.perf_counter()-start,'lp_calls':int((out/'solver-provenance.json').exists())}
        byhash[h]=key;dump(HERE/'witness-index.json',records)
        print('Witness',key,'certified',bool(records[key].get('certificate')),flush=True)
    dump(HERE/'witness-index.json',records)

def witness(key):
    records=load(HERE/'witness-index.json');r=records[key]
    while 'alias' in r:r=records[r['alias']]
    return Fraction(r['certificate']['objective_exact_fraction']) if 'certificate' in r else None

def worker(job_id,started):
    import numpy as np
    import gurobipy as gp
    import activation_study as a
    wf=library(ROOT/'exploration/oms-if1-workflow-20261015/study.py','workflow_native_check')
    d=load(HERE/'design.json');job=next(j for j in d['jobs'] if j['id']==job_id)
    folder=HERE/'runs'/job_id;folder.mkdir(parents=True)
    stages={}
    def timed(key,fun):
        t=time.perf_counter();v=fun();stages[key]=time.perf_counter()-t;return v
    base=timed('generator',lambda:generate(job['instance'],folder))
    parsed,physical=timed('parse_original',lambda:a.original_rows(base))
    _,lp,matrix=timed('matrix_metadata',lambda:a.campaign.afb.read_lp(base))
    factors,info=timed('factor_selection',lambda:choose(parsed,lp,job['budget']))
    assert not info['incompatible_count']
    export=folder/'scaled.lp';timed('scaled_export',lambda:a.export_scaled(base,export,factors))
    expected=d['models'][job['instance']+'/'+job['key']]
    assert sha(base)==d['inputs'][job['instance']]['base_sha256']
    assert sha(export)==expected['export_sha256']
    _,native_lp,native_a=timed('export_metadata',lambda:a.campaign.afb.read_lp(export))
    params={**d['parameters'],'Presolve':job['presolve'],'Seed':job['seed']}
    if job['policy']=='L2-tight':params.update(FeasibilityTol=1e-9,IntFeasTol=1e-9)
    if job['policy']=='L2-NF3':params['NumericFocus']=3
    def native():
        env=gp.Env(params={'OutputFlag':0});model=gp.read(str(export),env=env)
        model.setParam('OutputFlag',1);model.setParam('LogToConsole',0);model.setParam('LogFile',str(folder/'solver.log'))
        for k,v in params.items():model.setParam(k,v)
        return env,model
    env,model=timed('native_import',native)
    equality=timed('native_equality_check',lambda:wf.check_import(model,native_lp,native_a))
    timed('solve',model.optimize)
    def extraction():
        r={'status':model.Status,'solutions':model.SolCount,'native_completed':model.Status==2,'work':model.Work,
           'nodes':model.NodeCount,'native_runtime':model.Runtime,'objective':model.ObjVal if model.SolCount else None,
           'bound':model.ObjBound if math.isfinite(model.ObjBound) else None}
        values=None
        if model.SolCount:
            names=[v.VarName for v in model.getVars()];x=model.getAttr('X',model.getVars())
            np.savez_compressed(folder/'solution.npz',names=np.array(names),x=np.array(x));values=dict(zip(names,x))
        return r,values
    outcome,values=timed('extraction',extraction)
    def verification():
        U=witness(job['instance']+'/'+job['key'])
        r={'known_witness_objective_exact':None if U is None else str(U),
           'bound_contradiction':None if U is None else bool(outcome['bound'] is not None and F(outcome['bound'])>U+F(max(1e-6,8*math.ulp(outcome['bound'])))),
           'completion_contradiction':None if U is None else bool(outcome['native_completed'] and outcome['objective'] is not None and U<F(outcome['objective'])-Fraction(1,100)*abs(F(outcome['objective'])))}
        if values is None:return {**r,'candidate_present':False,'physical':None}
        assert all(math.isfinite(v) for v in values.values())
        integers={n for n,k in zip(lp.col_names_,lp.integrality_) if str(k)!='HighsVarType.kContinuous'}
        rows=a.audit_values(physical,values,integers)
        original_objective=sum((F(float(c))*F(values[n]) for n,c in zip(lp.col_names_,lp.col_cost_)),F(float(lp.offset_)))
        observed=[]
        native_rows,_=a.parse(export)
        for n in physical:observed.append(a.campaign.exact_violation(native_rows[n]['terms'],native_rows[n]['rhs'],values,native_rows[n]['sense']))
        r.update(candidate_present=True,physical=rows,point_objective_exact=str(original_objective),
            max_integer_violation=max(abs(values[n]-round(values[n])) for n in integers),
            observed_exported_physical_max_violation=float(max(observed)),
            exported_physical_rows_exceeding_epsilon=sum(v>F(1e-6) for v in observed),
            integer_gamma_hypothesis_holds=max(abs(values[n]-round(values[n])) for n in integers)<=params['IntFeasTol'])
        return r
    checks=timed('verification',verification)
    timed('cleanup',lambda:(model.dispose(),env.dispose()))
    dump(folder/'result.json',{'job':job,'parameters':params,'base_sha256':sha(base),'export_sha256':sha(export),
        'native_import':equality,'outcome':outcome,'checks':checks,'factor_info':info,'stages_seconds':stages,
        'worker_internal_seconds_before_result':time.perf_counter()-started,'global_optimality_independently_verified':False})

def run():
    d=load(HERE/'design.json')
    for p,h in d['dependencies'].items():assert sha(ROOT/p)==h,p
    assert sha(ROOT/'code/build-audit/SistemaElectrico')==d['generator_binary_sha256']
    parent=load(HERE/'parent-timing.json') if (HERE/'parent-timing.json').exists() else []
    done={r['job']['id'] for r in parent};assert len(done)==len(parent)
    assert all(r['returncode']==0 for r in parent),'failure retained; inspect before resuming'
    for i,job in enumerate(d['jobs']):
        if job['id'] in done:continue
        item=d['models'][job['instance']+'/'+job['key']]
        if item['incompatible_count']:
            parent.append({'job':job,'abstained':True,'returncode':0,'total_fresh_process_seconds':0.})
        else:
            assert not (HERE/'runs'/job['id']).exists(),'unrecorded output requires explicit amendment'
            start=time.perf_counter()
            with (HERE/(job['id']+'-execution.log')).open('w') as log:
                try:
                    p=subprocess.run([sys.executable,str(Path(__file__)),'worker',job['id']],cwd=ROOT,
                        env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'},stdout=log,stderr=subprocess.STDOUT,timeout=240)
                    rc=p.returncode
                except subprocess.TimeoutExpired:rc=124
            parent.append({'job':job,'abstained':False,'returncode':rc,'total_fresh_process_seconds':time.perf_counter()-start})
        dump(HERE/'parent-timing.json',parent)
        print(i+1,'/360',job['id'],'abstain' if item['incompatible_count'] else 'seconds '+str(round(parent[-1]['total_fresh_process_seconds'],2)),flush=True)
        if parent[-1]['returncode']!=0:raise RuntimeError('failed assignment retained')

if __name__=='__main__':
    start=time.perf_counter();p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','witnesses','run','worker']);p.add_argument('job',nargs='?');args=p.parse_args()
    if args.stage=='worker':worker(args.job,start)
    else:globals()[args.stage]()
