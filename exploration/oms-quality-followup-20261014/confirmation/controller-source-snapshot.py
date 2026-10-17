#!/usr/bin/env python3
"""Accept checked deliveries, retain their best objective, and veto bad bounds."""
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'exploration/oms-decision-study-20261014'))
from repair import delivery_check, exact_check

F = Fraction.from_float


def model_digest(model):
    return hashlib.sha256(json.dumps(model, sort_keys=True).encode()).hexdigest()


def cost(model, point):
    return sum((F(float(v['cost'])) * F(float(x)) for v, x in zip(model['variables'], point)), Fraction(0))


def accept(model, point, imported=True):
    if not imported or point is None or len(point) != len(model['variables']):
        return None
    if not all(math.isfinite(float(x)) for x in point):
        return None
    rounded = [float(round(float(x))) if v['integer'] else float(x) for x, v in zip(point, model['variables'])]
    check, converted = delivery_check(model, rounded)
    return converted if check['primal_accepted'] else None


def best(model, candidates):
    accepted = [(label, p) for label, p in candidates if p is not None and accept(model, p) == list(p)]
    return min(accepted, key=lambda item: cost(model, item[1])) if accepted else (None, None)


def screen_bound(model, bound, witness):
    status = {'optimality_status': 'unverified', 'bound_contradicted': False, 'eligible_exact_witness': False}
    if bound is None or not math.isfinite(float(bound)) or witness is None or witness.get('model_digest') != model_digest(model):
        return status
    check = exact_check(model, witness['point'])
    if not check['exact_feasible']:
        return status
    b, u = F(float(bound)), Fraction(check['objective_exact'])
    guard = max(F(1e-6), 8 * F(math.ulp(float(bound))))
    status.update(eligible_exact_witness=True, exact_feasible_objective=str(u),
                  witness= witness['label'], guard_exact=str(guard),
                  bound_contradicted=b > u + guard)
    return status
