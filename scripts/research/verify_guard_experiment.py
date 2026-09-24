#!/usr/bin/env python3
"""Independent exact saved-data/certificate checker; no compiler or solver import."""
import argparse,csv,json,hashlib
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import numpy as np


def minimum_margin(A,b,z,lam,eta,t):
    p=[sum((lam[r]*F(float(A[r,j])) for r in range(len(b))),F(0)) for j in range(len(z))]
    # Bound tolerance=eta gives the full symmetric error box for binary centers.
    return (sum((v*int(x) for v,x in zip(p,z)),F(0))-
            sum((l*(F(float(rhs))+tr) for l,rhs,tr in zip(lam,b,t)),F(0))-
            eta*sum(map(abs,p)))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);args=ap.parse_args()
    design=json.loads((args.root/'design.json').read_text());proofs=json.loads((args.root/'certificates.json').read_text())
    q=design['local_size'];blocks=design['blocks'];eps=F(1e-6);eta=eps
    centers=np.array(list(product([0,1],repeat=q)),np.int64)
    models={};model_details=[];certified_blocks=0;valid_clauses=0;coverage={'single_row':0,'joint':0,'integer_clause':0}
    for path in sorted(args.root.glob('M*_s*.npz')):
        data=np.load(path);A,b,c=data['A'],data['b'],data['c'];ai=A.astype(np.int64);ci=c.astype(np.int64)
        assert np.array_equal(A,ai) and np.array_equal(c,ci)
        assert float(np.max(abs(A)))*A.shape[1]<2**62
        cap=int(b[-1]);dp=np.full(cap+1,-10**9,dtype=np.int64);dp[0]=0
        for k in range(blocks):
            local=ai[2*k:2*k+2,k*q:(k+1)*q];rhs=b[2*k:2*k+2]
            good=np.all(centers@local.T<=np.floor(rhs).astype(np.int64),axis=1)
            new=np.full_like(dp,-10**9)
            for z in centers[good]:
                weight=int(ai[-1,k*q:(k+1)*q]@z);value=int(ci[k*q:(k+1)*q]@z)
                if weight<=cap:new[weight:]=np.maximum(new[weight:],dp[:cap+1-weight]+value)
            dp=new
            proof=proofs[path.stem+'_Unsafe-clauses'][k]
            for ar,br,alpha in zip(local,rhs,proof['factors']):
                for value in [*ar,br]:
                    assert F(float(alpha*value))==F(float(alpha))*F(float(value))
            clauses=proof.get('integer_clauses',[])
            for clause in clauses:
                ca=np.array(clause['a'],int);cb=int(clause['b'])
                assert np.array_equal(ca,clause['a']) and cb==clause['b']
                assert np.all(centers[good]@ca<=cb)
                valid_clauses+=1
            tr=[eps/F(float(a)) for a in proof['factors']]
            for z in centers[~good]:
                units=[[F(1),F(0)],[F(0),F(1)]]
                if any(minimum_margin(local,rhs,z,lam,eta,tr)>0 for lam in units):coverage['single_row']+=1;continue
                matching=[p for p in proof.get('joint_proofs',[]) if tuple(p['z'])==tuple(z)]
                if any(minimum_margin(local,rhs,z,list(map(F,p['lambda_'])),eta,tr)>0 for p in matching):coverage['joint']+=1;continue
                matched=False
                for clause in clauses:
                    margin=sum(F(float(a))*int(v) for a,v in zip(clause['a'],z))-F(float(clause['b']))-eta*sum(abs(F(float(a))) for a in clause['a'])-eps
                    if margin>0:matched=True;break
                assert matched,(path.stem,k,z.tolist())
                coverage['integer_clause']+=1
            certified_blocks+=1
        optimum=int(dp.max());assert optimum==int(data['optimum'])
        assert eps+eta*int(abs(ai[-1]).sum())<1
        models[path.stem]=(ai,b,ci,optimum)
        model_details.append(dict(model=path.stem,optimum=optimum))
    counts={};rows=[]
    for row in csv.DictReader((args.root/'runs.csv').open()):
        key=f"M{row['M']}_s{row['seed']}";A,b,c,opt=models[key];value=json.loads(row['x'])
        feasible=False;optimal=False
        if value is not None:
            x=np.array(value);z=np.rint(x).astype(np.int64)
            feasible=bool(np.all((z>=0)&(z<=1)) and np.all(A@z<=np.floor(b).astype(np.int64)))
            optimal=bool(feasible and int(c@z)==opt)
        assert optimal==(row['rounded_optimal']=='True')
        k=(row['solver'],row['method']);g=counts.setdefault(k,dict(n=0,feasible=0,optimal=0,abstain=0))
        g['n']+=1;g['feasible']+=feasible;g['optimal']+=optimal;g['abstain']+=row['status']=='ABSTAIN'
        rows.append(dict(**row,independent_rounded_feasible=feasible,independent_rounded_optimal=optimal))
    summary=[dict(solver=k[0],method=k[1],**v) for k,v in counts.items()]
    result=dict(models=len(models),configurations=len(rows),certified_blocks=certified_blocks,
                clauses_checked=valid_clauses,cell_coverage=coverage,summary=summary,
                runs_sha256=hashlib.sha256((args.root/'runs.csv').read_bytes()).hexdigest(),
                verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (args.root/'independent-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    with (args.root/'verified-runs.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
