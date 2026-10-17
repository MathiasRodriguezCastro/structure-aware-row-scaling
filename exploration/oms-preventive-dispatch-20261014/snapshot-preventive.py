#!/usr/bin/env python3
"""Computable cofactor envelope, with exact small-system completeness checks."""
from fractions import Fraction as Q
from itertools import combinations,product
import csv
import hashlib
import json
import math
from pathlib import Path

import sympy as sy

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]


def ceil_log2(q):
    q=Q(q);assert q>0
    k=q.numerator.bit_length()-q.denominator.bit_length()
    if q>power2(k):k+=1
    assert power2(k-1)<q<=power2(k)
    return k


def power2(k):return Q(2**k) if k>=0 else Q(1,2**(-k))


def envelope(A,b,B,c,w):
    """Original rational system; integerize each COMPLETE row, including b and B."""
    n=len(c);m=len(b);assert n and m and len(A)==len(B)==len(w)==m
    scales=[];integerA=[]
    for a,rhs,bb in zip(A,b,B):
        values=list(map(Q,a))+[Q(rhs)]+list(map(Q,bb))
        d=math.lcm(*(v.denominator for v in values));scales.append(d)
        integerA.append([int(Q(v)*d) for v in a])
    M=max([1]+[abs(v) for a in integerA for v in a]);r=min(n,m)
    # sqrt(k) <= 2**ceil(log2(r))/1 for every k <= r; a deliberately
    # coarse, rigorous integer exponent avoids floating log/overflow claims.
    G=ceil_log2(M);L=(max(1,r)-1).bit_length()
    ray_exp=r*(G+L)
    vertex_exp=max(0,r-1)*(G+L)
    W=max(Q(s)*Q(v) for s,v in zip(scales,w));C=max(map(lambda v:abs(Q(v)),c))
    assert W>0
    rayK=(r+1)*power2(ray_exp)*W
    costK=r*r*C*power2(vertex_exp)*W
    # epsilon=1 currency unit and rho=1/2; t is dyadic and uniformly safe.
    required=[ceil_log2(2*rayK)]
    if costK:required.append(ceil_log2(costK))
    N=max(0,*required)
    return {'rows':m,'continuous_variables':n,'rank_upper':r,'integer_A_max_bits':M.bit_length(),
            'row_scale_max_log2':max(ceil_log2(s) for s in scales),
            'ray_cofactor_exponent':ray_exp,'vertex_cofactor_exponent':vertex_exp,
            'maximum_scaled_budget_log2_ceiling':ceil_log2(W),
            'uniform_scale':'2^(-%d)'%N,'scale_exponent':N,
            'negative_decimal_exponent_approx':N*math.log10(2),
            'epsilon':'1','rho':'1/2','cost_zero':not bool(C),
            'proof':'all vertices/rays bounded by integer minors and Hadamard; no numerical rank used'},scales,integerA,costK,rayK


def complete_families(A,c):
    """Exact exhaustive support enumeration, intended ONLY for tiny validation."""
    A=sy.Matrix(A);c=sy.Matrix(c);m,n=A.shape;vertices=set();rays=set()
    if not any(c):vertices.add((Q(0),)*m)
    for k in range(1,min(m,n)+1):
        for S in combinations(range(m),k):
            T=A[list(S),:].T
            if T.rank()!=k:continue
            try:v=T.gauss_jordan_solve(c)[0]
            except ValueError:continue
            if all(x<=0 for x in v):
                full=[Q(0)]*m
                for i,x in zip(S,v):full[i]=Q(x)
                vertices.add(tuple(full))
    for k in range(1,min(m,n+1)+1):
        for S in combinations(range(m),k):
            null=A[list(S),:].T.nullspace()
            if len(null)!=1 or any(v==0 for v in null[0]):continue
            v=null[0]
            if all(x>0 for x in v):v=-v
            if not all(x<0 for x in v):continue
            den=math.lcm(*(Q(x).denominator for x in v));ints=[int(x*den) for x in v]
            g=math.gcd(*ints);full=[Q(0)]*m
            for i,x in zip(S,ints):full[i]=Q(x//g)
            rays.add(tuple(full))
    return sorted(vertices),sorted(rays)


def validate_small():
    cases=[('one-period storage',[[Q(-1)],[Q(1)]],[0,Q(1,2)],[[1],[0]],[1],[1,1]),
           ('two-period storage',[[-1,0],[1,0],[0,-1],[0,1],[1,-1]],[0,2,0,2,0],[[1,0],[0,0],[0,1],[0,0],[0,0]],[1,2],[1]*5),
           ('rational coupling',[[Q(-1,2),0],[1,0],[0,Q(-1,3)],[0,1],[1,-1]],[0,Q(3,2),0,2,Q(1,4)],[[1,0],[0,0],[0,1],[0,0],[0,0]],[Q(2,3),Q(5,7)],[Q(1,10)]*5)]
    records=[]
    for name,A,b,B,c,w in cases:
        e,scales,IA,cK,rK=envelope(A,b,B,c,w);V,R=complete_families(IA,c)
        assert V
        W=[Q(s)*Q(v) for s,v in zip(scales,w)]
        assert all(sum(abs(v)*ww for v,ww in zip(pi,W))<=cK for pi in V)
        assert all(sum(abs(v)*ww for v,ww in zip(r,W))<=rK for r in R)
        t=power2(-e['scale_exponent']);false_patterns=0;feasible=0;direct=[]
        for z in product((0,1),repeat=len(B[0])):
            d=[Q(s)*(Q(bi)-sum(Q(bij)*zz for bij,zz in zip(bb,z))) for s,bi,bb in zip(scales,b,B)]
            original=all(sum(ri*di for ri,di in zip(r,d))<=0 for r in R)
            relaxed=all(sum(ri*(di+t*wi) for ri,di,wi in zip(r,d,W))<=0 for r in R)
            assert original==relaxed
            if original:
                feasible+=1
                v0=max(sum(p*di for p,di in zip(pi,d)) for pi in V)
                vt=max(sum(p*(di+t*wi) for p,di,wi in zip(pi,d,W)) for pi in V)
                assert 0<=v0-vt<=1
                direct.append(str(v0-vt))
            else:false_patterns+=1
        records.append({'case':name,'complete_vertices':len(V),'complete_primitive_rays':len(R),
                        'binary_patterns_checked':2**len(B[0]),'feasible_patterns':feasible,
                        'infeasible_patterns_excluded':false_patterns,'cost_losses':direct,**e})
    # Boundary counterexample: no positive uniform infeasibility margin when a
    # continuous master parameter z can approach the feasible boundary.
    assert Q(3,4)-Q(1)<=Q(-1,4) and Q(3,4)<=Q(1,2)+Q(1,4)
    for t in [Q(1,10),Q(1,1000),Q(1,10**9)]:
        z=Q(1,2)+t;y=Q(1,2)
        assert y>=z-t and y<=Q(1,2)+t and z>Q(1,2)
    return records


def canonical_system(model):
    continuous=[i for i,v in enumerate(model['variables']) if not v['integer']]
    integers=[i for i,v in enumerate(model['variables']) if v['integer']]
    index={j:i for i,j in enumerate(continuous)};zi={j:i for i,j in enumerate(integers)}
    A=[];b=[];B=[];w=[]
    for row in model['rows']:
        for sign in ([1,-1] if row['sense']=='=' else [1] if row['sense']=='<' else [-1]):
            a=[Q(0)]*len(continuous);bb=[Q(0)]*len(integers)
            for j,v in row['terms'].items():
                j=int(j);v=sign*Q(float(v))
                if j in index:a[index[j]]=v
                else:bb[zi[j]]=v
            A.append(a);B.append(bb);b.append(sign*Q(float(row['rhs'])))
            w.append(Q(float(row.get('budget',1e-4*max(1,abs(row['rhs']))))))
    for j in continuous:
        v=model['variables'][j]
        for side,sign in (('lower',-1),('upper',1)):
            if v[side] is not None:
                a=[Q(0)]*len(continuous);a[index[j]]=Q(sign)
                A.append(a);B.append([Q(0)]*len(integers));b.append(sign*Q(float(v[side])))
                w.append(Q(float(v.get('bound_budget',1e-4))))
    return A,b,B,[Q(float(model['variables'][i]['cost'])) for i in continuous],w


def sparse_model_envelope(model):
    continuous={i for i,v in enumerate(model['variables']) if not v['integer']}
    n=len(continuous);M=1;m=0;W=Q(0);scale_max=1
    for row in model['rows']:
        terms={int(i):Q(float(v)) for i,v in row['terms'].items()}
        rhs=Q(float(row['rhs']));s=math.lcm(rhs.denominator,*(v.denominator for v in terms.values()))
        scale_max=max(scale_max,s);M=max(M,max([abs(int(v*s)) for i,v in terms.items() if i in continuous]+[0]))
        W=max(W,s*Q(float(row.get('budget',1e-4*max(1,abs(row['rhs']))))))
        m+=2 if row['sense']=='=' else 1
    for i in continuous:
        v=model['variables'][i]
        for side in ('lower','upper'):
            if v[side] is None:continue
            s=Q(float(v[side])).denominator;M=max(M,s);scale_max=max(scale_max,s)
            W=max(W,s*Q(float(v.get('bound_budget',1e-4))));m+=1
    r=min(n,m);G=ceil_log2(M);L=(max(1,r)-1).bit_length()
    C=max(abs(Q(float(model['variables'][i]['cost']))) for i in continuous)
    ray_exp=r*(G+L);vertex_exp=max(0,r-1)*(G+L)
    costK=r*r*C*power2(vertex_exp)*W;rayK=(r+1)*power2(ray_exp)*W
    N=max(0,ceil_log2(2*rayK),ceil_log2(costK) if costK else 0)
    return {'rows':m,'continuous_variables':n,'rank_upper':r,'integer_A_max_bits':M.bit_length(),
            'row_scale_max_log2':ceil_log2(scale_max),'ray_cofactor_exponent':ray_exp,
            'vertex_cofactor_exponent':vertex_exp,'maximum_scaled_budget_log2_ceiling':ceil_log2(W),
            'uniform_scale':'2^(-%d)'%N,'scale_exponent':N,
            'negative_decimal_exponent_approx':N*math.log10(2),'epsilon':'1','rho':'1/2',
            'cost_zero':not bool(C),'proof':'all vertices/rays bounded by integer minors and Hadamard; no numerical rank used'}


def main():
    small=validate_small();(HERE/'complete-small-checks.json').write_text(json.dumps(small,indent=2)+'\n')
    records=[]
    sources=sorted((ROOT/'exploration/oms-objective-budget-20261014/inputs/models').glob('*/original-model.json'))
    sources+=sorted((HERE/'inputs').glob('*/model.json'))
    for path in sources:
        model=json.loads(path.read_text());e=sparse_model_envelope(model)
        records.append({'model':model['name'],'input':str(path.relative_to(ROOT)),
                        'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),**e})
        print(model['name'],e['uniform_scale'],'~10^(-%.0f)'%e['negative_decimal_exponent_approx'],flush=True)
    (HERE/'preventive-results.json').write_text(json.dumps(records,indent=2)+'\n')
    with (HERE/'preventive-results.csv').open('w',newline='') as f:
        keys=list(records[0]);writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(records)
    print('Complete tiny families passed; real bounds are sufficient only, not necessary.',flush=True)


if __name__=='__main__':main()
