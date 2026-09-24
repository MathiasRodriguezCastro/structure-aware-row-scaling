"""Row equilibration subject to an explicit, conditional residual contract.

This module selects positive ROW factors only. It does not assert that a solver
enforces its tolerance on the exported rows. A returned solution still needs an
independent original-data check. Empty intervals are reported, never silently
replaced by a factor that purports to meet the requested contract.
"""
from dataclasses import dataclass
import math
from fractions import Fraction

import numpy as np


@dataclass(frozen=True)
class RowDecision:
    factor: float | None
    lower: float
    upper: float
    unconstrained: float
    reason: str


def select_factor(coefficients, delta, epsilon=1e-6, coefficient_floor=1e-9,
                  coefficient_ceiling=1e9, kernel="gm", rounding_allowance=0.):
    """Minimize max_j |log(alpha*abs(a_j))| over the feasible interval.

    For kernel='l2', project the L2 candidate onto the same interval instead;
    only 'gm' has the logarithmic minimax characterization. Nonzero finite rows
    and positive finite budgets/windows are required. RHS is multiplied on
    export but is not part of the coefficient objective or window.
    """
    a = np.asarray(coefficients, dtype=float)
    if a.ndim != 1 or not np.all(np.isfinite(a)):
        raise ValueError("coefficients must be a finite one-dimensional row")
    params = [delta, epsilon, coefficient_floor, coefficient_ceiling]
    if not all(math.isfinite(v) and v > 0 for v in params):
        raise ValueError("budgets, tolerance and coefficient limits must be positive and finite")
    if coefficient_floor > coefficient_ceiling:
        raise ValueError("empty coefficient window")
    if not math.isfinite(rounding_allowance) or rounding_allowance < 0:
        raise ValueError("rounding allowance must be finite and nonnegative")
    if kernel not in {"gm", "l2"}:
        raise ValueError("kernel must be gm or l2")
    nz = np.abs(a[a != 0])
    if not nz.size:
        raise ValueError("constant rows must be checked separately")
    lo_a, hi_a = float(nz.min()), float(nz.max())
    def representable_exp(x):
        try:
            return math.exp(x)
        except OverflowError:
            return math.inf
    unconstrained = representable_exp(-.5*(math.log(lo_a)+math.log(hi_a)))
    if rounding_allowance >= delta:
        return RowDecision(None, math.inf, coefficient_ceiling/hi_a,
                           unconstrained,
                           "rounding_budget_exhausted")
    # Build exact endpoints for the supplied binary64 data, then round inwards.
    # Logarithms alone can place a factor just outside a closed interval.
    f = lambda v: Fraction.from_float(float(v))
    remaining = f(delta)-f(rounding_allowance)
    exact_lower = max(f(epsilon)/remaining, f(coefficient_floor)/f(lo_a))
    exact_upper = f(coefficient_ceiling)/f(hi_a)
    def inward_float(value, lower):
        try:
            result = float(value)
        except OverflowError:
            return math.inf if lower else np.finfo(float).max
        if lower and f(result) < value:
            result = math.nextafter(result, math.inf)
        elif not lower and f(result) > value:
            result = math.nextafter(result, 0.)
        return result
    lower, upper = inward_float(exact_lower, True), inward_float(exact_upper, False)
    if exact_lower > exact_upper:
        return RowDecision(None, lower, upper, unconstrained, "empty_interval")
    if not math.isfinite(lower) or lower > upper or upper <= 0:
        return RowDecision(None, lower, upper, unconstrained, "no_binary64_factor")
    if kernel == "gm":
        target = -0.5*(math.log(lo_a)+math.log(hi_a))
    else:
        target = -math.log(hi_a)-math.log(float(np.linalg.norm(nz/hi_a)))
    unconstrained = representable_exp(target)
    value = min(max(unconstrained, lower), upper)
    if not math.isfinite(value) or value <= 0:
        return RowDecision(None, lower, upper, unconstrained, "unrepresentable_factor")
    return RowDecision(value, lower, upper, unconstrained,
                       "projected" if unconstrained < lower or unconstrained > upper else "unconstrained")


def exact_row_violation(a, b, x, sense="<="):
    """Exact rational residual of the supplied binary64 data and solution.

    This certifies a primal row residual for these stored numbers, not the
    intended pre-rounding physical data and not MIP optimality.
    """
    if len(a) != len(x):
        raise ValueError("row and solution dimensions differ")
    activity = sum((Fraction.from_float(float(c))*Fraction.from_float(float(v))
                    for c, v in zip(a, x)), Fraction(0))
    residual = activity-Fraction.from_float(float(b))
    if sense == "<=":
        return max(Fraction(0), residual)
    if sense == ">=":
        return max(Fraction(0), -residual)
    if sense == "=":
        return abs(residual)
    raise ValueError("unsupported row sense")
