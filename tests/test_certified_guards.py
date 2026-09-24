from fractions import Fraction as F
from itertools import product
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/research'))
from certified_guards import aggregate,partial_nogoods,compile_block


def test_outward_aggregate_dominates_exact_row_on_entire_box():
    A=[[10**12,1-10**12,-1],[1-10**12,10**12,-1]];b=[.5,.5]
    lam=[F(10**12,2*10**12-1),F(10**12-1,2*10**12-1)]
    g=aggregate(A,b,lam);gamma=F(g['gamma'])
    exact_a=[gamma*sum(lam[r]*A[r][j] for r in range(2)) for j in range(3)]
    exact_b=gamma*sum(lam[r]*F(b[r]) for r in range(2))
    # Every linear rounding-error maximum on the full continuous box occurs
    # at a vertex; enumerate it independently of the implementation's support.
    for x in product([0,1],repeat=3):
        difference=sum((F(a)-p)*v for a,p,v in zip(g['a'],exact_a,x))
        assert difference <= F(g['b'])-exact_b


def test_local_clauses_are_integer_valid_and_cover_requested_centers():
    A=[[1000,-999,-1],[-999,1000,-1]];b=[.5,.5]
    targets=[(1,1,0)]
    clauses=partial_nogoods(A,b,targets)
    assert len(clauses)==1
    for z in product([0,1],repeat=3):
        feasible=all(sum(a*v for a,v in zip(row,z))<=rhs for row,rhs in zip(A,b))
        satisfied=all(sum(a*v for a,v in zip(c['a'],z))<=c['b'] for c in clauses)
        if feasible:assert satisfied
        if z in targets:assert not satisfied


def test_intrinsic_collision_is_detected_and_distinguished():
    # Exact feasible x near z=(1,0), but z violates first row.
    # An infinitesimal decrease of x1 trades violation for slack in row2.
    M=10**9;A=[[M,1],[-M,1]];b=[M-.5,-M+2.]
    p=compile_block(A,b)
    assert (1,0) in p['intrinsic_uncovered']
    assert (1,0) in p['original_uncovered']
