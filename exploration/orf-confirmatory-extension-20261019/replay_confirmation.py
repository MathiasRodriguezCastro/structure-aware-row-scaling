#!/usr/bin/env python3
"""Replay one complete confirmation block from saved candidates; zero solver calls."""
import argparse
from fractions import Fraction as Q
import math
import sys

import numpy as np
from runner import HERE, ROOT, load, save, sha, library
from replay_pilot import candidate_cost, candidate_audit, exact_feasible
from verify_reference_witnesses_stdlib import read_model, check_point


def replay(index):
    plan = load(HERE / 'CONFIRMATION_PLAN.json')
    for name, digest in plan['dependencies'].items():
        assert sha(ROOT / name) == digest, name
    block = plan['blocks'][index]
    metadata = load(HERE / 'MODEL_PREPARATION.json')['models'][block['instance']]
    base = HERE / 'models' / block['instance'] / 'Base.lp'
    assert sha(base) == metadata['base_sha256']
    reader = library(ROOT / 'exploration/orf-confirmatory-20261018/check.py', 'confirmation_independent_reader')
    model = reader.canonical(base)
    written = read_model(base)
    assert set(model[1]) == set(written[1]) and model[3] == written[3]
    model = (model[0], {n: tuple(written[1][n]) for n in model[1]}, *model[2:])
    reference = None
    witness = None
    if not block['diagnostic']:
        reference_data = load(HERE / 'CONFIRMATION_PREREQUISITES_FROZEN.json')['common_references'][block['instance']]
        ref = HERE / reference_data['proof_folder']
        assert sha(ref / 'exact-witness.json') == reference_data['witness_sha256']
        witness = {n: Q(v) for n, v in load(ref / 'exact-witness.json').items()}
        reference = check_point(written, witness)
        assert reference == Q(load(ref / 'independent-certificate.json')['objective_exact_fraction'])
    rows = []
    missing = []
    failed = []
    counts = dict(candidate_vectors=0, full_candidate_audits=0, exact_reference_checks=int(witness is not None))
    for job in block['jobs']:
        folder = HERE / 'confirmation-runs' / job['id']
        if not (folder / 'result.json').exists():
            missing.append(job['id'])
            continue
        result = load(folder / 'result.json')
        assert result['job'] == job and result['confirmation_plan_sha256'] == sha(HERE / 'CONFIRMATION_PLAN.json')
        timing_file = HERE / 'confirmation-execution-logs' / (job['id'] + '.json')
        assert timing_file.exists(), 'Missing complete-process clock.'
        timing = load(timing_file)
        assert timing['job'] == job and timing['confirmation_plan_sha256'] == result['confirmation_plan_sha256']
        assert timing['complete_process_seconds'] >= result['worker_total_seconds'] >= 0
        row = dict(job=job, status=result['status'], result_sha256=sha(folder / 'result.json'),
                   diagnostic=job['diagnostic'], quality_evaluable=reference is not None,
                   success=False, par2_seconds=None, preparation_seconds=result.get('preparation_time'),
                   complete_process_seconds=timing['complete_process_seconds'],
                   maximum_RSS_KiB=result['maximum_RSS_KiB'], returncode=timing['returncode'])
        if result['status'] == 'abstained':
            assert result['selection']['incompatible_count'] > 0 and timing['returncode'] == 0
            if reference is not None:
                row['par2_seconds'] = 2 * job['time_limit'] + result['preparation_time']
            rows.append(row)
            continue
        if result['status'] not in ['completed', 'callback_error']:
            failed.append(dict(job=job['id'], status=result['status'], error=result.get('error')))
            rows.append(row)
            continue
        assert sha(folder / 'Base.lp') == sha(base) == result['base_sha256']
        rep = 'Base' if job['policy'] == 'Base' else 'Budget-L2' if job['policy'] == 'Budget-L2' else 'L2'
        export = folder / ('Base.lp' if rep == 'Base' else 'scaled.lp')
        expected = metadata['base_sha256'] if rep == 'Base' else metadata['policies'][rep]['export_sha256']
        assert sha(export) == result['export_sha256'] == expected
        assert result['quality_reference_available'] == (reference is not None)
        assert result['reference_exact'] == (str(reference) if reference is not None else None)
        first = None
        final = None
        with np.load(folder / 'candidates.npz', allow_pickle=False) as arrays:
            names, vectors = arrays['names'].tolist(), arrays['x']
            assert len(names) == len(set(names)) and set(names) == set(model[1])
            assert vectors.shape == (len(result['events']), len(names)) and np.isfinite(vectors).all()
            for i, (event, vector) in enumerate(zip(result['events'], vectors)):
                point = {n: Q.from_float(float(v)) for n, v in zip(names, vector)}
                cost, rounded = candidate_cost(model, point)
                quality = None if reference is None else cost <= reference + Q.from_float(.001) * max(Q(1), abs(reference))
                assert event['quality_pass'] == quality and Q(event['audit']['objective_exact']) == cost
                if quality or event['kind'] == 'final':
                    audit = candidate_audit(model, point, rounded)
                    assert audit == event['audit'], (job['id'], i)
                    counts['full_candidate_audits'] += 1
                    accepted = all(audit[k] for k in ['physical_pass', 'domain_pass', 'other_rows_pass'])
                    if quality and accepted and first is None:
                        first = i
                    if event['kind'] == 'final':
                        final = dict(audit, primal_pass=accepted, quality_pass=quality)
            counts['candidate_vectors'] += len(vectors)
        assert (None if result['first_qualified'] is None else result['first_qualified']['index']) == first
        native_witness = False
        contradiction = None
        if witness is not None:
            native_witness = exact_feasible(reader.canonical(export), witness)
            bound = result['outcome']['reported_bound']
            if native_witness and bound is not None:
                contradiction = Q.from_float(bound) > reference + Q.from_float(max(1e-6, 8 * math.ulp(bound)))
        assert result['exact_reference_feasible_for_imported_export'] == native_witness
        assert result['bound_contradiction'] == contradiction
        assert result['preparation_time'] == result['outcome']['solve_started'] >= 0
        success = first is not None and result['status'] == 'completed' and timing['returncode'] == 0
        if success:
            available = result['first_qualified']['offline_verified_available']
            assert result['solver_finished_process_seconds'] <= available <= result['worker_total_seconds']
            assert result['events'][first]['process_discovery'] <= available
        if reference is not None:
            row['par2_seconds'] = result['first_qualified']['offline_verified_available'] if success else 2 * job['time_limit'] + result['preparation_time']
        if result['status'] == 'callback_error':
            failed.append(dict(job=job['id'], status=result['status']))
        row.update(success=success, final=final, solver_work=result['outcome']['work'],
            native_gap_stop=result['outcome']['completed'], native_status=result['outcome']['status'],
            native_gap=result['outcome']['reported_gap'], native_nodes=result['outcome']['nodes'],
            bound_contradiction=contradiction, bound_comparison_available=contradiction is not None,
            reference_exact=str(reference) if reference is not None else None,
            verified_available_seconds=result['first_qualified']['offline_verified_available'] if success else None,
            candidate_archive_sha256=sha(folder / 'candidates.npz'))
        rows.append(row)
    report = dict(status='passed' if not missing and not failed else 'execution_failures_retained',
        block=index, instance=block['instance'], seed=block['seed'], rows=rows, missing_jobs=missing,
        failed_jobs=failed, counts=counts, optimizer_calls=0, independent_candidate_arithmetic=True,
        explicit_written_finite_bounds_checked=True, confirmation_plan_sha256=sha(HERE / 'CONFIRMATION_PLAN.json'))
    save(HERE / 'confirmation-replay' / f'{index:03d}.json', report)
    print('Confirmation block replay:', index, report['status'], counts, flush=True)


if __name__ == '__main__':
    if sys.flags.optimize:
        raise RuntimeError('Run without -O; integrity assertions are required.')
    if hasattr(sys, 'set_int_max_str_digits'):
        sys.set_int_max_str_digits(0)
    parser = argparse.ArgumentParser()
    parser.add_argument('block', type=int)
    replay(parser.parse_args().block)
