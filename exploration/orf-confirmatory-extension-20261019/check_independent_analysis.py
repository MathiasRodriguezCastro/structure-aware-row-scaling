#!/usr/bin/env python3
"""Check the independent bootstrap against analytic fixtures and the frozen kernel."""
import json
import math
import csv
from pathlib import Path
import tempfile
from analyze_confirmation import cluster_interval
from verify_confirmation_analysis import HERE, digest, close, multiplicity_interval, percentile, read_endpoints


def check_endpoint_schema():
    jobs = [dict(id='synthetic-schema-success', instance='schema-success', parent_id='A', family='simple',
                 horizon=24, seed=401, solver='gurobi', policy='L2', time_limit=60, diagnostic=False),
            dict(id='synthetic-schema-diagnostic', instance='schema-diagnostic', parent_id='B', family='completo',
                 horizon=168, seed=457, solver='cplex', policy='Base', time_limit=60, diagnostic=True)]
    raw = [dict(job=j, diagnostic=j['diagnostic'], status='completed', quality_evaluable=not j['diagnostic'],
        success=not j['diagnostic'], par2_seconds=None if j['diagnostic'] else 2.5,
        preparation_seconds=.5, complete_process_seconds=3., solver_work=20., native_gap_stop=True,
        native_status=2, native_gap=.001, native_nodes=0., bound_comparison_available=False,
        bound_contradiction=None, maximum_RSS_KiB=1000, returncode=0, result_sha256='synthetic-result',
        candidate_archive_sha256='synthetic-candidates', verified_available_seconds=None if j['diagnostic'] else 2.5)
        for j in jobs]
    fields = list(jobs[0]) + [k for k in raw[0] if k not in ['job', 'diagnostic', 'verified_available_seconds']]
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        def write(corrupt):
            with (folder/'CONFIRMATION_ASSIGNMENTS.csv').open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                for i, result in enumerate(raw):
                    record = dict(result['job'], **{k:v for k,v in result.items() if k not in ['job', 'diagnostic', 'verified_available_seconds']})
                    if corrupt and i == 0:
                        record['solver_work'] = 21.
                    writer.writerow(record)
        write(False)
        parsed = read_endpoints(dict(blocks=[dict(jobs=jobs)]), [dict(rows=raw)], directory=folder)
        assert parsed[0]['verified_available_seconds'] == 2.5 and parsed[1]['verified_available_seconds'] is None
        assert len(parsed) == 2 and sum(not r['job']['diagnostic'] for r in parsed) == 1
        write(True)
        try:
            read_endpoints(dict(blocks=[dict(jobs=jobs)]), [dict(rows=raw)], directory=folder)
        except AssertionError:
            return
        raise AssertionError('Corrupted CSV endpoint was accepted.')


def main():
    fixtures = [dict(name='unequal_parent_sizes', values=[math.log(2)] * 3 + [math.log(.5)],
                    parents=['A'] * 3 + ['B'], frame=['A', 'B'], logarithmic=True),
                dict(name='empty_conditional_parent', values=[math.log(2)], parents=['A'],
                     frame=['A', 'B'], logarithmic=True),
                dict(name='paired_success_difference', values=[1., 0., -1., 1., 0.],
                     parents=['A', 'A', 'B', 'C', 'C'], frame=['A', 'B', 'C'], logarithmic=False)]
    records = []
    for fixture in fixtures:
        actual = multiplicity_interval(fixture['values'], fixture['parents'], fixture['frame'], 123, fixture['logarithmic'])
        prior = cluster_interval(fixture['values'], fixture['parents'], 123,
                                fixture['logarithmic'], all_parents=fixture['frame'])
        for key in ['resamples', 'defined_resamples', 'parent_blocks']:
            assert actual[key] == prior[key]
        for a, b in zip(actual['interval_95'], prior['interval_95']):
            close(a, b)
        if fixture['name'] == 'unequal_parent_sizes':
            assert actual['interval_95'] == [.5, 2.]
            assert actual['defined_resamples'] == 100000
        if fixture['name'] == 'empty_conditional_parent':
            assert actual['interval_95'] == [2., 2.] and actual['parent_blocks'] == 2
            assert 73000 < actual['defined_resamples'] < 77000
        records.append(dict(name=fixture['name'], independent=actual, matched_frozen_kernel=True))
    assert percentile([0., 10., 20.], .25) == 5.
    rejected = False
    try:
        close(1., 1.01)
    except AssertionError:
        rejected = True
    assert rejected, 'A material reporting discrepancy must be rejected.'
    check_endpoint_schema()
    report = dict(status='passed', fixtures=records, material_discrepancy_rejected=True,
                  manual_percentile_interpolation_checked=True, optimizer_calls=0,
                  synthetic_CSV_success_and_diagnostic_checked=True, corrupted_CSV_endpoint_rejected=True,
                  no_benchmark_outcomes_used=True, source_sha256=digest(HERE / 'check_independent_analysis.py'),
                  verifier_sha256=digest(HERE / 'verify_confirmation_analysis.py'))
    (HERE / 'INDEPENDENT_ANALYSIS_CHECK.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Independent analysis checks passed: analytic parent fixtures, empty replicas and discrepancy rejection; zero optimizer calls.')


if __name__ == '__main__':
    import sys
    if sys.flags.optimize:
        raise RuntimeError('Run without -O; integrity assertions are required.')
    main()
