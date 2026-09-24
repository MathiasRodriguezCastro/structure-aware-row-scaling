#!/usr/bin/env python3
"""Exploratory random block benchmark with exact local-state/DP optima."""
import argparse,csv,hashlib,json,math,time
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import numpy as np
from certified_guards import compile_block,aggregate,partial_nogoods
from isolated_solvers import isolated_solve
from budget_scaling import exact_row_violation,dyadic_factor
from joint_rounding_certificate import multipliers


def generate(M,seed,blocks,nlocal):
    rng=np.random.default_rng(20260913+seed)
    A=np.zeros((2*blocks+1,blocks*nlocal));b=np.zeros(2*blocks+1)
    c=rng.integers(1,40,blocks*nlocal).astype(float)
    resource=rng.integers(1,10,blocks*nlocal);cap=int(.4*resource.sum());b[-1]=cap;A[-1]=resource
    states=np.array(list(product([0,1],repeat=nlocal)),int);local_states=[]
    for k in range(blocks):
        # Balanced direction guarantees a nontrivial zero-sum subset; randomness
        # in the smaller rows prevents this from being a duplicate-row example.
        v=np.r_[rng.integers(1,5,nlocal//2),-rng.integers(1,5,nlocal-nlocal//2)]
        v[1]=-v[0]
        small=rng.integers(1,8,(2,nlocal));rhs=np.floor(.55*small.sum(axis=1))+.5
        rows=np.array([M*v+small[0],-M*v+small[1]],float)
        A[2*k:2*k+2,k*nlocal:(k+1)*nlocal]=rows;b[2*k:2*k+2]=rhs
        feasible=np.all(states@rows.astype(np.int64).T<=np.floor(rhs),axis=1)
        local_states.append(states[feasible])
    dp=np.full(cap+1,-10**9,dtype=int);dp[0]=0
    for k,st in enumerate(local_states):
        sl=slice(k*nlocal,(k+1)*nlocal);new=np.full_like(dp,-10**9)
        for z in st:
            w=int(z@resource[sl]);p=int(z@c[sl])
            if w<=cap:new[w:]=np.maximum(new[w:],dp[:cap+1-w]+p)
        dp=new
    return A,b,c,int(dp.max()),[len(x) for x in local_states]


def transform(A,b,method,blocks,nlocal):
    if method=='Base':return A,b,[]
    if method=='GCD-floor':
        from functools import reduce
        gs=[reduce(math.gcd,map(abs,map(int,row))) for row in A]
        return A/np.array(gs)[:,None],np.array([float(F(float(rhs))//g) for rhs,g in zip(b,gs)]),[]
    B=A.copy();rhs=b.copy();extraA=[];extraB=[];proofs=[]
    for k in range(blocks):
        sl=slice(k*nlocal,(k+1)*nlocal);row=slice(2*k,2*k+2)
        if method in {'Selected-guards','Unsafe-clauses'}:
            proof=compile_block(A[row,sl],b[row])
        else:
            factors=[dyadic_factor(a,r).factor for a,r in zip(A[row,sl],b[row])]
            proof=dict(factors=factors,original_uncovered=[])
        factors=np.array(proof['factors']);B[row]*=factors[:,None];rhs[row]*=factors
        chosen=[]
        if method=='Selected-guards':
            if not proof['certified']:return None,None,[proof]
            chosen=[proof['candidates'][j] for j in proof['selected']]
        elif method=='All-elimination':
            chosen=[aggregate(A[row,sl],b[row],lam) for lam in multipliers(A[row,sl]) if all(v>0 for v in lam)]
            unique={(*g['a'],g['b']):g for g in chosen if g is not None};chosen=list(unique.values())
        elif method in {'Unsafe-clauses','All-clauses'}:
            chosen=partial_nogoods(A[row,sl],b[row],proof['original_uncovered'],all_bad=method=='All-clauses')
            proof['integer_clauses']=chosen
        elif method=='Pair-sum':chosen=[aggregate(A[row,sl],b[row],[F(1,2),F(1,2)])]
        for g in chosen:
            ar=np.zeros(A.shape[1]);ar[sl]=g['a'];extraA.append(ar);extraB.append(g['b'])
        proofs.append(proof)
    # The unscaled integer resource row is rounding safe: smallest bad activity
    # gap is one, and the declared noise/tolerance sum is strictly below it.
    assert F(1e-6)*(1+sum(map(F,map(float,A[-1]))))<1
    if extraA:B=np.vstack([B,extraA]);rhs=np.r_[rhs,np.array(extraB)]
    return B,rhs,proofs


def acceptance(A,b,c,opt,x):
    if x is None:return False,False,None,None
    z=np.rint(x);near=float(max(abs(x-z)))
    domain=np.all((z>=0)&(z<=1))
    feasible=domain and all(exact_row_violation(a,r,z)==0 for a,r in zip(A,b))
    usable=bool(feasible and int(c@z)==opt)
    return usable,bool(usable and near<=1e-6),near,float(c@z)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--seeds',type=int,default=2);ap.add_argument('--start-seed',type=int,default=50)
    ap.add_argument('--blocks',type=int,default=6);ap.add_argument('--local-size',type=int,default=6)
    args=ap.parse_args()
    if args.out.exists():raise ValueError('Choose a new output directory; frozen runs are never overwritten')
    args.out.mkdir(parents=True,exist_ok=True)
    import shutil
    source_hashes={}
    for name in ['explore_guard_selection.py','certified_guards.py','joint_rounding_certificate.py','budget_scaling.py','residual_budget_experiment.py','isolated_solvers.py']:
        path=Path(__file__).parent/name
        source_hashes[name]=hashlib.sha256(path.read_bytes()).hexdigest()
        shutil.copy2(path,args.out/('source-'+name))
    (args.out/'design.json').write_text(json.dumps(dict(blocks=args.blocks,local_size=args.local_size,
        seeds=list(range(args.start_seed,args.start_seed+args.seeds)),multipliers=[10**6,10**9,10**12],
        primary='exact feasibility of the rounded assignment',secondary='exact rounded optimum and solver cost',
        hypothesis='exported row residual <=1e-6 and integrality error<=1e-6, bound tolerance1e-6',
        source_sha256=source_hashes,external_wall_limit=25),indent=2)+'\n')
    methods=['Base','GCD-floor','Dyadic-GM','Pair-sum','All-elimination','Selected-guards','Unsafe-clauses','All-clauses'];runs=[];proofs={}
    for M in [10**6,10**9,10**12]:
        for seed in range(args.start_seed,args.start_seed+args.seeds):
            A,b,c,opt,states=generate(M,seed,args.blocks,args.local_size)
            key=f'M{M}_s{seed}';np.savez_compressed(args.out/(key+'.npz'),A=A,b=b,c=c,optimum=opt)
            for method in methods:
                tic=time.perf_counter();B,rhs,proof=transform(A,b,method,args.blocks,args.local_size);prep=time.perf_counter()-tic
                if method in {'Selected-guards','Unsafe-clauses','All-clauses'}:proofs[key+'_'+method]=proof
                for presolve in [False,True]:
                    for solver in ['highs','gurobi']:
                        if B is None:status,x,wall,nodes='ABSTAIN',None,0.,0
                        else:status,x,wall,nodes=isolated_solve(solver,B,rhs,c,presolve,1e-6,seed)
                        ok,nearok,error,obj=acceptance(A,b,c,opt,x)
                        exported_violation=None if x is None or B is None else max(float(exact_row_violation(a,r,x)) for a,r in zip(B,rhs))
                        runs.append(dict(M=M,seed=seed,method=method,presolve=presolve,solver=solver,status=status,
                                         rounded_optimal=ok,rounded_optimal_within_eta=nearok,integer_error=error,
                                         objective_rounded=obj,true_optimum=opt,prep_seconds=prep,solver_seconds=wall,
                                         exported_rows=None if B is None else len(B),nnz=None if B is None else np.count_nonzero(B),
                                         max_exported_violation=exported_violation,x=json.dumps(None if x is None else x.tolist())))
                        # Flush every completed assignment; an interrupted campaign
                        # retains all completed observations and its full design.
                        with (args.out/'runs-progress.jsonl').open('a') as progress:
                            progress.write(json.dumps(runs[-1])+'\n')
                print(key,method,flush=True)
    with (args.out/'runs.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(runs[0]));w.writeheader();w.writerows(runs)
    (args.out/'certificates.json').write_text(json.dumps(proofs,indent=2)+'\n')
    protocol=dict(purpose='exploratory; classical aggregation/elimination controls mandatory',
                  blocks=args.blocks,local_size=args.local_size,seeds=list(range(args.start_seed,args.start_seed+args.seeds)),
                  methods=methods,epsilon=1e-6,eta=1e-6,primary='exact feasibility of the rounded assignment',
                  secondary='primary plus returned integrality error<=eta',source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (args.out/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    import pandas as pd
    d=pd.DataFrame(runs);print(d.groupby(['solver','method']).agg(n=('status','size'),verified=('rounded_optimal','sum'),
                      verified_eta=('rounded_optimal_within_eta','sum'),prep=('prep_seconds','median'),runtime=('solver_seconds','median'),rows=('exported_rows','median')).to_string())


if __name__=='__main__':main()
