"""Native adapters, independent arithmetic, and exact fixed-pattern LP audits."""
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OBJECTIVE=ROOT/'exploration/oms-objective-budget-20261014'
PILOT=ROOT/'exploration/oms-generalization-20261014'
ARITH=ROOT/'exploration/oms-decision-study-20261014'
sys.path.insert(0,str(OBJECTIVE));sys.path.insert(0,str(PILOT))
from build_lp import build,write
from rational_lp import verify,verify_ray
import generalization_study as original

spec=importlib.util.spec_from_file_location('pinned_arithmetic',ARITH/'independent_check.py')
arithmetic=importlib.util.module_from_spec(spec);spec.loader.exec_module(arithmetic)
F=Fraction.from_float
SOPLEX=ROOT/'exploration/oms-followup-20261014/tools/soplex-build/bin/soplex'
TARGET=Fraction(2812951,100)


def load(p):return json.loads(Path(p).read_text())
def dump(p,v):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,point):
    with Path(p).open('wb') as stream:np.savez_compressed(stream,x=np.asarray(point,dtype=float))
def point(p):
    with np.load(p,allow_pickle=False) as z:return list(z['x'])
def finite(v):return float(v) if v is not None and math.isfinite(float(v)) and abs(float(v))<1e100 else None


def parse(path,header,prefix):
    if not path.exists():return None
    values={};active=False;found=False
    for line in path.read_text().splitlines():
        if header in line:active=found=True;continue
        if active and (line.startswith('All other') or 'Reduced costs' in line):break
        t=line.split()
        if active and len(t)==2 and t[0].startswith(prefix) and t[0][len(prefix):].isdigit():values[str(int(t[0][len(prefix):]))]=str(Fraction(t[1]))
    return values if found else None


def native(model,alphas,solver,tight,folder,seed,limit,deadline,start=None,import_only=False):
    began=time.perf_counter();folder.mkdir(parents=True,exist_ok=True);lp=folder/'imported.lp';original.write_lp(lp,model,alphas)
    record={'export_sha256':sha(lp),'start_supplied':start is not None,'limit_before_import':limit}
    if start is not None:save(folder/'start-point.npz',start)
    if solver=='gurobi':
        import gurobipy as gp
        env=gp.Env(params={'OutputFlag':0});m=gp.read(str(lp),env=env)
        m.Params.LogToConsole=0;m.Params.OutputFlag=1;m.Params.LogFile=str(folder/'solver.log')
        params={'Threads':4,'MIPGap':.01,'Seed':seed,'Presolve':-1,'ScaleFlag':-1,'IntegralityFocus':1,
                'FeasibilityTol':1e-9 if tight else 1e-6,'IntFeasTol':1e-9 if tight else 1e-5,'BestObjStop':float(TARGET)}
        for k,v in params.items():m.setParam(k,v)
        vs=m.getVars();names=[v.VarName for v in vs];rows=[]
        for c in m.getConstrs():
            e=m.getRow(c);rows.append((c.ConstrName,{e.getVar(i).VarName:float(e.getCoeff(i)) for i in range(e.size())},c.Sense,float(c.RHS)))
        data=[(v.VarName,finite(v.LB),finite(v.UB),v.VType!='C',float(v.Obj)) for v in vs]
        original.check_import(model,alphas,names,rows,data);assert m.ObjCon==0 and m.ModelSense==1
        if start is not None:
            for v in vs:v.Start=float(start[int(v.VarName[1:])])
        requested=min(limit,max(.01,deadline-time.perf_counter()-2.));m.Params.TimeLimit=requested;params['TimeLimit']=requested
        record.update(import_seconds=time.perf_counter()-began,parameters=params,import_preserved_original_exactly=True)
        if import_only:m.dispose();env.dispose();return record,None
        t=time.perf_counter();m.optimize();values={v.VarName:v.X for v in vs} if m.SolCount else None
        x=[values[f'x{i:05d}'] for i in range(len(model['variables']))] if values is not None else None
        record.update(solver_seconds=time.perf_counter()-t,status=m.Status,reported_completion=m.Status==2,
                      objective_api=finite(m.ObjVal) if x is not None else None,bound=finite(m.ObjBound),
                      mip_gap_api=finite(m.MIPGap) if x is not None else None,absolute_gap_target=float(m.Params.MIPGapAbs),work=float(m.Work),solver_version=gp.gurobi.version())
        m.dispose();env.dispose()
    else:
        import highspy
        h=highspy.Highs();h.setOptionValue('log_to_console',False);h.setOptionValue('log_file',str(folder/'solver.log'))
        params={'threads':4,'mip_rel_gap':.01,'random_seed':seed,'presolve':'on','objective_target':float(TARGET),
                'primal_feasibility_tolerance':1e-9 if tight else 1e-6,'mip_feasibility_tolerance':1e-9 if tight else 1e-6}
        for k,v in params.items():assert h.setOptionValue(k,v)==highspy.HighsStatus.kOk
        assert h.readModel(str(lp))!=highspy.HighsStatus.kError
        data=h.getLp();names=list(data.col_names_);matrix=data.a_matrix_
        starts=list(matrix.start_);indices=list(matrix.index_);values=list(matrix.value_);byrow=[{} for _ in range(data.num_row_)]
        if matrix.format_==highspy.MatrixFormat.kColwise:
            for j in range(data.num_col_):
                for k in range(starts[j],starts[j+1]):byrow[indices[k]][names[j]]=float(values[k])
        else:
            byrow=[{names[indices[k]]:float(values[k]) for k in range(starts[j],starts[j+1])} for j in range(data.num_row_)]
        lower=list(data.row_lower_);upper=list(data.row_upper_);rownames=list(data.row_names_);rows=[]
        for j,terms in enumerate(byrow):
            sense='=' if lower[j]==upper[j] else '<' if math.isfinite(upper[j]) else '>'
            rows.append((rownames[j],terms,sense,float(lower[j] if sense=='>' else upper[j])))
        lo=list(data.col_lower_);hi=list(data.col_upper_);kinds=list(data.integrality_);cost=list(data.col_cost_)
        variables=[(name,finite(lo[j]),finite(hi[j]),kinds[j]!=highspy.HighsVarType.kContinuous,float(cost[j])) for j,name in enumerate(names)]
        original.check_import(model,alphas,names,rows,variables);assert data.offset_==0
        if start is not None:
            vals=np.asarray([float(start[int(name[1:])]) for name in names]);indices=np.arange(len(names),dtype=np.int32)
            record['start_api_status']=str(h.setSolution(len(names),indices,vals))
        requested=min(limit,max(.01,deadline-time.perf_counter()-2.));assert h.setOptionValue('time_limit',requested)==highspy.HighsStatus.kOk;params['time_limit']=requested
        record.update(import_seconds=time.perf_counter()-began,parameters=params,import_preserved_original_exactly=True)
        if import_only:h.clear();return record,None
        t=time.perf_counter();h.run();info=h.getInfo();solution=h.getSolution();values=dict(zip(names,solution.col_value))
        x=[values[f'x{i:05d}'] for i in range(len(model['variables']))] if solution.value_valid else None
        record.update(solver_seconds=time.perf_counter()-t,status=h.modelStatusToString(h.getModelStatus()),reported_completion=h.getModelStatus()==highspy.HighsModelStatus.kOptimal,
                      objective_api=finite(info.objective_function_value) if x is not None else None,bound=finite(info.mip_dual_bound),mip_gap_api=finite(info.mip_gap) if x is not None else None,
                      absolute_gap_target=float(h.getOptionValue('mip_abs_gap')[1]),work=None,solver_version=h.version());h.clear()
    record['total_seconds']=time.perf_counter()-began;return record,x


def proof(folder):
    data=load(folder/'audit.json')
    return proof(HERE/data['proof_path']) if data.get('cache_hit') else (folder,data)


def audit(model,x,folder,cache,deadline):
    began=time.perf_counter();folder.mkdir(parents=True,exist_ok=True)
    if x is None:
        result={'outcome':'no_native_point','total_seconds':time.perf_counter()-began};dump(folder/'audit.json',result);return result
    rounded=[float(round(float(y))) if v['integer'] else float(y) for y,v in zip(x,model['variables'])]
    check,raw,qnum=arithmetic.floating_check(model,rounded);dump(folder/'numeric-check.json',check);save(folder/'rounded-point.npz',rounded)
    integers={str(i):int(y) for i,(y,v) in enumerate(zip(rounded,model['variables'])) if v['integer']}
    if arithmetic.integer_failures(model,[F(y) for y in rounded]):
        result={'outcome':'invalid_integer_domain','total_seconds':time.perf_counter()-began};dump(folder/'audit.json',result);return result
    key=hashlib.sha256(json.dumps(integers,sort_keys=True).encode()).hexdigest();dump(folder/'pattern.json',integers)
    if key in cache:
        result={'cache_hit':True,'proof_path':cache[key],'pattern_sha256':key,'numeric_accepted':check['primal_accepted'],'total_seconds':time.perf_counter()-began}
        dump(folder/'audit.json',result);return result
    result={'cache_hit':False,'pattern_sha256':key,'numeric_accepted':check['primal_accepted'],'outcome':'unverified','lp_called':False}
    exact=arithmetic.rational_check(model,qnum);dump(folder/'source-exact-check.json',exact)
    witness=None
    if exact['exact_feasible'] and Fraction(exact['objective_exact'])<=TARGET:
        witness=qnum;result['outcome']='source_exact_target'
    elif deadline-time.perf_counter()>.2:
        lp=build(model,integers,'cost');dump(folder/'model.json',lp);write(folder/'model.lp',lp)
        limit=min(2.,max(.01,deadline-time.perf_counter()-.1));settings=folder/'exact.set'
        settings.write_text('int:syncmode = 1\nint:readmode = 1\nint:solvemode = 2\nint:checkmode = 2\nreal:feastol = 0\nreal:opttol = 0\nreal:timelimit = '+str(limit)+'\n')
        command=[str(SOPLEX),'--loadset='+str(settings),'-X='+str(folder/'primal.txt'),'-Y='+str(folder/'dual.txt'),str(folder/'model.lp')]
        t=time.perf_counter()
        with (folder/'solver.log').open('w') as stream:
            try:r=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=min(4.,max(.1,deadline-time.perf_counter())));code=r.returncode
            except subprocess.TimeoutExpired:code=None
        result.update(lp_called=True,lp_seconds=time.perf_counter()-t,lp_limit=limit,lp_returncode=code,lp_sha256=sha(folder/'model.lp'),solver_binary_sha256=sha(SOPLEX))
        primal=parse(folder/'primal.txt','Primal solution (name, value):','x');dual=parse(folder/'dual.txt','Dual solution (name, value):','r');ray=parse(folder/'dual.txt','Dual ray (name, value):','r')
        if primal is not None and dual is not None:
            y=[primal.get(str(i),'0') for i in range(len(lp['cost']))];c=verify(lp,y,dual);dump(folder/'primal.json',y);dump(folder/'dual.json',dual);dump(folder/'certificate.json',c)
            if c['primal_feasible']:
                witness=[Fraction(0)]*len(model['variables'])
                for i,z in integers.items():witness[int(i)]=Fraction(z)
                for i,v in zip(lp['continuous_original_indices'],y):witness[i]=Fraction(v)
                assert arithmetic.rational_check(model,witness)['exact_feasible']
            result['outcome']='optimum_certified' if c['optimum_certified'] else 'primal_only' if witness is not None else 'unverified'
        elif ray is not None:
            c=verify_ray(lp,ray);dump(folder/'ray.json',ray);dump(folder/'certificate.json',c)
            if c['infeasibility_certified']:result['outcome']='infeasibility_certified'
    if witness is not None:
        value=arithmetic.objective(model,witness);dump(folder/'witness.json',[str(v) for v in witness]);converted=list(map(float,witness))
        delivered,_,_=arithmetic.floating_check(model,converted);dump(folder/'witness-float-check.json',delivered)
        if delivered['primal_accepted']:save(folder/'witness-float.npz',converted)
        result.update(exact_upper=str(value),float_deliverable=delivered['primal_accepted'],target_met=delivered['primal_accepted'] and value<=TARGET)
    result['total_seconds']=time.perf_counter()-began;dump(folder/'audit.json',result)
    cache[key]=str(folder.relative_to(HERE));return result
