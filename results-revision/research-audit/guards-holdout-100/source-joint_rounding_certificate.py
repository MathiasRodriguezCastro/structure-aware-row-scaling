"""Exact small-block certificates for conditional near-integer acceptance.

Farkas separation and box support functions are classical. This exploratory module
uses them to test a numerical acceptance contract, not solver correctness. For two
rows the finite multiplier set is complete; for more rows it is only a sufficient
pair-supported certificate family. All certificate checks use stored-data rationals.
"""
from fractions import Fraction as F
from itertools import product


def rational(x):
    return x if isinstance(x,F) else F(float(x))


def multipliers(A, pairs=True):
    """Units and all two-row simplex breakpoints where a column cancels."""
    A=[[rational(x) for x in row] for row in A]
    m=len(A); out=set()
    for i in range(m):
        lam=[F(0)]*m;lam[i]=F(1);out.add(tuple(lam))
    if pairs:
        for i in range(m):
            for k in range(i):
                for a,b in zip(A[i],A[k]):
                    if a==b:continue
                    t=-b/(a-b)
                    if 0<t<1:
                        lam=[F(0)]*m;lam[i]=t;lam[k]=1-t;out.add(tuple(lam))
    return sorted(out)


def row_gap(A,b,z,lam,eta,bound_tolerance=0):
    """g=lam*(Az-b)+min_e (A^T lam)*e, with bound-aware noise box."""
    A=[[rational(x) for x in row] for row in A]
    b=list(map(rational,b));lam=list(map(rational,lam));eta=rational(eta)
    tau=rational(bound_tolerance)
    p=[sum((lam[r]*A[r][j] for r in range(len(A))),F(0)) for j in range(len(z))]
    g=sum((p[j]*int(z[j]) for j in range(len(z))),F(0))-sum((l*v for l,v in zip(lam,b)),F(0))
    for j,v in enumerate(z):
        low=max(-eta,-int(v)-tau);high=min(eta,1-int(v)+tau)
        g+=min(p[j]*low,p[j]*high)
    return g


def certify_binary_block(A,b,t,eta,pairs=True,bound_tolerance=0):
    """Certify all bad rounded binary centers; return rational proof objects.

    Hypothesis: original row violations <=t and coordinate distance to the nearest
    binary center <=eta<1/2, with the stated bound tolerance. No optimizer is called.
    For m=2 an uncovered bad center is an exact counterexample to this universal
    contract (separation theorem); for m>2 it may require a larger-support multiplier.
    """
    A=[[rational(x) for x in row] for row in A];b=list(map(rational,b));t=list(map(rational,t))
    eta=rational(eta)
    if not 0<=eta<F(1,2) or any(x<0 for x in t):raise ValueError('invalid tolerances')
    candidates=multipliers(A,pairs)
    bad=[];proof=[]
    for z in product([0,1],repeat=len(A[0])):
        if all(sum((a*v for a,v in zip(row,z)),F(0))<=rhs for row,rhs in zip(A,b)):continue
        choices=[]
        for lam in candidates:
            gap=row_gap(A,b,z,lam,eta,bound_tolerance)
            margin=gap-sum((x*y for x,y in zip(lam,t)),F(0))
            choices.append((margin,lam,gap))
        margin,lam,gap=max(choices)
        if margin<=0:bad.append(z)
        else:proof.append(dict(z=z,lambda_=list(map(str,lam)),gap=str(gap),margin=str(margin)))
    return dict(certified=not bad,uncovered=bad,certificates=proof,
                complete_multiplier_family=len(A)<=2 and pairs,
                multiplier_count=len(candidates))


def exact_witness(A,b,z,e,t):
    """Check a candidate feasible point in an infeasible center's rounding cell."""
    x=[F(int(a))+rational(v) for a,v in zip(z,e)]
    residual=[sum((rational(a)*v for a,v in zip(row,x)),F(0))-rational(rhs)
              for row,rhs in zip(A,b)]
    return all(r<=rational(v) for r,v in zip(residual,t))
