"""Frozen controls first, then Budget only for an independently observed problem."""
import argparse
import gzip
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import time

import numpy as np
import scipy.sparse as sp

from factors import row_spec,select
from fetch import HERE,dump,sha


def load(name):
    with gzip.open(HERE/'models'/name/'original.json.gz','rt') as stream:return json.load(stream)


def factor_list(model,policy,budget):
    if policy.startswith('Base'):return [1.]*len(model['rows'])
    result=[]
    for r in model['rows']:
        spec=row_spec(r,model['variables'])
        decision=select(spec,budget if policy=='Budget-L2' else None)
        if decision['factor'] is None:raise ValueError('incompatible row '+r['name'])
        result.append(decision['factor'])
    return result


def export_lp(model,factors,path):
    assert model['objective_offset']==0.,'nonzero objective constant needs an explicit adapter'
    def terms(data):return ' '.join(f'{value:+.17g} v{j}' for j,value in data if value)
    with gzip.open(path,'wt') as stream:
        objective=terms((j,v['cost']) for j,v in enumerate(model['variables']))
        stream.write('Minimize\n obj: '+(objective or '0 v0')+'\nSubject To\n')
        for i,(row,alpha) in enumerate(zip(model['rows'],factors)):
            data=terms((int(j),value*alpha) for j,value in row['terms'].items())
            sense={'=':'=','<':'<=','>':'>='}[row['sense']]
            stream.write(f' r{i}: '+(data or '0 v0')+f' {sense} {row["rhs"]*alpha:.17g}\n')
        stream.write('Bounds\n')
        for j,var in enumerate(model['variables']):
            lo,hi=var['lower'],var['upper']
            if lo is None and hi is None:stream.write(f' v{j} free\n')
            elif hi is None:stream.write(f' {lo:.17g} <= v{j}\n')
            else:stream.write((' -inf' if lo is None else f' {lo:.17g}')+f' <= v{j} <= {hi:.17g}\n')
        for label,binary in [('Binaries',True),('Generals',False)]:
            chosen=[j for j,v in enumerate(model['variables']) if v['integer'] and
                ((v['lower'] is not None and v['upper'] is not None and 0<=v['lower']<=v['upper']<=1)==binary)]
            if chosen:
                stream.write(label+'\n')
                for j in chosen:stream.write(f' v{j}\n')
        stream.write('End\n')


def audit(reader,model,factors,original=False):
    variables=reader.getVars();rows=reader.getConstrs()
    assert reader.ModelSense==1 and reader.ObjCon==0 and reader.NumSOS==0 and reader.NumQConstrs==0
    vmap={v.VarName:v for v in variables};rmap={r.ConstrName:r for r in rows}
    vn=[v['name'] if original else f'v{j}' for j,v in enumerate(model['variables'])]
    rn=[r['source_name'] if original else f'r{i}' for i,r in enumerate(model['rows'])]
    assert len(vmap)==len(vn) and set(vn)==set(vmap)
    assert len(rmap)==len(rn) and set(rn)==set(rmap)
    ordered=[vmap[n] for n in vn];row_order=[rmap[n] for n in rn]
    lower=lambda x:None if x<=-1e100 else float(x)
    upper=lambda x:None if x>=1e100 else float(x)
    assert [lower(v.LB) for v in ordered]==[v['lower'] for v in model['variables']]
    assert [upper(v.UB) for v in ordered]==[v['upper'] for v in model['variables']]
    assert [v.VType in ('B','I') for v in ordered]==[v['integer'] for v in model['variables']]
    assert [float(v.Obj) for v in ordered]==[v['cost'] for v in model['variables']]
    assert [r.Sense for r in row_order]==[r['sense'] for r in model['rows']]
    assert [float(r.RHS) for r in row_order]==[r['rhs']*a for r,a in zip(model['rows'],factors)]
    rr=[];cc=[];vv=[]
    for i,(row,alpha) in enumerate(zip(model['rows'],factors)):
        for j,value in row['terms'].items():rr.append(i);cc.append(int(j));vv.append(value*alpha)
    expected=sp.csr_matrix((vv,(rr,cc)),shape=(len(rn),len(vn)))
    actual=reader.getA()[[r.index for r in row_order],:][:,[v.index for v in ordered]]
    difference=actual-expected
    if difference.nnz and np.any(difference.data):
        raise ValueError('import changed '+str(np.count_nonzero(difference.data))+' matrix entries')
    return dict(variables=len(vn),rows=len(rn),nonzeros=expected.nnz,
                coefficients_rhs_objective_bounds_integer_domains_checked=True)


def prepare(stage):
    import gurobipy as gp
    design=json.loads((HERE/f'stage-{stage}-design.json').read_text())
    dest=HERE/f'stage-{stage}-exports.json'
    assert not dest.exists(),'exports already frozen'
    env=gp.Env(empty=True);env.setParam('OutputFlag',0);env.start()
    records=[]
    for entry in design['selected']:
        name=entry['instance'];model=load(name)
        folder=HERE/'exports'/name;folder.mkdir(parents=True,exist_ok=True)
        policies=['Base','Dyadic-L2'] if stage.startswith('b') else ['Budget-L2']
        if stage.startswith('b'):
            try:
                source=gp.read(str(HERE/'sources'/(name+'.mps.gz')),env=env)
                result=audit(source,model,[1.]*len(model['rows']),True);source.dispose()
                dump(HERE/'models'/name/'source-reader-audit.json',result)
            except (AssertionError,ValueError) as error:
                dump(HERE/'models'/name/'source-reader-audit.json',dict(accepted=False,error=str(error)))
                # Each exported arm is still audited, and no source entry is discarded.
        for policy in policies:
            started=time.perf_counter()
            factors=factor_list(model,policy,entry['budget'])
            path=folder/(policy+'.lp.gz');export_lp(model,factors,path)
            prep=time.perf_counter()-started
            dump(folder/(policy+'-factors.json'),factors)
            rec=dict(instance=name,policy=policy,export_sha256=sha(path.read_bytes()),preparation_seconds=prep,
                     factors_sha256=sha((folder/(policy+'-factors.json')).read_bytes()))
            try:
                reader=gp.read(str(path),env=env);rec.update(audit(reader,model,factors));reader.dispose()
                rec['import_accepted']=True
            except (AssertionError,ValueError) as error:rec.update(import_accepted=False,error=str(error))
            records.append(rec)
            print('prepared',name,policy,rec['import_accepted'],round(prep,4),flush=True)
    env.dispose();dump(dest,records)


def worker(stage,name,policy):
    import gurobipy as gp
    design=json.loads((HERE/f'stage-{stage}-design.json').read_text())
    exports=json.loads((HERE/f'stage-{stage}-exports.json').read_text())
    folder=HERE/f'stage-{stage}'/name/policy;folder.mkdir(parents=True,exist_ok=True)
    assert not (folder/'run.json').exists()
    export='Base' if policy.startswith('Base') else 'Budget-L2' if policy=='Budget-L2' else 'Dyadic-L2'
    spec=next(r for r in exports if r['instance']==name and r['policy']==export)
    if not spec['import_accepted']:
        dump(folder/'run.json',dict(instance=name,policy=policy,abstention='import mismatch',sol_count=0));return
    path=HERE/'exports'/name/(export+'.lp.gz')
    assert sha(path.read_bytes())==spec['export_sha256']
    env=gp.Env(empty=True);env.setParam('OutputFlag',1);env.setParam('LogToConsole',0)
    env.setParam('LogFile',str(folder/'native.log'));env.start()
    started=time.perf_counter();solver=gp.read(str(path),env=env)
    params=design['common'].copy()
    if policy.endswith('tight'):params['FeasibilityTol']=1e-9
    if policy.endswith('NumericFocus3'):params['NumericFocus']=3
    for k,v in params.items():solver.setParam(k,v)
    solver.optimize();elapsed=time.perf_counter()-started
    finite=lambda v:float(v) if math.isfinite(float(v)) else None
    rec=dict(instance=name,policy=policy,status=int(solver.Status),sol_count=int(solver.SolCount),
        work=float(solver.Work),solver_seconds=float(solver.Runtime),load_solve_seconds=elapsed,
        preparation_seconds=spec['preparation_seconds'],measured_cycle_seconds=spec['preparation_seconds']+elapsed,
        best_bound=finite(solver.ObjBound),objective=finite(solver.ObjVal) if solver.SolCount else None,
        nodes=float(solver.NodeCount),parameters=params,export_sha256=spec['export_sha256'])
    if solver.SolCount:
        by_name={v.VarName:v for v in solver.getVars()};point=[float(by_name[f'v{j}'].X) for j in range(len(by_name))]
        with gzip.open(folder/'point.json.gz','wt') as stream:json.dump(point,stream)
        rec['point_sha256']=sha((folder/'point.json.gz').read_bytes())
    solver.dispose();env.dispose()
    dump(folder/'run.pending.json',rec);(folder/'run.pending.json').replace(folder/'run.json')


def run(stage):
    design=json.loads((HERE/f'stage-{stage}-design.json').read_text())
    jobs=[(r['instance'],p) for r in design['selected'] for p in design['policies']]
    random.Random(239).shuffle(jobs)
    for i,(name,policy) in enumerate(jobs):
        folder=HERE/f'stage-{stage}'/name/policy
        if (folder/'run.json').exists():continue
        folder.mkdir(parents=True,exist_ok=True)
        assert not (folder/'attempt-start.json').exists(),'incomplete attempt retained: '+str(folder)
        dump(folder/'attempt-start.json',dict(instance=name,policy=policy,unix=time.time()))
        started=time.perf_counter()
        with (folder/'process.log').open('w') as stream:
            result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'worker',stage,name,policy],stdout=stream,stderr=subprocess.STDOUT,
                env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'})
        dump(folder/'process.json',dict(returncode=result.returncode,wall_seconds=time.perf_counter()-started))
        if result.returncode:raise RuntimeError('worker failed: '+str(folder))
        rec=json.loads((folder/'run.json').read_text())
        print(i+1,'/',len(jobs),name,policy,rec.get('status'),rec.get('sol_count'),rec.get('work'),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=('prepare','run','worker'))
    ap.add_argument('stage',choices=('b','c','b2','c2'));ap.add_argument('instance',nargs='?');ap.add_argument('policy',nargs='?');args=ap.parse_args()
    if args.command=='worker':worker(args.stage,args.instance,args.policy)
    else:globals()[args.command](args.stage)
