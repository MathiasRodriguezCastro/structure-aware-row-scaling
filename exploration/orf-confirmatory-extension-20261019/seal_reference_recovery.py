#!/usr/bin/env python3
"""Seal the separate feasibility recovery without replacing the initial seal."""
import argparse
import json
from pathlib import Path
import sys

from seal_pending_validation import digest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name):
    return json.loads((HERE / name).read_text())


def main(check):
    destination = HERE / 'REFERENCE_RECOVERY_RAW_MANIFEST.json'
    if check:
        manifest = load(destination.name)
        assert manifest['status'] == 'sealed'
        assert len(manifest['files']) == len({r['path'] for r in manifest['files']}) == manifest['file_count']
        for item in manifest['files']:
            path = (HERE / item['path']).resolve()
            assert path.is_relative_to(HERE)
            assert path.stat().st_size == item['bytes'] and digest(path) == item['sha256'], item['path']
        assert sum(r['bytes'] for r in manifest['files']) == manifest['total_bytes']
        assert digest(HERE / 'PENDING_RAW_MANIFEST.json') == manifest['initial_raw_manifest_sha256']
        print('Separate recovery evidence verified:', manifest['file_count'], 'files; zero optimizer calls.')
        return

    plan = load('REFERENCE_FEASIBILITY_RECOVERY_PLAN.json')
    report = load('REFERENCE_FEASIBILITY_RECOVERY_REPORT.json')
    replay = load('REFERENCE_FEASIBILITY_RECOVERY_REPLAY.json')
    assert report['status'] == 'completed' and not report['missing_models']
    assert replay['status'] == 'passed' and replay['optimizer_calls'] == 0
    assert report['recovery_plan_sha256'] == replay['recovery_plan_sha256'] == digest(HERE / 'REFERENCE_FEASIBILITY_RECOVERY_PLAN.json')
    assert report['additional_MIP_calls'] == 0
    assert report['additional_LP_calls'] <= plan['maximum_additional_LP_calls']
    assert len(report['records']) == len(plan['models'])
    assert {r['instance'] for r in report['records']} == {r['instance'] for r in replay['records']} == set(plan['models'])
    for name, expected in plan['dependencies'].items():
        assert digest(ROOT / name) == expected, name
    paths = set()
    root = HERE / 'confirmation-reference-recovery'
    assert {p.name for p in root.iterdir() if p.is_dir()} == set(plan['models'])
    for record in report['records']:
        assert load('confirmation-reference-recovery/' + record['instance'] + '/result.json') == record
    paths.update(p for p in root.rglob('*') if p.is_file())
    paths.update(p for p in (HERE / 'setup-evidence/pending-validation').rglob('*') if p.is_file())
    for filename in ['PENDING_RAW_MANIFEST.json', 'STDLIB_REFERENCE_REPLAY.json',
                     'REFERENCE_FEASIBILITY_RECOVERY_PROTOCOL.md', 'REFERENCE_FEASIBILITY_RECOVERY_RULES.json',
                     'REFERENCE_FEASIBILITY_RECOVERY_PLAN.json', 'REFERENCE_FEASIBILITY_RECOVERY_SUBMISSION.json',
                     'REFERENCE_FEASIBILITY_RECOVERY_REPORT.json', 'REFERENCE_FEASIBILITY_RECOVERY_REPLAY.json',
                     'recover_confirmation_feasibility.py', 'verify_reference_witnesses_stdlib.py',
                     'verify_recovered_references_stdlib.py', 'seal_reference_recovery.py']:
        paths.add(HERE / filename)
    files = [dict(path=p.relative_to(HERE).as_posix(), bytes=p.stat().st_size, sha256=digest(p))
             for p in sorted(paths)]
    result = dict(status='sealed', file_count=len(files), total_bytes=sum(r['bytes'] for r in files),
                  files=files, optimizer_calls=0,
                  initial_raw_manifest_sha256=digest(HERE / 'PENDING_RAW_MANIFEST.json'),
                  recovery_plan_sha256=digest(HERE / 'REFERENCE_FEASIBILITY_RECOVERY_PLAN.json'))
    if destination.exists():
        assert load(destination.name) == result, 'An immutable recovery seal already exists.'
    else:
        destination.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print('Sealed separate recovery evidence:', len(files), 'files;', result['total_bytes'], 'bytes.')


if __name__ == '__main__':
    if sys.flags.optimize:
        raise RuntimeError('Run without -O; integrity assertions are required.')
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    main(parser.parse_args().check)
