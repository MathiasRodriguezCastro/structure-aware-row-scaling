#!/usr/bin/env python3
"""Non-vacuous exact boundary tests of selected finite-export certificates."""
from fractions import Fraction as Q
import hashlib
import json
import math
from pathlib import Path
import random

from export_selector import choose
from export_selector_fast import choose as ranked_choose

HERE=Path(__file__).resolve().parent;F=Q.from_float


def main():
    rng=random.Random(2026101907);checks=0;abstentions=0;non_dyadic=0
    for trial in range(80):
        a=[rng.uniform(-5,5) for _ in range(3)];b=rng.uniform(-30,30);X=[100.,100.,100.]
        result=choose(a,b,X,.0001)
        ranked=ranked_choose(a,b,X,.0001)
        assert result['certified']==ranked['certified'] and result['factor']==ranked['factor']
        if not result['certified']:abstentions+=1;continue
        alpha=result['factor'];wa=[F(float(format(v*alpha,'.17g'))) for v in a];wb=F(float(format(b*alpha,'.17g')))
        errors=[v-F(alpha)*F(old) for v,old in zip(wa,a)]
        B=sum((abs(e)*F(x) for e,x in zip(errors,X)),abs(wb-F(alpha)*F(b)))
        assert B==Q(result['B_exact'])
        assert (F(1e-6)+B)/F(alpha)<=F(.0001)
        non_dyadic+=bool(sum(bool(v) for v in errors))
        pivot=max(range(3),key=lambda j:abs(wa[j]))
        for _ in range(25):
            x=[F(rng.uniform(-10,10)) for _ in a]
            # Exact points on both sides of the allowed written-row residual.
            x[pivot]=(wb+F(1e-6)-sum((v*q for j,(v,q) in enumerate(zip(wa,x)) if j!=pivot),Q(0)))/wa[pivot]
            if abs(x[pivot])>100:continue
            assert sum((v*q for v,q in zip(wa,x)),Q(0))-wb==F(1e-6)
            original=sum((F(v)*q for v,q in zip(a,x)),Q(0))-F(b)
            assert max(Q(0),original)<=F(.0001)
            assert abs(sum((e*q for e,q in zip(errors,x)),Q(0))-(wb-F(alpha)*F(b)))<=B
            checks+=1
    # The ideal L2 projection passes its real-arithmetic condition but fails
    # the uniform bound based on the actual written products in this example.
    a=[3.];b=.1;X=[1e16];alpha=math.exp(-math.log(3.));delta=.01
    idealB=abs(F(alpha*3)-F(alpha)*3)*F(X[0])+abs(F(alpha*b)-F(alpha)*F(b))
    assert F(1e-6)/F(alpha)<=F(delta)<(F(1e-6)+idealB)/F(alpha)
    selected=choose(a,b,X,delta)
    assert selected['certified'] and selected['factor']!=alpha
    # No finite bound is needed when the corresponding product error is zero.
    unbounded=choose([3.,7.],.1,[None,None],.01)
    assert unbounded['certified'] and Q(unbounded['B_exact'])>=0
    f=unbounded['factor'];assert all(F(v*f)==F(v)*F(f) for v in [3.,7.])
    incompatible=choose([1e9,-1.],1e9,[1.,1e9],1.,E=Q(1))
    assert not incompatible['certified'] and incompatible['status']=='sufficient_rounding_contract_empty'
    assert checks>1500
    out=dict(status='passed',boundary_transfer_checks=checks,certified_rows=80-abstentions,
        rows_with_nonzero_coefficient_export_errors=non_dyadic,
        ideal_projection_counterexample=dict(ideal_factor=alpha,ideal_sufficient_violation=str((F(1e-6)+idealB)/F(alpha)),
            budget=delta,selected=selected),unbounded_column_example=unbounded,
        incompatibility_is_of_sufficient_condition_only=True,additional_optimizer_calls=0,
        selector_sha256=hashlib.sha256((HERE/'export_selector.py').read_bytes()).hexdigest())
    (HERE/'SELECTOR_VALIDATION.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))


if __name__=='__main__':main()
