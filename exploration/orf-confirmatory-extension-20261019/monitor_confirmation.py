#!/usr/bin/env python3
"""Read scheduling/replay progress without ranking partially observed policies."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess

HERE = Path(__file__).resolve().parent


def main(copy, snapshot):
    env = dict(os.environ, LC_ALL='C')
    receipt = json.loads((HERE / 'CONFIRMATION_SUBMISSION.json').read_text())
    expected_plan = receipt['confirmation_plan_sha256']
    assert hashlib.sha256((HERE / 'CONFIRMATION_PLAN.json').read_bytes()).hexdigest() == expected_plan
    jobs = dict(receipt['jobs'])
    extra = HERE / 'CONFIRMATION_ANALYSIS_VALIDATION_SUBMISSION.json'
    if extra.exists():
        jobs['analysis_verification'] = json.loads(extra.read_text())
    ids = ','.join(r['job_id'] for r in jobs.values())
    command = ['sacct', '-n', '-P', '-j', ids,
               '--format=JobID,State,ExitCode,Elapsed,AllocCPUS,MaxRSS,NodeList']
    process = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15',
        'mathiasr@login.cluster.uy', shlex.join(command)], text=True, capture_output=True,
        check=True, timeout=60, env=env)
    accounting = [r.split('|') for r in process.stdout.splitlines() if r.strip()]
    report = dict(captured_utc=datetime.now(timezone.utc).isoformat(),
                  confirmation_plan_sha256=expected_plan, stages={})
    for stage, item in jobs.items():
        job = item['job_id']
        if stage in ['array', 'first_block']:
            rows = [r for r in accounting if re.fullmatch(re.escape(job) + r'_\d+', r[0])]
            report['stages'][stage] = dict(states=dict(Counter(r[1] for r in rows)),
                unstarted_or_unlisted=(479 if stage == 'array' else 1) - len(rows),
                active=[dict(block=int(r[0].split('_')[1]), state=r[1], elapsed=r[3])
                    for r in rows if r[1] in ['RUNNING', 'COMPLETING']])
        else:
            report['stages'][stage] = [dict(state=r[1], exit=r[2], elapsed=r[3]) for r in accounting if r[0] == job]
    if copy:
        remote = receipt['remote_repository'] + '/exploration/orf-confirmatory-extension-20261019/'
        names = ['CONFIRMATION_GATE.json', 'PREFLIGHT-confirmation.json', 'CONFIRMATION_EXECUTION_REPORT.json',
                 'CONFIRMATION_ANALYSIS.json', 'CONFIRMATION_ASSIGNMENTS.csv', 'INFORME_CONFIRMACION.md',
                 'CONFIRMATION_RAW_MANIFEST.json', 'CONFIRMATION_ANALYSIS_REPLAY.json',
                 'CONFIRMATION_ANALYSIS_VALIDATION_MANIFEST.json']
        includes = ['--include=' + n for n in names] + ['--include=confirmation-replay/', '--include=confirmation-replay/*.json']
        subprocess.run(['rsync', '-rlt', *includes, '--exclude=*', '-e',
            'ssh -p 10022 -o BatchMode=yes -o ConnectTimeout=15', 'mathiasr@cluster.uy:' + remote, str(HERE) + '/'],
            check=True, env=env)
    replays = [json.loads(p.read_text()) for p in (HERE / 'confirmation-replay').glob('*.json')]
    assert all(r['confirmation_plan_sha256'] == expected_plan for r in replays), 'Stale block reports from another execution attempt.'
    for name in ['CONFIRMATION_GATE.json', 'CONFIRMATION_EXECUTION_REPORT.json',
                 'CONFIRMATION_RAW_MANIFEST.json', 'CONFIRMATION_ANALYSIS.json']:
        path = HERE / name
        if path.exists():
            assert json.loads(path.read_text())['confirmation_plan_sha256'] == expected_plan, 'Stale metadata: ' + name
    report['downloaded_block_replay_reports'] = dict(Counter(r['status'] for r in replays))
    report['cluster_verified_assignments'] = sum(len(r['rows']) for r in replays if r['status'] == 'passed')
    report['execution_failures_in_downloaded_reports'] = sum(len(r['failed_jobs']) for r in replays)
    report['local_independent_audit'] = None
    for name in ['CONFIRMATION_LOCAL_AUDIT.json', 'CONFIRMATION_INITIAL_LOCAL_REPLAY.json']:
        path = HERE / name
        if not path.exists():
            continue
        audit = json.loads(path.read_text())
        if audit['status'] == 'passed' and audit['confirmation_plan_sha256'] == receipt['confirmation_plan_sha256']:
            report['local_independent_audit'] = dict(assignments=audit['assignments'], source=name)
            break
    local_raw = HERE / 'CONFIRMATION_LOCAL_RAW_CHECK.json'
    if local_raw.exists():
        check = json.loads(local_raw.read_text())
        assert check['raw_manifest_sha256'] == hashlib.sha256((HERE / 'CONFIRMATION_RAW_MANIFEST.json').read_bytes()).hexdigest()
        assert check['verifier_sha256'] == hashlib.sha256((HERE / 'seal_confirmation.py').read_bytes()).hexdigest()
        report['local_raw_archive_verification'] = dict(status=check['status'],
            file_count=check['file_count'], total_bytes=check['total_bytes'],
            captured_utc=check['captured_utc'], source=local_raw.name)
    report['partial_policy_rankings_reported'] = False
    analysis_check = HERE / 'CONFIRMATION_ANALYSIS_REPLAY.json'
    if analysis_check.exists():
        report['independent_analysis_verification'] = json.loads(analysis_check.read_text())['status']
    if snapshot:
        folder = HERE / 'setup-evidence/confirmation'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'accounting.psv').write_text(process.stdout)
        (folder / 'capture.json').write_text(json.dumps(dict(command=command, stderr=process.stderr), indent=2) + '\n')
        (HERE / 'CONFIRMATION_PROGRESS.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--copy', action='store_true')
    parser.add_argument('--snapshot', action='store_true')
    args = parser.parse_args()
    main(args.copy, args.snapshot)
