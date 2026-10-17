from fractions import Fraction
from cuts import project,export,signature
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'oms-objective-budget-20261014'))
from build_lp import build


def test_partial_cost_floor_covers_an_unseen_binary_completion():
    m={'variables':[{'integer':True,'cost':0.,'lower':0.,'upper':1.,'bound_budget':0.},
                    {'integer':True,'cost':0.,'lower':0.,'upper':1.,'bound_budget':0.},
                    {'integer':False,'cost':1.,'lower':0.,'upper':None,'bound_budget':0.}],
       'rows':[{'terms':{'0':2.,'1':-3.,'2':-1.},'sense':'<','rhs':-3.,'budget':0.}]}
    z={'0':1,'1':1};lp=build(m,z,'cost');aggregate,guard=project(m,lp,{'0':'-1'},'cost',z)
    assert guard['support']==['0'] and guard['partial_floor']=='2'
    # z=(1,0) was not used to produce the certificate; its recourse min is five.
    for x in ([1,1,2],[1,0,5],[0,1,0],[0,0,3]):
        assert sum(Fraction(a)*x[int(i)] for i,a in guard['terms'].items())>=Fraction(guard['rhs'])
    assert aggregate['g_terms']=={'0':'2','1':'-3'}


def test_farkas_conflict_excludes_only_infeasible_assignments():
    m={'variables':[{'integer':True,'cost':0.,'lower':0.,'upper':1.,'bound_budget':0.},
                    {'integer':False,'cost':0.,'lower':0.,'upper':.5,'bound_budget':0.}],
       'rows':[{'terms':{'0':1.,'1':-1.},'sense':'<','rhs':0.,'budget':0.}]}
    lp=build(m,{'0':1},'cost');a,g=project(m,lp,{'0':'-1','2':'-1'},'ray',{'0':1})
    assert g['terms']=={'0':'-1'} and g['rhs']=='0'
    assert Fraction(g['partial_margin'])>0
    assert Fraction(g['terms']['0'])*0>=Fraction(g['rhs'])


def test_export_rounding_is_outward_over_integer_box():
    m={'variables':[{'integer':True,'lower':0.,'upper':1.}, {'integer':False,'lower':0.,'upper':None}]}
    cut={'kind':'partial-cost','terms':{'0':'1/3','1':'1'},'rhs':'1/3'};cut['signature']=signature(cut)[0]
    e=export(m,cut);assert e['exported']
    for x in ((Fraction(0),Fraction(1,3)),(Fraction(1),Fraction(0))):
        assert sum(Fraction.from_float(a)*x[int(i)] for i,a in e['terms'].items())>=Fraction.from_float(e['rhs'])


def test_export_abstains_when_necessary_rounding_endpoint_is_free():
    m={'variables':[{'integer':False,'lower':None,'upper':None}]}
    cut={'kind':'partial-cost','terms':{'0':'1/3'},'rhs':'1'};cut['signature']=signature(cut)[0]
    assert not export(m,cut)['exported']
