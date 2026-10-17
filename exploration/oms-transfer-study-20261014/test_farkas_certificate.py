from farkas_certificate import verify


def test_infeasible_pattern_can_meet_numerical_budgets():
    m={'variables':[{'integer':True,'lower':0.,'upper':1.,'bound_budget':0.},
                    {'integer':False,'lower':0.,'upper':None,'bound_budget':0.}],
       'rows':[{'terms':{'1':1.,'0':-1.},'sense':'>','rhs':0.,'budget':1.},
               {'terms':{'1':1.},'sense':'<','rhs':0.,'budget':0.}]}
    c=verify(m,[1.,0.],{'0':'1','1':'-1'})
    assert c['fixed_pattern_infeasible_certified'] and c['numeric_point_meets_budgets']
    assert c['budget_compatibility_verified'] and not c['global_mip_infeasibility_certified']
    assert not verify(m,[0.,0.],{'0':'1','1':'-1'})['fixed_pattern_infeasible_certified']


def test_free_variable_does_not_yield_false_infeasibility():
    m={'variables':[{'integer':False,'lower':None,'upper':None,'bound_budget':0.}],
       'rows':[{'terms':{'0':1.},'sense':'>','rhs':1.,'budget':0.}]}
    assert not verify(m,[1.],{'0':'1'})['fixed_pattern_infeasible_certified']
