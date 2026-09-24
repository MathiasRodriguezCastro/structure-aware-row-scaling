"""Exact intrinsic safety of one binary inequality, with an optional work cap.

After complementing negative columns, an unsafe cell is an interval subset sum.
For fixed positive eta, only O(1/eta) large items need to be enumerated. This is
a theoretical polynomial-time bound with an impractically high degree for usual
solver tolerances. The interval-subset-sum machinery is classical, not a new
general knapsack algorithm. A work cap returns UNKNOWN, never an unproved SAFE.
"""
from fractions import Fraction as F
from itertools import combinations

from joint_rounding_certificate import rational


def intrinsic_single_row(a, b, eta, max_subsets=None):
    a = list(map(rational, a))
    b, eta = rational(b), rational(eta)
    if not 0 <= eta < F(1, 2):
        raise ValueError('require 0 <= eta < 1/2')
    weights = list(map(abs, a))
    B = b - sum((v for v in a if v < 0), F(0))
    if eta == 0 or B <= 0 or B >= sum(weights):
        # B<0: relaxation empty. B=0: only zero-weight coordinates can vary.
        return dict(status='SAFE', examined_subsets=0, witness=None)
    U = B / (1 - eta)
    width = U - B
    large = [j for j, w in enumerate(weights) if width < w <= U]
    small = [j for j, w in enumerate(weights) if 0 < w <= width]
    small_sum = sum((weights[j] for j in small), F(0))
    inverse = 1 / eta
    # k<1/eta, because each large weight is strictly greater than width.
    max_large = min(len(large), (inverse.numerator-1)//inverse.denominator)
    examined = 0
    for size in range(max_large + 1):
        for subset in combinations(large, size):
            if max_subsets is not None and examined >= max_subsets:
                return dict(status='UNKNOWN', examined_subsets=examined, witness=None)
            examined += 1
            S = sum((weights[j] for j in subset), F(0))
            if S > U or S + small_sum <= B:
                continue
            chosen = list(subset)
            if S <= B:
                for j in small:
                    chosen.append(j)
                    S += weights[j]
                    if S > B:
                        break
            assert B < S <= U
            z = [int(j in chosen) for j in range(len(a))]
            x = [(1-eta)*v for v in z]
            for j, coefficient in enumerate(a):
                if coefficient < 0:
                    z[j] = 1-z[j]
                    x[j] = 1-x[j]
            assert sum((v*u for v, u in zip(a, x)), F(0)) <= b
            assert sum((v*u for v, u in zip(a, z)), F(0)) > b
            return dict(status='UNSAFE', examined_subsets=examined,
                        witness=dict(z=z, x=list(map(str, x))))
    return dict(status='SAFE', examined_subsets=examined, witness=None)
