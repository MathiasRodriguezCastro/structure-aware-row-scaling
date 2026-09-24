#!/usr/bin/env python3
"""Exact two-row geometry and a separately labeled exploratory block MIP pilot."""
import argparse,csv,json,math,hashlib,time
from fractions import Fraction as F
from pathlib import Path
import numpy as np
from joint_rounding_certificate import certify_binary_block,multipliers,row_gap
from residual_budget_experiment import solve_highs,solve_gurobi


def block(M):
    # Exact integer feasible choices: (0,0,0), (0,0,1), (1,1,1).
    return np.array([[M,1-M,-1],[1-M,M,-1]],float),np.array([.5,.5])


def model(M,seed,blocks):
    rng=np.random.default_rng(20260913+seed)
    A=np.zeros((2*blocks+1,3*blocks));b=np.full(2*blocks+1,.5)
    weight=rng.integers(1,15,blocks);cost=rng.integers(1,10,blocks)
    profit=rng.integers(10,40,(blocks,2));c=np.empty(3*blocks)
    for i in range(blocks):
        A[2*i:2*i+2,3*i:3*i+3]=block(M)[0]
        c[3*i:3*i+3]=[profit[i,0],profit[i,1],-cost[i]]
    A[-1,2::3]=weight;b[-1]=math.floor(.45*weight.sum())
    # Independent dynamic program on the exact block-domain reduction.
    dp=np.zeros(int(b[-1])+1,dtype=int)
    for w,p in zip(weight,profit.sum(axis=1)-cost):
        for k in range(len(dp)-1,int(w)-1,-1):dp[k]=max(dp[k],dp[k-int(w)]+int(p))
    return A,b,c,int(dp[-1]),weight


def scales(A,b,method,eta,eps):
    if method=='Base':return np.ones(len(b)),A,b
    if method=='GCD-floor':return np.ones(len(b)),A,np.floor(b)
    if method=='Aggregate-GM':
        # Classical nonnegative row aggregation control, no novelty claim.
        newA=np.vstack([A,*[A[i]+A[i+1] for i in range(0,len(b)-1,2)]])
        newb=np.concatenate([b,np.array([b[i]+b[i+1] for i in range(0,len(b)-1,2)])])
        A,b=newA,newb
    ds=np.array([1/math.sqrt(abs(row[row!=0]).min()*abs(row).max()) for row in A])
    if method in {'Joint-dyadic','Row-dyadic'}:
        for i in range(0,len(b)-1,2):
            local=A[i:i+2,3*(i//2):3*(i//2)+3]
            nz=abs(local[local!=0]);m,M=float(nz.min()),float(nz.max())
            # Exact-export grid within coefficient limits. Pick smallest exponent
            # >=GM that certifies the block. Enumeration is tiny and deterministic.
            first=math.ceil(-.5*(math.log2(m)+math.log2(M)))
            last=math.floor(math.log2(1e9/M));d=None
            for k in range(first,last+1):
                alpha=2.**k
                if certify_binary_block(local,b[i:i+2],[F(eps)/F(alpha)]*2,eta,
                                        pairs=method=='Joint-dyadic',bound_tolerance=eta)['certified']:
                    d=alpha;break
            if d is None:return None,A,b
            ds[i:i+2]=d
    return ds,A,b


def check(A,b,c,opt,x):
    if x is None:return False,'no_point'
    z=np.rint(x).astype(int)
    feasible=all(sum(F(float(a))*int(v) for a,v in zip(row,z))<=F(float(rhs)) for row,rhs in zip(A,b))
    if not feasible:return False,'rounded_infeasible'
    if np.any(z<0) or np.any(z>1) or max(abs(x-z))>1e-9:return False,'domain'
    return int(c@z)==opt, 'verified' if int(c@z)==opt else 'suboptimal'


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--solve',action='store_true');ap.add_argument('--seeds',type=int,default=3)
    ap.add_argument('--blocks',type=int,default=12);args=ap.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    eta=F(1,10**6);eps=F(1,10**6)
    geometry=[]
    for exponent in [3,6,9,12]:
        M=2**exponent if exponent==3 else 10**exponent
        A,b=block(M)
        for alpha in [1.,1/math.sqrt(M),2.**-17,2.**-18,2.**-19]:
            t=[eps/F(alpha)]*2
            for pair in [False,True]:
                proof=certify_binary_block(A,b,t,eta,pairs=pair,bound_tolerance=eta)
                geometry.append(dict(M=M,alpha=alpha,pairs=pair,**proof))
    (args.out/'geometry.json').write_text(json.dumps(geometry,indent=2)+'\n')
    if not args.solve:return
    import gurobipy as gp
    env=gp.Env(empty=True);env.setParam('OutputFlag',0);env.start()
    methods=['Base','GM','GCD-floor','Row-dyadic','Joint-dyadic','Aggregate-GM']
    rows=[]
    for M in [10**3,10**6,10**9,10**12]:
        for seed in range(args.seeds):
            A,b,c,opt,weights=model(M,seed,args.blocks)
            np.savez_compressed(args.out/f'model_M{M}_s{seed}.npz',A=A,b=b,c=c,optimum=opt)
            for method in methods:
                tic=time.perf_counter();d,B,rhs=scales(A,b,method,float(eta),float(eps));prep=time.perf_counter()-tic
                for presolve in [False,True]:
                    for solver in ['highs','gurobi']:
                        if d is None:status,x,wall,nodes='ABSTAIN',None,0.,0
                        elif solver=='highs':status,x,wall,nodes=solve_highs(d[:,None]*B,d*rhs,c,presolve,1e-6,seed)
                        else:status,x,wall,nodes=solve_gurobi(d[:,None]*B,d*rhs,c,presolve,1e-6,seed,env)
                        accepted,reason=check(A,b,c,opt,x)
                        rows.append(dict(M=M,seed=seed,blocks=args.blocks,method=method,presolve=presolve,
                                         solver=solver,status=status,verified=accepted,reason=reason,prep_seconds=prep,
                                         solver_seconds=wall,nodes=nodes,optimum=opt,x=json.dumps(None if x is None else x.tolist()),
                                         factors=json.dumps(None if d is None else d.tolist())))
            print(M,seed,flush=True)
    env.dispose()
    with (args.out/'runs.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    protocol=dict(purpose='exploratory two-row cancellation pilot; classical aggregation and GCD controls',
                  seeds=list(range(args.seeds)),blocks=args.blocks,methods=methods,
                  eta=str(eta),epsilon=str(eps),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  certificate_sha256=hashlib.sha256((Path(__file__).parent/'joint_rounding_certificate.py').read_bytes()).hexdigest())
    (args.out/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    for solver in ['highs','gurobi']:
        for method in methods:
            r=[x for x in rows if x['solver']==solver and x['method']==method]
            print(solver,method,sum(x['verified'] for x in r),len(r),sum(x['status']=='ABSTAIN' for x in r))


if __name__=='__main__':main()
