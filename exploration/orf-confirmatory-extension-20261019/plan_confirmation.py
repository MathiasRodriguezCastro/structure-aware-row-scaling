#!/usr/bin/env python3
"""Freeze the exact Cartesian confirmation design before any comparative solve."""
from collections import Counter
import itertools
import random
from runner import HERE, ROOT, load, save, sha


def main():
    frozen = load(HERE / 'CONFIRMATION_PREREQUISITES_FROZEN.json')
    assert frozen['status'] == 'prerequisites_complete' and len(frozen['common_references']) == 159
    assert frozen['confirmation_comparative_assignments_submitted'] == 0
    assert load(HERE / 'CONFIRMATION_EXECUTION_CHECK.json')['status'] == 'passed'
    assert load(HERE / 'CONFIRMATION_EXECUTION_CHECK.json')['source_sha256'] == sha(HERE / 'check_confirmation_execution.py')
    analysis_check = load(HERE / 'CONFIRMATION_ANALYSIS_CHECK.json')
    assert analysis_check['status'] == 'passed'
    assert analysis_check['analyzer_sha256'] == sha(HERE / 'analyze_confirmation.py')
    for name, digest in frozen['hashes'].items():
        assert sha(HERE / name) == digest, name
    data = load(HERE / 'MODEL_PREPARATION.json')['models']
    names = sorted(n for n, m in data.items() if m['role'] == 'confirmation')
    assert len(names) == 160 and len({data[n]['parent_id'] for n in names}) == 40
    caps = {(r['family'], r['horizon'], r['solver']): r['cap_seconds'] for r in frozen['caps']}
    rng = random.Random(2026102017)
    diagnostic = set(frozen['eligibility']['diagnostic'])
    blocks = []
    for name, seed in itertools.product(names, [401, 457, 503]):
        metadata = data[name]
        jobs = []
        for solver, numerical in [('gurobi', 'L2-NF3'), ('cplex', 'L2-NumEmphasis')]:
            for policy in ['Base', 'L2', 'Budget-L2', numerical]:
                jobs.append(dict(id=f'{name}-{solver}-s{seed}-{policy}', instance=name, seed=seed,
                    parent_id=metadata['parent_id'], family=metadata['family'], horizon=metadata['horizon'],
                    solver=solver, policy=policy, time_limit=caps[metadata['family'], metadata['horizon'], solver],
                    mip_gap=.001, relative_quality_threshold=.001, diagnostic=name in diagnostic))
        rng.shuffle(jobs)
        blocks.append(dict(instance=name, seed=seed, diagnostic=name in diagnostic, jobs=jobs))
    rng.shuffle(blocks)
    jobs = [j for b in blocks for j in b['jobs']]
    assert len(jobs) == len({j['id'] for j in jobs}) == 3840
    assert sum(j['diagnostic'] for j in jobs) == 24
    assert all(count == 24 for count in Counter(j['instance'] for j in jobs).values())
    dependencies = dict(load(HERE / 'PENDING_VALIDATION_PLAN.json')['dependencies'])
    dependencies.update({str((HERE / n).relative_to(ROOT)): digest for n, digest in frozen['hashes'].items()})
    sources = ['CONFIRMATION_PREREQUISITES_FROZEN.json', 'CONFIRMATION_EXECUTION_PROTOCOL.md',
        'CONFIRMATION_EXECUTION_CHECK.json', 'CONFIRMATION_ANALYSIS_CHECK.json',
        'check_confirmation_analysis.py', 'plan_confirmation.py', 'run_confirmation.py',
        'replay_confirmation.py', 'collect_confirmation.py', 'analyze_confirmation.py',
        'seal_confirmation.py', 'check_confirmation_execution.py', 'confirmation_gate.py',
        'cluster/confirmation.slurm', 'cluster/license_probe.py', 'launch_confirmation.py', 'replay_pilot.py']
    for name in sources:
        path = HERE / name
        dependencies[path.relative_to(ROOT).as_posix()] = sha(path)
    amendment_path = HERE / 'CONFIRMATION_EXECUTION_AMENDMENT.json'
    if amendment_path.exists():
        amendment = load(amendment_path)
        assert amendment['assignment_order_caps_policies_analysis_unchanged']
        assert amendment['corrected_wrapper_sha256'] == sha(HERE / 'cluster/confirmation.slurm')
        for name, expected in amendment['archived_evidence_sha256'].items():
            path = HERE / name
            assert sha(path) == expected
            dependencies[path.relative_to(ROOT).as_posix()] = expected
        dependencies[amendment_path.relative_to(ROOT).as_posix()] = sha(amendment_path)
    for name in names:
        path = HERE / 'models' / name / 'input.txt'
        dependencies[path.relative_to(ROOT).as_posix()] = sha(path)
    result = dict(stage='confirmation', date='2026-10-20', scientific_parent='2fbb5f14',
        prerequisite_freeze_sha256=sha(HERE / 'CONFIRMATION_PREREQUISITES_FROZEN.json'),
        registered_assignments=3840, quality_evaluable_assignments=3816, diagnostic_assignments=24,
        blocks=blocks, block_order_seed=2026102017, threads=4, memory_GiB=8,
        simultaneous_MIP_processes=1, cap_rules=frozen['caps'], dependencies=dependencies,
        runtime=dict(OPENBLAS_CORETYPE='Haswell', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', PYTHONINTMAXSTRDIGITS='0'),
        analysis=dict(primary_comparison='Budget-L2/L2 separately by solver', primary_metric='postsolve verified-availability PAR2',
            bootstrap_unit='complete parent including nested horizons, seeds and common eligibility mask',
            bootstrap_resamples=100000, bootstrap_seed=2026102021, marginal_confidence=.95),
        technical_gate_LP_calls=2, technical_gate_MIP_calls=0,
        original_generator_modified=False, submission_modified=False, new_reference_acquisitions_allowed=False)
    if amendment_path.exists():
        import hashlib
        import json
        design = {k: result[k] for k in ['blocks','cap_rules','analysis','threads','memory_GiB','runtime','simultaneous_MIP_processes']}
        assert hashlib.sha256(json.dumps(design,sort_keys=True).encode()).hexdigest() == amendment['scientific_design_sha256']
        result['execution_amendment_sha256'] = sha(amendment_path)
    destination = HERE / 'CONFIRMATION_PLAN.json'
    if destination.exists():
        assert load(destination) == result, 'Immutable confirmation plan differs; retain it and register an amendment.'
    else:
        save(destination, result)
    print('Frozen:', len(blocks), 'blocks,', len(jobs), 'assignments; no solve performed.')


if __name__ == '__main__':
    import sys
    if sys.flags.optimize:
        raise RuntimeError('Run without -O; integrity assertions are required.')
    main()
