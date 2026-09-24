#!/usr/bin/env python3
"""Frozen exploratory comparison of matrix-only integer-direction compression."""
import argparse,csv,hashlib,json,math,shutil,time
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import numpy as np

from integer_direction_compression import (canonical_integer_row,compress_matrix,
                                           compression_step,single_coefficient_control)
from isolated_solvers import isolated_solve
from budget_scaling import dyadic_factor,exact_row_violation


def dynamic_optimum(A,b,c,blocks,q,local_rows):
    states=np.array(list(product([0,1],repeat=q)),np.int64)
    cap=int(b[-1]);dp=np.full(cap+1,-10**12,dtype=np.int64);dp[0]=0;counts=[]
    for k in range(blocks):
        sl=slice(q*k,q*k+q);rr=slice(local_rows*k,local_rows*k+local_rows)
        good=np.all(states@A[rr,sl].astype(np.int64).T<=np.floor(b[rr]),axis=1)
        weights=states[good]@A[-1,sl].astype(np.int64);profits=states[good]@c[sl].astype(np.int64)
        by_weight={}
        for w,p in zip(weights,profits):
            by_weight[int(w)]=max(by_weight.get(int(w),-10**12),int(p))
        new=np.full_like(dp,-10**12)
        for w,p in by_weight.items():
            if w<=cap:new[w:]=np.maximum(new[w:],dp[:cap+1-w]+p)
        dp=new;counts.append(int(good.sum()))
    return int(dp.max()),counts


def generate(M,seed,blocks=8,q=10):
    rng=np.random.default_rng(2026091400+seed);local_rows=3;n=blocks*q
    A=np.zeros((local_rows*blocks+1,n));b=np.zeros(len(A));metadata=[]
    c=rng.integers(1,50,n).astype(float);A[-1]=rng.integers(1,10,n);b[-1]=int(.35*A[-1].sum())
    for k in range(blocks):
        for r in range(local_rows):
            # Independent signed directions; there is no planted opposite pair
            # or single fixed aggregate shared across all local constraints.
            v=rng.integers(-4,6,q);v[0]=int(rng.integers(1,6))
            u=rng.integers(-15,16,q)
            alpha=int(M*[11,17,23][r]+[31,29,71][r])
            level=max(1,int(.48*np.maximum(v,0).sum()))
            tau=int(rng.integers(-15,16))
            idx=local_rows*k+r;A[idx,q*k:q*k+q]=alpha*v+u;b[idx]=alpha*level+tau+.5
            vv=np.zeros(n,dtype=int);vv[q*k:q*k+q]=v
            metadata.append(dict(v=vv.tolist(),alpha=alpha))
    opt,counts=dynamic_optimum(A,b,c,blocks,q,local_rows)
    return A,b,c,opt,counts,metadata


def transform(A,b,method,metadata):
    if method=='Base':return A,b,[]
    if method in ['Rounded-direction','Rational-direction']:
        return compress_matrix(A,b,'rounded' if method.startswith('Rounded') else 'rational')
    if method=='Dyadic-GM':
        factors=[dyadic_factor(row,rhs).factor for row,rhs in zip(A,b)]
        if any(d is None for d in factors):return None,None,[]
        return A*np.array(factors)[:,None],b*np.array(factors),[]
    rows=[];rhs=[];proofs=[]
    for i,(row,br) in enumerate(zip(A,b)):
        if method=='Single-coefficient':ar,rr=single_coefficient_control(row,br)
        elif method=='GCD-floor':ar,rr,_=canonical_integer_row(row,br)
        elif method=='Oracle-direction':
            ar=[int(v) for v in row];rr=math.floor(br)
            if i<len(metadata):
                item=metadata[i]
                result=compression_step(ar,rr,item['v'],item['alpha'],[0]*len(ar),[1]*len(ar))
                assert result is not None
                ar,rr,proof=result;proofs.append(proof)
            ar,rr,_=canonical_integer_row(ar,rr)
        else:raise ValueError(method)
        assert all(F(float(v))==v for v in [*ar,rr])
        rows.append(ar);rhs.append(rr)
    return np.array(rows,float),np.array(rhs,float),proofs


def check_local_equivalence(A,b,B,rhs,blocks,q,local_rows):
    if B is None:return
    states=np.array(list(product([0,1],repeat=q)),np.int64)
    for k in range(blocks):
        sl=slice(q*k,q*k+q);rr=slice(local_rows*k,local_rows*k+local_rows)
        orig=np.all(states@A[rr,sl].astype(np.int64).T<=np.floor(b[rr]),axis=1)
        # Exact binary64 comparisons are required for pure scaling. Dyadic
        # products and activities here are exactly representable within 2^53.
        current=np.all(states@B[rr,sl].T<=rhs[rr],axis=1)
        assert np.array_equal(orig,current),(k,np.flatnonzero(orig!=current).tolist())


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--saved-input',type=Path);ap.add_argument('--methods',nargs='+')
    ap.add_argument('--seeds',type=int,default=4);ap.add_argument('--start-seed',type=int,default=200)
    args=ap.parse_args()
    if args.out.exists():raise ValueError('Use a new output directory; runs are frozen')
    args.out.mkdir(parents=True);(args.out/'exports').mkdir()
    methods=args.methods or ['Base','GCD-floor','Single-coefficient','Dyadic-GM','Rounded-direction','Rational-direction','Oracle-direction']
    sources={}
    for name in ['explore_direction_compression.py','integer_direction_compression.py','joint_rounding_certificate.py',
                 'isolated_solvers.py','residual_budget_experiment.py','budget_scaling.py']:
        p=Path(__file__).parent/name;sources[name]=hashlib.sha256(p.read_bytes()).hexdigest();shutil.copy2(p,args.out/('source-'+name))
    if args.saved_input:
        files=sorted(args.saved_input.glob('M*_s*.npz'));blocks,q,local_rows=12,6,2
        assigned=[dict(M=int(p.stem[1:].split('_s')[0]),seed=int(p.stem.split('_s')[1]),path=str(p)) for p in files]
    else:
        blocks,q,local_rows=8,10,3
        assigned=[dict(M=M,seed=s) for M in [1000,10**6,10**9] for s in range(args.start_seed,args.start_seed+args.seeds)]
    (args.out/'design.json').write_text(json.dumps(dict(
        purpose='Exploratory; direction extraction and coefficient reduction have prior art; no novelty claim',
        models=assigned,blocks=blocks,local_size=q,local_rows=local_rows,methods=methods,
        epsilon=1e-6,eta=1e-6,native_limit=10,external_limit=25,threads=1,
        primary='Exact original rounded feasibility and optimum, reported separately',
        sources=sources,oracle_uses_generator_metadata=True,matrix_only_methods=['Rounded-direction','Rational-direction']),indent=2)+'\n')
    runs=[];proofs={};instance_info={}
    for item in assigned:
        M,seed=item['M'],item['seed'];key=f'M{M}_s{seed}'
        if args.saved_input:
            raw=np.load(item['path']);A,b,c=raw['A'],raw['b'],raw['c'];metadata=[]
            opt,counts=dynamic_optimum(A,b,c,blocks,q,local_rows);assert opt==int(raw['optimum'])
        else:A,b,c,opt,counts,metadata=generate(M,seed)
        np.savez_compressed(args.out/(key+'.npz'),A=A,b=b,c=c,optimum=opt)
        instance_info[key]=dict(local_feasible_counts=counts,optimum=opt,metadata=metadata)
        assert np.max(abs(A))*A.shape[1]<2**62 and np.max(abs(A))*q<2**53
        for method in methods:
            start=time.perf_counter();B,rhs,proof=transform(A,b,method,metadata);prep=time.perf_counter()-start
            if B is not None:
                check_local_equivalence(A,b,B,rhs,blocks,q,local_rows)
                np.savez_compressed(args.out/'exports'/(key+'_'+method+'.npz'),A=B,b=rhs)
                proofs[key+'_'+method]=proof
                row_safe=all(F(1e-6)*(1+sum(abs(F(float(a))) for a in row))<1 for row in B) if np.array_equal(B,np.rint(B)) and np.array_equal(rhs,np.rint(rhs)) else None
            else:row_safe=None
            for presolve in [False,True]:
                for solver in ['highs','gurobi']:
                    if B is None:status,x,wall,nodes='ABSTAIN',None,0.,0
                    else:status,x,wall,nodes=isolated_solve(solver,B,rhs,c,presolve,1e-6,seed)
                    feasible=optimal=False;error=obj=violation=None
                    if x is not None:
                        z=np.rint(x);error=float(max(abs(x-z)))
                        if np.all((z>=0)&(z<=1)):
                            feasible=bool(np.all(A.astype(np.int64)@z.astype(np.int64)<=np.floor(b)))
                            obj=int(c.astype(np.int64)@z.astype(np.int64));optimal=bool(feasible and obj==opt)
                        violation=max(float(exact_row_violation(row,br,x)) for row,br in zip(B,rhs))
                    record=dict(M=M,seed=seed,method=method,solver=solver,presolve=presolve,status=status,
                                rounded_feasible=feasible,rounded_optimal=optimal,integer_error=error,
                                objective_rounded=obj,true_optimum=opt,prep_seconds=prep,solver_seconds=wall,nodes=nodes,
                                rows=None if B is None else len(B),nnz=None if B is None else int(np.count_nonzero(B)),
                                max_coefficient=None if B is None else float(np.max(abs(B))),all_rows_gap_safe=row_safe,
                                max_exported_violation=violation,x=json.dumps(None if x is None else x.tolist()))
                    runs.append(record)
                    with (args.out/'runs-progress.jsonl').open('a') as stream:stream.write(json.dumps(record)+'\n')
            print(key,method,flush=True)
    with (args.out/'runs.csv').open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(runs[0]));writer.writeheader();writer.writerows(runs)
    (args.out/'certificates.json').write_text(json.dumps(proofs,indent=2)+'\n')
    (args.out/'instances.json').write_text(json.dumps(instance_info,indent=2)+'\n')
    import pandas as pd
    d=pd.DataFrame(runs)
    print(d.groupby(['solver','method']).agg(n=('status','size'),feasible=('rounded_feasible','sum'),optimal=('rounded_optimal','sum'),
           prep=('prep_seconds','median'),runtime=('solver_seconds','median'),max_coefficient=('max_coefficient','max')).to_string())


if __name__=='__main__':main()
