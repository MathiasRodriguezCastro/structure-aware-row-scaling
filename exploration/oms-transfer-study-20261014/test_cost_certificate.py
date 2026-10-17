from fractions import Fraction
from cost_certificate import verify


def test_fixed_pattern_cost_and_budget_effect_not_global_bound():
    m={'variables':[{'integer':True,'cost':5.,'lower':0.,'upper':1.,'bound_budget':0.},
                    {'integer':False,'cost':2.,'lower':0.,'upper':None,'bound_budget':0.}],
       'rows':[{'terms':{'0':-3.,'1':1.},'sense':'>','rhs':0.,'budget':.5}]}
    c=verify(m,[1.,2.5],['1','3'],{'0':'2'})
    assert c['pattern_optimum_certified'] and c['pattern_lower_bound']==11.
    assert c['numeric_objective']==10. and c['weighted_budget_effect']==1.
    assert c['budget_inequality_verified'] and not c['global_mip_lower_bound_or_optimality_certified']
    # A different integer pattern has feasible objective zero, below eleven.
    assert not verify(m,[1.,2.5],['0','0'],{'0':'2'})['primal_exact_feasible_for_same_pattern']


def test_negative_reduced_cost_uses_upper_bound():
    m={'variables':[{'integer':False,'cost':-1.,'lower':None,'upper':3.,'bound_budget':.1}], 'rows':[]}
    c=verify(m,[3.05],['3'],{})
    assert c['pattern_optimum_certified'] and c['pattern_lower_bound']==-3.
    assert c['understatement_exceeds_one_percent'] and c['budget_inequality_verified']


def test_wrong_dual_sign_and_free_variable_rejected():
    m={'variables':[{'integer':False,'cost':1.,'lower':0.,'upper':None,'bound_budget':0.}],
       'rows':[{'terms':{'0':1.},'sense':'>','rhs':1.,'budget':0.}]}
    assert not verify(m,[1.],['1'],{'0':'-1'})['dual_feasible']
    m['variables'][0]['lower']=None;m['rows']=[]
    assert not verify(m,[0.],['0'],{})['dual_feasible']


def test_exact_rational_equality_certificate():
    m={'variables':[{'integer':False,'cost':1.,'lower':0.,'upper':1.,'bound_budget':1e-6}],
       'rows':[{'terms':{'0':3.},'sense':'=','rhs':1.,'budget':1e-6}]}
    c=verify(m,[1/3],['1/3'],{'0':'1/3'})
    assert c['pattern_optimum_certified'] and Fraction(c['pattern_lower_bound_exact'])==Fraction(1,3)
    assert c['budget_inequality_verified']
