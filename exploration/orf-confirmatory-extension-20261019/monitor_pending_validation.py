#!/usr/bin/env python3
"""Lightweight scheduler reads; optionally transfer small result summaries on port 10022."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import shlex
import subprocess

HERE = Path(__file__).resolve().parent


def main(copy_results, snapshot):
    receipt = json.loads((HERE / 'PENDING_VALIDATION_SUBMISSION.json').read_text())
    identifiers = ','.join(r['job_id'] for r in receipt['jobs'].values())
    command = ['sacct', '-j', identifiers,
        '--format=JobID,State,ExitCode,Elapsed,AllocCPUS,MaxRSS,NodeList', '-n', '-P']
    process = subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',
        'mathiasr@login.cluster.uy', shlex.join(command)], text=True, capture_output=True, check=True)
    rows = [line.split('|') for line in process.stdout.splitlines() if line.strip()]
    status = {}
    for stage, item in receipt['jobs'].items():
        job = item['job_id']
        if stage == 'references':
            cases = [r for r in rows if re.fullmatch(re.escape(job) + r'_\d+', r[0])]
            counts = Counter(r[1] for r in cases)
            status[stage] = dict(states=dict(counts),
                pending_or_not_started=160-len(cases),
                active=[dict(index=int(r[0].split('_')[1]), state=r[1], elapsed=r[3])
                    for r in cases if r[1] not in ['COMPLETED','FAILED','CANCELLED','TIMEOUT','OUT_OF_MEMORY']])
        else:
            status[stage] = [dict(state=r[1], exit=r[2], elapsed=r[3]) for r in rows if r[0] == job]
    if snapshot:
        directory = HERE / 'setup-evidence/pending-validation'
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'accounting.psv').write_text(process.stdout)
        (directory / 'capture.json').write_text(json.dumps(dict(command=command, ssh_stderr=process.stderr),indent=2)+'\n')
    if copy_results:
        remote = '/clusteruy/home/mathiasr/row-scaling-orf-extension-20261019/repository/exploration/orf-confirmatory-extension-20261019/'
        destination = HERE / 'confirmation-reference-acquisition'
        destination.mkdir(exist_ok=True)
        subprocess.run(['rsync','-rlt','--include=*/','--include=result.json','--exclude=*',
            '-e','ssh -p 10022 -o BatchMode=yes -o ConnectTimeout=15',
            'mathiasr@cluster.uy:'+remote+'confirmation-reference-acquisition/',str(destination)+'/'], check=True)
    results = [json.loads(p.read_text()) for p in (HERE / 'confirmation-reference-acquisition').glob('*/result.json')]
    status['downloaded_reference_outcomes'] = dict(Counter(r['status'] for r in results))
    status['downloaded_unknown_models'] = [r['instance'] for r in results if r['status'] == 'unknown']
    print(json.dumps(status, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--copy-results', action='store_true')
    parser.add_argument('--snapshot', action='store_true')
    args = parser.parse_args()
    main(args.copy_results,args.snapshot)
