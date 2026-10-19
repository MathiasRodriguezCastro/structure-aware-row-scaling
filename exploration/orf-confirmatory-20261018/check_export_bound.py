#!/usr/bin/env python3
"""Exact property checks of finite export and subsequent integer rounding."""
from fractions import Fraction as Q
import json
import math
from pathlib import Path
import random

HERE=Path(__file__).resolve().parent
F=Q.from_float
def violation(a,b,x,equality):
    r=sum((c*v for c,v in zip(a,x)),Q(0))-b
    return abs(r) if equality else max(Q(0),r)

def main():
    rng=random.Random(2026101901);checked=0;nonexact=0;exact=0
    for i in range(10000):
        n=1+i%5
        aa=[math.ldexp(rng.uniform(-2,2),rng.randrange(-100,100)) for _ in range(n)]
        bb=math.ldexp(rng.uniform(-2,2),rng.randrange(-100,100))
        alpha=math.ldexp(1. if i%4==0 else rng.uniform(.5,2),rng.randrange(-60,60))
        xx=[rng.uniform(-10,10) for _ in range(n)]
        a=list(map(F,aa));b=F(bb);s=F(alpha);x=list(map(F,xx))
        at=[F(alpha*v) for v in aa];bt=F(alpha*bb)
        ea=[u-s*v for u,v in zip(at,a)];eb=bt-s*b
        nonexact+=bool(any(ea) or eb);exact+=not any(ea) and eb==0
        rounded=[Q(round(v)) if j%2==0 else v for j,v in enumerate(x)]
        E=sum((abs(c)*abs(u-v) for c,u,v in zip(a,rounded,x)),Q(0))
        box=[Q(math.ceil(abs(v))) for v in x]
        B=sum((abs(e)*X for e,X in zip(ea,box)),abs(eb))
        point_error=abs(sum((e*v for e,v in zip(ea,x)),Q(0)))+abs(eb)
        for equality in [False,True]:
            epsilon=violation(at,bt,x,equality)
            observed=violation(a,b,x,equality);after=violation(a,b,rounded,equality)
            assert observed<=(epsilon+point_error)/s<=(epsilon+B)/s
            assert after<=(epsilon+B)/s+E
            # At the sufficient budget endpoint the rounded point must pass.
            delta=(epsilon+B)/s+E
            assert epsilon+B+s*E==s*delta and after<=delta
            if not any(ea) and not eb:assert (epsilon+B)/s==epsilon/s
            checked+=1
    assert exact>0 and nonexact>0
    result=dict(passed=True,exact_rational_row_checks=checked,nonexact_exports=nonexact,
        exact_exports=exact,solver_calls=0,policy_changed=False,
        scope='elementary sufficient error bound; not new interval completeness or MILP optimality')
    (HERE/'EXPORT_BOUND_VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
