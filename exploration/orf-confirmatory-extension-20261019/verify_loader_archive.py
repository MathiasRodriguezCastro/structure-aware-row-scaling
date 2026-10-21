#!/usr/bin/env python3
"""Verify the complete retained infrastructure attempt locally without solvers."""
from collections import Counter
import json
from pathlib import Path

from seal_confirmation import digest

HERE = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text())


def main():
    archive = HERE / 'infrastructure-attempts/loader-preload-6071906'
    report = load(archive / 'ARCHIVE.json')
    manifest_path = archive / 'ARCHIVE_RAW_MANIFEST.json'
    manifest = load(manifest_path)
    assert digest(manifest_path) == report['raw_manifest_sha256']
    assert manifest['path_base'] == 'archive_directory' and manifest['status'] == 'sealed'
    assert len(manifest['files']) == len({r['path'] for r in manifest['files']}) == manifest['file_count']
    assert sum(r['bytes'] for r in manifest['files']) == manifest['total_bytes']
    for item in manifest['files']:
        path = (archive / item['path']).resolve()
        assert path.is_relative_to(archive.resolve())
        assert path.stat().st_size == item['bytes'] and digest(path) == item['sha256'], item['path']
    plan = load(archive / 'CONFIRMATION_PLAN.json')
    assert digest(archive / 'CONFIRMATION_PLAN.json') == report['old_plan_sha256']
    for name, expected in plan['dependencies'].items():
        assert digest(archive / 'registered-dependencies' / name) == expected, name
    jobs = {j['id']: j for b in plan['blocks'] for j in b['jobs']}
    records = [load(p) for p in (archive / 'confirmation-runs').glob('*/result.json')]
    indexed = {r['job']['id']: r for r in records}
    assert len(records) == len(indexed) == report['recorded_assignments'] == 624
    assert dict(Counter(r['status'] for r in records)) == report['execution_status_counts']
    assert sum('outcome' in r for r in records) == report['recorded_native_solver_invocations'] == 612
    failures = []
    for key, result in indexed.items():
        assert result['job'] == jobs[key]
        assert result['confirmation_plan_sha256'] == report['old_plan_sha256']
        folder = archive / 'confirmation-runs' / key
        if result['status'] == 'failed':
            assert not (folder / 'solver.log').exists() and not (folder / 'candidates.npz').exists()
            assert 'assert sha(export)' in (archive / 'confirmation-execution-logs' / (key + '.log')).read_text()
            failures.append(key)
    assert len(failures) == report['pre_optimizer_failures'] == 12
    execution = load(archive / 'CONFIRMATION_EXECUTION_REPORT.json')
    assert execution['status'] == 'incomplete_or_failed_retained'
    assert set(execution['missing_jobs']) == set(jobs) - set(indexed)
    assert len(execution['missing_jobs']) == report['not_attempted_assignments'] == 3216
    assert {r['job'] for r in execution['failed_jobs']} == set(failures)
    original = load(HERE / 'setup-evidence/confirmation-loader-6071906/ARCHIVE.json')
    assert original == report
    answer = dict(status='passed', archived_assignments=624, prior_native_solver_invocations=612,
        pre_optimizer_failures=12, unattempted_registered_assignments=3216,
        all_archived_file_hashes_checked=True, original_registered_dependencies_checked=len(plan['dependencies']),
        file_count=manifest['file_count'], total_bytes=manifest['total_bytes'],
        raw_manifest_sha256=digest(manifest_path), old_plan_sha256=report['old_plan_sha256'],
        current_plan_sha256=digest(HERE / 'CONFIRMATION_PLAN.json'),
        prior_attempt_wholly_excluded_from_primary_analysis=True,
        optimizer_calls=0, policy_comparisons=False, source_sha256=digest(Path(__file__).resolve()))
    (HERE / 'LOADER_ATTEMPT_LOCAL_VERIFICATION.json').write_text(json.dumps(answer, indent=2) + '\n')
    print('Retained loader attempt independently checked locally:', manifest['file_count'], 'files, 624 assignments.')


if __name__ == '__main__':
    import sys
    if sys.flags.optimize:
        raise RuntimeError('Run without -O; integrity assertions are required.')
    main()
