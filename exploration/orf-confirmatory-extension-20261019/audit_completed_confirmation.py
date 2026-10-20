#!/usr/bin/env python3
"""Download a fixed set of completed blocks and replay them locally without solvers."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from seal_pending_validation import digest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(path):
    return json.loads(path.read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main(download):
    plan = load(HERE / 'CONFIRMATION_PLAN.json')
    plan_sha = digest(HERE / 'CONFIRMATION_PLAN.json')
    receipt = load(HERE / 'CONFIRMATION_SUBMISSION.json')
    assert receipt['confirmation_plan_sha256'] == plan_sha
    for name, expected in plan['dependencies'].items():
        assert digest(ROOT / name) == expected, name
    reports = {}
    for path in sorted((HERE / 'confirmation-replay').glob('*.json')):
        report = load(path)
        assert report['confirmation_plan_sha256'] == plan_sha
        if report['status'] == 'passed':
            index = int(path.stem)
            assert report['block'] == index and len(report['rows']) == 8
            reports[index] = dict(path=path, sha256=digest(path))
    assert reports, 'No completed and independently replayed block is available.'
    snapshot = dict(confirmation_plan_sha256=plan_sha,
        block_replay_sha256={str(i): r['sha256'] for i, r in reports.items()},
        selection_rule='All currently downloaded passed block reports; no efficiency or target-success selection.',
        comparative_assignments_selected=8 * len(reports), audit_optimizer_calls=0,
        rerun_optimizer_calls=0)
    identity = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()[:16]
    evidence = HERE / 'setup-evidence/confirmation-local' / identity
    snapshot_file = evidence / 'SNAPSHOT.json'
    if snapshot_file.exists():
        assert load(snapshot_file) == snapshot
    else:
        save(snapshot_file, snapshot)
    env = dict(os.environ, LC_ALL='C', **plan['runtime'])
    jobs = [job for i in reports for job in plan['blocks'][i]['jobs']]
    if download:
        remote = 'mathiasr@cluster.uy:' + receipt['remote_repository'] + '/exploration/orf-confirmatory-extension-20261019/'
        for directory in ['confirmation-runs', 'confirmation-execution-logs']:
            destination = HERE / directory
            destination.mkdir(exist_ok=True)
            if directory == 'confirmation-runs':
                sources = [remote + directory + '/' + j['id'] for j in jobs]
            else:
                sources = [remote + directory + '/' + j['id'] + suffix for j in jobs for suffix in ['.json', '.log']]
            subprocess.run(['rsync', '-rlt', '-e', 'ssh -p 10022 -o BatchMode=yes -o ConnectTimeout=15',
                *sources, str(destination) + '/'], check=True, env=env)
        print('Downloaded closed-block traces:', len(jobs), 'assignments.', flush=True)
    versions = load(HERE / 'PREFLIGHT-confirmation.json')['solvers']
    raw_files = set()
    counts = Counter()
    coverage = Counter()
    blocks = []
    for index, source in reports.items():
        block = plan['blocks'][index]
        hosts = set()
        for job in block['jobs']:
            folder = HERE / 'confirmation-runs' / job['id']
            result = load(folder / 'result.json')
            assert result['job'] == job and result['confirmation_plan_sha256'] == plan_sha
            assert result['status'] == 'completed' and not result['callback_errors']
            expected = dict(threads=4, time_limit=job['time_limit'], mip_gap=.001,
                feasibility_tolerance=1e-6, integer_tolerance=1e-9, seed=job['seed'],
                internal_scaling='automatic', numerical_control=job['policy'])
            assert all(result['parameters'].get(k) == v for k, v in expected.items()), job['id']
            if job['solver'] == 'cplex':
                assert result['parameters']['search'] == 'traditional'
                assert result['parameters']['numerical_emphasis'] == int(job['policy'] == 'L2-NumEmphasis')
            assert result['outcome']['solver_version'] == versions[job['solver']]['version']
            assert result['native_import']['matrix_rhs_objective_bounds_integer_domains_equal']
            assert result['explicit_written_finite_bounds_checked']
            hosts.add(result['hostname'])
            raw_files.update(p for p in folder.rglob('*') if p.is_file())
            raw_files.update(HERE / 'confirmation-execution-logs' / (job['id'] + suffix) for suffix in ['.json', '.log'])
        assert len(hosts) == 1, 'Paired block ran on multiple nodes.'
        assert digest(source['path']) == source['sha256']
        subprocess.run([sys.executable, str(HERE / 'replay_confirmation.py'), str(index)],
                       check=True, cwd=ROOT, env=env)
        assert digest(source['path']) == source['sha256'], 'Local replay differs from the compute-node report.'
        replay = load(source['path'])
        assert replay['status'] == 'passed' and not replay['missing_jobs'] and not replay['failed_jobs']
        counts.update(replay['counts'])
        job = block['jobs'][0]
        coverage[job['family'], job['horizon']] += 1
        blocks.append(dict(block=index, instance=block['instance'], seed=block['seed'],
            hostname=next(iter(hosts)), assignments=8, byte_identical_to_compute_report=True,
            replay_sha256=source['sha256']))
        raw_files.add(source['path'])
    inventory = [dict(path=p.relative_to(HERE).as_posix(), bytes=p.stat().st_size, sha256=digest(p))
                 for p in sorted(raw_files)]
    manifest = dict(status='sealed', files=inventory, file_count=len(inventory),
        total_bytes=sum(r['bytes'] for r in inventory), optimizer_calls=0,
        snapshot_sha256=digest(snapshot_file), confirmation_plan_sha256=plan_sha)
    manifest_path = evidence / 'RAW_MANIFEST.json'
    if manifest_path.exists():
        assert load(manifest_path) == manifest, 'An immutable local snapshot already exists.'
    else:
        save(manifest_path, manifest)
    report = dict(status='passed', captured_utc=datetime.now(timezone.utc).isoformat(),
        blocks=len(blocks), assignments=len(jobs), unique_models=len({b['instance'] for b in blocks}),
        block_records=blocks, counts=dict(counts),
        family_horizon_coverage=[dict(family=f, horizon=h, blocks=n) for (f, h), n in sorted(coverage.items())],
        byte_identical_to_compute_reports=True, native_imports_parameters_versions_checked=True,
        same_node_within_each_paired_block=True, all_original_frozen_dependencies_unchanged=True,
        optimizer_calls=0, performance_comparisons=False,
        snapshot=snapshot_file.relative_to(HERE).as_posix(), raw_manifest=manifest_path.relative_to(HERE).as_posix(),
        raw_manifest_sha256=digest(manifest_path), source_sha256=digest(Path(__file__).resolve()),
        replay_source_sha256=digest(HERE / 'replay_confirmation.py'), confirmation_plan_sha256=plan_sha)
    save(HERE / 'CONFIRMATION_LOCAL_AUDIT.json', report)
    print('Local confirmation audit passed:', len(blocks), 'blocks,', len(jobs), 'assignments,', dict(counts), flush=True)


if __name__ == '__main__':
    if sys.flags.optimize:
        raise RuntimeError('Run without -O; integrity assertions are required.')
    parser = argparse.ArgumentParser()
    parser.add_argument('--download', action='store_true')
    main(parser.parse_args().download)
