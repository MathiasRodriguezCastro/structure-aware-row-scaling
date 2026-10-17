from fractions import Fraction
from policy import choose


def test_zero_understatement_repaired_and_infeasible_pattern_abstained():
    assert choose(0,37251,repair_accepted=True,repair_nominal=37251)['action']=='repair'
    assert choose(0,infeasible=True)['reason']=='fixed_pattern_infeasible'


def test_one_sided_protection_and_unknown_witness():
    assert choose(Fraction(199,2),100)['action']=='accept_nominal'
    assert choose(150,100)['action']=='accept_nominal'  # This is not a quality-gap bound.
    assert choose(0)['reason']=='no_exact_continuation_witness'
    assert choose(0,100,repair_accepted=True,repair_nominal=0)['action']=='abstain'
