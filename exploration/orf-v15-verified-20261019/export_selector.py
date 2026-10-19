"""Finite-candidate row selection with actual binary64/17-digit export reserves.

The search is complete only over the explicitly enumerated candidate list.
An abstention never certifies nonexistence of some other binary64 factor.
"""
from fractions import Fraction as Q
import math

F=Q.from_float


def certificate(a,b,boxes,alpha,delta,E,epsilon=1e-6,floor=1e-9,ceiling=1e9):
    if not math.isfinite(alpha) or alpha<=0:return None,'invalid_factor'
    written=[float(format(float(v)*alpha,'.17g')) for v in a]
    wb=float(format(b*alpha,'.17g'))
    if not all(math.isfinite(v) for v in [*written,wb]):return None,'nonfinite_export'
    if any(v==0 or not F(floor)<=abs(F(v))<=F(ceiling) for v,old in zip(written,a) if old):
        return None,'written_coefficient_window'
    ea=[F(v)-F(alpha)*F(float(old)) for v,old in zip(written,a)]
    B=abs(F(wb)-F(alpha)*F(float(b)))
    for error,bound in zip(ea,boxes):
        if error and (bound is None or not math.isfinite(bound)):return None,'missing_finite_bound'
        if error:B+=abs(error)*F(float(bound))
    if delta is not None and F(epsilon)+B+F(alpha)*E>F(alpha)*delta:return None,'export_contract_not_met'
    return dict(B_exact=str(B),E_exact=str(E),delta_exact=None if delta is None else str(delta),
        sufficient_violation_exact=str((F(epsilon)+B)/F(alpha)+E),
        changed_coefficient_products=sum(bool(v) for v in ea),rhs_product_error_exact=str(F(wb)-F(alpha)*F(float(b)))),None


def choose(a,b,boxes,delta,E=Q(0),epsilon=1e-6,floor=1e-9,ceiling=1e9):
    a=list(map(float,a));nz=[abs(v) for v in a if v]
    if not nz or len(boxes)!=len(a) or not all(math.isfinite(v) for v in [*a,b]):raise ValueError('finite nonconstant row required')
    delta=delta if isinstance(delta,Q) else F(float(delta))
    if E>=delta:
        return dict(factor=None,certified=False,status='sufficient_rounding_contract_empty',
            E_exact=str(E),delta_exact=str(delta),candidates_tested=0)
    lo=max(F(floor)/F(min(nz)),F(epsilon)/(delta-E));hi=F(ceiling)/F(max(nz))
    if lo>hi:return dict(factor=None,certified=False,status='ideal_search_interval_empty',candidates_tested=0)
    lower=float(lo);upper=float(hi)
    if F(lower)<lo:lower=math.nextafter(lower,math.inf)
    if F(upper)>hi:upper=math.nextafter(upper,0.)
    if not 0<lower<=upper<math.inf:
        return dict(factor=None,certified=False,status='no_representable_factor_in_search_interval',candidates_tested=0)
    target=-math.log(max(nz))-.5*math.log(sum((v/max(nz))**2 for v in nz))
    ideal=min(max(math.exp(target),lower),upper)
    candidates={lower,upper,ideal}
    for direction in [0.,math.inf]:
        value=ideal
        for _ in range(32):
            value=math.nextafter(value,direction)
            if lower<=value<=upper:candidates.add(value)
    # Candidate grid is fixed in advance, not refined using solver outcomes.
    llog,hlog=math.log(lower),math.log(upper)
    for k in range(65):
        value=math.exp(llog+(hlog-llog)*k/64)
        if lower<=value<=upper:candidates.add(value)
    for k in range(max(-1074,math.floor(math.log2(lower))-1),min(1023,math.ceil(math.log2(upper))+1)+1):
        value=math.ldexp(1.,k)
        if lower<=value<=upper:candidates.add(value)
    good=[];rejections={}
    for alpha in sorted(candidates):
        cert,reason=certificate(a,b,boxes,alpha,delta,E,epsilon,floor,ceiling)
        if cert is not None:good.append((abs(math.log(alpha)-target),-alpha,alpha,cert))
        else:rejections[reason]=rejections.get(reason,0)+1
    if not good:return dict(factor=None,certified=False,status='finite_search_abstention',
        candidates_tested=len(candidates),rejections=rejections)
    distance,_,factor,cert=min(good,key=lambda item:item[:2])
    return dict(factor=factor,certified=True,status='finite_candidate_certificate',
        candidates_tested=len(candidates),certified_candidates=len(good),rejections=rejections,
        log_distance_to_L2=distance,**cert)
