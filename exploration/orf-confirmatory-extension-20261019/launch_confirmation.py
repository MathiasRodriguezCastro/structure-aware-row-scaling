#!/usr/bin/env python3
"""Transfer the frozen design and submit its gated serial array exactly once."""
from datetime import datetime, timezone
import os
import shlex
import subprocess
from runner import HERE, ROOT, load, save, sha

REMOTE = '/clusteruy/home/mathiasr/row-scaling-orf-extension-20261019'
TASK_ROOT = REMOTE + '/repository'
SUB = 'exploration/orf-confirmatory-extension-20261019'


def main():
    plan = load(HERE / 'CONFIRMATION_PLAN.json')
    assert plan['registered_assignments'] == 3840 and len(plan['blocks']) == 480
    for name, digest in plan['dependencies'].items():
        assert sha(ROOT / name) == digest, name
    receipt = HERE / 'CONFIRMATION_SUBMISSION.json'
    record = load(receipt) if receipt.exists() else dict(confirmation_plan_sha256=sha(HERE / 'CONFIRMATION_PLAN.json'),
        jobs={}, registered_assignments=3840, simultaneous_MIP_processes=1,
        remote_repository=TASK_ROOT, scientific_parent_modified=False)
    assert record['confirmation_plan_sha256'] == sha(HERE / 'CONFIRMATION_PLAN.json')
    # Upload only sources/evidence; the complete unchanged inputs and reference history already exist remotely.
    files = [p for p in plan['dependencies'] if p.startswith(SUB + '/') and not '/models/' in p]
    files.append(SUB + '/CONFIRMATION_PLAN.json')
    subprocess.run(['rsync', '-rlt', '--relative', '-e', 'ssh -p 10022 -o BatchMode=yes -o ConnectTimeout=15',
        *files, 'mathiasr@cluster.uy:' + TASK_ROOT + '/'], cwd=ROOT, check=True,
        env=dict(os.environ, LC_ALL='C'))
    stages = [('gate', None, 'afterok', '00:30:00'),
              ('first_block', 'gate', 'afterok', '02:00:00'),
              ('array', 'first_block', 'afterok', '02:00:00'),
              ('collection', 'array', 'afterany', '00:30:00'),
              ('analysis', 'collection', 'afterok', '01:00:00'),
              ('seal', 'analysis', 'afterany', '01:00:00')]
    for name, predecessor, condition, limit in stages:
        if name in record['jobs']:
            continue
        stage = dict(array='run', first_block='run', collection='collect', analysis='analyze').get(name, name)
        command = ['sbatch', '--parsable', '--chdir=' + TASK_ROOT, '--time=' + limit,
            '--output=' + REMOTE + '/logs/confirmation-' + name + '-%A_%a.out',
            '--error=' + REMOTE + '/logs/confirmation-' + name + '-%A_%a.err']
        if predecessor:
            command += ['--dependency=' + condition + ':' + record['jobs'][predecessor]['job_id']]
        if name == 'array':
            command += ['--array=1-479%1']
        elif name == 'first_block':
            command += ['--array=0-0%1']
        elif name != 'gate':
            command += ['--cpus-per-task=1']
        command += [TASK_ROOT + '/' + SUB + '/cluster/confirmation.slurm', TASK_ROOT, stage]
        process = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15',
            'mathiasr@login.cluster.uy', shlex.join(command)], text=True, capture_output=True,
            check=True, timeout=60, env=dict(os.environ, LC_ALL='C'))
        job = process.stdout.strip().split(';')[0]
        assert job.isdigit(), process.stdout
        record['jobs'][name] = dict(job_id=job, command=command, submitted_utc=datetime.now(timezone.utc).isoformat())
        record['comparative_assignments_submitted'] = 3840 if 'array' in record['jobs'] else 8 if 'first_block' in record['jobs'] else 0
        save(receipt, record)
        print(name, job, flush=True)
    subprocess.run(['rsync', '-rlt', '-e', 'ssh -p 10022 -o BatchMode=yes -o ConnectTimeout=15',
        str(receipt), 'mathiasr@cluster.uy:' + TASK_ROOT + '/' + SUB + '/'], check=True,
        env=dict(os.environ, LC_ALL='C'))


if __name__ == '__main__':
    import sys
    if sys.flags.optimize:
        raise RuntimeError('Run without -O; integrity assertions are required.')
    main()
