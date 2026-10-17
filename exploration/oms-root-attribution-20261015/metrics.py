"""Declared comparison rules; numerical completion never certifies MILP bounds."""
from fractions import Fraction as Q
import math
import re


def tolerance(x):return max(Q(1e-6),Q(8*math.ulp(float(x))))
def refuted(bound,reference):return bound is not None and Q(bound)>Q(reference)+tolerance(reference)
def supported(nominal,exact_minimum):return nominal is not None and Q(nominal)+tolerance(exact_minimum)>=Q(exact_minimum)
def root_line(log):
    match=re.search(r'Root relaxation: objective ([^,]+), ([0-9]+) iterations, ([0-9.]+) seconds \(([0-9.]+) work units\)',log)
    return None if match is None else dict(objective=float(match[1]),iterations=int(match[2]),seconds=float(match[3]),work=float(match[4]))


def start_loaded(log):return 'Loaded user MIP start with objective' in log
