from fractions import Fraction as F
from itertools import product
from pathlib import Path
import sys

import numpy as np
from scipy.optimize import linprog

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/research'))
from finite_safety_geometry import acceptance_radius, complete_multipliers
from joint_rounding_certificate import certify_binary_block, multipliers


def test_zero_columns_and_degenerate_rows_do_not_create_infinite_family():
    for A in [[[0, 0], [0, 0]], [[0, 1], [0, -1]], [[1, 1], [1, 1]]]:
        assert complete_multipliers(A) == multipliers(A)
    A = [[1, -1, 0], [1, -1, 0], [-1, 1, 0]]
    rays = complete_multipliers(A)
    assert all(sum(lam) == 1 and min(lam) >= 0 for lam in rays)
    assert len(rays) == 5


def test_three_row_certificate_requires_full_support():
    # At z=(1,1,1), each proper subset of rows permits an error direction
    # that hides the violation, but the sum has the strictly positive margin.
    M = 10**9
    A = [[M, -M, 1], [1, M, -M], [-M, 1, M]]
    b = [F(1, 2)] * 3
    eta = F(1, 10**6)
    assert (1, 1, 1) in certify_binary_block(A, b, [F(1, 4)] * 3, eta)['uncovered']
    result = acceptance_radius(A, b, eta)
    cell = next(p for p in result['cells'] if p['z'] == (1, 1, 1))
    assert F(cell['radius']) == F(1, 2) - eta
    assert all(F(v) > 0 for v in cell['lambda_'])


def test_exact_radius_matches_independent_minimax_lp():
    rng = np.random.default_rng(2026091301)
    for m in [1, 2, 3, 4]:
        for _ in range(12):
            A = rng.integers(-15, 16, (m, 3))
            b = rng.integers(-8, 9, m) + .25
            w = rng.integers(1, 6, m)
            eta = F(int(rng.integers(1, 8)), 20)
            tau = eta if rng.random() < .5 else F(0)
            result = acceptance_radius(A, b, eta, w, tau)
            expected = []
            for cell in result['cells']:
                z = np.array(cell['z'])
                bounds = [(max(-float(eta), -v-float(tau)),
                           min(float(eta), 1-v+float(tau))) for v in z]
                lp = linprog([0, 0, 0, 1], A_ub=np.c_[A, -w], b_ub=b-A@z,
                             bounds=bounds+[(None, None)], method='highs')
                assert lp.success, lp.message
                assert abs(float(F(cell['radius'])) - lp.fun) < 1e-8
                expected.append(lp.fun)
            if expected:
                assert abs(float(F(result['radius'])) - min(expected)) < 1e-8
            else:
                assert result['radius'] is None


def test_strict_boundary_and_intrinsic_obstruction():
    result = acceptance_radius([[2, -1], [-1, 2]], [F(1, 2)]*2, F(1, 10))
    cell = next(p for p in result['cells'] if p['z'] == (1, 1))
    assert F(cell['radius']) == F(2, 5)
    # Equality is unsafe: x=(.9,.9) attains both residuals .4 exactly.
    assert not certify_binary_block([[2, -1], [-1, 2]], [F(1, 2)]*2,
                                   [F(2, 5)]*2, F(1, 10))['certified']
    assert F(acceptance_radius([[1]], [F(9, 10)], F(1, 10))['radius']) == 0
    assert F(acceptance_radius([[1]], [F(19, 20)], F(1, 10))['radius']) < 0


def test_exact_integer_data_beyond_binary64_precision():
    a = 2**53+1
    b = 2**53
    eta = F(1, 2**54)
    result = acceptance_radius([[a]], [b], eta)
    assert F(result['radius']) == 1-eta*a > 0
