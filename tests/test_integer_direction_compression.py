from fractions import Fraction as F
from itertools import product
from pathlib import Path
import sys
import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/research'))
from integer_direction_compression import (compress_row,compression_step,
                                           directions,single_coefficient_control)


def same_integer_set(a,b,ar,br,lo,hi):
    for z in product(*(range(l,u+1) for l,u in zip(lo,hi))):
        assert (sum(v*x for v,x in zip(a,z))<=b)==(sum(v*x for v,x in zip(ar,z))<=br),(a,b,ar,br,z)


def test_signed_rows_and_general_bounds_exhaustively():
    rng=np.random.default_rng(2026091401)
    accepted=0
    for _ in range(160):
        v=[int(x) for x in rng.integers(-4,5,4)];e=[int(x) for x in rng.integers(-10,11,4)]
        alpha=int(rng.choice([3,20,1000,10**9]));a=[alpha*y+x for x,y in zip(e,v)]
        b=alpha*int(rng.integers(-4,5))+int(rng.integers(-20,21))
        lo=[-1,0,-2,0];hi=[1,2,1,1]
        step=compression_step(a,b,v,alpha,lo,hi)
        if step:
            same_integer_set(a,b,step[0],step[1],lo,hi);accepted+=1
    assert accepted>70


def test_automatic_discovery_without_magnitude_or_pairing():
    a=[10**12*v+u for v,u in zip([2,-3,4,1,-2,3],[7,1,-2,9,4,2])]
    b=2*10**12+7
    for strategy in ['rational','rounded','rounded-all']:
        result=compress_row(a,b,strategy=strategy)
        assert result['steps'] and max(map(abs,result['a']))<500
        same_integer_set(a,b,result['a'],result['b'],[0]*6,[1]*6)


def test_exact_rescaling_and_column_permutation():
    a=[10**9*v+u for v,u in zip([2,-3,4,1,-2,3],[7,1,-2,9,4,2])];b=2*10**9+7
    base=compress_row(a,b)
    for scale in [F(1,2**30),F(2**20),F(7,3)]:
        result=compress_row([scale*v for v in a],scale*b)
        assert result['a']==base['a'] and result['b']==base['b']
    perm=[3,5,0,4,1,2]
    changed=compress_row([a[j] for j in perm],b)
    same_integer_set([a[j] for j in perm],b,changed['a'],changed['b'],[0]*6,[1]*6)
    assert max(map(abs,changed['a']))<500


def test_dense_pivot_grid_handles_non_power_of_two_denominator():
    a=[10**9*v+u for v,u in zip([5,3,-2,1,4,-3],[7,1,-2,9,4,2])]
    b=3*10**9+7
    result=compress_row(a,b,strategy='rounded-all')
    assert result['steps'] and max(map(abs,result['a']))<500
    same_integer_set(a,b,result['a'],result['b'],[0]*6,[1]*6)


def test_threshold_equalities_and_zero_residual():
    # upper-tau equality is permitted; tau-lower equality must be strict.
    for b in range(-2,16):
        a=[7,13];v=[1,2];alpha=6
        result=compression_step(a,b,v,alpha,[0,0],[1,1])
        if result:same_integer_set(a,b,result[0],result[1],[0,0],[1,1])
    result=compress_row([1000,2000],1500)
    same_integer_set([1000,2000],1500,result['a'],result['b'],[0,0],[1,1])
    assert compress_row([0,0],-1)['b']==-1


def test_classical_single_coefficient_control_equivalence():
    rng=np.random.default_rng(88119)
    for _ in range(120):
        a=[int(v) for v in rng.integers(-50,51,6)];b=int(rng.integers(-80,81))
        ar,br=single_coefficient_control(a,b)
        same_integer_set(a,b,ar,br,[0]*6,[1]*6)


def test_integer_valued_float_bounds_do_not_round_exact_certificates():
    # Regression: float activity bounds used to erase the decisive +1 at 1e18.
    magnitude=10**18;a=[magnitude+1,2*magnitude+1];b=magnitude
    for hi in [[1,1],[1.0,1.0],np.ones(2,dtype=np.int64)]:
        result=compress_row(a,b,lo=[0.0,0.0],hi=hi)
        same_integer_set(a,b,result['a'],result['b'],[0,0],[1,1])
        assert all(isinstance(x,int) for x in result['hi'])
    for kwargs in [dict(hi=[1]),dict(lo=[0,.5]),dict(lo=[2,0])]:
        with pytest.raises(ValueError):compress_row(a,b,**kwargs)
    with pytest.raises(ValueError):compression_step(a,b,[1],magnitude,[0,0],[1,1])
    with pytest.raises(ValueError):compression_step(a,b,[1,2],F(3,2),[0,0],[1,1])


def test_repeated_maximum_pivots_preserve_signed_tie_candidates():
    # Positive and negative pivots can break rational approximation ties
    # differently; duplicates of the same value must add no new candidates.
    from importlib.util import spec_from_file_location,module_from_spec
    frozen=Path(__file__).resolve().parents[1]/'results-revision/research-audit/miplib-structure-screen-20260913/sources/integer_direction_compression.py'
    spec=spec_from_file_location('frozen_direction_compression',frozen)
    old=module_from_spec(spec);spec.loader.exec_module(old)
    for row in [[2,2,-2,1,-1],[10]*20+[-10]*20+[3,-7],[0]*4+[100,99,100]]:
        for strategy in ['rational','rounded','rounded-all']:
            assert directions(row,strategy=strategy)==old.directions(row,strategy=strategy)
