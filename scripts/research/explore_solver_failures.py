#!/usr/bin/env python3
"""Read-only diagnosis of archived solver candidates, separately from acceptance.

Does not import the experimental runner/checker or invoke either solver. All row
residuals are recomputed exactly for the stored binary64 values. The distinction
between original row budget and near-integrality is deliberate.
"""
import argparse
from collections import Counter, defaultdict
import csv
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np


def residual(a, b, x):
    return max(F(0), sum((F(float(v))*F(float(z)) for v,z in zip(a,x)), F(0))-F(float(b)))


def reruns(source, out):
    """24 predeclared diagnosis runs; lattice reformulation is a standard control."""
    import highspy as hs
    import gurobipy as gp
    from scipy.sparse import csr_matrix
    out=out/'reruns';out.mkdir(exist_ok=True)
    env=gp.Env(empty=True);env.setParam('OutputFlag',0);env.start()
    old=list(csv.DictReader((source/'runs.csv').open()))
    results=[]
    for name in ['cardinality_s100_e9','packing_s104_e9']:
        with np.load(source/'models'/f'{name}.npz') as data:
            A,b,c,delta=[data[k] for k in ('A','b','c','delta')];opt=int(data['optimum'])
        choices=((np.arange(2**len(c))[:,None] >> np.arange(len(c)))&1).astype(np.int64)
        original_feasible=np.all(choices@A.astype(np.int64).T<=np.floor(b),axis=1)
        for variant in ['Base','Budget-dyadic','Lattice-normalized']:
            if variant=='Lattice-normalized':
                gcds=np.array([math.gcd(*(int(x) for x in ar)) for ar in A],dtype=np.int64)
                assert all(g>0 for g in gcds)
                As=A/gcds[:,None];bs=np.array([math.floor(F(float(br))/int(g)) for br,g in zip(b,gcds)],dtype=float)
                # Exhaustive equivalence check precedes each transformed solve.
                assert np.array_equal(original_feasible,np.all(choices@As.T<=bs,axis=1))
            else:
                row=next(r for r in old if r['model_id']==name and r['method']==variant)
                ds=np.array(json.loads(row['factors']));As=ds[:,None]*A;bs=ds*b
            for presolve in [False,True]:
                for solver in ['highs','gurobi']:
                    key=f'{name}_{variant}_{solver}_p{int(presolve)}';log=out/f'{key}.log'
                    start=time.perf_counter()
                    if solver=='highs':
                        h=hs.Highs()
                        for k,v in [('output_flag',True),('log_to_console',False),('log_file',str(log)),('threads',1),
                                    ('random_seed',int(name.split('_s')[1].split('_')[0])),('presolve','on' if presolve else 'off'),
                                    ('time_limit',10.),('mip_rel_gap',0.),('mip_abs_gap',0.),('primal_feasibility_tolerance',1e-6),('mip_feasibility_tolerance',1e-6)]:
                            assert h.setOptionValue(k,v)==hs.HighsStatus.kOk
                        h.addVars(len(c),np.zeros(len(c)),np.ones(len(c)))
                        h.changeColsCost(len(c),np.arange(len(c),dtype=np.int32),-c)
                        h.changeColsIntegrality(len(c),np.arange(len(c),dtype=np.int32),np.ones(len(c),dtype=np.uint8))
                        mat=csr_matrix(As)
                        h.addRows(len(bs),np.full(len(bs),-hs.kHighsInf),bs,mat.nnz,mat.indptr.astype(np.int32),mat.indices.astype(np.int32),mat.data)
                        h.run();sol=h.getSolution();status=h.getModelStatus().name
                        x=np.array(sol.col_value) if sol.value_valid else None
                        info=h.getInfo();extra=dict(native_max_integrality_violation=info.max_integrality_violation,
                                                   native_max_primal_infeasibility=info.max_primal_infeasibility)
                    else:
                        m=gp.Model(env=env)
                        for k,v in [('OutputFlag',1),('LogToConsole',0),('LogFile',str(log)),('Threads',1),('Seed',int(name.split('_s')[1].split('_')[0])),
                                    ('Presolve',-1 if presolve else 0),('TimeLimit',10.),('MIPGap',0.),('MIPGapAbs',0.),('FeasibilityTol',1e-6),('IntFeasTol',1e-6)]:m.setParam(k,v)
                        xx=m.addMVar(len(c),vtype=gp.GRB.BINARY);m.addMConstr(As,xx,'<',bs);m.setObjective(-c@xx);m.optimize()
                        x=np.array(xx.X) if m.SolCount else None;status=str(m.Status)
                        extra=dict(native_max_integrality_violation=m.IntVio if m.SolCount else None,
                                   native_max_primal_infeasibility=m.ConstrVio if m.SolCount else None)
                        m.dispose()
                    row=dict(model_id=name,variant=variant,presolve=presolve,solver=solver,status=status,
                             seconds=time.perf_counter()-start,x=x.tolist() if x is not None else None,
                             optimum=opt,verified_optimum=False,original_row_budget=None,
                             rounded_objective=None,rounded_feasible=None,**extra)
                    if x is not None:
                        rounded=np.rint(x);feas=all(residual(ar,br,rounded)==0 for ar,br in zip(A,b))
                        obj=int(c@rounded)
                        row.update(verified_optimum=bool(feas and obj==opt and np.max(np.abs(x-rounded))<=1e-9),
                                   original_row_budget=all(residual(ar,br,x)<=F(float(d)) for ar,br,d in zip(A,b,delta)),
                                   rounded_objective=obj,rounded_feasible=feas)
                    results.append(row)
    env.dispose()
    assert len(results)==24
    (out/'runs.json').write_text(json.dumps(results,indent=2)+'\n')
    print('Reruns:',dict(Counter((r['variant'],r['verified_optimum']) for r in results)))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',type=Path,default=Path('results-revision/research-audit/budget-final'))
    ap.add_argument('--out',type=Path,default=Path('results-revision/research-audit/exploration-failures'))
    ap.add_argument('--reruns',action='store_true',help='Also run 24 solver diagnoses with native logs.')
    args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    models={}
    for path in sorted((args.source/'models').glob('*.npz')):
        with np.load(path) as data:
            models[path.stem]={k:data[k].copy() for k in data.files}
    rows=list(csv.DictReader((args.source/'runs.csv').open()))
    detailed=[]
    for row in rows:
        data=models[row['model_id']];A,b,c,delta=[data[k] for k in ('A','b','c','delta')]
        x=json.loads(row['x']);ds=json.loads(row['factors'])
        out={k:row[k] for k in ('model_id','family','seed','exponent','presolve','method','solver','status')}
        out.update(category='abstain' if row['status']=='ABSTAIN' else 'no_solution',
                   original_row_budget=False,exported_row_tolerance=False,exact_scaled_row_tolerance=False,
                   rounded_feasible=False,rounded_objective=None,rounded_optimum=False,
                   strict_integrality=False,native_integrality=False,original_max_violation=None,
                   exported_max_violation=None,exported_max_tolerance_ratio=None,
                   max_integrality_error=None,objective_difference=None)
        if x is not None:
            x=np.array(x);ds=np.array(ds);r=np.rint(x);tol=F(float(row['solver_tolerance']))
            v=[residual(a,z,x) for a,z in zip(A,b)]
            vr=[residual(a,z,r) for a,z in zip(A,b)]
            ve=[residual(d*a,float(d*z),x) for a,z,d in zip(A,b,ds)]
            integral=float(np.max(np.abs(x-r)))
            rounded_feasible=all(z==0 for z in vr) and bool(np.all((r>=0)&(r<=1)))
            rounded_objective=int(c@r)
            optimal=rounded_feasible and rounded_objective==int(data['optimum'])
            bounds=bool(np.all((x>=-1e-9)&(x<=1+1e-9)))
            out.update(original_row_budget=all(z<=F(float(d)) for z,d in zip(v,delta)),
                       exported_row_tolerance=all(z<=tol for z in ve),
                       exact_scaled_row_tolerance=all(z*F(float(d))<=tol for z,d in zip(v,ds)),
                       rounded_feasible=rounded_feasible,rounded_objective=rounded_objective,
                       rounded_optimum=optimal,strict_integrality=integral<=1e-9,
                       native_integrality=integral<=float(tol),original_max_violation=float(max(v)),
                       exported_max_violation=float(max(ve)),exported_max_tolerance_ratio=float(max(ve)/tol),
                       max_integrality_error=integral,objective_difference=rounded_objective-int(data['optimum']))
            if not rounded_feasible: out['category']='rounded_infeasible'
            elif not optimal: out['category']='feasible_suboptimal'
            elif not bounds: out['category']='bounds_only'
            elif integral>1e-9: out['category']='strict_integrality_only'
            else: out['category']='verified_optimum'
            assert (out['category']=='verified_optimum')==(row['rounded_optimal']=='True')
        detailed.append(out)
    with (args.out/'diagnostics.csv').open('w') as fh:
        w=csv.DictWriter(fh,fieldnames=list(detailed[0]));w.writeheader();w.writerows(detailed)
    summary={}
    for group in [('solver','method'),('solver','exponent','presolve'),('solver','method','exponent','presolve')]:
        grouped=defaultdict(list)
        for row in detailed:grouped[tuple(row[k] for k in group)].append(row)
        entries=[]
        for key,data in sorted(grouped.items()):
            accepted=[r for r in data if r['category'] not in ('abstain','no_solution')]
            item=dict(zip(group,key));item.update(n=len(data),categories=dict(Counter(r['category'] for r in data)),
                 row_budget_fail=sum(not r['original_row_budget'] for r in accepted),
                 exported_tolerance_fail=sum(not r['exported_row_tolerance'] for r in accepted),
                 rounded_optimal_but_row_budget_fail=sum(r['rounded_optimum'] and not r['original_row_budget'] for r in accepted),
                 rounded_infeasible_but_row_budget_ok=sum(r['category']=='rounded_infeasible' and r['original_row_budget'] for r in accepted))
            entries.append(item)
        summary['_'.join(group)]=entries
    summary['source_sha256']=hashlib.sha256((args.source/'runs.csv').read_bytes()).hexdigest()
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    for row in summary['solver_method']:print(json.dumps(row))
    if args.reruns:reruns(args.source,args.out)


if __name__=='__main__':main()
