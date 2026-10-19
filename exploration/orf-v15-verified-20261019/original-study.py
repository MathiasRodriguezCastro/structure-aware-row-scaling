#!/usr/bin/env python3
"""Preserved candidate traces for a bounded, separately registered ORF follow-up."""
import argparse
import csv
from fractions import Fraction as Q
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

import numpy as np

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
PARENT=ROOT/'exploration/orf-confirmatory-20261018'
sys.path[:0]=[str(ROOT/'scripts/research'),str(ROOT/'scripts'),str(ROOT/'exploration/oms-followup-20261014')]
F=Q.from_float
CONTRACTS={
    'b10':dict(activation=10.,water=10.,power=.01),
    'b100':dict(activation=100.,water=100.,power=.01),
    'b1000':dict(activation=1000.,water=1000.,power=.01),
    'heterogeneous':dict(activation=10.,water=.001,power=.001)}
CPLEX_LIB='/opt/ibm/ILOG/CPLEX_Studio2212/cplex/bin/x86-64_linux/libcplex2212.so'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def dump(p,d):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n');tmp.replace(p)
def library(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m;spec.loader.exec_module(m);return m
old=library(PARENT/'study.py','prospective_parent')
checker=library(PARENT/'check.py','prospective_point_checker')


def category(group,unit):
    return 'power' if unit=='MW' else 'activation' if group=='Volume-dependent activation' else 'water'


def select(parsed,lp,contract,export_aware=False):
    a,front=old.modules()
    if contract==CONTRACTS['b100'] and not export_aware:return front.choose(parsed,lp,100)
    integers={n for n,t in zip(lp.col_names_,lp.integrality_) if str(t)!='HighsVarType.kContinuous'}
    boxes={n:max(abs(float(l)),abs(float(u))) for n,l,u in zip(lp.col_names_,lp.col_lower_,lp.col_upper_)}
    factors={};decisions=[]
    if export_aware:from export_selector import choose as choose_export
    for n,row in parsed.items():
        spec=a.campaign.physical_spec(n,row['terms'])
        if not spec and a.activation_spec(n,row):spec=('Volume-dependent activation','m3',1.)
        delta=None if spec is None else contract[category(spec[0],spec[1])]*spec[2]
        e=F(1e-9)*sum((F(abs(float(v))) for j,v in row['terms'].items() if j in integers),Q(0)) if delta else Q(0)
        if export_aware and delta is not None:
            decision=choose_export(list(row['terms'].values()),float(row['rhs']),
                [boxes[j] if math.isfinite(boxes[j]) else None for j in row['terms']],
                F(contract[category(spec[0],spec[1])])*F(float(spec[2])),e)
            factor=decision.pop('factor');decision['row']=n;decisions.append(decision)
        else:
            rho=Q(0)
            if delta is not None and a.ACT.fullmatch(n):
                rho=F(2.**-52)*(sum((F(abs(float(v)))*F(boxes[j]) for j,v in row['terms'].items()),Q(0))+F(abs(float(row['rhs']))))
            reserve=float(e+rho)
            if F(reserve)<e+rho:reserve=math.nextafter(reserve,math.inf)
            decision=a.select_factor(list(row['terms'].values()),delta if delta is not None else 1e100,
                kernel='l2',rounding_allowance=reserve)
            factor=decision.factor
            decisions.append(dict(row=n,status=decision.reason,certified=factor is not None))
        if factor is not None:factors[n]=factor
    blocked=[d for d in decisions if not d['certified']]
    return factors,dict(incompatible_count=len(blocked),incompatible=blocked,decisions=decisions)


def prepare():
    assert not (HERE/'design.json').exists(),'design already frozen'
    p=load(PARENT/'design.json'); refs={}
    for r in csv.DictReader((PARENT/'verified-certificates.csv').open()):
        if r['kind']=='integer-pattern' and r['verified_upper']:
            refs[r['instance']+'/'+r['representation']]=r['verified_upper']
    names=sorted(p['models']);subset=[n for n in names if n.endswith(('-01','-08'))]
    cplex_names=[n for n in names if n.endswith(('-01','-03','-05','-07'))]
    jobs=[]
    def add(name,policy,solver='gurobi',scale=-1,contract='b100',experiment='I'):
        for seed in [211,257,293]:
            jid=f'{experiment}-{name}-{solver}-sf{scale}-s{seed}-{policy}-{contract}'
            jobs.append(dict(id=jid,instance=name,policy=policy,solver=solver,scale=scale,
                seed=seed,contract=contract,experiment=experiment))
    for n in names:
        for policy in ['Base','L2','Budget-L2','L2-NF3']:add(n,policy)
    for n in subset:
        for c in CONTRACTS:
            if c!='b100':add(n,'Budget-L2',contract=c,experiment='II')
            add(n,'Export-Budget-L2',contract=c,experiment='II')
    for n in cplex_names:
        for policy in ['Base','L2','Budget-L2']:add(n,policy,solver='cplex',experiment='III-cplex')
    for n in subset:
        for scale in [0,2]:
            for policy in ['Base','L2','Budget-L2']:add(n,policy,scale=scale,experiment='III-scale')
    assert len(jobs)==630;random.Random(2026101905).shuffle(jobs)
    # Execute I first; keep every stage's fixed relative randomized order.
    jobs.sort(key=lambda j: j['experiment']!='I')
    deps=[Path(__file__),HERE/'export_selector.py',HERE/'PROTOCOL.md',PARENT/'design.json',PARENT/'verified-certificates.csv',
          PARENT/'study.py',PARENT/'check.py',ROOT/'exploration/oms-frontier-20261016/study.py']
    dump(HERE/'design.json',dict(date='2026-10-19',parent_version='v1.4.2-orf-submission',models=p['models'],
        jobs=jobs,references=refs,contracts=CONTRACTS,seeds=[211,257,293],
        thresholds=[.001,.01],parameters=dict(Threads=4,TimeLimit=30.,MIPGap=.01,Presolve=-1,
            FeasibilityTol=1e-6,IntFeasTol=1e-9,ScaleFlag=-1,NumericFocus=0,IntegralityFocus=0),
        dependencies={str(x.relative_to(ROOT)):sha(x) for x in deps},CPLEX_native_library=CPLEX_LIB,
        CPLEX_native_library_sha256=sha(CPLEX_LIB),known_models=True,external_family=False,
        hostname=os.uname().nodename,shared_machine=True,additional_research_MIP_calls=630))
    print('Frozen',len(jobs),'assignments; no research solve yet',flush=True)


def verify(model,x,contract):
    rows,bounds,costs,integers,scope,offset=model
    point=dict(zip(bounds,map(lambda v:F(float(v)),x)))
    rounded={n:Q(round(v)) if n in integers else v for n,v in point.items()}
    maxima={'power':Q(0),'water':Q(0),'activation':Q(0)};other=Q(0)
    for n,row in rows.items():
        v=max(checker.residual(row,point),checker.residual(row,rounded))
        if n in scope:
            group,unit,conv=scope[n];k=category(group,unit);maxima[k]=max(maxima[k],v/conv)
        else:
            den=max(Q(1),abs(row['rhs']),sum((abs(a*rounded[j]) for j,a in row['terms'].items()),Q(0)))
            other=max(other,v/den)
    iv=max((abs(point[n]-round(point[n])) for n in integers),default=Q(0))
    bv=max([Q(0)]+[lo-rounded[n] for n,(lo,hi) in bounds.items() if lo is not None]+
        [rounded[n]-hi for n,(lo,hi) in bounds.items() if hi is not None])
    physical=all(maxima[k]<=F(contract[k]) for k in maxima)
    domain=bv==0 and iv<=F(1e-9)
    objective=offset+sum((a*rounded[n] for n,a in costs.items()),Q(0))
    return dict(physical_pass=physical,domain_pass=domain,other_rows_pass=other<=F(1e-6),
        maximum_physical_violation={k:str(v) for k,v in maxima.items()},
        max_integrality=str(iv),max_bound_violation=str(bv),max_other_backward_error=str(other),
        objective_exact=str(objective))


def cplex_import(m,lp,parsed):
    assert m.variables.get_names()==list(lp.col_names_)
    assert m.linear_constraints.get_names()==list(parsed)
    assert m.objective.get_linear()==list(lp.col_cost_)
    assert m.objective.get_offset()==float(lp.offset_)
    for n,t in zip(lp.col_names_,lp.integrality_):
        assert (m.variables.get_types(n) in 'BI')==(str(t)!='HighsVarType.kContinuous')
    for field,got,want in [('lower',m.variables.get_lower_bounds(),lp.col_lower_),('upper',m.variables.get_upper_bounds(),lp.col_upper_)]:
        for x,y in zip(got,want):
            assert (abs(x)>=1e20 and not math.isfinite(y) and x*y>0) or x==y,(field,x,y)
    names=lp.col_names_
    for (n,r),row,sense,rhs in zip(parsed.items(),m.linear_constraints.get_rows(),m.linear_constraints.get_senses(),m.linear_constraints.get_rhs()):
        assert dict(zip((names[j] for j in row.ind),row.val))=={j:float(v) for j,v in r['terms'].items()},n
        assert rhs==float(r['rhs']) and sense=={'<=':'L','>=':'G','=':'E'}[r['sense']],n
    return dict(matrix_rhs_objective_bounds_integer_domains_equal=True,rows=len(parsed),columns=len(names))


def worker(jid):
    started=float(os.environ.get('ORF_FOLLOWUP_LAUNCHED',time.perf_counter()))
    d=load(HERE/'design.json');job=next(j for j in d['jobs'] if j['id']==jid)
    folder=HERE/'runs'/jid;folder.mkdir(parents=True);stages={}
    def timed(k,fn):
        t=time.perf_counter();v=fn();stages[k]=time.perf_counter()-t;return v
    a,front=old.modules();base=timed('generation',lambda:old.generate(job['instance'],folder))
    assert sha(base)==d['models'][job['instance']]['base_sha256']
    parsed,physical=timed('original_parse',lambda:a.original_rows(base))
    _,lp,_=timed('original_metadata',lambda:a.campaign.afb.read_lp(base))
    contract=CONTRACTS[job['contract']];policy=job['policy'];rep='Base' if policy=='Base' else 'L2' if policy.startswith('L2') else policy
    if rep=='Base':export=base
    else:
        if rep=='L2':factors,info=timed('selection',lambda:front.choose(parsed,lp,None))
        else:factors,info=timed('selection',lambda:select(parsed,lp,contract,rep=='Export-Budget-L2'))
        dump(folder/'selection.json',info)
        if info['incompatible_count']:
            dump(folder/'result.json',dict(job=job,abstained=True,reason='no_certified_factor',stages_seconds=stages));return
        export=folder/'scaled.lp';timed('export',lambda:a.export_scaled(base,export,factors))
    h=sha(export);events=[];points=[];callback_seconds=0.;callback_errors=[]
    export_parsed,_=a.original_rows(export)
    _,elp,ea=timed('export_metadata',lambda:a.campaign.afb.read_lp(export))
    params={**d['parameters'],'Seed':job['seed'],'ScaleFlag':job['scale']}
    if policy=='L2-NF3':params['NumericFocus']=3
    if job['solver']=='gurobi':
        import gurobipy as gp
        env=gp.Env(params={'OutputFlag':0});m=gp.read(str(export),env=env)
        m.setParam('OutputFlag',1);m.setParam('LogToConsole',0);m.setParam('LogFile',str(folder/'solver.log'))
        for k,v in params.items():m.setParam(k,v)
        wf=library(ROOT/'exploration/oms-if1-workflow-20261015/study.py','native_import_followup')
        equality=timed('import_check',lambda:wf.check_import(m,elp,ea))
        variables=[m.getVarByName(n) for n in lp.col_names_]
        def callback(model,where):
            nonlocal callback_seconds
            if where!=gp.GRB.Callback.MIPSOL:return
            t=time.perf_counter()
            try:
                x=model.cbGetSolution(variables)
                events.append(dict(kind='MIPSOL',process_discovery=time.perf_counter()-started,
                    solver_discovery=model.cbGet(gp.GRB.Callback.RUNTIME),work=model.cbGet(gp.GRB.Callback.WORK),
                    objective=model.cbGet(gp.GRB.Callback.MIPSOL_OBJ),nodes=model.cbGet(gp.GRB.Callback.MIPSOL_NODCNT)))
                points.append(x)
            except Exception as e:callback_errors.append(type(e).__name__+': '+str(e))
            callback_seconds+=time.perf_counter()-t
        solve_start=time.perf_counter();timed('solve',lambda:m.optimize(callback))
        outcome=dict(status=m.Status,completed=m.Status==2,solutions=m.SolCount,work=m.Work,
            objective=m.ObjVal if m.SolCount else None,bound=m.ObjBound if math.isfinite(m.ObjBound) else None,
            runtime=m.Runtime,nodes=m.NodeCount,solver_version=list(gp.gurobi.version()))
        if m.SolCount:
            points.append([v.X for v in variables]);events.append(dict(kind='final',process_discovery=time.perf_counter()-started,
                solver_discovery=m.Runtime,work=m.Work,objective=m.ObjVal,nodes=m.NodeCount))
        m.dispose();env.dispose()
    else:
        import cplex
        from cplex.callbacks import IncumbentCallback
        m=cplex.Cplex();log=(folder/'solver.log').open('w')
        for fn in [m.set_log_stream,m.set_results_stream,m.set_warning_stream,m.set_error_stream]:fn(log)
        timed('native_read',lambda:m.read(str(export)))
        equality=timed('import_check',lambda:cplex_import(m,elp,export_parsed))
        m.parameters.threads.set(4);m.parameters.timelimit.set(30.);m.parameters.mip.tolerances.mipgap.set(.01)
        m.parameters.simplex.tolerances.feasibility.set(1e-6);m.parameters.mip.tolerances.integrality.set(1e-9)
        m.parameters.randomseed.set(job['seed']);m.parameters.mip.strategy.search.set(1)
        m.parameters.mip.display.set(4);m.parameters.mip.interval.set(1)
        class Capture(IncumbentCallback):
            def __call__(self):
                nonlocal callback_seconds
                t=time.perf_counter()
                try:
                    events.append(dict(kind='CPLEX-incumbent',process_discovery=time.perf_counter()-started,
                        solver_discovery=self.get_time()-solver_epoch,work=self.get_dettime()-det_epoch,
                        objective=self.get_objective_value(),nodes=self.get_num_nodes()))
                    points.append(self.get_values())
                except Exception as e:callback_errors.append(type(e).__name__+': '+str(e))
                callback_seconds+=time.perf_counter()-t
        m.register_callback(Capture);solver_epoch=m.get_time();det_epoch=m.get_dettime()
        solve_start=time.perf_counter();timed('solve',m.solve)
        found=m.solution.is_primal_feasible();status=m.solution.get_status()
        outcome=dict(status=status,completed=status in [101,102],solutions=int(found),work=m.get_dettime()-det_epoch,
            objective=m.solution.get_objective_value() if found else None,bound=m.solution.MIP.get_best_objective(),
            runtime=time.perf_counter()-solve_start,nodes=m.solution.progress.get_num_nodes_processed(),solver_version=m.get_version())
        if found:
            points.append(m.solution.get_values());events.append(dict(kind='final',process_discovery=time.perf_counter()-started,
                solver_discovery=outcome['runtime'],work=outcome['work'],objective=outcome['objective'],nodes=outcome['nodes']))
        m.end();log.close()
    assert not callback_errors,callback_errors
    solve_finished=time.perf_counter()-started
    np.savez_compressed(folder/'candidates.npz',names=np.array(lp.col_names_),x=np.array(points,dtype=float).reshape(-1,len(lp.col_names_)))
    model=timed('rational_model',lambda:checker.canonical(base))
    reference=Q(d['references'][job['instance']+'/Base']);first={str(t):None for t in d['thresholds']}
    verification_start=time.perf_counter()
    for i,(event,x) in enumerate(zip(events,points)):
        audit=verify(model,x,contract);event['audit']=audit
        for tau in d['thresholds']:
            passed=all(audit[k] for k in ['physical_pass','domain_pass','other_rows_pass']) and (
                Q(audit['objective_exact'])<=reference+F(tau)*max(Q(1),abs(reference)))
            if passed and first[str(tau)] is None:
                first[str(tau)]=dict(index=i,kind=event['kind'],solver_discovery=event['solver_discovery'],
                    process_discovery=event['process_discovery'],work=event['work'],
                    offline_verified_available=time.perf_counter()-started,
                    objective_exact=audit['objective_exact'])
    stages['verification']=time.perf_counter()-verification_start
    native_ref_rep='L2' if policy=='L2-NF3' else rep
    known=(job['contract']=='b100' and native_ref_rep in ['Base','L2','Budget-L2'])
    if known:
        expected=d['models'][job['instance']]['base_sha256'] if rep=='Base' else d['models'][job['instance']]['policies'][native_ref_rep]['sha256']
        assert h==expected
    native_ref=Q(d['references'][job['instance']+'/'+native_ref_rep]) if known else None
    b=outcome['bound'];contradiction=None if native_ref is None or b is None else F(b)>native_ref+F(max(1e-6,8*math.ulp(b)))
    dump(folder/'result.json',dict(job=job,abstained=False,parameters=params if job['solver']=='gurobi' else
        dict(threads=4,timelimit=30.,mipgap=.01,epRHS=1e-6,epInt=1e-9,search='traditional',scaling='default',seed=job['seed']),
        native_import=equality,export_sha256=h,outcome=outcome,callback_seconds=callback_seconds,
        events=events,first_qualified=first,reference_exact=str(reference),reference_is_global_optimum=False,
        known_native_export_witness=known,bound_contradiction=contradiction,
        solve_started_process_seconds=solve_start-started,solver_finished_process_seconds=solve_finished,
        stages_seconds=stages,worker_seconds=time.perf_counter()-started))
    if export!=base:export.unlink()
    base.unlink()


def run():
    d=load(HERE/'design.json')
    for p,h in d['dependencies'].items():assert sha(ROOT/p)==h,p
    assert sha(CPLEX_LIB)==d['CPLEX_native_library_sha256']
    records=load(HERE/'timing.json') if (HERE/'timing.json').exists() else []
    assert [r['job'] for r in records]==d['jobs'][:len(records)]
    assert all(r['returncode']==0 for r in records),'retain failure; register amendment'
    for job in d['jobs'][len(records):]:
        assert not (HERE/'runs'/job['id']).exists(),'unrecorded attempt retained'
        start=time.perf_counter();env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1',
            'ORF_FOLLOWUP_LAUNCHED':str(start)}
        if job['solver']=='cplex':env['LD_PRELOAD']=CPLEX_LIB
        with (HERE/(job['id']+'-execution.log')).open('w') as log:
            try:
                r=subprocess.run([sys.executable,str(Path(__file__)),'worker',job['id']],cwd=ROOT,env=env,
                    stdout=log,stderr=subprocess.STDOUT,timeout=180);rc=r.returncode
            except subprocess.TimeoutExpired:rc=124
        records.append(dict(job=job,returncode=rc,total_seconds=time.perf_counter()-start));dump(HERE/'timing.json',records)
        print(len(records),'/',len(d['jobs']),job['id'],'rc',rc,'seconds',round(records[-1]['total_seconds'],3),flush=True)
        if rc:raise RuntimeError('failed attempt retained')


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['prepare','run','worker']);ap.add_argument('job',nargs='?');args=ap.parse_args()
    if args.stage=='worker':worker(args.job)
    else:globals()[args.stage]()
