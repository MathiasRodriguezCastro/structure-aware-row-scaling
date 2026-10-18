#!/usr/bin/env python3
"""Conditional, interleaved fresh-process confirmation at the principal 100 m3 target."""
import argparse
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import time

import study as source

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=HERE/'confirmation'


def prepare():
    if (OUT/'design.json').exists():
        raise RuntimeError('confirmation already frozen')
    result=source.load(HERE/'VALIDATION.json')
    assert result['temporal_confirmation_gate']['100'], '100 m3 confirmation not qualified'
    d=source.load(HERE/'design.json')
    old=source.load(source.FRONT/'design.json')
    OUT.mkdir()
    # Block by (instance,seed), randomize the blocks and within-block treatment order.
    # All treatments run consecutively on the same shared host, in fresh processes.
    rng=random.Random(2026101819)
    blocks=[(n,s) for n in d['instances'] for s in d['seeds']]
    rng.shuffle(blocks)
    jobs=[]
    for n,s in blocks:
        policies=['Base','Base-tight','Budget-L2']
        rng.shuffle(policies)
        for p in policies:
            jobs.append(dict(instance=n,seed=s,policy=p,presolve=-1,
                budget=100 if p=='Budget-L2' else None,key='B100' if p=='Budget-L2' else 'Base',
                id=f'{n}-s{s}-{p}'))
    for n in d['instances']:
        folder=OUT/'models'/n
        folder.mkdir(parents=True)
        (folder/'input.txt').write_bytes((source.FRONT/'models'/n/'input.txt').read_bytes())
    (OUT/'witness-index.json').write_bytes((source.FRONT/'witness-index.json').read_bytes())
    deps=[HERE/'PROTOCOL.md',HERE/'confirmation.py',HERE/'check.py',HERE/'study.py',
          HERE/'design.json',HERE/'VALIDATION.json',HERE/'verified-runs.csv',
          OUT/'witness-index.json',*[(OUT/'models'/n/'input.txt') for n in d['instances']]]
    design=dict(date='2026-10-18',conditional=True,confirmation_target_m3=100,
        trigger='36 matched Base controls passed the fixed Work/quality gate at 100 m3',
        parameters=d['parameters'],jobs=jobs,instances=d['instances'],seeds=d['seeds'],
        power_budget_MW=.01,volume_budgets=[100],
        input_hashes=d['input_hashes'],inputs=old['inputs'],models=old['models'],
        base_witnesses=d['base_witnesses'],environment=d['environment'],
        dependencies={str(p.relative_to(ROOT)):source.sha(p) for p in deps},
        native_MIP_calls_assigned=54,new_LP_calls=0,
        timing_scope='fresh Python process through generator, any selector/export, native import/equality check, solve, point extraction, original-unit verification and result persistence',
        exclusions=['compilation','prior exact-witness acquisition','independent replay after all runs'],
        stop_rule='all 54 assignments; no adaptive additions, reruns or exclusions',
        prior_seed_reuse=True,same_known_models=True,shared_machine=True)
    source.dump(OUT/'design.json',design)
    print('Frozen conditional confirmation: 54 calls, 18 consecutive blocks',flush=True)


def worker(job_id,started):
    design=source.load(OUT/'design.json')
    job=next(j for j in design['jobs'] if j['id']==job_id)
    if job['policy']=='Budget-L2':
        runner=source.library(source.FRONT/'study.py','historical_budget_worker')
    else:
        runner=source.library(HERE/'study.py','unscaled_worker')
    runner.HERE=OUT
    runner.worker(job_id,started)


def run():
    d=source.load(OUT/'design.json')
    for p,h in d['dependencies'].items():
        assert source.sha(ROOT/p)==h,p
    records=[]
    target=OUT/'parent-timing.json'
    if target.exists():
        records=source.load(target)
    assert [r['job'] for r in records]==d['jobs'][:len(records)]
    assert all(r['returncode']==0 for r in records)
    for i,job in enumerate(d['jobs'][len(records):],len(records)+1):
        assert not (OUT/'runs'/job['id']).exists(), 'unrecorded attempt; amendment required'
        start=time.perf_counter()
        with (OUT/(job['id']+'-execution.log')).open('w') as log:
            try:
                p=subprocess.run([sys.executable,str(Path(__file__)),'worker',job['id']],
                    cwd=ROOT,env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'},
                    stdout=log,stderr=subprocess.STDOUT,timeout=240)
                rc=p.returncode
            except subprocess.TimeoutExpired:
                rc=124
        records.append(dict(job=job,returncode=rc,total_fresh_process_seconds=time.perf_counter()-start))
        source.dump(target,records)
        print(i,'/54',job['id'],'rc',rc,'seconds',round(records[-1]['total_fresh_process_seconds'],2),flush=True)
        if rc:
            raise RuntimeError('failure retained; amendment required')


def check():
    replay=source.library(HERE/'check.py','confirmation_reader_only')
    replay.HERE=OUT
    d=replay.load(OUT/'design.json')
    for p,h in d['dependencies'].items():
        assert source.sha(ROOT/p)==h,p
    timing=replay.load(OUT/'parent-timing.json')
    assert len(timing)==len(d['jobs'])==54
    assert [r['job'] for r in timing]==d['jobs']
    assert all(r['returncode']==0 for r in timing)
    old=replay.load(source.FRONT/'design.json')
    wi=replay.load(source.FRONT/'witness-index.json')
    witnesses={}
    for n in d['instances']:
        witnesses[n,'Base']=replay.check_witness(ROOT/d['base_witnesses'][n],source.FRONT/'models'/n/'Base.lp')
        w=wi[n+'/B100']
        while 'alias' in w:
            w=wi[w['alias']]
        witnesses[n,'Budget-L2']=replay.check_witness(ROOT/w['folder'],ROOT/old['models'][n+'/B100']['model'])
    previous=list(__import__('csv').DictReader((HERE/'verified-runs.csv').open()))
    records=[]
    for t in timing:
        j=t['job'];folder=OUT/'runs'/j['id']
        r=replay.load(folder/'result.json')
        assert r['job']==j
        assert sum(r['stages_seconds'].values())<=r['worker_internal_seconds_before_result']<=t['total_fresh_process_seconds']
        budget=j['policy']=='Budget-L2'
        model=source.FRONT/'models'/j['instance']/('B100.lp' if budget else 'Base.lp')
        rr=replay.audit(folder,model,witnesses[j['instance'],'Budget-L2' if budget else 'Base'],budget)
        assert len(rr)==1
        v=rr[0]
        v['total_seconds']=t['total_fresh_process_seconds']
        oldrow=next(p for p in previous if p['instance']==j['instance'] and p['seed']==str(j['seed']) and p['policy']==j['policy'] and p['budget']=='100')
        v['same_work_as_prior']=v['work']==float(oldrow['work'])
        v['same_status_as_prior']=v['status']==int(oldrow['status'])
        prior_folder=(source.FRONT/'runs'/f"{j['instance']}-P-1-s{j['seed']}-Budget-L2100") if budget else HERE/'runs'/j['id']
        prior=replay.load(prior_folder/'result.json')
        v['same_native_endpoint_as_prior']=all(r['outcome'][k]==prior['outcome'][k]
            for k in ['status','solutions','work','nodes','objective','bound'])
        with replay.np.load(folder/'solution.npz',allow_pickle=False) as current, replay.np.load(prior_folder/'solution.npz',allow_pickle=False) as earlier:
            v['same_point_as_prior']=replay.np.array_equal(current['names'],earlier['names']) and replay.np.array_equal(current['x'],earlier['x'])
        records.append(v)
    replay.write(OUT/'verified-runs.csv',records)
    pairs=[]
    for n in d['instances']:
        for s in d['seeds']:
            a=next(r for r in records if r['instance']==n and r['seed']==s and r['policy']=='Budget-L2')
            for control in ['Base','Base-tight']:
                c=next(r for r in records if r['instance']==n and r['seed']==s and r['policy']==control)
                pairs.append(dict(instance=n,seed=s,control=control,work_ratio=a['work']/c['work'],
                    total_time_ratio=a['total_seconds']/c['total_seconds'],
                    cost_deterioration_percent=float(100*(replay.Fraction(a['objective_exact'])-replay.Fraction(c['objective_exact']))/abs(replay.Fraction(c['objective_exact']))),
                    both_budgets_pass=a['physical_budgets_pass'] and c['physical_budgets_pass']))
    replay.write(OUT/'pairs.csv',pairs)
    summaries=[]
    for control in ['Base','Base-tight']:
        pp=[p for p in pairs if p['control']==control]
        per_model=[dict(instance=n,work_ratio=replay.gm([p['work_ratio'] for p in pp if p['instance']==n]),
            total_time_ratio=replay.gm([p['total_time_ratio'] for p in pp if p['instance']==n])) for n in d['instances']]
        summaries.append(dict(control=control,paired_work_ratio=replay.gm([p['work_ratio'] for p in pp]),
            paired_full_time_ratio=replay.gm([p['total_time_ratio'] for p in pp]),
            cheaper_work_pairs=sum(p['work_ratio']<1 for p in pp),cheaper_time_pairs=sum(p['total_time_ratio']<1 for p in pp),
            max_cost_deterioration_percent=max(p['cost_deterioration_percent'] for p in pp),per_model=per_model))
    result=dict(native_MIP_calls=54,new_LP_calls=0,independently_checked_points=54,
        original_row_point_checks=54*10080*2,verified_exact_witnesses=12,
        both_budgets_pass=sum(r['physical_budgets_pass'] for r in records),
        bound_flags=sum(r['bound_contradiction'] for r in records),completion_flags=sum(r['completion_contradiction'] for r in records),
        timed_out=sum(r['status']==9 for r in records),same_work_as_prior=sum(r['same_work_as_prior'] for r in records),
        same_status_as_prior=sum(r['same_status_as_prior'] for r in records),paired=summaries,
        same_native_endpoint_as_prior=sum(r['same_native_endpoint_as_prior'] for r in records),
        same_point_as_prior=sum(r['same_point_as_prior'] for r in records),
        limitation='Same known models and seeds; consecutively interleaved fresh processes on a shared host; not an isolated hardware benchmark or a general MILP optimality certificate')
    replay.dump(OUT/'VALIDATION.json',result)
    replay.dump(OUT/'replay-inputs.json',replay.INPUTS)
    print(__import__('json').dumps(result,indent=2),flush=True)


if __name__=='__main__':
    start=time.perf_counter()
    ap=argparse.ArgumentParser()
    ap.add_argument('stage',choices=['prepare','run','worker','check'])
    ap.add_argument('job',nargs='?')
    args=ap.parse_args()
    if args.stage=='worker':
        worker(args.job,start)
    else:
        globals()[args.stage]()
