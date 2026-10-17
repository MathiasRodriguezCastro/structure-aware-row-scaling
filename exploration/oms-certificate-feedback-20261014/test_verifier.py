import copy
import math
from pathlib import Path
import sys
import pytest
from cuts import project,export
from verify_cuts import check
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'oms-objective-budget-20261014'))
from build_lp import build


def fixture():
    model={'variables':[{'integer':True,'cost':0.,'lower':0.,'upper':1.,'bound_budget':0.},
                        {'integer':False,'cost':1.,'lower':0.,'upper':None,'bound_budget':0.}],
           'rows':[{'terms':{'0':2.,'1':-1.},'sense':'<','rhs':0.,'budget':0.}]}
    z={'0':1};lp=build(model,z,'cost');mu={'0':'-1'};_,cut=project(model,lp,mu,'cost',z);e=export(model,cut)
    return model,lp,z,mu,cut,e


def test_independent_checker_rejects_false_floor_or_export_strengthening():
    m,lp,z,mu,c,e=fixture();assert check(m,lp,z,mu,'cost',c,e)['globally_valid_for_original_mip']
    wrong=copy.deepcopy(c);wrong['rhs']='1'
    with pytest.raises(AssertionError):check(m,lp,z,mu,'cost',wrong,e)
    wrong=copy.deepcopy(e);wrong['rhs']=math.nextafter(wrong['rhs'],math.inf)
    with pytest.raises(AssertionError):check(m,lp,z,mu,'cost',c,wrong)


def test_source_rhs_and_dual_sign_are_checked_independently():
    m,lp,z,mu,c,e=fixture();wrong=copy.deepcopy(lp);wrong['rows'][0]['rhs']='-3'
    with pytest.raises(AssertionError):check(m,wrong,z,mu,'cost',c,e)
    with pytest.raises(AssertionError):check(m,lp,z,{'0':'1'},'cost',c,e)
