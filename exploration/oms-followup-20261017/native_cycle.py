"""Paired full-process benchmark using the already verified, isolated C++ binary."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import time
from common import HERE,ROOT,FRONT,OLD,INSTANCES,F,load,dump,sha,module,choose

OUT=HERE/'native-cycle'
NATIVE=ROOT/'exploration/oms-native-selector-20261016'

def fingerprint(lp,a):
    m=a.tocsr(copy=True);m.sort_indices()
    d={'columns':list(lp.col_names_),'rows':list(lp.row_names_),'sense':str(lp.sense_),'offset':float(lp.offset_).hex(),
        'column_data':[[float(c).hex(),float(l).hex(),float(u).hex(),str(k)] for c,l,u,k in zip(lp.col_cost_,lp.col_lower_,lp.col_upper_,lp.integrality_)],
        'row_data':[[float(l).hex(),float(u).hex()] for l,u in zip(lp.row_lower_,lp.row_upper_)],
        'indptr':m.indptr.tolist(),'indices':m.indices.tolist(),'values':[float(v).hex() for v in m.data]}
    return hashlib.sha256(json.dumps(d,separators=(',',':')).encode()).hexdigest()

def prepare():
    import activation_study as a
    assert not (OUT/'design.json').exists();OUT.mkdir(exist_ok=True)
    models={}
    for instance in INSTANCES:
        records=[]
        for backend in ['python','cpp']:
            p=NATIVE/'preflight'/instance/'Budget-L2'/backend/'scaled.lp'
            _,lp,matrix=a.campaign.afb.read_lp(p);records.append(fingerprint(lp,matrix))
        assert records[0]==records[1],instance
        base=FRONT/'models'/instance/'Base.lp'
        assert sha(base)==sha(NATIVE/'preflight'/instance/'Budget-L2/python/Base.lp')
        models[instance]={'base_sha256':sha(base),'input_sha256':sha(FRONT/'models'/instance/'input.txt'),
            'ordered_binary64_model_fingerprint':records[0]}
    blocks=[(n,s) for n in INSTANCES for s in [59,71,89]];rng=random.Random(2026101704);rng.shuffle(blocks)
    jobs=[]
    for n,s in blocks:
        arms=['python','cpp'];rng.shuffle(arms)
        for backend in arms:jobs.append({'instance':n,'seed':s,'backend':backend,'id':f'{n}-{s}-{backend}'})
    dependencies=[Path(__file__),HERE/'common.py',HERE/'PROTOCOL.md',NATIVE/'source/build/SistemaElectrico',NATIVE/'NativeContracts.h',
        ROOT/'exploration/oms-if1-workflow-20261015/study.py',FRONT/'study.py',OLD/'activation_study.py']
    dump(OUT/'design.json',{'date':'2026-10-17','jobs':jobs,'models':models,'parameters':{**load(FRONT/'design.json')['parameters'],'Presolve':-1},
        'dependencies':{str(p.relative_to(ROOT)):sha(p) for p in dependencies},'timing_scope':'whole fresh process; generation once, original metadata in both arms, selection/export, native import/data equality, solve, physical verification, and persistence',
        'excluded_costs':['prior compilation','prior exact witness acquisition'],'shared_machine':True,
        'all_preflight_numeric_data_and_native_order_equal':True,'own_other_solver_campaigns_run_concurrently':False})
    print('Frozen 36 complete-process calls, all six ordered model fingerprints equal.',flush=True)

def worker(jobid,start):
    import numpy as np
    import gurobipy as gp
    import activation_study as a
    from validar_preprocesamiento import clean_instance_text
    d=load(OUT/'design.json');job=next(j for j in d['jobs'] if j['id']==jobid)
    folder=OUT/'runs'/jobid;folder.mkdir(parents=True);export=folder/'scaled.lp';base=folder/'Base.lp'
    stages={}
    def timed(key,fn):
        t=time.perf_counter();v=fn();stages[key]=time.perf_counter()-t;return v
    env={**os.environ};env.pop('OMS_NATIVE_POLICY',None);env.pop('OMS_NATIVE_FACTORS',None)
    if job['backend']=='cpp':env.update(OMS_NATIVE_POLICY='Budget-L2',OMS_NATIVE_FACTORS=str(folder/'factors.csv'))
    destination=export if job['backend']=='cpp' else base
    text=clean_instance_text(FRONT/'models'/job['instance']/'input.txt')+'\nconfigurarSolver --DummyLp\npreprocesar --solodiagnostico\n'+f'grabar {destination} --noConstante\nsalir\n'
    (folder/'commands.txt').write_text(text)
    def generate():
        with (folder/'generator.log').open('w') as log:
            p=subprocess.run([str(NATIVE/'source/build/SistemaElectrico')],input=text,cwd=ROOT/'code',env=env,text=True,stdout=log,stderr=subprocess.STDOUT,timeout=60)
        assert p.returncode==0 and destination.exists()
        if job['backend']=='python':assert sha(base)==d['models'][job['instance']]['base_sha256']
    timed('generation_and_native_selection_if_cpp',generate)
    original=FRONT/'models'/job['instance']/'Base.lp'
    parsed,physical=timed('original_rows',lambda:a.original_rows(original))
    _,lp,_=timed('original_matrix_metadata',lambda:a.campaign.afb.read_lp(original))
    def selection():
        if job['backend']=='cpp':
            with (folder/'factors.csv').open() as stream:return {r['row']:float(r['factor']) for r in csv.DictReader(stream)}
        factors,info,_=choose(parsed,lp,100);assert not info['incompatible_count']
        return factors
    factors=timed('read_native_or_select_python_factors',selection)
    def write_export():
        if job['backend']=='python':
            a.export_scaled(base,export,factors)
            with (folder/'factors.csv').open('w',newline='') as stream:
                w=csv.writer(stream);w.writerow(['row','factor']);w.writerows(factors.items())
    timed('python_export_and_factor_recording',write_export)
    _,scaled_lp,matrix=timed('export_metadata',lambda:a.campaign.afb.read_lp(export))
    model_digest=timed('ordered_model_digest',lambda:fingerprint(scaled_lp,matrix))
    assert model_digest==d['models'][job['instance']]['ordered_binary64_model_fingerprint']
    def native():
        e=gp.Env(params={'OutputFlag':0});m=gp.read(str(export),env=e)
        m.Params.OutputFlag=1;m.Params.LogToConsole=0;m.Params.LogFile=str(folder/'solver.log')
        for k,v in {**d['parameters'],'Seed':job['seed']}.items():m.setParam(k,v)
        return e,m
    env,m=timed('native_import',native)
    wf=module(ROOT/'exploration/oms-if1-workflow-20261015/study.py','frozen_import_equality_cycle')
    equality=timed('native_equality',lambda:wf.check_import(m,scaled_lp,matrix))
    assert [v.VarName for v in m.getVars()]==list(scaled_lp.col_names_)
    assert [r.ConstrName for r in m.getConstrs()]==list(scaled_lp.row_names_)
    timed('solve',m.optimize)
    def extract():
        r={'status':m.Status,'solutions':m.SolCount,'native_completed':m.Status==2,'work':m.Work,'native_runtime':m.Runtime,
            'objective':m.ObjVal if m.SolCount else None,'bound':m.ObjBound if math.isfinite(m.ObjBound) else None}
        if not m.SolCount:return r,None
        names=[v.VarName for v in m.getVars()];xs=m.getAttr('X',m.getVars())
        np.savez_compressed(folder/'solution.npz',names=np.array(names),x=np.array(xs))
        return r,dict(zip(names,xs))
    outcome,point=timed('extraction',extract)
    def verify():
        if point is None:return None
        integers={n for n,k in zip(lp.col_names_,lp.integrality_) if str(k)!='HighsVarType.kContinuous'}
        groups=a.audit_values(physical,point,integers)
        gamma=max(abs(point[n]-round(point[n])) for n in integers)
        rows,_=a.parse(export)
        violations=[a.campaign.exact_violation(rows[n]['terms'],rows[n]['rhs'],point,rows[n]['sense']) for n in physical]
        return {'physical':groups,'maximum_integer_distance':gamma,'integer_gamma_hypothesis_holds':gamma<=1e-9,
            'exported_physical_rows_exceeding_epsilon':sum(v>F(1e-6) for v in violations),'max_observed_exported_violation':float(max(violations))}
    verification=timed('original_unit_verification',verify)
    timed('cleanup',lambda:(m.dispose(),env.dispose()))
    dump(folder/'result.json',{'job':job,'parameters':{**d['parameters'],'Seed':job['seed']},'stages_seconds':stages,
        'outcome':outcome,'verification':verification,'native_equality':equality,'export_sha256':sha(export),
        'ordered_binary64_model_fingerprint':model_digest,'worker_seconds_before_persistence':time.perf_counter()-start})

def run():
    d=load(OUT/'design.json')
    for p,h in d['dependencies'].items():assert sha(ROOT/p)==h,p
    assert not (OUT/'parent-timing.json').exists();records=[]
    for i,j in enumerate(d['jobs']):
        load_before=os.getloadavg();start=time.perf_counter()
        with (OUT/(j['id']+'-execution.log')).open('w') as log:
            p=subprocess.run([sys.executable,str(Path(__file__)),'worker',j['id']],cwd=ROOT,
                env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'},stdout=log,stderr=subprocess.STDOUT,timeout=240)
        records.append({'job':j,'returncode':p.returncode,'total_fresh_process_seconds':time.perf_counter()-start,
            'system_load_before':load_before,'system_load_after':os.getloadavg()})
        dump(OUT/'parent-timing.json',records);print(i+1,'/36',j['id'],round(records[-1]['total_fresh_process_seconds'],3),flush=True)
        assert p.returncode==0,'Failed attempt retained; no automatic retry'

if __name__=='__main__':
    start=time.perf_counter();p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','run','worker']);p.add_argument('job',nargs='?');args=p.parse_args()
    if args.stage=='worker':worker(args.job,start)
    else:globals()[args.stage]()
