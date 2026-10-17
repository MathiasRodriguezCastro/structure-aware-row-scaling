from fractions import Fraction as F
import math
import study as s


def test_dyadic_products_and_contract_projection():
    a=[.00018,1.,3600.];rhs=2625516646.
    for kernel in ('gm','l2','ruiz'):
        plain=s.exponent(a,rhs,kernel)
        tight=s.exponent(a,rhs,kernel,1e-6)
        assert tight>=plain
        assert math.ldexp(1.,tight)>=1.
        for k in (plain,tight):
            assert all(F(math.ldexp(x,k))==F(x)*s.power(k) for x in a+[rhs])


def test_gm_minimax_and_identity_band():
    a=[1e-7,100.]
    k=s.exponent(a,0.,'gm')
    def objective(j):return max(s.power(j)*F(max(a)),1/(s.power(j)*F(min(a))))
    assert objective(k)<=objective(k-1) and objective(k)<=objective(k+1)
    assert s.exponent([1.,1.],0.,'gm')==0
    assert s.exponent([1.,1.],0.,'l2')==0


def test_empty_contract_is_reported():
    assert s.exponent([1e9],0.,'gm',1e-9) is None


def test_role_and_units_are_distinct():
    assert s.role({'g(1)':1.,'g1(1)':-1.})=='coupling'
    assert s.role({'a1_v4h(1)':1.,'a1_x4h(1)':3600.})=='local'
    assert s.role({'g(1)':1.})=='global'
    assert s.physical_spec('a1_balance(1)',{'a1_v4h(1)':1e-6,'a1_x4h(1)':.0036})==('m3',1e-6)
    assert s.physical_spec('gh_total(1)',{'g(1)':2.,'g1(1)':-2.})==('MW',2.)


def test_fingerprint_ignores_positive_row_scale():
    data=dict(sense=1,constant=0.,variables=[dict(name='x',lb=0.,ub=None,obj=1.,type='C')],
              rows=[dict(name='r',sense='<',rhs=4.,terms=[[0,2.]])])
    other={**data,'rows':[dict(name='r',sense='<',rhs=2.,terms=[[0,1.]])]}
    assert s.fingerprint(data)['normalized_sha256']==s.fingerprint(other)['normalized_sha256']
    other['rows'][0]['rhs']=3.
    assert s.fingerprint(data)['normalized_sha256']!=s.fingerprint(other)['normalized_sha256']


def test_observed_residual_and_conditional_budget_are_distinct():
    d=dict(sense=1,constant=0.,variables=[dict(name='g(1)',lb=0.,ub=None,obj=1.,type='C')],
           rows=[dict(name='gen_menor_demanda(1)',sense='<',rhs=1.,terms=[[0,1.]])])
    check=s.verification(d,[1.001],[-20])
    assert check['max_physical_ratio']['Reference']<1
    assert check['admissible_physical_rows']['Reference']==0
    assert check['max_reconstructed_exported_residual']<1e-6
