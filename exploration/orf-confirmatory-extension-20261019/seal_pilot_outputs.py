#!/usr/bin/env python3
"""Inventory the completed pilot's raw evidence; never launch an optimizer."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def inventory():
    plan = json.loads((HERE / 'PILOT_PLAN.json').read_text())
    files = []
    jobs = [job for block in plan['blocks'] for job in block['jobs']]
    assert len(jobs) == 256 and len({j['id'] for j in jobs}) == 256
    paths = set()
    for job in jobs:
        folder = HERE / 'pilot-runs' / job['id']
        assert json.loads((folder / 'result.json').read_text())['job'] == job
        paths.update(p for p in folder.rglob('*') if p.is_file())
        paths.update(HERE / 'pilot-execution-logs' / (job['id'] + suffix)
                     for suffix in ['.json', '.log'])
    for block in plan['blocks']:
        name = block['instance']
        for parent in ['references', 'reference-acquisition', 'reference-recovery']:
            paths.update(p for p in (HERE / parent / name).rglob('*') if p.is_file())
        paths.update(HERE / 'models' / name / filename
                     for filename in ['Base.lp', 'input.txt', 'metadata.json'])
    for path in sorted(paths):
        files.append(dict(path=path.relative_to(HERE).as_posix(),
                          bytes=path.stat().st_size, sha256=sha(path)))
    return dict(status='sealed', pilot_plan_sha256=sha(HERE / 'PILOT_PLAN.json'),
                registered_assignments=len(jobs), files=files,
                file_count=len(files), total_bytes=sum(f['bytes'] for f in files),
                optimizer_calls=0,
                scope='Raw corrected pilot, outer timings, pilot models, references and recovery provenance.')


if __name__ == '__main__':
    report = inventory()
    destination = HERE / 'PILOT_RAW_MANIFEST.json'
    destination.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print('Pilot sealed:', report['file_count'], 'files;', report['total_bytes'], 'bytes.')
