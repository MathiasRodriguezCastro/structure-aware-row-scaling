"""Exact fixed-pattern LP dual certificate and one-sided budget effect.

No solver or experimental module is imported. All arithmetic uses the original
canonical binary64 model. A pattern lower bound is NEVER a global MIP lower bound.
"""
from fractions import Fraction
import math

F=Fraction.from_float


def verify(model,delivered,primal,dual):
    n=len(model['variables']);assert len(delivered)==len(primal)==n
    y=[F(float(x)) for x in delivered];q=[Fraction(x) for x in primal]
    fixed={i:y[i] for i,v in enumerate(model['variables']) if v['integer']}
    assert all(z.denominator==1 for z in fixed.values())
    pi={int(i):Fraction(v) for i,v in dual.items()};assert all(0<=i<len(model['rows']) for i in pi)
    reduced={i:F(float(v['cost'])) for i,v in enumerate(model['variables']) if not v['integer']}
    constant=sum((F(float(model['variables'][i]['cost']))*z for i,z in fixed.items()),Fraction(0))
    lower=constant;delta=Fraction(0);primal_ok=True;numeric_ok=True
    for j,row in enumerate(model['rows']):
        p=pi.get(j,Fraction(0));sense=row['sense']
        if sense=='<' and p>0 or sense=='>' and p<0:
            return {'dual_feasible':False,'reason':'wrong_multiplier_sign','row':j}
        b=F(float(row['rhs']))-sum((F(float(c))*fixed[int(i)] for i,c in row['terms'].items() if int(i) in fixed),Fraction(0))
        lower+=p*b;delta+=abs(p)*F(float(row['budget']))
        for i,c in row['terms'].items():
            if int(i) in reduced:reduced[int(i)]-=p*F(float(c))
        for values,exact in ((q,True),(y,False)):
            difference=sum((F(float(c))*values[int(i)] for i,c in row['terms'].items()),Fraction(0))-F(float(row['rhs']))
            violation=abs(difference) if sense=='=' else max(Fraction(0),difference if sense=='<' else -difference)
            if exact and violation:primal_ok=False
            if not exact and violation>F(float(row['budget'])):numeric_ok=False
    for i,v in enumerate(model['variables']):
        if v['integer'] and (q[i].denominator!=1 or q[i]!=fixed[i]):primal_ok=False
        lo=F(float(v['lower'])) if v['lower'] is not None else None
        hi=F(float(v['upper'])) if v['upper'] is not None else None
        if lo is not None and q[i]<lo or hi is not None and q[i]>hi:primal_ok=False
        if v['integer']:
            if lo is not None and y[i]<lo or hi is not None and y[i]>hi:numeric_ok=False
        else:
            beta=F(float(v['bound_budget']))
            if lo is not None and y[i]<lo-beta or hi is not None and y[i]>hi+beta:numeric_ok=False
            rc=reduced[i];bound=lo if rc>0 else hi if rc<0 else Fraction(0)
            if rc and bound is None:return {'dual_feasible':False,'reason':'nonzero_reduced_cost_toward_unbounded_endpoint','variable':i}
            lower+=rc*bound;delta+=abs(rc)*beta
    numeric_cost=sum((F(float(v['cost']))*x for v,x in zip(model['variables'],y)),Fraction(0))
    primal_cost=sum((F(float(v['cost']))*x for v,x in zip(model['variables'],q)),Fraction(0))
    if numeric_ok:assert numeric_cost>=lower-delta
    if primal_ok:assert primal_cost>=lower
    threshold=max(F(1e-6),F(.01)*abs(lower),8*F(math.ulp(float(lower))))
    return {'dual_feasible':True,'primal_exact_feasible_for_same_pattern':primal_ok,
            'pattern_optimum_certified':primal_ok and primal_cost==lower,
            'numeric_point_meets_original_budgets':numeric_ok,
            'numeric_objective_exact':str(numeric_cost),'numeric_objective':float(numeric_cost),
            'pattern_lower_bound_exact':str(lower),'pattern_lower_bound':float(lower),
            'primal_objective_exact':str(primal_cost),'primal_objective':float(primal_cost),
            'weighted_budget_effect_exact':str(delta),'weighted_budget_effect':float(delta),
            'understatement_exact':str(lower-numeric_cost),'understatement':float(lower-numeric_cost),
            'understatement_exceeds_one_percent':lower-numeric_cost>threshold,
            'budget_inequality_verified':numeric_ok and numeric_cost>=lower-delta,
            'global_mip_lower_bound_or_optimality_certified':False,
            'scope':'fixed integer pattern only; original canonical binary64 model'}
