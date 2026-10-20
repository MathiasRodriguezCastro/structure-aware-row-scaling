#!/usr/bin/env python3
"""Check unequal-size parent blocks and empty conditional bootstrap replicas."""
import math
from analyze_confirmation import cluster_interval, summarize_pairs
from runner import HERE, save, sha


def main():
    # Three nested observations belong to A, one to B. Resample parents, not seeds.
    values = [math.log(2)] * 3 + [math.log(.5)]
    parents = ['A'] * 3 + ['B']
    interval = cluster_interval(values, parents, 123, True)
    assert interval['interval_95'] == [.5, 2.] and interval['parent_blocks'] == 2
    assert interval['defined_resamples'] == 100000
    a = dict(job=dict(parent_id='A'), success=True, par2_seconds=2., complete_process_seconds=2., solver_work=2.)
    b = dict(job=dict(parent_id='B'), success=False, par2_seconds=.5, complete_process_seconds=.5, solver_work=.5)
    one = dict(job=dict(parent_id='A'), success=True, par2_seconds=1., complete_process_seconds=1., solver_work=1.)
    other = dict(one, job=dict(parent_id='B'))
    summary = summarize_pairs([(a, one)] * 3 + [(b, other)], 'gurobi', 'fixture', 'L2', 123)
    assert math.isclose(summary['metrics']['par2_seconds']['geometric_mean_paired_ratio'], math.sqrt(2), rel_tol=1e-14)
    assert summary['numerator_successes'] == 3 and summary['denominator_successes'] == 4
    assert summary['metrics']['verified_available_seconds']['paired_assignments'] == 0
    conditional = cluster_interval([math.log(2)], ['A'], 123, True, all_parents=['A', 'B'])
    assert conditional['parent_blocks'] == 2
    assert 73000 < conditional['defined_resamples'] < 77000
    assert conditional['interval_95'] == [2., 2.]
    save(HERE / 'CONFIRMATION_ANALYSIS_CHECK.json', dict(status='passed', optimizer_calls=0,
        unequal_parent_sizes_preserve_observation_weights=True,
        empty_conditional_parents_preserved=True, zero_denominators_not_imputed=True,
        parent_block_interval_fixture=interval, conditional_interval_fixture=conditional,
        source_sha256=sha(HERE / 'check_confirmation_analysis.py'),
        analyzer_sha256=sha(HERE / 'analyze_confirmation.py')))
    print('Whole-parent bootstrap and unavailable conditional endpoints checked; zero optimizer calls.')


if __name__ == '__main__':
    import sys
    if sys.flags.optimize:
        raise RuntimeError('Run without -O; integrity assertions are required.')
    main()
