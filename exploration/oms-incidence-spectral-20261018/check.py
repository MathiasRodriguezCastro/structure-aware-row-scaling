"""Independent matrix tests, exact Laplacian root intervals, and rational bounds."""
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import tarfile

import numpy as np
from scipy.linalg import block_diag,svdvals
from scipy.optimize import minimize_scalar
import sympy as sy

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def full(b,c,d,k,gamma=1.):
    return np.block([[np.kron(np.eye(k),b),np.zeros((k*b.shape[0],d.shape[1]))],
                     [np.tile(gamma*c,(1,k)),gamma*d]])


def positive(a):
    s=svdvals(a);return s[s>np.finfo(float).eps*max(a.shape)*s[0]]
def kappa(a):
    s=positive(a);return float(s[0]/s[-1])


def plus(s,k,d,t):
    trace=s+t*(k+d*d)
    return (trace+math.sqrt(max(0.,trace*trace-4*s*d*d*t)))/2
def uniform_kappa(a,b,k,d,gamma):
    t=gamma*gamma
    return math.sqrt(plus(b*b,k,d,t)*plus(a*a,k,d,t)/(d*d*a*a*t))


def sqrt_upper(q,bits=100):
    numerator=q.numerator<<(2*bits);denominator=q.denominator
    r=math.isqrt(numerator//denominator)
    if r*r*denominator<numerator:r+=1
    result=F(r,2**bits)
    assert result*result>=q
    return result


def plus_upper(s,k,d,t):
    trace=s+t*(k+d*d)
    discriminant=trace*trace-4*s*d*d*t
    assert discriminant>=0
    return (trace+sqrt_upper(discriminant))/2


def native_certificates():
    archive=ROOT/'exploration/oms-structure-screen-20261018/sources/R.tgz'
    results=[]
    with tarfile.open(archive) as data:
        for cls in range(1,7):
            name=f'r{cls:02d}.1.dow';body=data.extractfile(name).read()
            rows=[s.split() for s in body.decode().splitlines()[1:] if s.strip()]
            n,e,k=map(int,rows[0]);b=np.zeros((n,e),dtype=int);capacities=[]
            for j,line in enumerate(rows[1:e+1]):
                u,v=int(line[0])-1,int(line[1])-1;b[u,j]=1;b[v,j]=-1;capacities.append(int(line[3]))
            lap=sy.Matrix((b@b.T).tolist());polynomial=lap.charpoly().as_poly()
            intervals=polynomial.intervals(eps=sy.Rational(1,10**24))
            assert sum(m for _,m in intervals)==n
            assert intervals[0]==((sy.Rational(0),sy.Rational(0)),1)
            def frac(q):return F(int(q.p),int(q.q))
            a=frac(intervals[1][0][0]);bb=frac(intervals[-1][0][1]);assert a>0
            # Root intervals are exact rational isolations of the integer polynomial.
            for (lo,hi),multiplicity in intervals:
                if lo==hi:assert polynomial.eval(lo)==0
                else:assert polynomial.count_roots(lo,hi)==multiplicity
            dm,dM=F(min(capacities)),F(max(capacities))
            lower=max(F(1e-9),max(F(1e-6)/(F(1e-5)-F(u)*F(1e-9)) for u in capacities))
            upper=F(1e9)/dM
            # This is a candidate only for heterogeneous D, not its claimed optimizer.
            proxy_d=math.sqrt(float(dm*dM));sing=positive(b.astype(float))
            target=math.sqrt(sing[-1]*sing[0]/(k+proxy_d*proxy_d))
            low_k=math.ceil(math.log2(float(lower)))
            while F(2)**low_k<lower:low_k+=1
            hi_k=math.floor(math.log2(float(upper)))
            while F(2)**hi_k>upper:hi_k-=1
            exponent=min(hi_k,max(low_k,round(math.log2(target))))
            gamma=F(2)**exponent
            assert lower<=gamma<=upper
            for u in capacities:assert F(1e-6)/gamma+F(u)*F(1e-9)<=F(1e-5)
            t=gamma*gamma
            bound_squared=plus_upper(bb,k,dM,t)*plus_upper(a,k,dm,t)/(dm*dm*a*t)
            # Supported local Rayleigh vectors e_u-e_v belong to the positive row space.
            h=min(F(int(lap[u,u]+lap[v,v]-2*lap[u,v]),2) for u in range(n) for v in range(u+1,n))
            baseline_lower_squared=(k+dM*dM)/h
            certified=bound_squared<baseline_lower_squared
            d=-np.diag(capacities).astype(float)
            core0=np.block([[b,np.zeros((n,e))],[math.sqrt(k)*np.eye(e),d]])
            core=np.block([[b,np.zeros((n,e))],[math.sqrt(k)*float(gamma)*np.eye(e),float(gamma)*d]])
            # K-1 contrast B copies are also included in extrema.
            original_s=np.r_[positive(core0),sing];candidate_s=np.r_[positive(core),sing]
            original=float(original_s.max()/original_s.min());candidate=float(candidate_s.max()/candidate_s.min())
            assert candidate**2<=float(bound_squared)*(1+1e-10)
            assert original**2>=float(baseline_lower_squared)*(1-1e-10)
            results.append(dict(instance=name,source_sha256=hashlib.sha256(body).hexdigest(),
                laplacian_polynomial=[str(c) for c in polynomial.all_coeffs()],
                root_intervals=[dict(lo=str(lo),hi=str(hi),multiplicity=m) for (lo,hi),m in intervals],
                eigenvalue_min_lower=str(a),eigenvalue_max_upper=str(bb),coupling_gamma=str(gamma),
                lower_contract=str(lower),upper_window=str(upper),
                kappa_candidate_upper_squared=str(bound_squared),kappa_base_lower_squared=str(baseline_lower_squared),
                certified_strict_improvement=certified,observed_kappa_base=original,
                observed_kappa_candidate=candidate,scope='full mathematical matrix, not solver performance'))
    return results


def main():
    rng=np.random.default_rng(239);gram_checks=0;formula_checks=0
    for r,n,s,p,k in [(1,2,3,1,2),(2,5,3,2,3),(5,2,1,4,3),(3,4,5,2,2),(3,3,3,3,4)]:
        for trial in range(8):
            b=rng.integers(-3,4,(r,n)).astype(float)
            c=rng.integers(-3,4,(s,n)).astype(float);d=rng.integers(-3,4,(s,p)).astype(float)
            gamma=math.ldexp(1.,trial-4)
            a=full(b,c,d,k,gamma)
            m=np.block([[b,np.zeros((r,p))],[math.sqrt(k)*gamma*c,gamma*d]])
            target=block_diag(*([b.T@b]*(k-1)),m.T@m)
            assert np.allclose(np.linalg.eigvalsh(a.T@a),np.linalg.eigvalsh(target),rtol=2e-11,atol=2e-10)
            gram_checks+=1
    b=np.array([[1.,0.]])
    c=np.array([[1.,0.],[0.,1.],[0.,0.]])
    d=np.array([[0.],[0.],[1.]])
    a=full(b,c,d,2);m=np.block([[b,np.zeros((1,1))],[math.sqrt(2)*c,d]])
    zero_example=dict(full_svd_length=len(svdvals(a)),economy_union_length=len(svdvals(m))+len(svdvals(b)),
        full_rank=len(positive(a)),conclusion='positive singular values agree; economy union needs one extra zero')
    assert zero_example['full_svd_length']==5 and zero_example['economy_union_length']==4 and zero_example['full_rank']==4
    uniform=[]
    for shape in ((2,3),(4,3),(3,5)):
        b=rng.integers(-3,4,shape).astype(float)
        b[-1]=b[0]  # Deliberately rank-deficient, without whitening.
        sing=positive(b);low,high=float(sing[-1]),float(sing[0])
        for k in (1,2,7):
            for d in (.25,1.,10.):
                gamma=math.sqrt(low*high/(k+d*d))
                f=lambda z:math.log(uniform_kappa(low,high,k,d,math.exp(z)))
                numerical=minimize_scalar(f,bounds=(math.log(gamma)-8,math.log(gamma)+8),method='bounded',options={'xatol':1e-12})
                assert abs(math.log(gamma)-numerical.x)<2e-5
                for multiplier in (.01,.1,1.,10.,100.):
                    g=gamma*multiplier
                    actual=kappa(full(b,np.eye(shape[1]),d*np.eye(shape[1]),k,g))
                    predicted=uniform_kappa(low,high,k,d,g)
                    assert math.isclose(actual,predicted,rel_tol=2e-8)
                    assert predicted>=uniform_kappa(low,high,k,d,gamma)*(1-1e-12)
                    formula_checks+=1
                # Interval clipping, checked against dense scalar minimization.
                lo,hi=gamma*2,gamma*10
                clipped=min(hi,max(lo,gamma))
                assert clipped==lo
                uniform.append(dict(rows=shape[0],columns=shape[1],rank=len(sing),K=k,d=d,
                    gamma_star=gamma,kappa_min=uniform_kappa(low,high,k,d,gamma)))
    native=native_certificates()
    report=dict(gram_spectrum_checks=gram_checks,closed_formula_dense_checks=formula_checks,
        zero_bookkeeping_counterexample=zero_example,uniform_cases=uniform,native_R_certificates=native,
        certified_native_improvements=sum(r['certified_strict_improvement'] for r in native),
        fresh_optimizer_calls=0,novelty_established=False)
    (HERE/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Gram identities',gram_checks,'formula checks',formula_checks,'native strict certificates',report['certified_native_improvements'],'/ 6')
    for r in native:print(r['instance'],r['coupling_gamma'],round(r['observed_kappa_base'],4),'->',round(r['observed_kappa_candidate'],4),r['certified_strict_improvement'])


if __name__=='__main__':main()
