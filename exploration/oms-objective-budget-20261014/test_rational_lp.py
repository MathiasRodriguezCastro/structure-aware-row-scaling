from fractions import Fraction
from rational_lp import verify,verify_ray
from build_lp import build,plain


def test_exact_fractional_optimum_and_sign():
    lp={'cost':['1'],'offset':'5','rows':[{'terms':{'0':'-3'},'rhs':'-1'}]}
    assert verify(lp,['1/3'],{'0':'-1/3'})['optimum_certified']
    assert not verify(lp,['0'],{'0':'-1/3'})['primal_feasible']
    assert not verify(lp,['1/3'],{'0':'1/3'})['dual_feasible']


def test_free_variable_stationarity_required():
    lp={'cost':['1'],'offset':'0','rows':[]}
    assert not verify(lp,['0'],{})['dual_feasible']


def test_farkas_proof_and_nonzero_combination_rejected():
    lp={'cost':['0'],'offset':'0','rows':[{'terms':{'0':'1'},'rhs':'0'},{'terms':{'0':'-1'},'rhs':'-1'}]}
    assert verify_ray(lp,{'0':'-1','1':'-1'})['infeasibility_certified']
    assert not verify_ray(lp,{'1':'-1'})['infeasibility_certified']
    lp['rows'][1]['rhs']='0'
    assert not verify_ray(lp,{'0':'-1','1':'-1'})['infeasibility_certified']


def test_relaxation_both_equality_sides_and_only_continuous_bounds():
    m={'variables':[{'integer':True,'cost':2.,'lower':0.,'upper':1.,'bound_budget':.25},
                    {'integer':False,'cost':1.,'lower':0.,'upper':2.,'bound_budget':.125}],
       'rows':[{'terms':{'0':-1.,'1':1.},'sense':'=','rhs':0.,'budget':.5}]}
    lp=build(m,{'0':1},'cost',Fraction(1,2))
    assert len(lp['rows'])==4 and lp['offset']=='2'
    assert verify(lp,['3/4'],{'1':'-1'})['optimum_certified']
    t=build(m,{'0':1},'feasibility-threshold')
    assert verify(t,['1','0'],{'4':'-1'})['optimum_certified']
    assert not verify(t,['1','2'],{})['primal_feasible']
    assert plain(Fraction(1,2**80)) and Fraction(plain(Fraction(1,2**80)))==Fraction(1,2**80)
