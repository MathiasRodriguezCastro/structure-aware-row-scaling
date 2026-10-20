#!/usr/bin/env python3
"""Bounded exact-feasibility recovery using saved Base patterns; zero new MIPs."""
import argparse
from fractions import Fraction as Q
from pathlib import Path
import shutil
import subprocess
import sys
import time
import numpy as np
from runner import HERE, ROOT, load, save, sha, library
from verify_reference_witnesses_stdlib import read_model, check_point

PLAN = HERE / 'REFERENCE_FEASIBILITY_RECOVERY_PLAN.json'


def checked_plan():
    plan = load(PLAN)
    for name, digest in plan['dependencies'].items():
        assert sha(ROOT / name) == digest, name
    assert load(HERE/'CONFIRMATION_REFERENCE_REPORT.json')['status'] == 'completed'
    return plan


def feasibility_text(model, mapping, text, ceiling, decimal):
    constant = sum((model[2].get(n,Q(0))*Q(value) for n,value in mapping['integers'].items()),Q(0))
    body = text.split('Subject To\n',1)[1]
    rows, bounds = body.split('Bounds\n',1)
    alias = next(iter(mapping['aliases'].values()))
    lines = ['Minimize\n obj:\n  +0 '+alias+'\nSubject To\n',rows,' reference_cost_ceiling:\n']
    for name, coefficient in model[2].items():
        if name not in mapping['integers'] and coefficient:
            lines.append('  '+('+' if coefficient>=0 else '')+decimal(coefficient)+' '+mapping['aliases'][name]+'\n')
    lines += ['  <= '+decimal(ceiling-constant)+'\nBounds\n',bounds]
    recovery_text = ''.join(lines)
    assert recovery_text.split('Subject To\n',1)[1].split(' reference_cost_ceiling:\n',1)[0] == rows
    assert recovery_text.split('Bounds\n',1)[1] == bounds
    return recovery_text, body


def recover(index):
    plan = checked_plan()
    name = plan['models'][index]
    original = load(HERE/'confirmation-reference-acquisition'/name/'result.json')
    assert original['status'] == 'unknown'
    root = HERE/'confirmation-reference-recovery'/name
    root.mkdir(parents=True,exist_ok=False)
    started = time.perf_counter()
    result = dict(instance=name, status='unknown', attempts=[], additional_MIP_calls=0,
                  additional_LP_calls=0, recovery_plan_sha256=sha(PLAN))
    seen = set()
    try:
        sealed = {r['path']:r['sha256'] for r in load(HERE/'PENDING_RAW_MANIFEST.json')['files']}
        base = HERE/'models'/name/'Base.lp'
        assert sha(base) == sealed[base.relative_to(HERE).as_posix()]
        model = read_model(base)
        exact = library(ROOT/'exploration/oms-followup-20261014/exact_dispatch_witness.py',
                        'confirmation_feasibility_exact')
        for solver in ['gurobi','cplex']:
            old = HERE/'confirmation-reference-acquisition'/name/solver/'exact'
            if not (old/'mapping.json').exists() or not (old/'fixed-original-binary64.lp').exists():
                continue
            mapping = load(old/'mapping.json')
            for original_input in [old/'mapping.json',old/'fixed-original-binary64.lp',old/'exact.set']:
                assert sha(original_input) == sealed[original_input.relative_to(HERE).as_posix()]
            assert mapping['original_model_sha256'] == sha(base)
            assert mapping['fixed_lp_sha256'] == sha(old/'fixed-original-binary64.lp')
            solution = ROOT/mapping['saved_solution']
            assert sha(solution) == mapping['saved_solution_sha256']
            assert sha(solution) == sealed[solution.relative_to(HERE).as_posix()]
            with np.load(solution,allow_pickle=False) as arrays:
                point = {n:Q.from_float(float(v)) for n,v in zip(arrays['names'].tolist(),arrays['x'])}
            assert set(point) == set(model[1])
            for n, integer in mapping['integers'].items():
                assert round(point[n]) == integer
                point[n] = Q(integer)
            baseline = sum((c*point[n] for n,c in model[2].items()),Q(0))
            ceiling = baseline + Q.from_float(.001)*max(Q(1),abs(baseline))
            text = (old/'fixed-original-binary64.lp').read_text()
            recovery_text,body = feasibility_text(model,mapping,text,ceiling,exact.decimal)
            import hashlib
            signature = hashlib.sha256(recovery_text.encode()).hexdigest()
            if signature in seen:
                continue
            seen.add(signature)
            folder = root/solver
            folder.mkdir()
            (folder/'fixed-original-binary64.lp').write_text(recovery_text)
            save(folder/'mapping.json',dict(mapping, fixed_lp_sha256=signature,
                initial_fixed_lp_sha256=sha(old/'fixed-original-binary64.lp'),
                reference_feasibility_objective=0, original_cost_ceiling_exact=str(ceiling)))
            settings = folder/'exact.set'
            shutil.copyfile(old/'exact.set',settings)
            attempt = dict(source_solver=solver, baseline_candidate_cost_exact=str(baseline),
                cost_ceiling_exact=str(ceiling), status='unknown',
                original_fixed_lp_sha256=sha(old/'fixed-original-binary64.lp'),
                original_rows_and_bounds_sha256=hashlib.sha256(body.encode()).hexdigest(),
                feasibility_lp_sha256=signature)
            result['attempts'].append(attempt)
            binary = ROOT/'exploration/oms-followup-20261014/tools/soplex-build/bin/soplex'
            command = [str(binary),'--loadset='+str(settings),'-X='+str(folder/'rational-solution.txt'),
                       str(folder/'fixed-original-binary64.lp')]
            result['additional_LP_calls'] += 1
            provenance = dict(command=command, binary_sha256=sha(binary), settings_sha256=sha(settings),
                              optimizer_calls=1, original_model_modified=False)
            try:
                try:
                    with (folder/'soplex.log').open('w') as log:
                        process = subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=180)
                    provenance['returncode'] = process.returncode
                    assert process.returncode == 0, 'Exact feasibility LP process failed.'
                finally:
                    save(folder/'solver-provenance.json',provenance)
                rational = folder/'rational-solution.txt'
                assert rational.exists() and 'Primal solution (name, value):' in rational.read_text(), 'No exact primal vector; retained SoPlex log.'
                exact.check(folder)
                witness = {n:Q(v) for n,v in load(folder/'exact-witness.json').items()}
                objective = check_point(model,witness)
                certificate = load(folder/'independent-certificate.json')
                assert objective == Q(certificate['objective_exact_fraction'])
                assert objective <= ceiling
                attempt['status'] = 'verified_feasible'
                result.update(status='verified_feasible', objective_exact=str(objective),
                    original_model_sha256=sha(base), witness_sha256=sha(folder/'exact-witness.json'),
                    proof_folder=folder.relative_to(HERE).as_posix(),
                    cost_ceiling_exact=str(ceiling), source_solver=solver)
                break
            except Exception as error:
                attempt.update(status='unknown',error=type(error).__name__+': '+str(error))
    finally:
        result.update(total_seconds=time.perf_counter()-started, reference_is_certified_optimum=False,
                      policy_outcomes_used=False, original_model_modified=False)
        save(root/'result.json',result)
        print(name,result['status'],flush=True)


def collect():
    plan = checked_plan()
    rows = []
    missing = []
    for name in plan['models']:
        file = HERE/'confirmation-reference-recovery'/name/'result.json'
        if file.exists():
            record = load(file)
            assert record['recovery_plan_sha256'] == sha(PLAN)
            rows.append(record)
        else:
            missing.append(name)
    save(HERE/'REFERENCE_FEASIBILITY_RECOVERY_REPORT.json',dict(
        status='completed' if not missing else 'incomplete', records=rows, missing_models=missing,
        additional_MIP_calls=0, additional_LP_calls=sum(r['additional_LP_calls'] for r in rows),
        recovered_references=sum(r['status']=='verified_feasible' for r in rows),
        unknown_models=[r['instance'] for r in rows if r['status']=='unknown'],
        recovery_plan_sha256=sha(PLAN), policy_outcomes_used=False, original_model_modified=False))


if __name__ == '__main__':
    if sys.flags.optimize:
        raise RuntimeError('Run without -O for exact verification.')
    parser = argparse.ArgumentParser()
    parser.add_argument('stage',choices=['worker','collect'])
    parser.add_argument('--index',type=int)
    args = parser.parse_args()
    recover(args.index) if args.stage=='worker' else collect()
