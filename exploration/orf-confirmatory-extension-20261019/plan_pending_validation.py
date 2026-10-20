#!/usr/bin/env python3
"""Freeze the explicitly requested continuation, leaving the closed pilot immutable."""
import random
from runner import HERE, ROOT, load, save, sha


def main():
    destination = HERE / 'PENDING_VALIDATION_PLAN.json'
    assert not destination.exists(), 'A registered continuation already exists.'
    pilot = load(HERE / 'PILOT_PLAN.json')
    for name, digest in pilot['dependencies'].items():
        assert sha(ROOT / name) == digest, name
    data = load(HERE / 'MODEL_PREPARATION.json')['models']
    names = sorted(n for n, d in data.items() if d['role'] == 'confirmation')
    random.Random(2026102001).shuffle(names)
    assert len(names) == 160 and len({data[n]['parent_id'] for n in names}) == 40
    assessment = load(HERE / 'BASE_RESOURCE_ASSESSMENT.json')
    jobs = []
    for j in assessment['proposed_120_second_Base_only_jobs']:
        d = data[j['instance']]
        jobs.append(dict(id=j['instance'] + '-' + j['solver'] + '-Base-s401',
            instance=j['instance'], solver=j['solver'], policy='Base', seed=401,
            stratum=f"{d['family']}-h{d['horizon']}-{j['solver']}"))
    assert len(jobs) == len({j['id'] for j in jobs}) == 7
    dependencies = dict(pilot['dependencies'])
    for name in ['PENDING_VALIDATION_PROTOCOL.md', 'continue_validation.py',
                 'plan_pending_validation.py', 'cluster/continue_validation.slurm',
                 'PILOT_CLOSURE.json', 'BASE_RESOURCE_ASSESSMENT.json',
                 'FACTOR_PORTABILITY-Haswell-all.json', 'STRUCTURAL_FEASIBILITY_AUDIT.json',
                 'STRUCTURAL_CERTIFICATE_REPLAY.json']:
        path = HERE / name
        dependencies[path.relative_to(ROOT).as_posix()] = sha(path)
    infeasible = load(HERE / 'STRUCTURAL_FEASIBILITY_AUDIT.json')['certified_infeasible_instances']
    save(destination, dict(stage='Base calibration and common references only', date='2026-10-20',
        parent_commit='4788582d870a3f5fd143763b16b3c23058a65d85',
        immutable_pilot_plan_sha256=sha(HERE / 'PILOT_PLAN.json'),
        calibration_jobs=jobs, calibration_caps_seconds=[120, 300],
        calibration_native_gap_stop_target=.8, maximum_calibration_MIP_calls=14,
        calibration_at_ceiling_keeps_unmet_target_and_censoring=True,
        confirmation_instances=names, reference_order_seed=2026102001,
        certified_infeasible_confirmation_models=sorted(set(names) & set(infeasible)),
        reference_solver_order=['gurobi', 'cplex'], reference_seed=389,
        reference_MIP_limit_seconds=120, reference_LP_limit_seconds=120,
        reference_LP_simplifier=0, maximum_reference_MIP_calls=318,
        maximum_reference_LP_calls=318, reference_is_certified_optimum=False,
        threads=4, memory_GiB=8, simultaneous_MIP_processes=1,
        dependencies=dependencies, policy_ranking_used=False,
        confirmation_comparative_assignments_submitted=0, manuscript_modified=False,
        original_generator_modified=False))
    print('Registered 7 Base calibration cases and 160 common-reference identities.')


if __name__ == '__main__':
    main()
