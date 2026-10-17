from report_gate import gap_screen


def test_observed_optimal_label_with_large_gap_is_rejected():
    assert gap_screen(True,5.643360547801297,-24.17788230987879)['report_gap_inconsistent']
    assert not gap_screen(False,5.643360547801297,-24.17788230987879)['report_gap_inconsistent']


def test_inclusive_boundary_and_absolute_gap_are_respected():
    assert not gap_screen(True,100.,99.)['report_gap_inconsistent']
    assert not gap_screen(True,0.,5e-11)['report_gap_inconsistent']
    assert gap_screen(True,100.,95.)['report_gap_inconsistent']


def test_consistency_never_certifies_optimality():
    assert gap_screen(True,100.,100.)['optimality_status']=='unverified'
    assert not gap_screen(True,None,None)['report_gap_inconsistent']
