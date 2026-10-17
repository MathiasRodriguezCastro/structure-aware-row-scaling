#!/usr/bin/env python3
"""Materialize declared aliases, replay points, and attribute the 2x2 effects."""
import csv
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import statistics
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(p):return json.loads(p.read_text())
def dump(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def gm(values):return math.exp(statistics.mean(math.log(x) for x in values))

def main():
    d=load(HERE/'ablation-design.json');timing=load(HERE/'ablation-timings.json');pilot=load(HERE/'solve-timings.json')
    assert len(timing)==len(d['new_jobs'])==36 and all(r['returncode']==0 for r in timing)
    assert [r['job'] for r in timing]==d['new_jobs']
    for p,h in d['dependencies'].items():assert sha(ROOT/p)==h,p
    byjob={(r['job']['policy'],r['job']['id']):r for r in timing}
    oldbyjob={r['job']['id']:r for r in pilot}
    # This module contains only independent parsing/rational point checks.
    spec=importlib.util.spec_from_file_location('ablation_point_checker',HERE/'check_solves.py')
    checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
    records=[]
    for policy in ['Row-contract','Row-uncontracted','Joint-contract','Joint-uncontracted']:
        phase=HERE/'ablation'/policy;phase_timing=[]
        link=phase/'base-witnesses'
        if link.is_symlink():link.unlink()
        link.mkdir(exist_ok=True)
        for instance in sorted({a['instance'] for a in d['assignments']}):
            original=HERE/'base-witnesses'/instance;target=link/instance;target.mkdir(exist_ok=True)
            for filename in ['exact-witness.json','independent-certificate.json']:
                shutil.copyfile(original/filename,target/filename)
            ex=load(phase/'solve-models'/instance/'exponents.json')
            # Each column scaling has its own transformed witness. Reusing the
            # original joint coordinate vector for the row control is invalid.
            point={n:str(Fraction(q)/(Fraction(2)**ex['v'][n])) for n,q in load(original/'exact-witness.json').items()}
            dump(target/'joint-witness.json',point)
        for a in [a for a in d['assignments'] if a['policy']==policy]:
            m=d['models'][a['key']];sourcekey=m.get('alias',a['key']);sourcepolicy=sourcekey.split('/')[1]
            if sourcepolicy=='Joint-contract':
                source=HERE/'solve-runs'/a['id'];r=oldbyjob[a['id']]
            else:
                source=HERE/'ablation'/sourcepolicy/'solve-runs'/a['id'];r=byjob[sourcepolicy,a['id']]
            assert sha(source/'result.json')
            original=load(source/'result.json');assert original['export_sha256']==m['export_sha256']
            dest=phase/'solve-runs'/a['id']
            if source!=dest:
                dest.mkdir(parents=True,exist_ok=True)
                for filename in ['result.json','solution.npz','solver.log']:
                    if (dest/filename).exists():assert sha(dest/filename)==sha(source/filename)
                    else:shutil.copyfile(source/filename,dest/filename)
            phase_timing.append({'job':{k:a[k] for k in ['instance','seed','id']},'returncode':r['returncode'],'process_seconds':r['process_seconds']})
        # Match phase job order, not the order of randomized actual calls.
        jobs=load(phase/'solve-design.json')['jobs'];order={j['id']:i for i,j in enumerate(jobs)}
        phase_timing.sort(key=lambda r:order[r['job']['id']]);dump(phase/'solve-timings.json',phase_timing)
        checker.HERE=phase;checker.main()
        for r in csv.DictReader((phase/'verified-solves.csv').open()):
            r['policy']=policy;r['source_key']=d['models'][r['instance']+'/'+policy].get('alias',r['instance']+'/'+policy)
            records.append(r)
    with (HERE/'verified-ablation.csv').open('w',newline='') as out:
        w=csv.DictWriter(out,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    summary=[];pairs=[]
    for policy in ['Row-contract','Row-uncontracted','Joint-contract','Joint-uncontracted']:
        rr=[r for r in records if r['policy']==policy]
        summary.append({'policy':policy,'arms':len(rr),'unique_new_native_calls':sum(j['policy']==policy for j in d['new_jobs']),
            'physical_budgets_passed':sum(r['physical_budget_pass']=='True' for r in rr),'bound_flags':sum(r['bound_contradiction']=='True' for r in rr),
            'gap_flags':sum(r['gap_contradiction']=='True' for r in rr),'geometric_work':gm([float(r['work']) for r in rr]),
            'native_time_limits':sum(r['status']=='9' for r in rr),'maximum_budget_ratio':max(float(r['max_rounded_ratio']) for r in rr)})
    for instance in sorted({r['instance'] for r in records}):
        for control in ['Row-contract','Joint-uncontracted']:
            a={r['seed']:r for r in records if r['instance']==instance and r['policy']=='Joint-contract'}
            b={r['seed']:r for r in records if r['instance']==instance and r['policy']==control}
            assert set(a)==set(b)=={'59','71','89'}
            pairs.append({'instance':instance,'control':control,'pairs':3,
                'work_ratio_joint_contract_control':gm([float(a[s]['work'])/float(b[s]['work']) for s in a]),
                'joint_contract_primal_pass':sum(a[s]['physical_budget_pass']=='True' for s in a),
                'control_primal_pass':sum(b[s]['physical_budget_pass']=='True' for s in b),
                'joint_contract_bound_flags':sum(a[s]['bound_contradiction']=='True' for s in a),
                'control_bound_flags':sum(b[s]['bound_contradiction']=='True' for s in b),
                'maximum_relative_cost_excess':max(float((Fraction(a[s]['objective_exact'])-Fraction(b[s]['objective_exact']))/max(abs(Fraction(b[s]['objective_exact'])),Fraction(1))) for s in a)})
    for filename,rr in [('ablation-summary.csv',summary),('ablation-pairs.csv',pairs)]:
        with (HERE/filename).open('w',newline='') as out:
            w=csv.DictWriter(out,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)
    report={'factorial_arms':72,'pilot_calls_reused':18,'new_MIP_calls':36,'new_LP_calls':0,
        'row_uncontracted_export_aliases_declared_before_calls':6,'unique_total_MIP_calls':54,'summary':summary,'pairs':pairs,
        'independent_external_validation':False,'MIP_global_optimality_certified':False}
    dump(HERE/'ABLATION_VALIDATION.json',report);print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()
