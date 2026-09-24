import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts' / 'research'))
import robustness_analysis as ra


def run(**kw):
    """One record with the fields the analysis reads."""
    base = dict(stage='primary', family='Simple', solver='gurobi', gap=0.01, seed=1,
                instance='i1', instance_sha256='h1', policy='Base', outcome='COMPLETED',
                tiempo_solver_s=1.0, cap_s=1800.0, wall_s=2.0, gap_pct=0.0,
                objetivo_solver=-100.0, best_bound=-100.0, verif_solver_obj_original=-100.0,
                verif_solver_max_viol_relact=1e-13, verif_solver_max_lb=0.0,
                verif_solver_max_ub=0.0, verif_solver_max_int=0.0, verif_solver_missing=0.0,
                infrastructure_failure=False, run_id='r')
    base.update(kw)
    return base


def prepared(records):
    """Apply the derived columns that load() adds, without touching the filesystem."""
    d = pd.DataFrame(records)
    d['completed'] = d.outcome.eq('COMPLETED')
    d['censored'] = d.outcome.isin(['TIME_LIMIT', 'TIME_LIMIT_NO_SOLUTION', 'WRAPPER_TIMEOUT'])
    d['failed'] = ~(d.completed | d.censored)
    d['no_incumbent'] = d.outcome.eq('TIME_LIMIT_NO_SOLUTION')
    d['verified_strict'] = ((d.verif_solver_max_viol_relact <= 1e-9) & (d.verif_solver_max_lb <= 1e-9)
                            & (d.verif_solver_max_ub <= 1e-9) & (d.verif_solver_max_int <= 1e-9)
                            & (d.verif_solver_missing == 0))
    d['verified'] = ((d.verif_solver_max_viol_relact <= 1e-6) & (d.verif_solver_max_lb <= 1e-6)
                     & (d.verif_solver_max_ub <= 1e-6) & (d.verif_solver_max_int <= 1e-5)
                     & (d.verif_solver_missing == 0))
    return d


def test_no_contradiction_when_claims_agree():
    d = prepared([run(policy='Base'), run(policy='Flat-GM', objetivo_solver=-99.5,
                                          verif_solver_obj_original=-99.5, best_bound=-100.2)])
    assert ra.contradictions(d).empty


def test_claim_contradicted_by_a_better_verified_point():
    """Base claims optimality 50% above a point verified for the same model."""
    d = prepared([run(policy='Base', objetivo_solver=-100.0, verif_solver_obj_original=-100.0,
                      best_bound=-100.0),
                  run(policy='Flat-GM', objetivo_solver=-200.0, verif_solver_obj_original=-200.0,
                      best_bound=-201.0)])
    bad = ra.contradictions(d)
    assert set(bad.policy) == {'Base'}
    row = bad.iloc[0]
    assert row.optimality_claim_contradicted and row.dual_bound_invalid
    assert row.optimality_claim_contradicted_strict
    assert row.relative_excess == pytest.approx(0.5)
    assert row.best_known == -200.0


def test_a_loosely_feasible_point_does_not_create_a_strict_contradiction():
    """The better point is only feasible at the campaign tolerance, not at round-off."""
    d = prepared([run(policy='Base', best_bound=-100.0),
                  run(policy='Flat-GM', objetivo_solver=-200.0, verif_solver_obj_original=-200.0,
                      best_bound=-201.0, verif_solver_max_viol_relact=1e-7)])
    bad = ra.contradictions(d)
    row = bad[bad.policy.eq('Base')].iloc[0]
    assert row.optimality_claim_contradicted
    assert not row.optimality_claim_contradicted_strict


def test_gap_absorbs_a_small_difference():
    """A claim within its own gap of the best known point is not contradicted."""
    d = prepared([run(policy='Base', objetivo_solver=-99.5, verif_solver_obj_original=-99.5,
                      best_bound=-100.4),
                  run(policy='Flat-GM', objetivo_solver=-100.0, verif_solver_obj_original=-100.0,
                      best_bound=-100.4)])
    bad = ra.contradictions(d)
    assert bad.empty or not bad.optimality_claim_contradicted.any()


def test_different_instances_are_never_compared():
    d = prepared([run(policy='Base', instance='i1', instance_sha256='h1'),
                  run(policy='Flat-GM', instance='i2', instance_sha256='h2',
                      objetivo_solver=-500.0, verif_solver_obj_original=-500.0, best_bound=-501.0)])
    assert ra.contradictions(d).empty


def test_par10_charges_ten_caps_for_a_timeout():
    d = prepared([run(policy='Base', outcome='TIME_LIMIT', tiempo_solver_s=1800.0)])
    d['par10_s'] = (d.tiempo_solver_s).where(d.completed, 10.0 * d.cap_s)
    cells = ra.cells(d)
    assert cells.iloc[0].par10_mean_s == pytest.approx(18000.0)
    assert cells.iloc[0].completion_rate == 0.0
