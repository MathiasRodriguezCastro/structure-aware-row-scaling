from fractions import Fraction

from controller import accept,best,cost,model_digest,screen_bound


def model(budget=1e-6):
    return {'variables':[{'cost':1.,'lower':0.,'upper':2.,'integer':True,'bound_budget':1e-6}],
            'rows':[{'terms':{'0':1.},'sense':'>','rhs':1.,'budget':budget,'unit':'test'}]}


def test_false_cheap_candidate_cannot_replace_verified_point():
    m=model()
    assert best(m,[('earlier',[1.]),('later',[1e-6])])==('earlier',[1.])


def test_better_verified_point_is_retained_and_import_is_required():
    m=model();assert best(m,[('earlier',[2.]),('later',[1.])])==('later',[1.])
    assert accept(m,[1.],imported=False) is None


def test_fractional_integer_bounds_remain_exact():
    m=model();m['variables'][0]['lower']=1.+1e-8
    assert accept(m,[1.]) is None


def test_wrong_model_or_numerical_only_witness_cannot_veto_bound():
    m=model();w={'point':['1'],'model_digest':'wrong','label':'wrong model'}
    assert not screen_bound(m,2.,w)['eligible_exact_witness']
    w.update(model_digest=model_digest(m),point=['999999/1000000'])
    assert not screen_bound(m,2.,w)['eligible_exact_witness']


def test_uncontradicted_bound_still_has_unverified_optimality():
    m=model();w={'point':['1'],'model_digest':model_digest(m),'label':'exact'}
    assert screen_bound(m,0.,w)['optimality_status']=='unverified'
    assert screen_bound(m,2.,w)['bound_contradicted']


def test_exact_rational_witness_can_veto_without_float_delivery():
    m={'variables':[{'cost':1.,'lower':0.,'upper':1.,'integer':False,'bound_budget':1e-6}],
       'rows':[{'terms':{'0':3.},'sense':'=','rhs':1.,'budget':2.**-55,'unit':'test'}]}
    assert accept(m,[1/3]) is None
    w={'point':['1/3'],'model_digest':model_digest(m),'label':'rational'}
    assert screen_bound(m,1.,w)['bound_contradicted']
