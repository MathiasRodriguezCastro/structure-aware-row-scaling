#!/usr/bin/env python3
"""Fresh-process pilot runs; frozen row policies and independent postsolve checks."""
import time
IMPORTED=time.perf_counter()
import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import sys

import numpy as np

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'scripts/research'),str(ROOT/'exploration/oms-followup-20261014')]


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n');tmp.replace(p)
def library(p,name):
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s)
    sys.modules[name]=m;s.loader.exec_module(m);return m


def native(export,folder,job,started,lp,parsed,follow,matrix):
    """Both optimizers receive the same gap, budget-related tolerances and thread cap."""
    events=[];points=[];callback_errors=[]
    parameters=dict(threads=4,time_limit=job['time_limit'],mip_gap=.001,
        feasibility_tolerance=1e-6,integer_tolerance=1e-9,seed=job['seed'],
        internal_scaling='automatic',numerical_control=job['policy'])
    if job['solver']=='gurobi':
        import gurobipy as gp
        wf=library(ROOT/'exploration/oms-if1-workflow-20261015/study.py','extension_import_check')
        with gp.Env(params={'OutputFlag':0}) as env,gp.read(str(export),env=env) as m:
            for n,v in dict(Threads=4,TimeLimit=job['time_limit'],MIPGap=.001,
                FeasibilityTol=1e-6,IntFeasTol=1e-9,Seed=job['seed'],Presolve=-1,ScaleFlag=-1,
                NumericFocus=3 if job['policy']=='L2-NF3' else 0,IntegralityFocus=0,
                OutputFlag=1,LogToConsole=0,LogFile=str(folder/'solver.log')).items():m.setParam(n,v)
            imported=wf.check_import(m,lp,matrix)
            variables=[m.getVarByName(n) for n in lp.col_names_]
            def callback(model,where):
                if where!=gp.GRB.Callback.MIPSOL:return
                try:
                    points.append(model.cbGetSolution(variables))
                    events.append(dict(kind='MIPSOL',process_discovery=time.perf_counter()-started,
                        work=model.cbGet(gp.GRB.Callback.WORK),objective=model.cbGet(gp.GRB.Callback.MIPSOL_OBJ)))
                except Exception as e:callback_errors.append(str(e))
            epoch=time.perf_counter();m.optimize(callback)
            if m.SolCount:
                points.append([v.X for v in variables]);events.append(dict(kind='final',
                    process_discovery=time.perf_counter()-started,work=m.Work,objective=m.ObjVal))
            result=dict(status=m.Status,completed=m.Status==2,solutions=m.SolCount,runtime=m.Runtime,
                work=m.Work,nodes=m.NodeCount,objective=m.ObjVal if m.SolCount else None,
                reported_bound=m.ObjBound if math.isfinite(m.ObjBound) else None,
                reported_gap=m.MIPGap if m.SolCount and math.isfinite(m.MIPGap) else None,
                solver_version=list(gp.gurobi.version()),solve_started=epoch-started)
    elif job['solver']=='cplex':
        import cplex
        from cplex.callbacks import IncumbentCallback
        with (folder/'solver.log').open('w') as log,cplex.Cplex() as m:
            for fn in [m.set_log_stream,m.set_results_stream,m.set_warning_stream,m.set_error_stream]:fn(log)
            m.read(str(export));imported=follow.cplex_import(m,lp,parsed)
            m.parameters.threads.set(4);m.parameters.timelimit.set(job['time_limit'])
            m.parameters.mip.tolerances.mipgap.set(.001)
            m.parameters.simplex.tolerances.feasibility.set(1e-6)
            m.parameters.mip.tolerances.integrality.set(1e-9)
            m.parameters.randomseed.set(job['seed']);m.parameters.mip.strategy.search.set(1)
            m.parameters.emphasis.numerical.set(int(job['policy']=='L2-NumEmphasis'))
            parameters.update(search='traditional',numerical_emphasis=int(job['policy']=='L2-NumEmphasis'))
            class Capture(IncumbentCallback):
                def __call__(self):
                    try:
                        points.append(self.get_values());events.append(dict(kind='CPLEX-incumbent',
                            process_discovery=time.perf_counter()-started,work=self.get_dettime()-det_epoch,
                            objective=self.get_objective_value()))
                    except Exception as e:callback_errors.append(str(e))
            m.register_callback(Capture);det_epoch=m.get_dettime();epoch=time.perf_counter();m.solve()
            found=m.solution.is_primal_feasible();elapsed=time.perf_counter()-epoch
            if found:
                points.append(m.solution.get_values());events.append(dict(kind='final',
                    process_discovery=time.perf_counter()-started,work=m.get_dettime()-det_epoch,
                    objective=m.solution.get_objective_value()))
            bound=m.solution.MIP.get_best_objective()
            result=dict(status=m.solution.get_status(),completed=m.solution.get_status() in [101,102],
                solutions=int(found),runtime=elapsed,work=m.get_dettime()-det_epoch,
                nodes=m.solution.progress.get_num_nodes_processed(),
                objective=m.solution.get_objective_value() if found else None,
                reported_bound=bound if math.isfinite(bound) else None,
                reported_gap=m.solution.MIP.get_mip_relative_gap() if found else None,
                solver_version=m.get_version(),solve_started=epoch-started)
    else:raise ValueError('unsupported solver')
    assert len(points)==len(events)
    return result,points,events,parameters,imported,callback_errors


def generate(name,folder,metadata):
    base=folder/'Base.lp';text=(HERE/'models'/name/'input.txt').read_text()
    commands=text+'\nconfigurarSolver --DummyLp\npreprocesar --solodiagnostico\n'+f'grabar {base} --noConstante\nsalir\n'
    (folder/'generator-commands.txt').write_text(commands)
    with (folder/'generator.log').open('w') as log:
        p=subprocess.run([str(ROOT/'code/build-audit/SistemaElectrico')],input=commands,text=True,
            cwd=ROOT/'code',stdout=log,stderr=subprocess.STDOUT,timeout=120)
    assert p.returncode==0 and sha(base)==metadata['base_sha256'],'generator export identity failed'
    return base


def witness_feasible(canonical,values):
    rows,bounds,_,integers,_,_=canonical
    if set(values)!=set(bounds):return False
    for n,r in rows.items():
        v=sum((a*values[j] for j,a in r['terms'].items()),Q(0))-r['rhs']
        if (r['sense']=='=' and v!=0) or (r['sense']=='<=' and v>0) or (r['sense']=='>=' and v<0):return False
    for n,(lo,hi) in bounds.items():
        if (lo is not None and values[n]<lo) or (hi is not None and values[n]>hi):return False
        if n in integers and values[n].denominator!=1:return False
    return True


def worker(job):
    started=float(os.environ.get('ORF_PROCESS_STARTED',IMPORTED))
    folder=HERE/'pilot-runs'/job['id'];folder.mkdir(parents=True,exist_ok=False)
    result=dict(job=job,stage='resource_pilot',primary_confirmatory_observation=False)
    try:
        plan=load(HERE/'PILOT_PLAN.json')
        for n,h in plan['dependencies'].items():assert sha(ROOT/n)==h,'Frozen dependency changed: '+n
        d=load(HERE/'MODEL_PREPARATION.json');metadata=d['models'][job['instance']]
        follow=library(ROOT/'exploration/orf-v15-verified-20261019/study.py','extension_frozen_helpers')
        a,front=follow.old.modules();base=generate(job['instance'],folder,metadata)
        rows,physical=a.original_rows(base);_,lp,ea=a.campaign.afb.read_lp(base)
        representation='Base' if job['policy']=='Base' else 'Budget-L2' if job['policy']=='Budget-L2' else 'L2'
        export=base;selection={}
        if representation!='Base':
            factors,selection=front.choose(rows,lp,100 if representation=='Budget-L2' else None)
            save(folder/'selection.json',selection)
            if selection['incompatible_count']:
                result.update(status='abstained',abstained=True,selection=selection);save(folder/'result.json',result);return
            export=folder/'scaled.lp';a.export_scaled(base,export,factors)
            assert sha(export)==metadata['policies'][representation]['export_sha256']
        _,elp,matrix=a.campaign.afb.read_lp(export);export_parsed,_=follow.checker.parse(export)
        # Gurobi's import checker requires the sparse array, not a placeholder.
        outcome,points,events,parameters,imported,errors=native(export,folder,job,started,elp,export_parsed,follow,matrix)
        solver_finished=time.perf_counter()-started
        np.savez_compressed(folder/'candidates.npz',names=np.array(lp.col_names_),
            x=np.array(points,dtype=float).reshape(-1,len(lp.col_names_)))
        model=follow.checker.canonical(base);reference_folder=HERE/'references'/job['instance']
        cert=reference_folder/'independent-certificate.json';reference=None;point=None
        if cert.exists():
            certificate=load(cert);assert certificate['original_model_sha256']==sha(base)
            point={n:Q(v) for n,v in load(reference_folder/'exact-witness.json').items()}
            assert witness_feasible(model,point),'reference fails independent original-model check'
            reference=Q(certificate['objective_exact_fraction'])
        first=None;verify_started=time.perf_counter()
        for i,(event,x) in enumerate(zip(events,points)):
            # The resource pilot preserves all points. Only final points and
            # quality-eligible candidates require complete residual checks.
            raw={n:Q.from_float(float(v)) for n,v in zip(model[1],x)}
            rounded={n:Q(round(v)) if n in model[3] else v for n,v in raw.items()}
            cost=model[5]+sum((c*rounded[n] for n,c in model[2].items()),Q(0))
            quality=reference is not None and cost<=reference+Q.from_float(.001)*max(Q(1),abs(reference))
            audit=follow.verify(model,x,follow.CONTRACTS['b100']) if quality or event['kind']=='final' else dict(objective_exact=str(cost))
            event['audit']=audit;event['quality_pass']=quality if reference is not None else None
            if quality and all(audit.get(k,False) for k in ['physical_pass','domain_pass','other_rows_pass']) and first is None:
                first=dict(index=i,process_discovery=event['process_discovery'],work=event['work'],
                    offline_verified_available=time.perf_counter()-started)
        native_witness=False;contradiction=None
        if point is not None:
            native_witness=witness_feasible(follow.checker.canonical(export),point)
            bound=outcome['reported_bound']
            if native_witness and bound is not None:
                contradiction=Q.from_float(bound)>reference+Q.from_float(max(1e-6,8*math.ulp(bound)))
        result.update(status='callback_error' if errors else 'completed',abstained=False,outcome=outcome,parameters=parameters,
            native_import=imported,events=events,first_qualified=first,reference_exact=str(reference) if reference is not None else None,
            quality_reference_available=reference is not None,reference_is_certified_optimum=False,
            exact_reference_feasible_for_imported_export=native_witness,bound_contradiction=contradiction,
            verification_seconds=time.perf_counter()-verify_started,solver_finished_process_seconds=solver_finished,
            preparation_time=outcome['solve_started'],worker_total_seconds=time.perf_counter()-started,
            callback_errors=errors,base_sha256=sha(base),export_sha256=sha(export))
    except Exception as e:
        result.update(status='failed',error=type(e).__name__+': '+str(e),failed_attempt_retained=True)
        raise
    finally:
        result.update(maximum_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            hostname=os.uname().nodename,slurm_job=os.environ.get('SLURM_JOB_ID'))
        save(folder/'result.json',result)


def launch(block):
    plan=load(HERE/'PILOT_PLAN.json');jobs=plan['blocks'][block]['jobs']
    for job in jobs:
        folder=HERE/'pilot-runs'/job['id']
        if folder.exists():raise RuntimeError('Attempt already exists; retain it and register a retry explicitly')
        outer_started=time.perf_counter()
        env={**os.environ,'ORF_PROCESS_STARTED':str(outer_started)}
        logs=HERE/'pilot-execution-logs';logs.mkdir(exist_ok=True)
        with (logs/(job['id']+'.log')).open('w') as log:
            try:
                r=subprocess.run([sys.executable,str(Path(__file__)),'worker',job['id']],cwd=ROOT,
                    env=env,stdout=log,stderr=subprocess.STDOUT,timeout=job['time_limit']+600)
                code=r.returncode
            except subprocess.TimeoutExpired:code=124
        save(logs/(job['id']+'.json'),dict(job=job,returncode=code,
            complete_process_seconds=time.perf_counter()-outer_started))
        if code:raise RuntimeError('Pilot worker failed; remaining block retained as unattempted: '+job['id'])


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['worker','block']);ap.add_argument('key');args=ap.parse_args()
    if args.stage=='block':launch(int(args.key))
    else:
        jobs=[j for b in load(HERE/'PILOT_PLAN.json')['blocks'] for j in b['jobs']]
        worker(next(j for j in jobs if j['id']==args.key))
