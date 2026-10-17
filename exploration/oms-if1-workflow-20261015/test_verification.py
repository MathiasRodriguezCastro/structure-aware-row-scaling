"""Meaningful endpoint checks for the separate rational verifier."""
from fractions import Fraction as Q
import math
from independent_check import flags, violation


def test_rounding_changes_activation_interpretation():
    row={'terms':{'b':1e10,'v':1.},'rhs':0.,'sense':'<='}
    raw={'b':Q(1,10**10),'v':Q(-1)}
    rounded={'b':Q(0),'v':Q(-1)}
    assert violation(row,raw)==0 and violation(row,rounded)==0
    row={'terms':{'b':1e10,'v':-1.},'rhs':1e10-100.,'sense':'<='}
    raw={'b':Q(9999999999,10**10),'v':Q(99)}
    assert violation(row,raw)==0
    assert violation(row,{'b':Q(1),'v':Q(99)})==1


def test_exact_cancellation_preserves_unit_violation():
    row={'terms':{'x':1e16,'y':1.,'z':-1e16},'rhs':0.,'sense':'='}
    assert violation(row,{'x':Q(1),'y':Q(1),'z':Q(1)})==1


def test_bound_refutation_does_not_require_optimal_witness():
    assert flags(-50.,-50.,True,Q(-100))==(True,True)
    assert flags(-101.,-50.,True,Q(-100))==(False,True)
    assert flags(-101.,-50.,False,Q(-100))==(False,False)


def test_presentation_margin_and_negative_objective_gap():
    assert flags(math.nextafter(-100.,math.inf),-100.,True,Q(-100))==(False,False)
    assert flags(None,-100.,True,Q(-101))==(False,False)
    assert flags(None,-100.,True,Q(-10101,100))==(False,True)
