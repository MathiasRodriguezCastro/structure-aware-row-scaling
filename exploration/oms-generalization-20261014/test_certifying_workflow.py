"""Mathematical support checks and adverse acceptance cases; no solver used."""
from fractions import Fraction
import itertools
import math
import random

from certifying_workflow import decision_loop
from generalization_study import export_support

F=Fraction.from_float


def model():
    return {'variables':[{'cost':0.,'lower':0.,'upper':1.,'integer':True,'bound_budget':1e-6},
                         {'cost':1.,'lower':0.,'upper':2000.,'integer':False,'bound_budget':1e-6}],
            'rows':[{'terms':{'0':1000.,'1':-1.},'sense':'<','rhs':0.,'budget':1e-3,'unit':'kg'}]}


def test_rounding_failure_is_retried_and_returned_point_is_checked():
    points={'normal':[.9995,999.5],'repair':[1.,1000.]}
    result=decision_loop(model(),['normal','repair'],lambda p:{'point':points[p],
        'reported_status':'optimal','import_matches_original_exactly':True})
    assert result['attempts'][0]['state']=='primal_check_failed'
    assert result['selected_policy']=='repair' and result['point']==[1.,1000.]
    assert result['optimality_status']=='unverified'


def test_status_optimal_cannot_override_failed_verification():
    result=decision_loop(model(),['normal'],lambda p:{'point':[.9995,999.5],
        'reported_status':'optimal','import_matches_original_exactly':True})
    assert result['state']=='abstained' and result['point'] is None


def test_fractional_integer_bounds_are_enforced_exactly():
    original=model();original['variables'][0]['lower']=1e-9
    result=decision_loop(original,['near_bound'],lambda p:{'point':[0.,0.],
        'import_matches_original_exactly':True})
    assert result['state']=='abstained'
    assert result['attempts'][0]['state']=='exact_integer_domain_failed'


def test_unchecked_import_and_nonfinite_point_are_never_accepted():
    result=decision_loop(model(),['changed','nan'],lambda p:{'point':[1.,math.nan] if p=='nan' else [1.,1000.],
        'import_matches_original_exactly':p!='changed'})
    assert result['state']=='abstained' and len(result['attempts'])==2


def test_support_matches_exhaustive_box_vertices_for_both_signs():
    rng=random.Random(20261014)
    for _ in range(100):
        n=4;a=[rng.uniform(-100,100) for _ in range(n)];b=rng.uniform(-100,100)
        alpha=rng.uniform(.01,100);ahat=[alpha*c for c in a];bhat=alpha*b
        lower=[rng.uniform(-50,0) for _ in range(n)];upper=[rng.uniform(0,50) for _ in range(n)]
        for sign in (-1,1):
            reference=max(sign*(sum(((F(alpha)*F(c)-F(d))*F(x) for c,d,x in zip(a,ahat,point)),Fraction(0))
                                -(F(alpha)*F(b)-F(bhat)))
                          for point in itertools.product(*zip(lower,upper)))
            assert export_support(a,b,alpha,ahat,bhat,lower,upper,sign)==reference


def test_zero_export_error_requires_no_finite_variable_box():
    assert export_support([3.],2.,.5,[1.5],1.,[None],[None])==0


def test_one_sided_support_uses_only_the_required_endpoint():
    # Positive export error needs an upper bound; its absent lower bound is irrelevant.
    assert export_support([3.],0.,1.,[2.],0.,[None],[7.])==7
    assert export_support([3.],0.,1.,[2.],0.,[0.],[None]) is None
