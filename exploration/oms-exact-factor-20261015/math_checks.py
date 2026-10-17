#!/usr/bin/env python3
"""Deterministic exhaustive toy and binary64 boundary checks."""
from fractions import Fraction as Q
from pathlib import Path
import json
import math
import random
from factors import p2,oddparts,select,score,representable


def main():
    rng=random.Random(20261015)
    toy=sorted({Q(n)*p2(k) for n in range(1,32,2) for k in range(-8,6) if k+n.bit_length()-1<=5})
    results=[];comparisons=0
    for _ in range(40):
        aa=[rng.choice(toy) for _ in range(3)];rhs=rng.choice(toy);lo,hi=sorted(rng.sample(toy,2))
        for powers in [False,True]:
            feasible=[]
            for alpha in toy:
                comparisons+=1
                if not lo<=alpha<=hi or (powers and oddparts(alpha)[0]!=1):continue
                if all(representable(alpha*z,5,-8,5) for z in [*aa,rhs]):feasible.append(alpha)
            expected=min(feasible,key=lambda q:(score(q,min(aa),max(aa)),-q)) if feasible else None
            got=select(tuple([*aa,rhs]),min(aa),max(aa),lo,hi,powers,5,-8,5)
            assert expected==got
            results.append(dict(coefficients=list(map(str,aa)),rhs=str(rhs),lower=str(lo),upper=str(hi),
                powers_only=powers,feasible_factors=len(feasible),optimum=None if got is None else str(got)))
    native=[]
    for i in range(300):
        # Mix short/full significands and normal/subnormal/exponent boundaries.
        n=rng.randrange(1,1<<(rng.choice([3,20,52,53])))|1
        expo=rng.choice([-1074,-1022,-100,-1,0,1,100,800,970])
        z=float(n*p2(expo))
        if not math.isfinite(z) or z==0:continue
        h=rng.choice([1,3,5,(1<<20)-1,(1<<52)-1]);k=rng.choice([-1074,-1022,-100,-1,0,1,10,800])
        alpha=float(h*p2(k))
        if not math.isfinite(alpha) or alpha<=0:continue
        a,e=oddparts(Q(z));b,f=oddparts(Q(alpha))
        predicted=(a*b).bit_length()<=53 and e+f>=-1074 and e+f+(a*b).bit_length()-1<=1023
        p=z*alpha;actual=math.isfinite(p) and Q(p)==Q(z)*Q(alpha)
        assert predicted==actual
        native.append(dict(datum_hex=z.hex(),alpha_hex=alpha.hex(),products_exact=actual))
    result=dict(toy_formats_checked=80,toy_candidate_comparisons=comparisons,toy_cases=results,
        binary64_cases=native,binary64_cases_count=len(native),native_optimizer_calls=0)
    dest=Path(__file__).resolve().parent/'mathematical-checks.json'
    dest.write_text(json.dumps(result,indent=2)+'\n')
    print('Mathematical checks:',comparisons,'toy comparisons;',len(native),'binary64 pairs')


if __name__=='__main__':main()
