from fractions import Fraction as Q
from metrics import refuted,supported,start_loaded,root_line
from study import start_check


def test_lower_bound_and_conditional_cost_are_distinct():
    assert refuted(3.,Q(2))
    assert not refuted(2.+1e-8,Q(2))
    assert not supported(0.,Q(10))
    assert supported(12.,Q(10))


def test_start_rejection_is_not_acceptance():
    assert not start_loaded('User MIP start did not produce a new incumbent solution')
    assert start_loaded('Loaded user MIP start with objective -123')


def test_root_parser_keeps_only_printed_precision():
    line='Root relaxation: objective -1.234567e+06, 52 iterations, 0.02 seconds (0.03 work units)'
    assert root_line(line)==dict(objective=-1234567.,iterations=52,seconds=.02,work=.03)
    assert root_line('Presolve: All rows and columns removed') is None


def test_start_original_and_exported_residual_separated():
    d=dict(constant=0.,variables=[dict(obj=1.,type='B',lb=0.,ub=1.)],
           rows=[dict(rhs=0.,sense='<',terms=[[0,8.]])])
    r=start_check(d,[.25],[-3])
    assert Q(r['max_raw_residual_exact'])==2
    assert Q(r['max_exported_residual_exact'])==Q(1,4)
    assert not r['integers_exact']
