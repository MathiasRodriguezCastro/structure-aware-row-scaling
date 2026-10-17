from fractions import Fraction as Q
import math
from common import ExactData,exact_feasibility,exponent,choose,pow2,gcd_audit
import exact_lp


def example():
    return dict(sense=1,constant=0.,variables=[dict(name='g(1)',type='C',lb=0.,ub=20.,obj=1.),
        dict(name='a1_varphi41(1)',type='B',lb=0.,ub=1.,obj=3.)],
        rows=[dict(name='gen_menor_demanda(1)',sense='<',rhs=1.,terms=[[0,1.]]),
              dict(name='other',sense='>',rhs=.1,terms=[[0,.01],[1,100.]])])


def test_integer_accumulator_matches_fraction():
    data=example();engine=ExactData(data)
    for x in [[.001,.999999999],[1.,0.],[1.001,1.],[19.,.3]]:
        c=engine.check(x);q=[Q(x[0]),Q(round(x[1]))]
        v=max(Q(0),q[0]-1);assert Q(c['physical_ratios_exact'][0])==v/Q(.01)
        aux=max(Q(0),Q(.1)-(Q(.01)*q[0]+100*q[1]))/(Q(1e-8)*max(Q(1),Q(.1)))
        assert Q(c['max_auxiliary_budget_ratio_exact'])==aux
        assert Q(c['objective_exact'])==q[0]+3*q[1]


def test_products_are_exact_and_projection_preserves_candidate():
    r=dict(name='r',sense='<',rhs=2625516646.,terms=[[0,1.],[1,1.3e10]])
    for kernel in ['gm','l2','ruiz']:
        k=exponent(r,kernel)
        for a in [r['rhs']]+[a for _,a in r['terms']]:assert Q(math.ldexp(a,k))==Q(a)*pow2(k)
        assert exponent(r,kernel,Q(1e100))==k
    assert exponent(r,'l2',Q(-1)) is None


def test_contract_reserves_integer_rounding():
    d=dict(sense=1,constant=0.,variables=[dict(name='a1_v4h(1)',type='C',lb=0.,ub=2e9,obj=0.),
           dict(name='a1_varphi41(1)',type='B',lb=0.,ub=1.,obj=0.)],
           rows=[dict(name='a1_activacion_1(1)',sense='<',rhs=1.2e10,terms=[[0,-1.],[1,1.3e10]])])
    ex,bad=choose(d,'Budget-Demanding');assert not bad
    assert Q(1e-6)/pow2(ex[0])+Q(1e-9)*Q(1.3e10)<=100
    assert gcd_audit(d)['eligible_rows']==0


def test_gcd_primitive_only_alias():
    d=example();d['rows']=[dict(name='order',sense='<',rhs=0.,terms=[[1,1.]])]
    assert gcd_audit(d)['identical_to_base']
    d['rows'][0]['terms'][0][1]=2.
    try:gcd_audit(d)
    except AssertionError:pass
    else:raise AssertionError('a nonprimitive row must not be silently aliased')


def test_exact_lp_certificate_and_full_feasibility():
    lp=dict(cost=['1'],offset='0',rows=[dict(terms={'0':'-1'},rhs='-1')])
    assert exact_lp.verify(lp,['1'],{'0':'-1'})['optimum_certified']
    assert not exact_lp.verify(lp,['0'],{'0':'-1'})['primal_feasible']
    data=example();assert exact_feasibility(data,['1','1'])['exact_feasible']
    assert not exact_feasibility(data,['1.01','1'])['exact_feasible']


def test_exact_decimal_export_roundtrip():
    for v in [0.,.1,-.000710916736527979,1.3e10,1e-9]:assert Q(exact_lp.decimal(Q(v)))==Q(v)
