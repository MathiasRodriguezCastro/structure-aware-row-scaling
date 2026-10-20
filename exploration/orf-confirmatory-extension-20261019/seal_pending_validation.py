#!/usr/bin/env python3
"""Seal or verify the completed prerequisite evidence without solver calls."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main(check):
    destination = HERE / 'PENDING_RAW_MANIFEST.json'
    if check:
        result = json.loads(destination.read_text())
        assert result['status'] == 'sealed'
        assert len(result['files']) == len({r['path'] for r in result['files']}) == result['file_count']
        for item in result['files']:
            path = (HERE / item['path']).resolve()
            assert path.is_relative_to(HERE)
            assert path.stat().st_size == item['bytes'] and digest(path) == item['sha256'], item['path']
        assert sum(r['bytes'] for r in result['files']) == result['total_bytes']
        print('Raw prerequisite evidence verified:', result['file_count'], 'files.')
        return
    plan = json.loads((HERE / 'PENDING_VALIDATION_PLAN.json').read_text())
    report = json.loads((HERE / 'CONFIRMATION_REFERENCE_REPORT.json').read_text())
    replay = json.loads((HERE / 'CONFIRMATION_REFERENCE_REPLAY.json').read_text())
    assert report['status'] == 'completed' and report['recorded_models'] == 160
    assert replay['status'] == 'passed' and replay['models_replayed'] == 160
    paths = set()
    for directory in ['resource-calibration', 'confirmation-reference-acquisition', 'confirmation-references']:
        paths.update(p for p in (HERE / directory).rglob('*') if p.is_file())
    model_names = set(plan['confirmation_instances']) | {r['instance'] for r in plan['calibration_jobs']}
    for name in model_names:
        paths.update(HERE / 'models' / name / filename for filename in ['Base.lp','input.txt','metadata.json'])
    for filename in ['PENDING_VALIDATION_PLAN.json', 'PENDING_VALIDATION_PROTOCOL.md',
                     'BASE_CALIBRATION_REPORT.json', 'CONFIRMATION_BASE_ADMISSION.json',
                     'CONFIRMATION_REFERENCE_REPORT.json', 'CONFIRMATION_REFERENCE_REPLAY.json']:
        paths.add(HERE / filename)
    files = [dict(path=p.relative_to(HERE).as_posix(), bytes=p.stat().st_size, sha256=digest(p))
             for p in sorted(paths)]
    result = dict(status='sealed', file_count=len(files), total_bytes=sum(r['bytes'] for r in files),
                  files=files, optimizer_calls=0, plan_sha256=digest(HERE / 'PENDING_VALIDATION_PLAN.json'))
    if destination.exists():
        assert json.loads(destination.read_text()) == result, 'An immutable seal already exists.'
    else:
        destination.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print('Sealed prerequisite evidence:', len(files), 'files;', result['total_bytes'], 'bytes.')


if __name__ == '__main__':
    if sys.flags.optimize:
        raise RuntimeError('Integrity checks require Python without -O.')
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    main(parser.parse_args().check)
