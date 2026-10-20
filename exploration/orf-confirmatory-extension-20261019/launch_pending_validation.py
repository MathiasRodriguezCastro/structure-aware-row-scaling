#!/usr/bin/env python3
"""Submit each prerequisite once, with serial optimization and immediate receipts."""
from datetime import datetime, timezone
import shlex
import subprocess
from runner import HERE, ROOT, load, save, sha


def main():
    receipt = HERE / 'PENDING_VALIDATION_SUBMISSION.json'
    if receipt.exists():
        state = load(receipt)
        assert state['plan_sha256'] == sha(HERE / 'PENDING_VALIDATION_PLAN.json')
    else:
        state = dict(plan_sha256=sha(HERE / 'PENDING_VALIDATION_PLAN.json'), jobs={},
            simultaneous_MIP_processes=1, confirmation_comparative_assignments_submitted=0)
    remote = '/clusteruy/home/mathiasr/row-scaling-orf-extension-20261019'
    stages = [('admission', 'admit', None, '00:10:00'),
              ('calibration', 'calibrate', 'admission', '01:30:00'),
              ('references', 'reference', 'calibration', '00:20:00'),
              ('collection', 'collect', 'references', '00:10:00'),
              ('replay', 'replay', 'collection', '01:00:00')]
    for key, stage, predecessor, wall in stages:
        if key in state['jobs']:
            continue
        command = ['sbatch', '--parsable', '--time=' + wall,
            '--chdir=' + remote + '/repository',
            '--output=' + remote + '/logs/pending-' + key + '-%A_%a.out',
            '--error=' + remote + '/logs/pending-' + key + '-%A_%a.err']
        if predecessor:
            dependency = 'afterany' if stage == 'collect' else 'afterok'
            command.append('--dependency=' + dependency + ':' + state['jobs'][predecessor]['job_id'])
        if stage == 'reference':
            command.append('--array=0-159%1')
        command += [remote + '/repository/exploration/orf-confirmatory-extension-20261019/cluster/continue_validation.slurm',
                    remote + '/repository', stage]
        process = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15',
            'mathiasr@login.cluster.uy', shlex.join(command)], text=True, capture_output=True, check=True)
        job = process.stdout.strip()
        assert job.isdigit(), job
        state['jobs'][key] = dict(job_id=job, command=command,
            submitted_utc=datetime.now(timezone.utc).isoformat())
        save(receipt, state)
        print(key, job, flush=True)


if __name__ == '__main__':
    main()
