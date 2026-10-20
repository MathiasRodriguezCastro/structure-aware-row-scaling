#!/usr/bin/env python3
"""Seal raw confirmation evidence on a compute node, including retained failures."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def main(check):
    target = HERE / 'CONFIRMATION_RAW_MANIFEST.json'
    if check:
        manifest = json.loads(target.read_text())
        assert manifest['path_base'] == 'repository_root'
        assert len(manifest['files']) == len({r['path'] for r in manifest['files']}) == manifest['file_count']
        for item in manifest['files']:
            path = (ROOT / item['path']).resolve()
            assert path.is_relative_to(ROOT)
            assert path.stat().st_size == item['bytes'] and digest(path) == item['sha256'], item['path']
        assert sum(r['bytes'] for r in manifest['files']) == manifest['total_bytes']
        print('Confirmation raw seal verified:', manifest['file_count'], 'files.')
        return
    plan = json.loads((HERE / 'CONFIRMATION_PLAN.json').read_text())
    execution = json.loads((HERE / 'CONFIRMATION_EXECUTION_REPORT.json').read_text())
    paths = set()
    for folder in ['confirmation-runs', 'confirmation-execution-logs', 'confirmation-replay']:
        paths.update(p for p in (HERE / folder).rglob('*') if p.is_file())
    for filename, expected in plan['dependencies'].items():
        path = ROOT / filename
        assert digest(path) == expected, filename
        paths.add(path)
    for name in ['CONFIRMATION_PLAN.json', 'CONFIRMATION_SUBMISSION.json', 'CONFIRMATION_GATE.json',
                 'PREFLIGHT-confirmation.json', 'CONFIRMATION_EXECUTION_REPORT.json',
                 'CONFIRMATION_ASSIGNMENTS.csv', 'CONFIRMATION_ANALYSIS.json', 'INFORME_CONFIRMACION.md',
                 'PENDING_RAW_MANIFEST.json', 'REFERENCE_RECOVERY_RAW_MANIFEST.json']:
        if (HERE / name).exists():
            paths.add(HERE / name)
    files = [dict(path=p.relative_to(ROOT).as_posix(), bytes=p.stat().st_size, sha256=digest(p))
             for p in sorted(paths)]
    result = dict(status='sealed', path_base='repository_root', file_count=len(files),
        total_bytes=sum(r['bytes'] for r in files), files=files, optimizer_calls=0,
        execution_status=execution['status'], registered_assignments=3840,
        confirmation_plan_sha256=digest(HERE / 'CONFIRMATION_PLAN.json'),
        reference_evidence_manifests={n: digest(HERE / n) for n in
            ['PENDING_RAW_MANIFEST.json', 'REFERENCE_RECOVERY_RAW_MANIFEST.json']})
    if target.exists():
        assert json.loads(target.read_text()) == result, 'An immutable raw seal already exists.'
    else:
        target.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print('Sealed confirmation evidence:', len(files), 'files;', result['total_bytes'], 'bytes.', flush=True)


if __name__ == '__main__':
    if sys.flags.optimize:
        raise RuntimeError('Run without -O; integrity assertions are required.')
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    main(parser.parse_args().check)
