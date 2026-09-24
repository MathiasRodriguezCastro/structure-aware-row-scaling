from fractions import Fraction as F
from itertools import product
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/research'))
from single_row_safety import intrinsic_single_row


def brute_collision(a, b, eta):
    for z in product([0, 1], repeat=len(a)):
        activity = sum(v*w for v, w in zip(a, z))
        if activity <= b:
            continue
        minimum = activity - eta*sum(v if v>0 and bit else -v if v<0 and not bit else 0
                                     for v, bit in zip(a, z))
        if minimum <= b:
            return True
    return False


def test_interval_algorithm_against_exhaustive_exact_cells():
    rng = np.random.default_rng(2026091319)
    for _ in range(160):
        a = [int(v) for v in rng.integers(-30, 31, 7)]
        b = F(int(rng.integers(-60, 61)), 2)
        eta = F(int(rng.integers(1, 10)), 20)
        result = intrinsic_single_row(a, b, eta)
        assert (result['status']=='UNSAFE') == brute_collision(a, b, eta)
        if result['witness']:
            z = result['witness']['z']
            x = list(map(F, result['witness']['x']))
            assert all(0<=v<=1 and abs(v-w)<=eta for v, w in zip(x, z))
            assert sum(v*w for v, w in zip(a, x))<=b<sum(v*w for v, w in zip(a, z))


def test_input_tolerance_reduction_from_subset_sum():
    a = [3, 7, 19, 31]
    for target in range(3, 61):
        result = intrinsic_single_row(a, target-1, F(1, target))
        exists = any(sum(v*w for v, w in zip(a, z))==target for z in product([0,1], repeat=4))
        assert (result['status']=='UNSAFE') == exists


def test_boundaries_zero_coefficients_and_work_cap():
    for a, b in [([0,0], 0), ([2,4], 0), ([2,4], -1), ([2,4], 6), ([-2,4], -2)]:
        assert intrinsic_single_row(a, b, F(1,10))['status']=='SAFE'
    assert intrinsic_single_row([10,11,12], 15, F(1,10), max_subsets=1)['status']=='UNKNOWN'
    # Exact boundary U=10 is included; only S>B is strict.
    result = intrinsic_single_row([10], 9, F(1,10))
    assert result['status']=='UNSAFE' and result['witness']['x']==['9/10']
