import sys
from pathlib import Path
from fractions import Fraction

import numpy as np
import pytest
from scipy.optimize import linprog

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts' / 'research'))
from budget_scaling import select_factor, dyadic_factor, exact_row_violation


def test_against_independent_linear_program():
    """The minimax problem in log coordinates is an LP in (log alpha, radius)."""
    rng = np.random.default_rng(20260908)
    for _ in range(120):
        a = 10.0**rng.uniform(-8, 8, size=15)
        delta = 10.0**rng.uniform(-8, 2)
        d = select_factor(a, delta, coefficient_floor=1e-7, coefficient_ceiling=1e7)
        logs = np.log(a)
        inequalities = np.array([[1., -1.]]*len(a) + [[-1., -1.]]*len(a))
        rhs = np.concatenate([-logs, logs])
        if d.factor is None:
            assert d.lower > d.upper
            continue
        lp = linprog([0., 1.], A_ub=inequalities, b_ub=rhs,
                     bounds=[(np.log(d.lower), np.log(d.upper)), (0., None)])
        assert lp.success
        assert np.isclose(max(abs(np.log(d.factor*a))), lp.fun, atol=1e-9)


def test_reemission_invariance_and_conditional_bound():
    for a, delta in [(np.array([1., 1e4]), .01), (np.array([1e5, 1e6]), .01),
                     (np.array([1e-9, 1e9]), 1e-10)]:
        original = select_factor(a, delta)
        for q in [1e-7, .3, 17., 1e7]:
            changed = select_factor(q*a, q*delta)
            assert (original.factor is None) == (changed.factor is None)
            if original.factor is not None:
                assert np.allclose(original.factor*a, changed.factor*q*a, rtol=1e-12)
                assert 1e-6/original.factor <= delta*(1+1e-12)


def test_empty_interval_has_two_distinct_causes():
    spread = select_factor([1e-12, 1e12], 1., coefficient_floor=1e-6, coefficient_ceiling=1e6)
    budget = select_factor([1e6], 1e-12, coefficient_ceiling=1e3)
    assert spread.reason == budget.reason == 'empty_interval'


def test_integer_rounding_can_exhaust_budget_before_row_scaling():
    rejected = select_factor([1e6, 2e6], .01, rounding_allowance=3.)
    assert rejected.factor is None
    assert rejected.reason == 'rounding_budget_exhausted'
    accepted = select_factor([1e6, 2e6], .01, rounding_allowance=.003)
    assert 1e-6/accepted.factor + .003 <= .01*(1+1e-12)


def test_binary64_boundary_contract_is_checked_exactly():
    a, delta = [5.553463723932229], 8.064351077921271e-8
    d = select_factor(a, delta)
    assert Fraction.from_float(d.factor)*Fraction.from_float(delta) >= Fraction.from_float(1e-6)
    # The sole real factor 0.3/3 has no exact binary64 representation.
    singleton = select_factor([3.], 1., coefficient_floor=.3, coefficient_ceiling=.3)
    assert singleton.factor is None
    assert singleton.reason == 'no_binary64_factor'
    tiny = select_factor([5e-324], 1e-6, rounding_allowance=1e-6)
    assert tiny.factor is None
    assert dyadic_factor([5e-324], 0., 1e-6, rounding_allowance=1e-6).factor is None


def test_exact_dyadic_export_with_subnormal_and_large_rhs():
    for a, b, delta in [([1e6, 3e6], 1e7-.1, .01), ([5e-324, 1e-320], 1e-310, 1.),
                        ([1e200, 1e190], 1e250, .1)]:
        d = dyadic_factor(a, b, delta)
        if d.factor is not None:
            for v in [*a,b]:
                assert Fraction.from_float(d.factor*v) == Fraction.from_float(d.factor)*Fraction.from_float(v)
            assert Fraction.from_float(d.factor)*Fraction.from_float(delta) >= Fraction.from_float(1e-6)


def test_dyadic_optimum_against_enumeration():
    a = np.array([3., 71.])
    d = dyadic_factor(a, 13.1, .01)
    feasible = []
    for k in range(-40,40):
        f = 2.**k
        if min(abs(a*f)) >= 1e-9 and max(abs(a*f)) <= 1e9 and f*.01 >= 1e-6:
            feasible.append(max(abs(np.log(a*f))))
    assert np.isclose(max(abs(np.log(a*d.factor))), min(feasible))


def test_dyadic_near_midpoint_and_true_tie_use_exact_objective():
    # Floating log2 values cancel to a target of 0.5, although the exact
    # product of these represented coefficients is strictly greater than 1/2.
    # Thus factor 1 strictly beats factor 2; this is not a genuine objective tie.
    lo, hi = 1e-100, 5e99
    assert Fraction(lo)*Fraction(hi) > Fraction(1, 2)
    d = dyadic_factor([lo, hi], 0., coefficient_floor=1e-300,
                      coefficient_ceiling=1e300)
    assert d.factor == 1.
    # A genuine midpoint uses the declared larger-factor tie convention.
    tied = dyadic_factor([.5, 1.], 0.)
    assert tied.factor == 2.


def test_exact_checker_detects_cancelled_float_residual():
    a = [1e16, 1., -1e16]
    assert float(np.array(a) @ np.ones(3)) == 0.
    assert exact_row_violation(a, 0., [1., 1., 1.]) == Fraction(1)
    assert exact_row_violation([2.], 1., [1.], '=') == Fraction(1)


@pytest.mark.parametrize('a,delta', [([0., 0.], .01), ([np.nan], .01), ([1.], 0.)])
def test_invalid_contract_is_not_silently_accepted(a, delta):
    with pytest.raises(ValueError):
        select_factor(a, delta)
