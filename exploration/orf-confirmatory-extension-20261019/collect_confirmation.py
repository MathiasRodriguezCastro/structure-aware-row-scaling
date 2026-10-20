#!/usr/bin/env python3
"""Collect independently replayed blocks, preserving every registered identity."""
from collections import Counter
import csv
from runner import HERE, load, save, sha


def read_blocks():
    plan = load(HERE / 'CONFIRMATION_PLAN.json')
    rows, reports = [], []
    missing_blocks = []
    for index, block in enumerate(plan['blocks']):
        file = HERE / 'confirmation-replay' / f'{index:03d}.json'
        if not file.exists():
            missing_blocks.append(index)
            continue
        report = load(file)
        assert report['confirmation_plan_sha256'] == sha(HERE / 'CONFIRMATION_PLAN.json')
        assert report['block'] == index and report['instance'] == block['instance'] and report['seed'] == block['seed']
        expected = {j['id']: j for j in block['jobs']}
        assert len({r['job']['id'] for r in report['rows']}) == len(report['rows'])
        for row in report['rows']:
            assert row['job'] == expected[row['job']['id']]
        rows.extend(report['rows'])
        reports.append(report)
    return plan, rows, reports, missing_blocks


def main():
    plan, rows, reports, missing_blocks = read_blocks()
    present = {r['job']['id'] for r in rows}
    all_jobs = [j for b in plan['blocks'] for j in b['jobs']]
    missing = [j['id'] for j in all_jobs if j['id'] not in present]
    complete = not missing and not missing_blocks and all(r['status'] == 'passed' for r in reports)
    report = dict(status='complete_verified' if complete else 'incomplete_or_failed_retained',
        registered_assignments=len(all_jobs), replayed_assignments=len(rows),
        replayed_blocks=len(reports), missing_blocks=missing_blocks, missing_jobs=missing,
        failed_jobs=[j for r in reports for j in r['failed_jobs']],
        execution_status_counts=dict(Counter(r['status'] for r in rows)),
        diagnostic_assignments=sum(r['diagnostic'] for r in rows),
        quality_evaluable_assignments=sum(r['quality_evaluable'] for r in rows),
        replay_counts={k: sum(r['counts'][k] for r in reports) for k in
            ['candidate_vectors', 'full_candidate_audits', 'exact_reference_checks']},
        optimizer_calls=0, confirmation_plan_sha256=sha(HERE / 'CONFIRMATION_PLAN.json'),
        no_policy_ranking_from_incomplete_results=True)
    save(HERE / 'CONFIRMATION_EXECUTION_REPORT.json', report)
    fields = ['id', 'instance', 'parent_id', 'family', 'horizon', 'seed', 'solver', 'policy',
        'time_limit', 'diagnostic', 'status', 'quality_evaluable', 'success', 'par2_seconds',
        'preparation_seconds', 'complete_process_seconds', 'solver_work', 'native_gap_stop',
        'native_status', 'native_gap', 'native_nodes', 'bound_comparison_available',
        'bound_contradiction', 'maximum_RSS_KiB', 'returncode', 'result_sha256', 'candidate_archive_sha256']
    with (HERE / 'CONFIRMATION_ASSIGNMENTS.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        by_id = {r['job']['id']: r for r in rows}
        for job in all_jobs:
            row = by_id.get(job['id'], dict(status='missing', job=job))
            flat = dict(job, **{k: v for k, v in row.items() if k != 'job'})
            writer.writerow({k: flat.get(k) for k in fields})
    print('Confirmation collection:', report['status'], len(rows), '/', len(all_jobs), flush=True)


if __name__ == '__main__':
    import sys
    if sys.flags.optimize:
        raise RuntimeError('Run without -O; integrity assertions are required.')
    main()
