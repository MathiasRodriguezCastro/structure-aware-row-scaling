"""Research activity reformulation, exact dyadic selection; no solver import.

SOS/indicator reformulations and slack scaling are established techniques.
This candidate chooses activity units from an explicit rounded-point budget.
"""
from fractions import Fraction
import math

F = Fraction.from_float
EPS, GAMMA, TAU = F(1e-6), F(1e-9), F(1e-6)
LOW, HIGH, CAP = F(1e-9), F(1e9), F(1e19)


def power(k):
    return Fraction(2**k) if k >= 0 else Fraction(1, 2**(-k))


def floorlog(q):
    if q <= 0:
        raise ValueError("positive rational required")
    k = q.numerator.bit_length() - q.denominator.bit_length()
    return k - int(power(k) > q)


def ceillog(q):
    k = floorlog(q)
    return k + int(power(k) < q)


def exact_float(q):
    try:
        x = float(q)
    except OverflowError:
        return None
    return x if math.isfinite(x) and F(x) == q else None


def row_scale(terms, rhs=0., delta=None, reserve=Fraction(0)):
    a = [abs(F(float(x))) for x in terms if x]
    if not a:
        raise ValueError("nonconstant row required")
    low, high = ceillog(LOW / min(a)), floorlog(HIGH / max(a))
    if delta is not None:
        rest = delta - reserve
        if rest <= 0:
            return None
        low = max(low, ceillog(EPS / rest))
    for x in [*terms, rhs]:
        if not x:
            continue
        n, d = abs(float(x)).as_integer_ratio()
        trailing = (n & -n).bit_length() - 1
        low = max(low, -1074 - (trailing - (d.bit_length() - 1)))
        high = min(high, 1023 - (n.bit_length() - d.bit_length()))
    low, high = max(-1074, low), min(1023, high)
    if low > high:
        return None
    norm2 = sum((x*x for x in a), Fraction(0))
    middle = (-floorlog(norm2)) // 2
    candidates = {min(high, max(low, u)) for u in range(middle-1, middle+2)}
    def objective(u):
        q = norm2 * power(2*u)
        return max(q, 1/q), -u
    u = min(candidates, key=objective)
    alpha = math.ldexp(1., u)
    assert all(exact_float(F(float(x))*F(alpha)) is not None for x in [*terms, rhs])
    return alpha


def select_activity(terms, M, delta):
    """Largest admissible h, then nearest admissible dyadic L2 row factor."""
    M = F(float(M)); delta = F(float(delta))
    first = min(1023, floorlog(delta / max(GAMMA, TAU)))
    # A finite backend cap is a necessary lower bound on h.
    last = max(-1074, ceillog(M / CAP))
    for v in range(first, last-1, -1):
        h = power(v)
        bound = exact_float(M / h)
        if bound is None or bound > float(CAP):
            continue
        alpha = row_scale([*terms, -float(h)], delta=delta,
                          reserve=h*max(GAMMA, TAU))
        if alpha is None:
            continue
        guarantee = EPS / F(alpha) + h*max(GAMMA, TAU)
        assert guarantee <= delta
        return {"h": float(h), "alpha": alpha, "auxiliary_upper": bound,
                "rounded_residual_bound": str(guarantee), "budget": str(delta),
                "h_exponent": v}
    return None
