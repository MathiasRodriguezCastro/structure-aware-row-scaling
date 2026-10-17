"""Exact finite binary multipliers and an explicitly finite rounded search.

All decisions use rational arithmetic in the supplied floating point data.
The full exact-product search is complete; the rounded-product search is not.
"""
from fractions import Fraction as Q
from functools import lru_cache
import math


def p2(k):
    return Q(1 << k) if k >= 0 else Q(1, 1 << -k)


def floorlog(q):
    k=q.numerator.bit_length()-q.denominator.bit_length()
    return k-1 if p2(k)>q else k


def ceillog(q):
    k=floorlog(q)
    return k+(p2(k)<q)


def ceilq(q):
    return -((-q.numerator)//q.denominator)


def oddparts(q):
    q=abs(Q(q));assert q>0 and q.denominator & (q.denominator-1)==0
    n=q.numerator;v=(n & -n).bit_length()-1
    return n>>v,v-(q.denominator.bit_length()-1)


def representable(q,bits=53,emin=-1074,emax=1023):
    if not q:return True
    n,k=oddparts(q)
    return n.bit_length()<=bits and k>=emin and k+n.bit_length()-1<=emax


def score(alpha,m,M):
    return max(alpha*M,1/(alpha*m))


@lru_cache(maxsize=100000)
def select(zs,m,M,lower,upper,powers=False,bits=53,emin=-1074,emax=1023):
    """Global centered optimum among ALL exact positive binary multipliers.

    A multiplier has unique odd significand h. Exact products require
    h <= floor((2**bits-1)/max N_z). Bounds on exponents and product range
    leave independent intervals of odd h for each k. The objective is
    unimodal in h, so endpoints and the two neighbors of its real optimum
    suffice. At most the finite format's exponent span is inspected.
    """
    assert zs and m>0 and M>=m and lower>0
    if lower>upper:return None
    parts=[oddparts(z) for z in zs if z]
    limit=(1<<bits)-1
    hmax=1 if powers else min(limit//n for n,_ in parts)
    if hmax<1:return None
    biggest=Q(limit)*p2(emax-bits+1)
    upper=min(upper,biggest,biggest/max(map(abs,zs)))
    if lower>upper:return None
    first=max(emin,max(emin-e for _,e in parts),ceillog(lower/Q(hmax)))
    last=min(emax,floorlog(upper));best=None
    for k in range(first,last+1):
        unit=p2(k)
        lo=max(1,ceilq(lower/unit));hi=min(hmax,(upper/unit).__floor__())
        lo+=1-lo%2;hi-=1-hi%2
        if lo>hi:continue
        # floor(sqrt(1/(m*M*unit**2))) without floating point logs.
        x=1/(m*M*unit*unit);near=math.isqrt(x.numerator//x.denominator)
        below=near if near%2 else near-1
        for h in {lo,hi,min(hi,max(lo,below)),min(hi,max(lo,below+2))}:
            alpha=h*unit
            key=(score(alpha,m,M),-alpha)
            if best is None or key<best[0]:best=(key,alpha)
    return None if best is None else best[1]


def interval(row,variables,delta=None,epsilon=Q(1e-6),gamma=Q(1e-9)):
    nz=[abs(Q(a)) for _,a in row['terms'] if a]
    m,M=min(nz),max(nz);lower=Q(1e-9)/m;upper=Q(1e9)/M
    reserve=gamma*sum(abs(Q(a)) for j,a in row['terms'] if variables[j]['type']!='C')
    if delta is not None:
        if delta<=reserve:return m,M,Q(2),Q(1),reserve
        lower=max(lower,epsilon/(delta-reserve))
    return m,M,lower,upper,reserve


def defect(row,variables,alpha):
    """Exact max |(a-ahat/alpha)x + bhat/alpha-b| on the stored box.

    A nonzero error on an unbounded coordinate returns None. Zero error
    does not need a bound. This is an export defect, NOT a solver residual.
    """
    f=float(alpha)
    try:
        bhat=f*row['rhs'];ahat=[f*a for _,a in row['terms']]
    except OverflowError:return None
    if not all(map(math.isfinite,[bhat,*ahat])):return None
    low=high=Q(bhat)/alpha-Q(row['rhs'])
    for (j,a),rounded in zip(row['terms'],ahat):
        error=Q(a)-Q(rounded)/alpha
        if not error:continue
        v=variables[j];lb,ub=v['lb'],v['ub']
        if lb is None or ub is None:return None
        one,two=error*Q(lb),error*Q(ub)
        low+=min(one,two);high+=max(one,two)
    return max(abs(low),abs(high))


def inward(q,up):
    try:f=float(q)
    except OverflowError:f=math.inf
    if math.isinf(f):return f if up else float.fromhex('0x1.fffffffffffffp+1023')
    if (up and Q(f)<q) or (not up and Q(f)>q):f=math.nextafter(f,math.inf if up else 0.)
    return f


def rounded_center(m,M,lower,upper):
    if lower>upper:return None
    lo,hi=inward(lower,True),inward(upper,False)
    if lo>hi or not math.isfinite(lo) or hi<=0:return None
    target=math.exp(-.5*(math.log(float(m))+math.log(float(M))))
    f=min(hi,max(lo,target))
    # Compare neighbors exactly, avoiding log cancellation in near ties.
    choices={f,lo,hi,math.nextafter(f,0.),math.nextafter(f,math.inf)}
    return min((Q(v) for v in choices if math.isfinite(v) and v>0 and lower<=Q(v)<=upper),
               key=lambda q:(score(q,m,M),-q))


def export_aware(row,variables,delta,epsilon=Q(1e-6)):
    """Best centered VERIFIED candidate in a declared finite pool.

    Pool: exact-GM, power-of-two-GM, rounded-GM, inward endpoints and
    eight nextafter neighbors on either side of rounded-GM.
    """
    m,M,lo,hi,E=interval(row,variables,delta,epsilon)
    if lo>hi:return None
    zs=tuple(Q(a) for _,a in row['terms'] if a)+(Q(row['rhs']),)
    one=select(zs,m,M,lo,hi,True);exact=select(zs,m,M,lo,hi)
    rounded=rounded_center(m,M,lo,hi);pool={one,exact,rounded}
    if rounded is not None:
        down=up=float(rounded)
        for _ in range(8):
            down=math.nextafter(down,0.);up=math.nextafter(up,math.inf)
            if math.isfinite(down):pool.add(Q(down))
            if math.isfinite(up):pool.add(Q(up))
    for endpoint,upward in [(lo,True),(hi,False)]:
        f=inward(endpoint,upward)
        if math.isfinite(f):pool.add(Q(f))
    viable=[]
    for alpha in pool:
        if alpha is None or not lo<=alpha<=hi:continue
        products=[float(alpha)*a for _,a in row['terms'] if a]
        if not all(math.isfinite(v) and Q(1e-9)<=abs(Q(v))<=Q(1e9) for v in products):continue
        rho=defect(row,variables,alpha)
        if rho is None or epsilon/alpha+E+rho>delta:continue
        viable.append((score(alpha,m,M),epsilon/alpha+E+rho,-alpha,alpha))
    return None if not viable else min(viable)[-1]
