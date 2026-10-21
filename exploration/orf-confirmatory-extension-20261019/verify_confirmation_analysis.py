#!/usr/bin/env python3
"""Independent aggregation from the endpoint CSV and parent-multiplicity bootstrap."""
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
METRICS = ['par2_seconds', 'complete_process_seconds', 'solver_work', 'verified_available_seconds']


def load(path):
    return json.loads(path.read_text())


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def close(actual, expected):
    assert math.isfinite(actual) and math.isfinite(expected)
    assert math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-12), (actual, expected)


def percentile(sorted_values, probability):
    position = (len(sorted_values) - 1) * probability
    low = math.floor(position)
    weight = position - low
    return float(sorted_values[low] if not weight else
                 (1 - weight) * sorted_values[low] + weight * sorted_values[low + 1])


def multiplicity_interval(values, parents, frame, seed, logarithmic):
    """Count selected parents, then weight their observation totals and counts."""
    frame = sorted(set(frame))
    grouped = defaultdict(list)
    for value, parent in zip(values, parents):
        grouped[parent].append(value)
    totals = np.array([math.fsum(grouped[p]) for p in frame], dtype=float)
    counts = np.array([len(grouped[p]) for p in frame], dtype=np.int64)
    rng = np.random.default_rng(seed)
    samples = []
    for _ in range(10):
        draws = rng.integers(0, len(frame), size=(10000, len(frame)))
        multiplicity = np.zeros((10000, len(frame)), dtype=np.int64)
        np.add.at(multiplicity, (np.repeat(np.arange(10000), len(frame)), draws.ravel()), 1)
        denominators = multiplicity @ counts
        numerators = multiplicity @ totals
        samples.append(numerators[denominators > 0] / denominators[denominators > 0])
    ordered = np.sort(np.concatenate(samples))
    assert len(ordered)
    bounds = [percentile(ordered, p) for p in [.025, .975]]
    if logarithmic:
        bounds = [math.exp(v) for v in bounds]
    return dict(interval_95=bounds, resamples=100000, defined_resamples=len(ordered), parent_blocks=len(frame))


def compare_interval(record, values, parents, frame, seed, logarithmic):
    expected = multiplicity_interval(values, parents, frame, seed, logarithmic)
    for field in ['resamples', 'defined_resamples', 'parent_blocks']:
        assert record[field] == expected[field], field
    for actual, wanted in zip(record['interval_95'], expected['interval_95']):
        close(actual, wanted)


def read_endpoints(plan, block_reports, directory=HERE):
    jobs = {j['id']: j for b in plan['blocks'] for j in b['jobs']}
    rows = list(csv.DictReader((directory / 'CONFIRMATION_ASSIGNMENTS.csv').open(newline='')))
    assert len(rows) == len({r['id'] for r in rows}) == len(jobs)
    replay_rows = {r['job']['id']: r for report in block_reports for r in report['rows']}
    assert set(replay_rows) == set(jobs) == {r['id'] for r in rows}
    parsed = []
    for row in rows:
        job = jobs[row['id']]
        for key in ['instance', 'parent_id', 'family', 'horizon', 'seed', 'solver', 'policy', 'time_limit', 'diagnostic']:
            assert row[key] == str(job[key]), (row['id'], key)
        raw = replay_rows[row['id']]
        assert row['status'] == raw['status'] and row['status'] in ['completed', 'abstained']
        for key in ['status', 'quality_evaluable', 'success', 'par2_seconds', 'preparation_seconds',
                    'complete_process_seconds', 'solver_work', 'native_gap_stop', 'native_status',
                    'native_gap', 'native_nodes', 'bound_comparison_available', 'bound_contradiction',
                    'maximum_RSS_KiB', 'returncode', 'result_sha256', 'candidate_archive_sha256']:
            expected = raw.get(key)
            assert row[key] == ('' if expected is None else str(expected)), (row['id'], key)
        for key in ['quality_evaluable', 'success']:
            assert row[key] in ['True', 'False'] and (row[key] == 'True') == raw[key]
        assert raw['diagnostic'] == job['diagnostic']
        assert raw['quality_evaluable'] == (not job['diagnostic'])
        for key in ['result_sha256', 'candidate_archive_sha256']:
            assert row[key] == (raw.get(key) or ''), key
        item = dict(job=job, success=row['success'] == 'True', final=raw.get('final'),
            native_gap_stop=raw.get('native_gap_stop', False),
            bound_comparison_available=raw.get('bound_comparison_available', False),
            bound_contradiction=raw.get('bound_contradiction'))
        for metric in METRICS[:-1]:
            value = None if row[metric] == '' else float(row[metric])
            assert value == raw.get(metric), (row['id'], metric)
            assert value is None or (math.isfinite(value) and value >= 0)
            item[metric] = value
        item['verified_available_seconds'] = item['par2_seconds'] if item['success'] else None
        assert item['verified_available_seconds'] == raw.get('verified_available_seconds')
        parsed.append(item)
    assert sum(not r['job']['diagnostic'] for r in parsed) == sum(not j['diagnostic'] for j in jobs.values())
    return parsed


def main():
    validation = load(HERE / 'CONFIRMATION_ANALYSIS_VALIDATION_PLAN.json')
    assert validation['confirmation_plan_sha256'] == digest(HERE / 'CONFIRMATION_PLAN.json')
    assert validation['float_comparison_tolerance'] == dict(relative=1e-10, absolute=1e-12)
    for path, expected in validation['sources'].items():
        assert digest(ROOT / path) == expected, path
    execution = load(HERE / 'CONFIRMATION_EXECUTION_REPORT.json')
    assert execution['status'] == 'complete_verified'
    assert execution['replayed_assignments'] == 3840 and not execution['missing_jobs'] and not execution['failed_jobs']
    # Check the complete frozen archive before deriving statistics from its endpoints.
    subprocess.run([sys.executable, str(HERE / 'seal_confirmation.py'), '--check'], check=True)
    plan = load(HERE / 'CONFIRMATION_PLAN.json')
    analysis = load(HERE / 'CONFIRMATION_ANALYSIS.json')
    assert analysis['status'] == 'analyzed' and analysis['confirmation_plan_sha256'] == digest(HERE / 'CONFIRMATION_PLAN.json')
    assert analysis['execution_report_sha256'] == digest(HERE / 'CONFIRMATION_EXECUTION_REPORT.json')
    blocks = [load(HERE / 'confirmation-replay' / f'{i:03d}.json') for i in range(480)]
    for i, block in enumerate(blocks):
        assert block['status'] == 'passed' and block['block'] == i and block['optimizer_calls'] == 0
        assert block['confirmation_plan_sha256'] == digest(HERE / 'CONFIRMATION_PLAN.json')
    all_endpoints = read_endpoints(plan, blocks)
    assert len(all_endpoints) == 3840
    endpoints = [r for r in all_endpoints if not r['job']['diagnostic']]
    assert len(endpoints) == 3816
    indexed = {(r['job']['instance'], r['job']['seed'], r['job']['solver'], r['job']['policy']): r for r in endpoints}
    comparisons = {(r['solver'], r['stratum'], r['denominator']): r for r in analysis['comparisons']}
    assert len(comparisons) == len(analysis['comparisons']) == 48
    checked = 0
    intervals = 0
    for solver in ['gurobi', 'cplex']:
        for comparator in ['L2', 'Base', 'L2-NF3' if solver == 'gurobi' else 'L2-NumEmphasis']:
            pairs = []
            for a in endpoints:
                j = a['job']
                if j['solver'] == solver and j['policy'] == 'Budget-L2':
                    pairs.append((a, indexed[j['instance'], j['seed'], solver, comparator]))
            assert len(pairs) == 477
            for group in ['all', 'simple', 'sgtm', 'completo', 'h24', 'h72', 'h168', 'h360']:
                subset = [(a, b) for a, b in pairs if group == 'all' or group == a['job']['family'] or group == f"h{a['job']['horizon']}"]
                record = comparisons[solver, group, comparator]
                assert record['numerator'] == 'Budget-L2' and record['paired_assignments'] == len(subset)
                frame = [a['job']['parent_id'] for a, b in subset]
                assert record['parents'] == len(set(frame))
                assert record['numerator_successes'] == sum(a['success'] for a, b in subset)
                assert record['denominator_successes'] == sum(b['success'] for a, b in subset)
                differences = [int(a['success']) - int(b['success']) for a, b in subset]
                close(record['success_rate_difference']['value'], math.fsum(differences) / len(subset))
                seed = plan['analysis']['bootstrap_seed'] + int.from_bytes(hashlib.sha256((solver + '/' + group).encode()).digest()[:4], 'big')
                if comparator == 'L2':
                    compare_interval(record['success_rate_difference'], differences, frame, frame, seed, False)
                    intervals += 1
                for metric in METRICS:
                    usable = [(a, b) for a, b in subset if a.get(metric) is not None and b.get(metric) is not None and a[metric] > 0 and b[metric] > 0]
                    item = record['metrics'][metric]
                    assert item['paired_assignments'] == len(usable)
                    assert item['unavailable_pairs'] == len(subset) - len(usable)
                    assert item['conditional_on_common_success'] == (metric == 'verified_available_seconds')
                    if not usable:
                        assert 'geometric_mean_paired_ratio' not in item and 'interval_95' not in item
                        continue
                    logs = [math.log(a[metric]) - math.log(b[metric]) for a, b in usable]
                    close(item['geometric_mean_paired_ratio'], math.exp(math.fsum(logs) / len(logs)))
                    assert item['numerator_lower_count'] == sum(a[metric] < b[metric] for a, b in usable)
                    if comparator == 'L2':
                        compare_interval(item, logs, [a['job']['parent_id'] for a, b in usable], frame, seed, True)
                        intervals += 1
                checked += 1
    counts = {(r['solver'], r['policy']): r for r in analysis['policy_counts']}
    assert len(counts) == 8
    for key, record in counts.items():
        rows = [r for r in endpoints if (r['job']['solver'], r['job']['policy']) == key]
        expected = dict(assignments=len(rows), verified_target_successes=sum(r['success'] for r in rows),
            final_primal_pass=sum(r['final']['primal_pass'] for r in rows if r['final']),
            final_candidates=sum(r['final'] is not None for r in rows),
            native_gap_stops=sum(r['native_gap_stop'] for r in rows),
            bound_comparisons=sum(r['bound_comparison_available'] for r in rows),
            detected_bound_contradictions=sum(r['bound_contradiction'] is True for r in rows))
        assert all(record[k] == value for k, value in expected.items()), key
    report = dict(status='passed', comparisons_reproduced=checked, bootstrap_intervals_reproduced=intervals,
        endpoint_records=3840, quality_evaluable=3816, diagnostic=24,
        optimizer_calls=0, independent_CSV_aggregation=True,
        bootstrap_method='parent multiplicities, weighted totals/counts; manual percentile interpolation',
        relative_float_comparison_tolerance=1e-10, absolute_float_comparison_tolerance=1e-12,
        certified_optimality_claimed=False, confirmation_plan_sha256=digest(HERE / 'CONFIRMATION_PLAN.json'),
        validation_plan_sha256=digest(HERE / 'CONFIRMATION_ANALYSIS_VALIDATION_PLAN.json'),
        input_sha256={n: digest(HERE / n) for n in ['CONFIRMATION_EXECUTION_REPORT.json',
            'CONFIRMATION_ASSIGNMENTS.csv', 'CONFIRMATION_ANALYSIS.json', 'CONFIRMATION_RAW_MANIFEST.json']},
        source_sha256=digest(Path(__file__).resolve()))
    (HERE / 'CONFIRMATION_ANALYSIS_REPLAY.json').write_text(json.dumps(report, indent=2) + '\n')
    paths = {ROOT / name for name in validation['sources']}
    paths.update(HERE / name for name in ['CONFIRMATION_ANALYSIS_VALIDATION_PLAN.json',
        'CONFIRMATION_ANALYSIS_VALIDATION_SUBMISSION.json', 'CONFIRMATION_ANALYSIS_REPLAY.json'])
    files = [dict(path=p.relative_to(ROOT).as_posix(), bytes=p.stat().st_size, sha256=digest(p)) for p in sorted(paths)]
    manifest = dict(status='sealed', path_base='repository_root', files=files, file_count=len(files),
        total_bytes=sum(r['bytes'] for r in files), optimizer_calls=0,
        original_raw_manifest_sha256=digest(HERE / 'CONFIRMATION_RAW_MANIFEST.json'),
        verification_status='passed', validation_plan_sha256=digest(HERE / 'CONFIRMATION_ANALYSIS_VALIDATION_PLAN.json'))
    destination = HERE / 'CONFIRMATION_ANALYSIS_VALIDATION_MANIFEST.json'
    if destination.exists():
        assert load(destination) == manifest, 'An immutable postvalidation seal already exists.'
    else:
        destination.write_text(json.dumps(manifest, indent=2) + '\n')
    print('Independent confirmation analysis replay passed:', checked, 'comparisons,', intervals, 'intervals.', flush=True)


if __name__ == '__main__':
    if sys.flags.optimize:
        raise RuntimeError('Run without -O; integrity assertions are required.')
    try:
        main()
    except Exception as error:
        failure = dict(status='failed', error=type(error).__name__ + ': ' + str(error),
                       optimizer_calls=0, scientific_results_accepted=False,
                       source_sha256=digest(Path(__file__).resolve()))
        (HERE / 'CONFIRMATION_ANALYSIS_REPLAY.json').write_text(json.dumps(failure, indent=2) + '\n')
        raise
