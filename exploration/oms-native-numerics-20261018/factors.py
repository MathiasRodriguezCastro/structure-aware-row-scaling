"""Exact dyadic L2 factors and explicit full/raw contract intervals."""
from fractions import Fraction as F
import math


def power(k):return F(2**k) if k>=0 else F(1,2**(-k))
def floorlog(q):
    assert q>0
    k=q.numerator.bit_length()-q.denominator.bit_length()
    return k-1 if power(k)>q else k
def ceillog(q):
    k=floorlog(q)
    return k+(power(k)<q)


def row_spec(row,variables):
    a=list(row['terms'].values())
    if not a:return None
    nz=list(map(F,a));m=min(map(abs,nz));M=max(map(abs,nz))
    low=max(-1074,ceillog(F(1e-9)/m));high=min(1023,floorlog(F(1e9)/M))
    for value in [*a,row['rhs']]:
        if not value:continue
        num,den=abs(float(value)).as_integer_ratio();trailing=(num&-num).bit_length()-1
        p=trailing-(den.bit_length()-1);top=math.frexp(abs(value))[1]-1
        low=max(low,-1074-p);high=min(high,1023-top)
    norm2=sum((v*v for v in nz),F(0))
    bracket=(-floorlog(norm2)-1)//2
    E=F(1e-9)*sum((abs(F(value)) for j,value in row['terms'].items() if variables[int(j)]['integer']),F(0))
    return dict(low=low,high=high,norm2=norm2,bracket=bracket,E=E,m=m,M=M)


def select(spec,delta=None,rounded=True):
    if spec is None:return dict(factor=1.,reason='constant_row',low=0,high=0)
    lo,hi=spec['low'],spec['high']
    if delta is not None:
        remaining=F(delta)-(spec['E'] if rounded else F(0))
        if remaining<=0:return dict(factor=None,reason='rounding_budget_exhausted',low=None,high=hi)
        lo=max(lo,ceillog(F(1e-6)/remaining))
    if lo>hi:return dict(factor=None,reason='empty_exact_dyadic_interval',low=lo,high=hi)
    candidates={min(hi,max(lo,spec['bracket'])),min(hi,max(lo,spec['bracket']+1))}
    def cost(k):
        q=power(2*k)*spec['norm2']
        return max(q,1/q)
    k=min(candidates,key=lambda k:(cost(k),-k))
    return dict(factor=math.ldexp(1.,k),reason='exact_dyadic',low=lo,high=hi)
