"""Exact finite geometry for small binary-block acceptance contracts.

The finite rays are vertices of a classical hyperplane arrangement / zonotope
normal fan restricted to the nonnegative orthant. They are not a new polyhedral
construction. Their use here gives exact acceptance radii without an optimizer.
All row data, endpoints and tolerances are interpreted as stored-data rationals.
"""
from fractions import Fraction as F
from itertools import combinations, product

from joint_rounding_certificate import rational, row_gap


def _unique_solution(matrix, rhs):
    """Exact square-system elimination; return None for singular systems."""
    n = len(rhs)
    aug = [list(map(rational, row)) + [rational(v)] for row, v in zip(matrix, rhs)]
    for k in range(n):
        pivot = next((i for i in range(k, n) if aug[i][k]), None)
        if pivot is None:
            return None
        aug[k], aug[pivot] = aug[pivot], aug[k]
        scale = aug[k][k]
        aug[k] = [v / scale for v in aug[k]]
        for i in range(n):
            if i == k or not aug[i][k]:
                continue
            scale = aug[i][k]
            aug[i] = [a - scale * b for a, b in zip(aug[i], aug[k])]
    return tuple(row[-1] for row in aug)


def complete_multipliers(A):
    """Enumerate every required nonnegative ray, normalized by sum(lambda)=1.

    For a support of size s, a vertex requires s-1 independent column
    cancellations. Zero/duplicate columns and rank deficiencies are harmless.
    At most binom(n+m,m-1) systems are considered. Enumeration remains
    exponential in the row count; this is a small-block algorithm.
    """
    A = [list(map(rational, row)) for row in A]
    if not A or not A[0] or any(len(row) != len(A[0]) for row in A):
        raise ValueError('A must be a nonempty rectangular matrix')
    m, n = len(A), len(A[0])
    candidates = set()
    for s in range(1, min(m, n + 1) + 1):
        for support in combinations(range(m), s):
            for columns in combinations(range(n), s - 1):
                matrix = [[F(1)] * s] + [[A[i][j] for i in support] for j in columns]
                value = _unique_solution(matrix, [F(1)] + [F(0)] * (s - 1))
                if value is None or any(v < 0 for v in value):
                    continue
                lam = [F(0)] * m
                for i, v in zip(support, value):
                    lam[i] = v
                candidates.add(tuple(lam))
    return sorted(candidates)


def acceptance_radius(A, b, eta, weights=None, bound_tolerance=0):
    """Return exact R: the contract A x <= b + s*w is safe iff 0<=s<R.

    R = min over bad centers z of max over finite rays lambda of
        [lambda*(Az-b) - support_Ez(-A^T lambda)] / (lambda*w).
    This equals min_z min_{x in C_z} max_r (a_r*x-b_r)/w_r.
    R<=0 identifies a collision with the zero-residual relaxation. With exact
    bounds it is the intrinsic row-scaling obstruction. R=None means all binary
    centers are feasible, so every nonnegative s is safe. This routine enumerates
    every binary center; the finite row geometry does not remove that cost.
    """
    A = [list(map(rational, row)) for row in A]
    b = list(map(rational, b))
    m = len(A)
    eta, tau = rational(eta), rational(bound_tolerance)
    w = [F(1)] * m if weights is None else list(map(rational, weights))
    if len(b) != m or len(w) != m or any(v <= 0 for v in w):
        raise ValueError('one RHS and strictly positive weight per row required')
    if not 0 <= eta < F(1, 2) or tau < 0:
        raise ValueError('invalid rounding or bound tolerance')
    rays = complete_multipliers(A)
    cells = []
    for z in product([0, 1], repeat=len(A[0])):
        if all(sum((a * v for a, v in zip(row, z)), F(0)) <= rhs
               for row, rhs in zip(A, b)):
            continue
        choices = []
        for lam in rays:
            gap = row_gap(A, b, z, lam, eta, tau)
            weight = sum((v * wr for v, wr in zip(lam, w)), F(0))
            choices.append((gap / weight, lam, gap, weight))
        radius, lam, gap, weight = max(choices)
        cells.append(dict(z=z, radius=str(radius), lambda_=list(map(str, lam)),
                          gap=str(gap), weight=str(weight)))
    radius = min((F(cell['radius']) for cell in cells), default=None)
    return dict(radius=None if radius is None else str(radius), cells=cells,
                multiplier_count=len(rays), eta=str(eta), bound_tolerance=str(tau),
                weights=list(map(str, w)), complete=True)
