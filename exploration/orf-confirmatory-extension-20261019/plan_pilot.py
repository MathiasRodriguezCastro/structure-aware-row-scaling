#!/usr/bin/env python3
"""Freeze a resource-only pilot and the counts of the unlaunched confirmation."""
import json
import random
from pathlib import Path
from runner import ROOT,HERE,sha,save,load


def main():
    data=load(HERE/'MODEL_PREPARATION.json')
    assert data['status']=='complete' and len(data['models'])==192 and not data['failures']
    assert load(HERE/'SOURCE_AUDIT.json')['status']=='passed_for_generated_population'
    env=load(HERE/'PREFLIGHT-final.json');assert env['status']=='passed'
    license_probe=load(HERE/'PREFLIGHT-license-fixed.json')
    assert license_probe['status']=='passed' and license_probe['variables']>2000
    assert license_probe['explicit_Gurobi_license_file_set']
    assert load(HERE/'DATA_GATE.json')['status']=='passed_for_generated_population'
    assert load(HERE/'HELD_OUT_AUDIT.json')['status']=='passed'
    assert load(HERE/'PRIOR_POLICY_EXPOSURE.json')['selection_unchanged']
    names=sorted(n for n,m in data['models'].items() if m['role']=='pilot')
    assert len(names)==32
    blocks=[];rng=random.Random(2026101917)
    for n in names:
        jobs=[]
        for solver,policies in [('gurobi',['Base','L2','Budget-L2','L2-NF3']),
                                ('cplex',['Base','L2','Budget-L2','L2-NumEmphasis'])]:
            for policy in policies:
                jobs.append(dict(instance=n,solver=solver,policy=policy,seed=401,time_limit=60.,
                    id=f'{n}-{solver}-s401-{policy}',mip_gap=.001,relative_quality_threshold=.001))
        rng.shuffle(jobs);blocks.append(dict(instance=n,jobs=jobs))
    rng.shuffle(blocks)
    frozen=load(HERE/'FROZEN_POLICIES.json')
    dependencies=dict(frozen['policy_source_sha256'])
    for p in [HERE/'runner.py',HERE/'references.py',HERE/'PROTOCOL.md',HERE/'MODEL_PREPARATION.json',
        HERE/'SOURCE_AUDIT.json',HERE/'HELD_OUT_AUDIT.json',HERE/'PRIOR_POLICY_EXPOSURE.json',
        HERE/'cluster/pilot.slurm',HERE/'PREFLIGHT-license-fixed.json',
        ROOT/'code/build-audit/SistemaElectrico',
        ROOT/'exploration/oms-followup-20261014/exact_dispatch_witness.py',
        ROOT/'exploration/oms-followup-20261014/tools/soplex-build/bin/soplex',
        ROOT/'exploration/oms-if1-workflow-20261015/study.py',
        ROOT/'exploration/orf-confirmatory-20261018/check.py']:
        dependencies[str(p.relative_to(ROOT))]=sha(p)
    value=dict(stage='resource_pilot_only',date='2026-10-19',parent_version='v1.5.0-orf-submission',
        data_population='historical-component generated bank; not new observed operational datasets',
        pilot_parents=8,pilot_models=32,pilot_MIP_assignments=256,blocks=blocks,
        reference_MIP_assignments=32,reference_exact_LP_attempts_at_most=32,
        threads=4,concurrency=1,solver_limit_seconds=60,reference_limit_seconds=120,
        requested_memory='site default: 2048 MiB per CPU; measure actual RSS in pilot',
        cluster_environment_sha256=sha(HERE/'PREFLIGHT-license-fixed.json'),dependencies=dependencies,
        quality_unknown_if_reference_unavailable=True,
        pilot_used_for_policy_selection=False,pilot_used_as_confirmatory_evidence=False,
        confirmatory_assignments_if_all_later_gates_pass=3840,
        confirmation_started=False,confirmation_caps_frozen=False)
    target=HERE/'PILOT_PLAN.json'
    if target.exists():assert load(target)==value,'Frozen pilot differs; register an amendment'
    else:save(target,value)
    print('Frozen 32 reference assignments and 256 resource-only pilot assignments; confirmation not launched.')


if __name__=='__main__':main()
