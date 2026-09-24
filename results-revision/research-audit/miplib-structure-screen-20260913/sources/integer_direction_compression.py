"""Certified coefficient reduction along discovered bounded integer directions.

For research, not a claim of a new general coefficient-reduction algorithm.
Discovery uses projective rational approximation or bounded integer rounding;
validity uses exact arithmetic and integer levels of an aggregate. No truth
table, generator magnitude, row pairing, or optimizer is used by the reducer.
"""
from fractions import Fraction as F
from functools import reduce
from math import gcd, lcm

from joint_rounding_certificate import rational


def canonical_integer_row(a, b):
    a=list(map(rational,a));b=rational(b)
    denominator=lcm(*(v.denominator for v in a))
    integers=[int(v*denominator) for v in a]
    divisor=reduce(gcd,map(abs,integers),0) or 1
    factor=F(denominator,divisor)
    return [v//divisor for v in integers], int(b*factor//1), factor


def directions(a, caps=(1,2,3,4,8,16,32), strategy='rational'):
    if not any(a):return []
    if strategy=='rounded-all':caps=tuple(range(1,max(caps)+1));strategy='rounded'
    # Include all tied largest pivots. Exact projective ratios are invariant
    # under positive exact row multiplication, including dyadic re-emission.
    maximum=max(map(abs,a));out=set()
    for pivot in [j for j,v in enumerate(a) if abs(v)==maximum]:
        ratios=[F(v,a[pivot]) for v in a]
        for cap in caps:
            if strategy=='rounded':
                v=[int(round(cap*r)) for r in ratios]
            elif strategy=='rational':
                approx=[r.limit_denominator(cap) for r in ratios]
                denominator=lcm(*(r.denominator for r in approx))
                v=[int(r*denominator) for r in approx]
            else:raise ValueError('unknown discovery strategy')
            divisor=reduce(gcd,map(abs,v),0)
            if not divisor:continue
            v=[q//divisor for q in v]
            if max(map(abs,v))>max(caps):continue
            if sum(x*y for x,y in zip(a,v))<0:v=[-q for q in v]
            out.add(tuple(v))
    return sorted(out)


def scales(a, v, lo, hi):
    pairs=sorted((F(x,y),abs(y)*(u-l)) for x,y,l,u in zip(a,v,lo,hi) if y and u>l)
    if not pairs:return []
    total=sum(weight for _,weight in pairs);running=0;candidates=set()
    for value,weight in pairs:
        running+=weight
        if 2*running>=total:
            candidates.update([value.numerator//value.denominator,
                               -((-value.numerator)//value.denominator)])
            if 2*running>total:break
    return sorted(q for q in candidates if q>0)


def compression_step(a, b, v, alpha, lo, hi):
    """Return an exact integer-equivalent row, or None if the proof fails."""
    if alpha<=0 or any(not isinstance(vj,int) for vj in v):
        raise ValueError('positive integer scale and integer direction required')
    e=[x-alpha*y for x,y in zip(a,v)]
    lower=sum(min(x*l,x*u) for x,l,u in zip(e,lo,hi))
    upper=sum(max(x*l,x*u) for x,l,u in zip(e,lo,hi))
    k=(b-lower)//alpha;tau=b-alpha*k
    assert lower<=tau<lower+alpha
    if alpha<upper-tau:return None
    if tau>=upper:
        new_a=list(v);new_b=k;beta=None;kind='aggregate_bound'
    else:
        beta=max(upper-tau,tau-lower+1)
        assert 1<=beta<=alpha
        new_a=[beta*y+x for x,y in zip(e,v)];new_b=beta*k+tau;kind='coefficient_compression'
    proof=dict(kind=kind,a=list(map(str,a)),b=str(b),v=list(v),alpha=str(alpha),
               residual=list(map(str,e)),lower=str(lower),upper=str(upper),
               k=str(k),tau=str(tau),beta=None if beta is None else str(beta),
               output_a=list(map(str,new_a)),output_b=str(new_b))
    return new_a,new_b,proof


def compress_row(a, b, lo=None, hi=None, strategy='rational', max_passes=4, tolerance=1e-6):
    lo=[0]*len(a) if lo is None else list(lo)
    hi=[1]*len(a) if hi is None else list(hi)
    if any(int(x)!=x for x in [*lo,*hi]) or any(l>u for l,u in zip(lo,hi)):
        raise ValueError('finite integer bounds required')
    current,rhs,normalization=canonical_integer_row(a,b)
    start_a,start_b=current[:],rhs;steps=[]
    for _ in range(max_passes):
        # No extra arithmetic compression is needed for the stated primal
        # rounding contract once this ordinary integer-gap test already passes.
        if rational(tolerance)*(1+sum(map(abs,current)))<1:break
        choices=[]
        old_score=max([abs(rhs),*map(abs,current),1])
        for v in directions(current,strategy=strategy):
            for alpha in scales(current,v,lo,hi):
                result=compression_step(current,rhs,v,alpha,lo,hi)
                if result is None:continue
                ar,br,proof=result
                ar,br,factor=canonical_integer_row(ar,br)
                score=max([abs(br),*map(abs,ar),1])
                if score*2>old_score:continue
                proof['post_factor']=str(factor)
                proof['post_a']=list(map(str,ar));proof['post_b']=str(br)
                choices.append((score,sum(map(abs,ar)),tuple(ar),br,proof))
        if not choices:break
        _,_,row,rhs,proof=min(choices,key=lambda x:x[:4]);current=list(row);steps.append(proof)
    return dict(a=current,b=rhs,steps=steps,input_normalization=str(normalization),
                canonical_a=list(map(str,start_a)),canonical_b=str(start_b),
                lo=list(lo),hi=list(hi),strategy=strategy)


def compress_matrix(A,b,strategy='rational'):
    import numpy as np
    rows=[];rhs=[];proofs=[]
    for a,br in zip(A,b):
        columns=[j for j,value in enumerate(a) if value!=0]
        proof=compress_row([a[j] for j in columns],br,strategy=strategy)
        proof['columns']=columns
        exact=[*proof['a'],proof['b']]
        # Only emit exactly representable binary64 data. A successful discovery
        # never licenses rounding a replacement inequality inward or outward.
        try:representable=all(F(float(v))==v for v in exact)
        except OverflowError:representable=False
        if representable:
            row=np.zeros(len(a))
            for j,v in zip(columns,proof['a']):row[j]=v
            rows.append(row);rhs.append(proof['b'])
        else:rows.append(a);rhs.append(br)
        proof['exported']=representable;proofs.append(proof)
    return np.array(rows,dtype=float),np.array(rhs,dtype=float),proofs


def single_coefficient_control(a,b):
    """Elementary binary single-coefficient reductions, plus GCD/RHS flooring.

    This is a specified classical control, not a complete commercial presolver.
    Negative columns are complemented internally and mapped back exactly.
    """
    a,b,_=canonical_integer_row(a,b)
    signs=[1 if v>=0 else -1 for v in a]
    weights=list(map(abs,a));rhs=b+sum(-v for v in a if v<0)
    if rhs<0:return [0]*len(a),-1
    for _ in range(max(1,2*len(a))):
        old=(weights[:],rhs)
        for j,w in enumerate(weights):
            if w>rhs:
                weights[j]=rhs+1
            remaining=sum(weights)-weights[j]
            slack=rhs-remaining
            if 0<slack<weights[j]:weights[j]-=slack;rhs-=slack
        weights,rhs,_=canonical_integer_row(weights,rhs)
        if old==(weights,rhs):break
    return [s*w for s,w in zip(signs,weights)],rhs-sum(w for s,w in zip(signs,weights) if s<0)
