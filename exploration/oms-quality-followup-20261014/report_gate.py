"""Check compatibility of completed reports with the requested numerical gap.

One-sided rejection of a report, never certification of global optimality.
For replay the incumbent objective is recomputed from the saved binary64 point.
"""
from fractions import Fraction
import math

F=Fraction.from_float


def gap_screen(completed,incumbent,bound,relative=.01,absolute=1e-10):
    result={'report_gap_inconsistent':False,'optimality_status':'unverified'}
    if not completed or incumbent is None or bound is None or not all(math.isfinite(float(x)) for x in (incumbent,bound)):
        return result
    c,b=F(float(incumbent)),F(float(bound))
    gap=abs(c-b);allowed=max(F(float(relative))*abs(c),F(float(absolute)))
    guard=max(F(1e-6),8*F(math.ulp(float(incumbent))),8*F(math.ulp(float(bound))))
    result.update(report_gap_inconsistent=gap>allowed+guard,gap_exact=str(gap),allowed_exact=str(allowed),guard_exact=str(guard))
    return result
