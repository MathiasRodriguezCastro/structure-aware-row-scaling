#!/usr/bin/env python3
"""Register and queue one independent check after the original terminal stages."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import subprocess
from verify_confirmation_analysis import HERE, ROOT, digest, load


def write(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def main(register_only=False):
    plan = load(HERE / 'CONFIRMATION_PLAN.json')
    receipt = load(HERE / 'CONFIRMATION_SUBMISSION.json')
    check = load(HERE / 'INDEPENDENT_ANALYSIS_CHECK.json')
    assert check['status'] == 'passed' and check['no_benchmark_outcomes_used']
    assert check['verifier_sha256'] == digest(HERE / 'verify_confirmation_analysis.py')
    assert check['source_sha256'] == digest(HERE / 'check_independent_analysis.py')
    assert receipt['confirmation_plan_sha256'] == digest(HERE / 'CONFIRMATION_PLAN.json')
    for name, expected in plan['dependencies'].items():
        assert digest(ROOT / name) == expected, name
    sources = ['verify_confirmation_analysis.py', 'check_independent_analysis.py',
        'INDEPENDENT_ANALYSIS_CHECK.json', 'launch_confirmation_analysis_check.py',
        'cluster/verify_confirmation_analysis.slurm', 'analyze_confirmation.py',
        'collect_confirmation.py', 'seal_confirmation.py']
    source_hashes = {(HERE / name).relative_to(ROOT).as_posix(): digest(HERE / name) for name in sources}
    registration = dict(date='2026-10-20', confirmation_plan_sha256=digest(HERE / 'CONFIRMATION_PLAN.json'),
        sources=source_hashes, additional_MIP_calls=0, additional_LP_calls=0,
        scientific_design_modified=False, primary_analysis_modified=False,
        purpose='Independent reproduction of the already registered aggregates and parent bootstrap; no new estimand.',
        inputs_must_be_complete_and_independently_replayed=True,
        verify_complete_raw_seal_before_statistics=True,
        float_comparison_tolerance=dict(relative=1e-10, absolute=1e-12),
        bootstrap_resamples=100000, bootstrap_unit='whole parent with fixed diagnostic mask',
        maximum_comparisons=48, maximum_primary_bootstrap_intervals=80,
        threads=1, memory_GiB=4, simultaneous_benchmark_solves_added=0,
        predecessor_jobs={stage: receipt['jobs'][stage]['job_id'] for stage in ['analysis', 'seal']})
    target = HERE / 'CONFIRMATION_ANALYSIS_VALIDATION_PLAN.json'
    if target.exists():
        assert load(target) == registration, 'An immutable validation registration already exists.'
    else:
        write(target, registration)
    if register_only:
        print('Independent final-analysis validation registered; no job submitted.')
        return
    env = dict(os.environ, LC_ALL='C')
    files = list(source_hashes) + [target.relative_to(ROOT).as_posix()]
    subprocess.run(['rsync', '-rlt', '--relative', '-e', 'ssh -p 10022 -o BatchMode=yes -o ConnectTimeout=15',
        *files, 'mathiasr@cluster.uy:' + receipt['remote_repository'] + '/'], cwd=ROOT, check=True, env=env)
    submitted = HERE / 'CONFIRMATION_ANALYSIS_VALIDATION_SUBMISSION.json'
    if submitted.exists():
        assert load(submitted)['validation_plan_sha256'] == digest(target)
        print('Independent final-analysis check already submitted:', load(submitted)['job_id'])
        return
    remote = receipt['remote_repository']
    log_root = str(Path(remote).parent / 'logs')
    predecessors = ':'.join(registration['predecessor_jobs'].values())
    command = ['sbatch', '--parsable', '--chdir=' + remote,
        '--dependency=afterany:' + predecessors,
        '--output=' + log_root + '/confirmation-analysis-check-%j.out',
        '--error=' + log_root + '/confirmation-analysis-check-%j.err',
        remote + '/exploration/orf-confirmatory-extension-20261019/cluster/verify_confirmation_analysis.slurm', remote]
    process = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15',
        'mathiasr@login.cluster.uy', shlex.join(command)], text=True, capture_output=True,
        check=True, timeout=60, env=env)
    job = process.stdout.strip().split(';')[0]
    assert job.isdigit(), process.stdout
    record = dict(job_id=job, command=command, submitted_utc=datetime.now(timezone.utc).isoformat(),
                  validation_plan_sha256=digest(target), additional_MIP_calls=0, additional_LP_calls=0)
    write(submitted, record)
    subprocess.run(['rsync', '-rlt', '-e', 'ssh -p 10022 -o BatchMode=yes -o ConnectTimeout=15',
        str(submitted), 'mathiasr@cluster.uy:' + remote + '/exploration/orf-confirmatory-extension-20261019/'],
        check=True, env=env)
    print('Independent final-analysis check submitted:', job, flush=True)


if __name__ == '__main__':
    import argparse
    import sys
    if sys.flags.optimize:
        raise RuntimeError('Run without -O; integrity assertions are required.')
    parser = argparse.ArgumentParser()
    parser.add_argument('--register-only', action='store_true')
    main(parser.parse_args().register_only)
