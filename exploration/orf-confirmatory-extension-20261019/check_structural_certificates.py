#!/usr/bin/env python3
"""Independently sum saved row/bound multipliers to verify 0 <= a negative RHS."""
from collections import defaultdict
from fractions import Fraction as Q
from runner import HERE,ROOT,load,save,sha,library

checker=library(ROOT/'exploration/orf-confirmatory-20261018/check.py','farkas_replay_reader')
report=load(HERE/'STRUCTURAL_FEASIBILITY_AUDIT.json');count=0;decimal_gaps={}
for certificate in report['certificates']:
    path=HERE/'models'/certificate['instance']/'Base.lp'
    assert sha(path)==certificate['base_sha256'];rows,bounds,*_=checker.canonical(path)
    lhs=defaultdict(Q);rhs=Q(0)
    for name,value in certificate['row_multipliers'].items():
        multiplier=Q(value);row=rows[name]
        assert row['sense']=='=' or (row['sense']=='<=' and multiplier>=0)
        for j,c in row['terms'].items():lhs[j]+=multiplier*c
        rhs+=multiplier*row['rhs']
    for bound in certificate['bound_multipliers']:
        name=bound['variable'];multiplier=Q(bound['positive_multiplier']);assert multiplier>=0
        lo,hi=bounds[name]
        if bound['bound']=='lower':
            assert lo==Q(bound['value']);lhs[name]-=multiplier;rhs-=multiplier*lo
        else:
            assert hi==Q(bound['value']);lhs[name]+=multiplier;rhs+=multiplier*hi
    assert not any(lhs.values()) and rhs<0 and rhs==Q(certificate['contradiction_rhs_exact'])
    # Separately read the written decimal coefficients as exact decimals,
    # without a binary64 conversion. The contradiction is not a rounding artifact.
    decimal_rows,_=checker.parse(path);decimal_lhs=defaultdict(Q);decimal_rhs=Q(0)
    for name,value in certificate['row_multipliers'].items():
        multiplier=Q(value);row=decimal_rows[name]
        for j,c in row['terms'].items():decimal_lhs[j]+=multiplier*Q(c)
        decimal_rhs+=multiplier*Q(row['rhs'])
    decimal_minimum=Q(0)
    for j,c in decimal_lhs.items():
        if c:
            endpoint=bounds[j][0 if c>0 else 1];assert endpoint is not None
            decimal_minimum+=c*endpoint
    assert decimal_rhs<decimal_minimum
    decimal_gaps[certificate['instance']]=str(decimal_rhs-decimal_minimum)
    count+=1
save(HERE/'STRUCTURAL_CERTIFICATE_REPLAY.json',dict(status='passed',certificates_checked=count,
    decimal_LP_certificates_checked=len(decimal_gaps),decimal_contradiction_RHS=decimal_gaps,
    optimizer_calls=0,proof='Each nonnegative inequality combination cancels every coefficient and has a strictly negative RHS.'))
print('Independently checked',count,'exact infeasibility certificates; zero optimizer calls.')
