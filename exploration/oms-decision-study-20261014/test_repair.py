from fractions import Fraction
import math

from repair import exact_check,delivery_check,fixed_subproblem,unary_delivery_obstructions,plain


def unary(budget):
    return {'variables':[{'name':'x','cost':0.,'lower':0.,'upper':1.,'integer':False,'bound_budget':1e-6}],
            'rows':[{'name':'third','terms':{'0':3.},'sense':'=','rhs':1.,'budget':budget,'unit':'test units'}]}


def test_exact_witness_is_not_automatically_valid_binary64_delivery():
    m=unary(2.**-55)
    assert exact_check(m,[Fraction(1,3)])['exact_feasible']
    assert not delivery_check(m,[Fraction(1,3)])[0]['primal_accepted']
    c=unary_delivery_obstructions(m,fixed_subproblem(m,[1/3]))
    assert len(c)==1 and Fraction(c[0]['minimum_binary64_residual'])==Fraction(1,2**54)


def test_unary_representability_threshold_is_inclusive():
    m=unary(2.**-54)
    assert delivery_check(m,[Fraction(1,3)])[0]['primal_accepted']
    assert unary_delivery_obstructions(m,fixed_subproblem(m,[1/3]))==[]


def test_integer_only_contradiction_is_detected_before_lp():
    m={'variables':[{'cost':0.,'lower':0.,'upper':1.,'integer':True,'bound_budget':1e-6}],
       'rows':[{'terms':{'0':1.},'sense':'=','rhs':1.,'budget':1e-6,'unit':'test'}]}
    f=fixed_subproblem(m,[.000001])
    assert f['failure']=='fixed_integer_contradicts_constant_row'


def test_fractional_integer_bounds_are_not_relaxed_during_repair():
    m={'variables':[{'cost':0.,'lower':1e-9,'upper':1.,'integer':True,'bound_budget':1e-6}], 'rows':[]}
    assert fixed_subproblem(m,[0.])['failure']=='fixed_integer_outside_exact_domain'


def test_plain_binary64_decimal_round_trips_exactly_without_exponents():
    for v in (1e-20,-.3,1e17,math.nextafter(1.,2.)):
        q=Fraction.from_float(v);s=plain(q)
        assert 'e' not in s.lower() and Fraction(s)==q
