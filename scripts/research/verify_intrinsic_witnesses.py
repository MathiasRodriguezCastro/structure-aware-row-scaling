#!/usr/bin/env python3
"""Construct and check rational obstruction points independently of the compiler.

No optimizer or certificate compiler is imported. A two-row box vertex has at
most two coordinates off a box endpoint; exhaustive exact vertex enumeration
is a fallback after a cheap one-coordinate search. Local points are embedded
into the full saved global model and checked against every original row.
"""
import argparse
from fractions import Fraction as F
import hashlib
from itertools import combinations, product
import json
from pathlib import Path
import numpy as np


def find_point(A, b, z, eta):
    n = len(z)
    bounds = [(max(F(0), F(v)-eta), min(F(1), F(v)+eta)) for v in z]
    def valid(x):
        return (all(lo<=v<=hi for v, (lo,hi) in zip(x,bounds)) and
                all(sum(a*v for a,v in zip(row,x))<=rhs for row,rhs in zip(A,b)))
    for j in range(n):
        lo, hi = bounds[j]
        for row, rhs in zip(A,b):
            remainder = rhs-sum(row[k]*z[k] for k in range(n) if k!=j)
            if row[j]>0:hi=min(hi,remainder/row[j])
            elif row[j]<0:lo=max(lo,remainder/row[j])
            elif remainder<0:hi=lo-1
        if lo<=hi:
            x = list(map(F,z));x[j]=lo
            assert valid(x)
            return x
    for size in [0,1,2]:
        for free in combinations(range(n),size):
            fixed = [j for j in range(n) if j not in free]
            for active in combinations(range(2),size):
                for sides in product([0,1],repeat=len(fixed)):
                    x = [F(0)]*n
                    for j,side in zip(fixed,sides):x[j]=bounds[j][side]
                    rhs = [b[r]-sum(A[r][j]*x[j] for j in fixed) for r in active]
                    if size==1:
                        coefficient = A[active[0]][free[0]]
                        if not coefficient:continue
                        x[free[0]]=rhs[0]/coefficient
                    elif size==2:
                        p,q = active;j,k = free
                        det = A[p][j]*A[q][k]-A[p][k]*A[q][j]
                        if not det:continue
                        x[j]=(rhs[0]*A[q][k]-A[p][k]*rhs[1])/det
                        x[k]=(A[p][j]*rhs[1]-rhs[0]*A[q][j])/det
                    if valid(x):return x
    return None


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    proofs=json.loads((args.root/'certificates.json').read_text());eta=F(1e-6)
    witnesses=[];counts={}
    for key, blocks in proofs.items():
        if not key.endswith('_Unsafe-clauses'):continue
        model=key.removesuffix('_Unsafe-clauses');raw=np.load(args.root/(model+'.npz'))
        A=[[F(float(a)) for a in row] for row in raw['A']];b=[F(float(v)) for v in raw['b']]
        counts[model]=0
        for k,block in enumerate(blocks):
            sl=slice(6*k,6*k+6);local=[row[sl] for row in A[2*k:2*k+2]];rhs=b[2*k:2*k+2]
            for z in block['intrinsic_uncovered']:
                x=find_point(local,rhs,z,eta)
                assert x is not None,(model,k,z)
                global_x=[F(0)]*len(A[0]);global_x[sl]=x
                global_z=[0]*len(A[0]);global_z[sl]=z
                activities=[sum(a*v for a,v in zip(row,global_x)) for row in A]
                assert all(v<=r for v,r in zip(activities,b))
                assert any(sum(a*v for a,v in zip(row,global_z))>r for row,r in zip(A,b))
                assert all(0<=v<=1 and abs(v-w)<=eta for v,w in zip(global_x,global_z))
                witnesses.append(dict(model=model,block=k,z=z,x=list(map(str,x)),
                                      distance=str(max(abs(v-w) for v,w in zip(x,z))),
                                      coupling_slack=str(b[-1]-activities[-1])))
                counts[model]+=1
    assert all(counts.values())
    result=dict(models_with_global_obstruction=len(counts),global_witnesses=len(witnesses),
                counts=counts,witnesses=witnesses,eta=str(eta),
                conclusion='No positive row scaling or LP-valid added inequalities can make all near-binary feasible points safe in these original relaxations.',
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                certificates_sha256=hashlib.sha256((args.root/'certificates.json').read_bytes()).hexdigest())
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='witnesses'},indent=2))


if __name__=='__main__':main()
