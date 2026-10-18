"""Bounded native network pilot; immutable exports, fresh processes, atomic records."""
import argparse
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import subprocess
import sys
import time

import numpy as np
import scipy.sparse as sp

from screen import HERE, blocks, digest, dump, factor_rows

ARMS=('Base','Ruiz-R4','Flat-L2','Role-Hybrid','Budget-L2','Flat-L2-tight','Flat-L2-NF3')


def factors(model,policy):
    policy='Flat-L2' if policy in ('Flat-L2-tight','Flat-L2-NF3') else policy
    decisions=factor_rows(model,'Flat-L2',1e-5) if policy=='Budget-L2' else factor_rows(model,policy)
    assert all(r['factor'] is not None for r in decisions)
    return np.array([r['factor'] for r in decisions if r['role']=='local']),np.array(
        [r['factor'] for r in decisions if r['role']=='coupling'])


def numeric_data(model):
    b,d=blocks(model)
    k=len(model['demands'])
    n,q=b.shape
    p=d.shape[1]
    matrix=sp.vstack([sp.hstack([sp.kron(sp.eye(k),sp.csr_matrix(b)),sp.csr_matrix((k*n,p))]),
                      sp.hstack([sp.hstack([sp.eye(q)]*k),sp.csr_matrix(d)])],format='csr')
    rhs=np.zeros(k*n+q)
    for i,r in enumerate(model['demands']):
        rhs[i*n+r['u']]=r['amount']
        rhs[i*n+r['v']]=-r['amount']
    cost=[a['cost'] for a in model['arcs']]
    if model['family']=='Gunluk-expansion':
        cost=cost*2
        design=[a['small_cost'] for a in model['arcs']]+[a['large_cost'] for a in model['arcs']]
        existing=[a['existing'] for a in model['arcs']]
        rhs[k*n:]=existing*2
        upper=[None]*(k*q+p)
    else:
        design=[a['fixed'] for a in model['arcs']]
        upper=[None]*(k*q)+[1.]*p
    return matrix,rhs,np.array(cost*k+design),upper


def write_lp(model,policy,path):
    matrix,rhs,cost,upper=numeric_data(model)
    local,coupling=factors(model,policy)
    k=len(model['demands'])
    scales=np.r_[np.tile(local,k),coupling]
    nflow=k*len(coupling)
    def terms(indices,values):
        return ' '.join(f'{float(v):+.17g} v{j}' for j,v in zip(indices,values) if v)
    with gzip.open(path,'wt') as stream:
        stream.write('Minimize\n obj: '+terms(np.flatnonzero(cost),cost[cost!=0])+'\nSubject To\n')
        for i in range(len(rhs)):
            start,end=matrix.indptr[i:i+2]
            vals=matrix.data[start:end]*scales[i]
            sense='=' if i<k*len(local) else '<='
            stream.write(f' r{i}: '+terms(matrix.indices[start:end],vals)+f' {sense} {rhs[i]*scales[i]:.17g}\n')
        stream.write('Bounds\n')
        for j,ub in enumerate(upper):
            stream.write(f' 0 <= v{j}'+(f' <= {ub:.17g}' if ub is not None else '')+'\n')
        stream.write('Generals\n' if model['family']=='Gunluk-expansion' else 'Binaries\n')
        for j in range(nflow,matrix.shape[1]):
            stream.write(f' v{j}\n')
        stream.write('End\n')


def check_import(model,policy,path,env):
    import gurobipy as gp
    m=gp.read(str(path),env=env)
    matrix,rhs,cost,upper=numeric_data(model)
    local,coupling=factors(model,policy)
    scale=np.r_[np.tile(local,len(model['demands'])),coupling]
    imported=m.getVars()
    by_name={v.VarName:v for v in imported}
    assert len(by_name)==matrix.shape[1] and set(by_name)=={f'v{j}' for j in range(matrix.shape[1])}
    variables=[by_name[f'v{j}'] for j in range(matrix.shape[1])]
    assert m.ModelSense==1 and m.ObjCon==0 and m.NumSOS==0 and m.NumQConstrs==0
    expected=sp.diags(scale)@matrix
    difference=m.getA()[:,[v.index for v in variables]]-expected
    assert difference.nnz==0 or np.all(difference.data==0)
    assert np.array_equal(m.getAttr('RHS'),rhs*scale)
    assert np.array_equal(m.getAttr('Obj',variables),cost)
    nflow=len(model['demands'])*len(coupling)
    expected_type='I' if model['family']=='Gunluk-expansion' else 'B'
    assert m.getAttr('VType',variables)==['C']*nflow+[expected_type]*(len(variables)-nflow)
    assert m.getAttr('LB',variables)==[0.]*len(variables)
    assert [None if u>=1e100 else u for u in m.getAttr('UB',variables)]==upper
    assert m.getAttr('Sense')==['=']*(len(model['demands'])*len(local))+['<']*len(coupling)
    assert m.getAttr('ConstrName')==[f'r{j}' for j in range(matrix.shape[0])]
    m.dispose()
    return dict(coefficients=int(matrix.nnz),rows=matrix.shape[0],variables=matrix.shape[1],
                objective_bounds_domains_rhs_names_checked=True,export_sha256=digest(path.read_bytes()))


def prepare():
    import gurobipy as gp
    assert not (HERE/'pilot-design.json').exists(),'immutable design already prepared'
    models=json.loads((HERE/'models.json').read_text())
    env=gp.Env(empty=True);env.setParam('OutputFlag',0);env.start()
    exports=[]
    for model in models:
        folder=HERE/'exports'/model['name'];folder.mkdir(parents=True,exist_ok=True)
        for policy in ARMS[:5]:
            path=folder/(policy+'.lp.gz')
            write_lp(model,policy,path)
            checks=check_import(model,policy,path,env)
            exports.append(dict(instance=model['name'],policy=policy,**checks))
        print('prepared',model['name'],flush=True)
    env.dispose()
    order=[dict(instance=m['name'],policy=p) for m in models for p in ARMS]
    random.Random(223).shuffle(order)
    dump(HERE/'pilot-design.json',dict(protocol_sha256=digest((HERE/'PROTOCOL.md').read_bytes()),
        models_sha256=digest((HERE/'models.json').read_bytes()), exports=exports,
        gurobi_version=list(gp.gurobi.version()),python=platform.python_version(),
        platform=platform.platform(),processor=platform.processor(),order=order,
        alias={'Coupling-only':'Role-Hybrid'},
        alias_evidence='identical local unit coefficients and complete row factors on all twelve models; no duplicated solver evidence',
        common=dict(Threads=4,Seed=223,Presolve=-1,ScaleFlag=-1,IntFeasTol=1e-9,
                    MIPGap=.01,WorkLimit=.25,TimeLimit=10.,FeasibilityTol=1e-6)))


def worker(instance,policy,study='pilot',seed=None):
    import gurobipy as gp
    design=json.loads((HERE/'pilot-design.json').read_text())
    followup=json.loads((HERE/'replication-design.json').read_text()) if study=='replication' else None
    model=next(m for m in json.loads((HERE/'models.json').read_text()) if m['name']==instance)
    folder=HERE/'runs'/instance/policy if study=='pilot' else HERE/'replication'/instance/policy/f'seed-{seed}'
    folder.mkdir(parents=True,exist_ok=True)
    assert not (folder/'run.json').exists(),'completed result must not be overwritten'
    export_policy='Flat-L2' if policy in ('Flat-L2-tight','Flat-L2-NF3') else policy
    path=HERE/'exports'/instance/(export_policy+'.lp.gz')
    expected=next(r['export_sha256'] for r in design['exports'] if r['instance']==instance and r['policy']==export_policy)
    assert digest(path.read_bytes())==expected
    env=gp.Env(empty=True);env.setParam('OutputFlag',1);env.setParam('LogToConsole',0)
    env.setParam('LogFile',str(folder/'native.log'));env.start()
    started=time.perf_counter()
    solver=gp.read(str(path),env=env)
    params=design['common'].copy()
    if followup is not None:
        assert seed in followup['seeds']
        params['Seed']=seed
        params['BestObjStop']=followup['references'][instance]['target_inward_float']
    if policy=='Flat-L2-tight':params['FeasibilityTol']=1e-9
    if policy=='Flat-L2-NF3':params['NumericFocus']=3
    for key,value in params.items():solver.setParam(key,value)
    solver.optimize()
    elapsed=time.perf_counter()-started
    finite=lambda x:float(x) if math.isfinite(float(x)) else None
    record=dict(instance=instance,policy=policy,seed=params['Seed'],status=int(solver.Status),sol_count=int(solver.SolCount),
        work=float(solver.Work),solver_seconds=float(solver.Runtime),read_and_solve_seconds=elapsed,
        nodes=float(solver.NodeCount),iterations=float(solver.IterCount),
        objective=finite(solver.ObjVal) if solver.SolCount else None,
        best_bound=finite(solver.ObjBound),parameters=params,export_sha256=expected)
    if solver.SolCount:
        by_name={v.VarName:v for v in solver.getVars()}
        point=[float(by_name[f'v{j}'].X) for j in range(len(by_name))]
        with gzip.open(folder/'point.json.gz','wt') as stream:json.dump(point,stream)
        record['point_sha256']=digest((folder/'point.json.gz').read_bytes())
    solver.dispose();env.dispose()
    dump(folder/'run.pending.json',record)
    (folder/'run.pending.json').replace(folder/'run.json')


def run():
    design=json.loads((HERE/'pilot-design.json').read_text())
    for i,record in enumerate(design['order']):
        instance,policy=record['instance'],record['policy']
        folder=HERE/'runs'/instance/policy
        if (folder/'run.json').exists():continue
        folder.mkdir(parents=True,exist_ok=True)
        if (folder/'attempt-start.json').exists():
            raise RuntimeError('incomplete attempt retained; diagnose before rerunning '+str(folder))
        dump(folder/'attempt-start.json',dict(unix=time.time(),pid=os.getpid(),**record))
        started=time.perf_counter()
        with (folder/'process.log').open('w') as log:
            process=subprocess.run([sys.executable,str(Path(__file__).resolve()),'worker',instance,policy],
                stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'})
        dump(folder/'process.json',dict(returncode=process.returncode,wall_seconds=time.perf_counter()-started))
        if process.returncode:raise RuntimeError('worker failure; inspect '+str(folder/'process.log'))
        result=json.loads((folder/'run.json').read_text())
        print(i+1,'/',len(design['order']),instance,policy,result['status'],
              'point',result['sol_count'],'work',round(result['work'],6),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=('prepare','run','worker'))
    ap.add_argument('instance',nargs='?');ap.add_argument('policy',nargs='?');args=ap.parse_args()
    if args.command=='worker':worker(args.instance,args.policy)
    else:globals()[args.command]()
