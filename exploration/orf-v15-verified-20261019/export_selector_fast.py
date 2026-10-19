"""Same finite numerical objective; stop at the first certified ranked candidate.

Ordering before evaluation preserves the selected factor of the exhaustive
prototype, including its floating-logarithm tie break. This is not an assertion
of exact real-logarithm ordering among arbitrarily close binary64 values.
"""
from fractions import Fraction as Q
import math

from export_selector import certificate

F=Q.from_float


def choose(a,b,boxes,delta,E=Q(0),epsilon=1e-6,floor=1e-9,ceiling=1e9):
    a=list(map(float,a));nz=[abs(v) for v in a if v]
    if not nz or len(boxes)!=len(a) or not all(math.isfinite(v) for v in [*a,b]):raise ValueError('finite nonconstant row required')
    delta=delta if isinstance(delta,Q) else F(float(delta))
    if E>=delta:return dict(factor=None,certified=False,status='sufficient_rounding_contract_empty',candidates_tested=0)
    lo=max(F(floor)/F(min(nz)),F(epsilon)/(delta-E));hi=F(ceiling)/F(max(nz))
    if lo>hi:return dict(factor=None,certified=False,status='ideal_search_interval_empty',candidates_tested=0)
    lower=float(lo);upper=float(hi)
    if F(lower)<lo:lower=math.nextafter(lower,math.inf)
    if F(upper)>hi:upper=math.nextafter(upper,0.)
    if not 0<lower<=upper<math.inf:return dict(factor=None,certified=False,status='no_representable_factor_in_search_interval',candidates_tested=0)
    target=-math.log(max(nz))-.5*math.log(sum((v/max(nz))**2 for v in nz))
    ideal=min(max(math.exp(target),lower),upper);candidates={lower,upper,ideal}
    for direction in [0.,math.inf]:
        value=ideal
        for _ in range(32):
            value=math.nextafter(value,direction)
            if lower<=value<=upper:candidates.add(value)
    llog,hlog=math.log(lower),math.log(upper)
    for k in range(65):
        value=math.exp(llog+(hlog-llog)*k/64)
        if lower<=value<=upper:candidates.add(value)
    for k in range(max(-1074,math.floor(math.log2(lower))-1),min(1023,math.ceil(math.log2(upper))+1)+1):
        value=math.ldexp(1.,k)
        if lower<=value<=upper:candidates.add(value)
    rejections={}
    ranked=sorted(candidates,key=lambda alpha:(abs(math.log(alpha)-target),-alpha))
    for count,alpha in enumerate(ranked,1):
        cert,reason=certificate(a,b,boxes,alpha,delta,E,epsilon,floor,ceiling)
        if cert is not None:return dict(factor=alpha,certified=True,status='ranked_finite_candidate_certificate',
            candidates_tested=count,candidate_list_size=len(candidates),rejections=rejections,**cert)
        rejections[reason]=rejections.get(reason,0)+1
    return dict(factor=None,certified=False,status='finite_search_abstention',candidates_tested=len(candidates),rejections=rejections)
