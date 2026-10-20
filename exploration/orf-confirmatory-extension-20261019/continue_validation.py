#!/usr/bin/env python3
"""Registered Base-only calibration and common-reference acquisition, not policy comparisons."""
import argparse
from collections import defaultdict
from fractions import Fraction as Q
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time

import numpy as np
from runner import HERE, ROOT, load, save, sha, library, native

PLAN = HERE / 'PENDING_VALIDATION_PLAN.json'


def checked_plan():
    plan = load(PLAN)
    for name, digest in plan['dependencies'].items():
        assert sha(ROOT / name) == digest, 'Registered dependency changed: ' + name
    assert os.environ.get('OPENBLAS_CORETYPE') == 'Haswell'
    assert os.environ.get('OPENBLAS_NUM_THREADS') == '1'
    assert os.environ.get('OMP_NUM_THREADS') == '1'
    assert os.environ.get('PYTHONINTMAXSTRDIGITS') == '0'
    return plan


def helpers():
    follow = library(ROOT / 'exploration/orf-v15-verified-20261019/study.py', 'pending_validation_helpers')
    a, _ = follow.old.modules()
    return follow, a


def base_native(name, folder, solver, seed, limit):
    follow, a = helpers()
    base = HERE / 'models' / name / 'Base.lp'
    metadata = load(HERE / 'MODEL_PREPARATION.json')['models'][name]
    assert sha(base) == metadata['base_sha256']
    _, lp, matrix = a.campaign.afb.read_lp(base)
    parsed, _ = follow.checker.parse(base)
    job = dict(instance=name, policy='Base', solver=solver, seed=seed, time_limit=limit)
    started = time.perf_counter()
    outcome, points, events, parameters, imported, errors = native(
        base, folder, job, started, lp, parsed, follow, matrix)
    np.savez_compressed(folder / 'candidates.npz', names=np.array(lp.col_names_),
                        x=np.array(points, dtype=float).reshape(-1, len(lp.col_names_)))
    result = dict(job=job, outcome=outcome, events=events, parameters=parameters,
                  native_import=imported, callback_errors=errors, optimization_calls=1,
                  base_sha256=sha(base), native_process_seconds=time.perf_counter() - started)
    save(folder / 'native-result.json', result)
    assert not errors, 'Native callback errors retained.'
    return result, lp, points


def admit():
    plan = checked_plan()
    data = load(HERE / 'MODEL_PREPARATION.json')['models']
    assert load(HERE / 'FACTOR_PORTABILITY-Haswell-all.json')['status'] == 'passed'
    records = []
    for name in plan['confirmation_instances']:
        destination = HERE / 'models' / name / 'Base.lp'
        source = HERE / 'factor-portability' / 'Haswell-all' / name / 'Base.lp'
        assert sha(source) == data[name]['base_sha256']
        if destination.exists():
            assert sha(destination) == data[name]['base_sha256']
        else:
            shutil.copyfile(source, destination)
        assert sha(destination) == data[name]['base_sha256']
        assert sha(HERE / 'models' / name / 'input.txt') == data[name]['input_sha256']
        records.append(dict(instance=name, base_sha256=sha(destination)))
    assert len(records) == 160
    save(HERE / 'CONFIRMATION_BASE_ADMISSION.json', dict(status='passed', records=records,
        model_count=len(records), generator_modified=False, optimizer_calls=0,
        method='Copy the already byte-verified original Base export from the compute-node portability gate.'))
    print('Admitted 160 original confirmation Base models; no optimization.', flush=True)


def calibration_worker(index, cap):
    plan = checked_plan()
    job = plan['calibration_jobs'][index]
    assert cap in plan['calibration_caps_seconds']
    folder = HERE / 'resource-calibration' / f'cap-{cap}' / job['id']
    folder.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    result = dict(job=job, cap_seconds=cap, status='failed', policy_ranking_used=False)
    try:
        native_result, _, _ = base_native(job['instance'], folder, job['solver'], 401, float(cap))
        result.update(status='completed', native=native_result['outcome'])
    except Exception as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        result.update(worker_seconds=time.perf_counter() - started,
                      maximum_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                      hostname=os.uname().nodename, plan_sha256=sha(PLAN))
        save(folder / 'result.json', result)


def calibrate():
    plan = checked_plan()
    groups = defaultdict(list)
    for index, job in enumerate(plan['calibration_jobs']):
        groups[job['stratum']].append(index)
    remaining = set(groups)
    recommended = {}
    records = []
    log_root = HERE / 'resource-calibration'
    log_root.mkdir(exist_ok=True)
    for cap in plan['calibration_caps_seconds']:
        for stratum in sorted(remaining):
            results = []
            for index in groups[stratum]:
                job = plan['calibration_jobs'][index]
                result_path = log_root / f'cap-{cap}' / job['id'] / 'result.json'
                if result_path.exists():
                    result = load(result_path)
                    assert result['status'] == 'completed' and result['plan_sha256'] == sha(PLAN)
                else:
                    log = log_root / (job['id'] + f'-cap-{cap}.log')
                    with log.open('w') as stream:
                        subprocess.run([sys.executable, str(Path(__file__)), 'calibration-worker',
                            '--index', str(index), '--cap', str(cap)], stdout=stream,
                            stderr=subprocess.STDOUT, timeout=cap + 600, check=True)
                    result = load(result_path)
                results.append(result)
                print('Base calibration:', cap, job['id'], result['native']['status'], flush=True)
            completed = sum(r['native']['completed'] for r in results)
            target = completed / len(results) >= plan['calibration_native_gap_stop_target']
            records.append(dict(stratum=stratum, cap_seconds=cap, cases=len(results),
                native_gap_stops=completed, native_gap_stop_fraction=completed / len(results),
                operational_target_met=target, cases_repeated_in_full=True))
            if target or cap == plan['calibration_caps_seconds'][-1]:
                recommended[stratum] = dict(cap_seconds=cap, operational_target_met=target,
                    right_censoring_retained=not target)
        remaining -= set(recommended)
        save(HERE / 'BASE_CALIBRATION_REPORT.json', dict(
            status='completed' if not remaining else 'in_progress', records=records,
            recommended_caps=recommended, pending_strata=sorted(remaining),
            actual_MIP_calls=sum(r['cases'] for r in records), plan_sha256=sha(PLAN),
            policy_ranking_used=False, confirmation_launched=False,
            ceiling_rule='Stop at 300 seconds even if the 80% native-gap target is unmet; retain censoring explicitly.'))
    assert not remaining
    print('Base resource calibration completed; no confirmatory comparisons.', flush=True)


def exact_reference(base, solution, proof):
    exact = library(ROOT / 'exploration/oms-followup-20261014/exact_dispatch_witness.py', 'pending_exact_reference')
    independent = library(HERE / 'replay_pilot.py', 'pending_independent_reference')
    exact.prepare(proof, base, solution)
    settings = proof / 'exact.set'
    settings.write_text('int:syncmode = 1\nint:readmode = 1\nint:solvemode = 2\nint:checkmode = 2\n'
        'int:simplifier = 0\nreal:feastol = 0\nreal:opttol = 0\nreal:timelimit = 120\n')
    binary = ROOT / 'exploration/oms-followup-20261014/tools/soplex-build/bin/soplex'
    command = [str(binary), '--loadset=' + str(settings), '-X=' + str(proof / 'rational-solution.txt'),
               str(proof / 'fixed-original-binary64.lp')]
    provenance = dict(command=command, optimization_calls=1, binary_sha256=sha(binary),
                      settings_sha256=sha(settings), simplifier=0)
    try:
        with (proof / 'soplex.log').open('w') as stream:
            process = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=180)
        provenance['returncode'] = process.returncode
        assert process.returncode == 0, 'Exact-LP process failed.'
    finally:
        save(proof / 'solver-provenance.json', provenance)
    exact.check(proof)
    model = independent.library(ROOT / 'exploration/orf-confirmatory-20261018/check.py',
                                 'pending_independent_reader').canonical(base)
    values = {n: Q(v) for n, v in load(proof / 'exact-witness.json').items()}
    assert independent.exact_feasible(model, values)
    cost, _ = independent.candidate_cost(model, values)
    certificate = load(proof / 'independent-certificate.json')
    assert cost == Q(certificate['objective_exact_fraction'])
    assert certificate['witness_sha256'] == sha(proof / 'exact-witness.json')
    return certificate


def acquire_reference(index):
    plan = checked_plan()
    name = plan['confirmation_instances'][index]
    root = HERE / 'confirmation-reference-acquisition' / name
    root.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    result = dict(instance=name, status='unknown', attempts=[], reference_is_certified_optimum=False,
                  policy_outcomes_used=False, plan_sha256=sha(PLAN), MIP_calls=0, exact_LP_calls=0)
    try:
        if name in plan['certified_infeasible_confirmation_models']:
            result.update(status='certified_infeasible_diagnostic', quality_endpoint='not_applicable')
            return
        assert load(HERE / 'CONFIRMATION_BASE_ADMISSION.json')['status'] == 'passed'
        base = HERE / 'models' / name / 'Base.lp'
        for solver in plan['reference_solver_order']:
            folder = root / solver
            folder.mkdir()
            attempt = dict(solver=solver, status='unknown', MIP_calls=1, exact_LP_calls=0)
            result['MIP_calls'] += 1
            result['attempts'].append(attempt)
            try:
                record, lp, points = base_native(name, folder, solver, 389, 120.)
                attempt['native_status'] = record['outcome']['status']
                if not points:
                    attempt['status'] = 'unknown_no_incumbent'
                    continue
                solution = folder / 'solution.npz'
                np.savez_compressed(solution, names=np.array(lp.col_names_), x=np.array(points[-1]))
                proof = folder / 'exact'
                # Mark an LP call when its subprocess provenance exists; preparation
                # can reject an impossible fixed binary pattern before optimization.
                try:
                    certificate = exact_reference(base, solution, proof)
                finally:
                    calls = int((proof / 'solver-provenance.json').exists())
                    attempt['exact_LP_calls'] = calls
                    result['exact_LP_calls'] += calls
                destination = HERE / 'confirmation-references' / name
                destination.mkdir(parents=True, exist_ok=False)
                for filename in ['exact-witness.json', 'independent-certificate.json']:
                    shutil.copyfile(proof / filename, destination / filename)
                attempt['status'] = 'verified_feasible'
                result.update(status='verified_feasible', objective_exact=certificate['objective_exact_fraction'],
                    original_model_sha256=certificate['original_model_sha256'],
                    witness_sha256=certificate['witness_sha256'], source_solver=solver)
                break
            except Exception as error:
                attempt.update(status='unknown_retained_failure', error=type(error).__name__ + ': ' + str(error))
    finally:
        result.update(total_seconds=time.perf_counter() - started,
                      maximum_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                      hostname=os.uname().nodename)
        save(root / 'result.json', result)
        print(name, result['status'], flush=True)


def collect():
    plan = checked_plan()
    rows = []
    missing = []
    for name in plan['confirmation_instances']:
        path = HERE / 'confirmation-reference-acquisition' / name / 'result.json'
        if path.exists():
            result = load(path)
            assert result['plan_sha256'] == sha(PLAN)
            rows.append(result)
        else:
            missing.append(name)
    from collections import Counter
    save(HERE / 'CONFIRMATION_REFERENCE_REPORT.json', dict(
        status='completed' if not missing else 'incomplete', registered_models=160,
        recorded_models=len(rows), counts=dict(Counter(r['status'] for r in rows)), missing_models=missing,
        unknown_models=[r['instance'] for r in rows if r['status'] == 'unknown'],
        actual_MIP_calls=sum(r['MIP_calls'] for r in rows),
        actual_exact_LP_calls=sum(r['exact_LP_calls'] for r in rows),
        plan_sha256=sha(PLAN), reference_is_certified_optimum=False,
        confirmation_launched=False, policy_outcomes_used=False, records=rows))
    print('Common references:', len(rows), 'of 160 models.', flush=True)


def replay_references():
    plan = checked_plan()
    independent = library(HERE / 'replay_pilot.py', 'confirmation_reference_replay')
    reader = library(ROOT / 'exploration/orf-confirmatory-20261018/check.py', 'confirmation_reference_reader')
    records = []
    for name in plan['confirmation_instances']:
        result = load(HERE / 'confirmation-reference-acquisition' / name / 'result.json')
        if result['status'] != 'verified_feasible':
            records.append(dict(instance=name, status=result['status']))
            continue
        folder = HERE / 'confirmation-references' / name
        certificate = load(folder / 'independent-certificate.json')
        base = HERE / 'models' / name / 'Base.lp'
        assert sha(base) == certificate['original_model_sha256'] == result['original_model_sha256']
        assert sha(folder / 'exact-witness.json') == certificate['witness_sha256'] == result['witness_sha256']
        point = {n: Q(v) for n, v in load(folder / 'exact-witness.json').items()}
        model = reader.canonical(base)
        assert independent.exact_feasible(model, point), name
        cost, _ = independent.candidate_cost(model, point)
        assert cost == Q(result['objective_exact']) == Q(certificate['objective_exact_fraction'])
        records.append(dict(instance=name, status='verified_feasible',
            rows_checked=len(model[0]), variables_checked=len(model[1]), integers_checked=len(model[3]),
            base_sha256=sha(base), witness_sha256=sha(folder / 'exact-witness.json')))
    save(HERE / 'CONFIRMATION_REFERENCE_REPLAY.json', dict(status='passed', records=records,
        models_replayed=len(records), verified_feasible=sum(r['status']=='verified_feasible' for r in records),
        optimizer_calls=0, plan_sha256=sha(PLAN), optimality_certified=False))
    print('Independent reference replay passed:', len(records), 'models.', flush=True)


if __name__ == '__main__':
    if sys.flags.optimize:
        raise RuntimeError('Integrity assertions require Python without -O.')
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['admit', 'calibrate', 'calibration-worker', 'reference', 'collect', 'replay'])
    parser.add_argument('--index', type=int)
    parser.add_argument('--cap', type=int)
    args = parser.parse_args()
    if args.stage == 'calibration-worker':
        calibration_worker(args.index, args.cap)
    elif args.stage == 'reference':
        acquire_reference(args.index)
    else:
        {'admit': admit, 'calibrate': calibrate, 'collect': collect, 'replay': replay_references}[args.stage]()
