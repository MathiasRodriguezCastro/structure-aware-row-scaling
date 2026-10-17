"""Candidate gate: exact continuation with one-sided cost protection only."""
from fractions import Fraction


def choose(nominal,upper=None,infeasible=False,repair_accepted=False,repair_nominal=None):
    if nominal is None:return {'action':'abstain','reason':'no_numeric_delivery'}
    if infeasible:return {'action':'abstain','reason':'fixed_pattern_infeasible'}
    if upper is None:return {'action':'abstain','reason':'no_exact_continuation_witness'}
    nominal,upper=Fraction(nominal),Fraction(upper)
    epsilon=max(Fraction.from_float(1e-6),abs(upper)/100)
    if upper<=nominal+epsilon:
        return {'action':'accept_nominal','exact_continuation_upper':str(upper),'epsilon':str(epsilon)}
    if repair_accepted and repair_nominal is not None and upper<=Fraction(repair_nominal)+epsilon:
        return {'action':'repair','exact_continuation_upper':str(upper),'epsilon':str(epsilon)}
    return {'action':'abstain','reason':'understatement_without_safe_float_repair'}
