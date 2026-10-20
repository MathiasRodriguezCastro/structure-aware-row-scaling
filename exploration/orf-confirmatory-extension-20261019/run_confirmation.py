#!/usr/bin/env python3
"""Confirmation workers reuse the frozen pilot's generator, policies and native calls."""
import time
IMPORTED = time.perf_counter()
import argparse
from fractions import Fraction as Q
import math
import os
import resource
import subprocess
import sys

import numpy as np
from runner import HERE, ROOT, load, save, sha, library, generate, native, witness_feasible
from verify_reference_witnesses_stdlib import read_model, check_point

PLAN = HERE / 'CONFIRMATION_PLAN.json'


def checked_plan():
    plan = load(PLAN)
    for name, digest in plan['dependencies'].items():
        assert sha(ROOT / name) == digest, 'Registered dependency changed: ' + name
    for name, value in plan['runtime'].items():
        assert os.environ.get(name) == value, name
    return plan


def worker(job):
    started = float(os.environ.get('ORF_CONFIRMATION_STARTED', IMPORTED))
    folder = HERE / 'confirmation-runs' / job['id']
    folder.mkdir(parents=True, exist_ok=False)
    result = dict(job=job, stage='confirmation', status='failed',
                  confirmation_plan_sha256=sha(PLAN), preparation_time=None,
                  primary_confirmatory_observation=not job['diagnostic'])
    try:
        plan = checked_plan()
        assert any(job == item for block in plan['blocks'] for item in block['jobs'])
        metadata = load(HERE / 'MODEL_PREPARATION.json')['models'][job['instance']]
        follow = library(ROOT / 'exploration/orf-v15-verified-20261019/study.py', 'confirmation_frozen_helpers')
        a, front = follow.old.modules()
        base = generate(job['instance'], folder, metadata)
        rows, _ = a.original_rows(base)
        _, lp, _ = a.campaign.afb.read_lp(base)
        representation = 'Base' if job['policy'] == 'Base' else 'Budget-L2' if job['policy'] == 'Budget-L2' else 'L2'
        export = base
        if representation != 'Base':
            factors, selection = front.choose(rows, lp, 100 if representation == 'Budget-L2' else None)
            save(folder / 'selection.json', selection)
            if selection['incompatible_count']:
                result.update(status='abstained', abstained=True, selection=selection,
                              preparation_time=time.perf_counter() - started)
                return
            export = folder / 'scaled.lp'
            a.export_scaled(base, export, factors)
            assert sha(export) == metadata['policies'][representation]['export_sha256']
        _, elp, matrix = a.campaign.afb.read_lp(export)
        parsed, _ = follow.checker.parse(export)
        outcome, points, events, parameters, imported, errors = native(
            export, folder, job, started, elp, parsed, follow, matrix)
        solver_finished = time.perf_counter() - started
        np.savez_compressed(folder / 'candidates.npz', names=np.array(lp.col_names_),
                            x=np.array(points, dtype=float).reshape(-1, len(lp.col_names_)))
        model = follow.checker.canonical(base)
        written = read_model(base)
        assert set(model[1]) == set(written[1]) and model[3] == written[3]
        # Keep the native column order; retain all finite bounds written in Base.
        model = (model[0], {n: tuple(written[1][n]) for n in model[1]}, *model[2:])
        reference = None
        witness = None
        frozen = load(HERE / 'CONFIRMATION_PREREQUISITES_FROZEN.json')
        if not job['diagnostic']:
            reference_data = frozen['common_references'][job['instance']]
            ref = HERE / reference_data['proof_folder']
            assert sha(base) == reference_data['base_sha256']
            assert sha(ref / 'exact-witness.json') == reference_data['witness_sha256']
            certificate = load(ref / 'independent-certificate.json')
            witness = {n: Q(v) for n, v in load(ref / 'exact-witness.json').items()}
            reference = check_point(written, witness)
            assert reference == Q(certificate['objective_exact_fraction'])
        first = None
        verify_started = time.perf_counter()
        for index, (event, vector) in enumerate(zip(events, points)):
            point = {n: Q.from_float(float(v)) for n, v in zip(model[1], vector)}
            rounded = {n: Q(round(v)) if n in model[3] else v for n, v in point.items()}
            cost = model[5] + sum((c * rounded[n] for n, c in model[2].items()), Q(0))
            quality = None if reference is None else cost <= reference + Q.from_float(.001) * max(Q(1), abs(reference))
            audit = follow.verify(model, vector, follow.CONTRACTS['b100']) if quality or event['kind'] == 'final' else dict(objective_exact=str(cost))
            event.update(audit=audit, quality_pass=quality)
            if quality and all(audit.get(k, False) for k in ['physical_pass', 'domain_pass', 'other_rows_pass']) and first is None:
                first = dict(index=index, process_discovery=event['process_discovery'], work=event['work'],
                             offline_verified_available=time.perf_counter() - started)
        native_witness = False
        contradiction = None
        if witness is not None:
            native_witness = witness_feasible(follow.checker.canonical(export), witness)
            bound = outcome['reported_bound']
            if native_witness and bound is not None:
                contradiction = Q.from_float(bound) > reference + Q.from_float(max(1e-6, 8 * math.ulp(bound)))
        result.update(status='callback_error' if errors else 'completed', abstained=False,
            outcome=outcome, parameters=parameters, native_import=imported, events=events,
            first_qualified=first, reference_exact=str(reference) if reference is not None else None,
            quality_reference_available=reference is not None, reference_is_certified_optimum=False,
            exact_reference_feasible_for_imported_export=native_witness, bound_contradiction=contradiction,
            verification_seconds=time.perf_counter() - verify_started,
            solver_finished_process_seconds=solver_finished, preparation_time=outcome['solve_started'],
            callback_errors=errors, base_sha256=sha(base), export_sha256=sha(export),
            explicit_written_finite_bounds_checked=True)
    except Exception as error:
        result.update(error=type(error).__name__ + ': ' + str(error), failed_attempt_retained=True)
        raise
    finally:
        result.update(worker_total_seconds=time.perf_counter() - started,
            maximum_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            hostname=os.uname().nodename, slurm_job=os.environ.get('SLURM_JOB_ID'))
        save(folder / 'result.json', result)


def block(index):
    plan = checked_plan()
    jobs = plan['blocks'][index]['jobs']
    logs = HERE / 'confirmation-execution-logs'
    logs.mkdir(exist_ok=True)
    failures = []
    for job in jobs:
        assert not (HERE / 'confirmation-runs' / job['id']).exists(), 'Attempt already exists; no automatic overwrite or retry.'
        epoch = time.perf_counter()
        env = dict(os.environ, ORF_CONFIRMATION_STARTED=str(epoch))
        with (logs / (job['id'] + '.log')).open('w') as stream:
            try:
                process = subprocess.run([sys.executable, str(__file__), 'worker', job['id']],
                    cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT,
                    timeout=job['time_limit'] + 600)
                code = process.returncode
            except subprocess.TimeoutExpired:
                code = 124
        save(logs / (job['id'] + '.json'), dict(job=job, returncode=code,
            complete_process_seconds=time.perf_counter() - epoch, confirmation_plan_sha256=sha(PLAN)))
        if code:
            failures.append(job['id'])
        print(job['id'], 'exit', code, flush=True)
    subprocess.run([sys.executable, str(HERE / 'replay_confirmation.py'), str(index)],
                   cwd=ROOT, check=True)
    if failures:
        raise RuntimeError('Failed attempts retained after processing the complete block: ' + ', '.join(failures))


if __name__ == '__main__':
    if sys.flags.optimize:
        raise RuntimeError('Run without -O; integrity assertions are required.')
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['worker', 'block'])
    parser.add_argument('key')
    args = parser.parse_args()
    if args.stage == 'block':
        block(int(args.key))
    else:
        jobs = [j for b in load(PLAN)['blocks'] for j in b['jobs']]
        worker(next(j for j in jobs if j['id'] == args.key))
