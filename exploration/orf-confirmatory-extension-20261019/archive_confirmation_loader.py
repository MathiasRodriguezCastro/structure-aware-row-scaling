#!/usr/bin/env python3
"""Seal and retain the whole loader-failed attempt before a uniform repetition."""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

from runner import HERE, ROOT, load, save, sha


def main():
    plan = load(HERE / 'CONFIRMATION_PLAN.json')
    assert sha(HERE / 'CONFIRMATION_PLAN.json') == 'b960242359f2645cb6b6b9e05558e80c64ff2385b6daae7130a0716cdce85fda'
    for name, expected in plan['dependencies'].items():
        assert sha(ROOT / name) == expected, name
    execution = load(HERE / 'CONFIRMATION_EXECUTION_REPORT.json')
    assert execution['status'] == 'incomplete_or_failed_retained'
    assert len(execution['failed_jobs']) == 12
    assert load(HERE / 'FACTOR_PORTABILITY-Haswell-library-path-all.json')['byte_identical_exports'] == 384
    assert load(HERE / 'PREFLIGHT-loader-corrected.json')['status'] == 'passed'
    target = HERE / 'infrastructure-attempts/loader-preload-6071906'
    target.mkdir(parents=True, exist_ok=False)
    for name, expected in plan['dependencies'].items():
        dest = target / 'registered-dependencies' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, dest)
        assert sha(dest) == expected
    metadata = ['CONFIRMATION_PLAN.json', 'CONFIRMATION_SUBMISSION.json',
        'CONFIRMATION_EXECUTION_AMENDMENT.json', 'CONFIRMATION_GATE.json',
        'PREFLIGHT-confirmation.json', 'CONFIRMATION_PROGRESS.json',
        'CONFIRMATION_LOCAL_AUDIT.json', 'CONFIRMATION_INITIAL_LOCAL_REPLAY.json',
        'CONFIRMATION_ANALYSIS_VALIDATION_PLAN.json',
        'CONFIRMATION_EXECUTION_REPORT.json', 'CONFIRMATION_ASSIGNMENTS.csv',
        'CONFIRMATION_RAW_MANIFEST.json', 'LOADER_RECOVERY_PROTOCOL.md']
    for name in metadata:
        path = HERE / name
        if path.exists():
            shutil.copyfile(path, target / name)
    for relative in ['setup-evidence/confirmation', 'setup-evidence/confirmation-local',
                     'setup-evidence/confirmation-failure-diagnosis']:
        path = HERE / relative
        if path.exists():
            shutil.copytree(path, target / relative)
    records = []
    for path in sorted((HERE / 'confirmation-runs').glob('*/result.json')):
        value = load(path)
        if value['status'] == 'failed':
            log = HERE / 'confirmation-execution-logs' / (value['job']['id'] + '.log')
            assert 'assert sha(export)' in log.read_text()
            assert not (path.parent / 'solver.log').exists()
        records.append(value)
    assert len(records) == execution['replayed_assignments']
    assert sum(r['status'] == 'failed' for r in records) == 12
    for name in ['confirmation-runs', 'confirmation-execution-logs', 'confirmation-replay']:
        (HERE / name).rename(target / name)
    files = [dict(path=p.relative_to(target).as_posix(), bytes=p.stat().st_size, sha256=sha(p))
             for p in sorted(target.rglob('*')) if p.is_file()]
    manifest = dict(status='sealed', path_base='archive_directory', files=files,
        file_count=len(files), total_bytes=sum(r['bytes'] for r in files), optimizer_calls=0)
    save(target / 'ARCHIVE_RAW_MANIFEST.json', manifest)
    report = dict(status='retained_before_loader_correction',
        captured_utc=datetime.now(timezone.utc).isoformat(), original_array='6071906',
        old_plan_sha256=sha(HERE / 'CONFIRMATION_PLAN.json'),
        recorded_assignments=len(records), execution_status_counts=dict(Counter(r['status'] for r in records)),
        pre_optimizer_failures=12,
        not_attempted_assignments=len(execution['missing_jobs']),
        recorded_native_solver_invocations=sum('outcome' in r for r in records),
        all_original_attempts_retained=True, full_scientific_design_to_be_repeated=True,
        policy_rankings_consulted=False, optimizer_calls=0,
        raw_manifest_sha256=sha(target / 'ARCHIVE_RAW_MANIFEST.json'),
        archived_dependency_files=len(plan['dependencies']))
    report['recorded_complete_process_seconds'] = sum(load(path)['complete_process_seconds']
        for path in (target / 'confirmation-execution-logs').glob('*.json'))
    save(target / 'ARCHIVE.json', report)
    evidence = HERE / 'setup-evidence/confirmation-loader-6071906'
    evidence.mkdir(exist_ok=False)
    for name in metadata + ['ARCHIVE.json', 'ARCHIVE_RAW_MANIFEST.json']:
        if (target / name).exists():
            shutil.copyfile(target / name, evidence / name)
    shutil.copyfile(target / 'registered-dependencies' / HERE.relative_to(ROOT) / 'cluster/confirmation.slurm',
                    evidence / 'confirmation.slurm')
    print('Retained loader attempt:', len(records), 'assignments;', manifest['file_count'],
          'files;', manifest['total_bytes'], 'bytes.', flush=True)


if __name__ == '__main__':
    if sys.flags.optimize:
        raise RuntimeError('Run without -O; integrity assertions are required.')
    main()
