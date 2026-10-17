#!/usr/bin/env python3
"""Final strong-control comparison from already independently verified points."""
import csv
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import statistics

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    f=ROOT/'exploration/oms-frontier-20261016/verified-runs.csv'
    j=ROOT/'exploration/oms-joint-contracts-20261016/verified-solves.csv'
    budget={(r['instance'],r['seed']):r for r in csv.DictReader(f.open()) if r['presolve']=='-1' and r['policy']=='Budget-L2' and r['evaluated_volume_budget']=='100'}
    rows=list(csv.DictReader(j.open()));assert len(rows)==len(budget)==18
    front_design=json.loads((f.parent/'design.json').read_text())
    joint_design=json.loads((j.parent/'solve-design.json').read_text())
    for key in ['Threads','TimeLimit','MIPGap','FeasibilityTol','IntFeasTol','ScaleFlag','IntegralityFocus','NumericFocus']:
        assert front_design['parameters'][key]==joint_design['parameters'][key]
    for instance,model in joint_design['models'].items():
        assert model['Base_sha256']==front_design['inputs'][instance]['base_sha256']
    assert {(r['instance'],r['seed']) for r in rows}==set(budget)
    ratios=[];per=[];quality=[]
    for r in rows:
        b=budget[r['instance'],r['seed']]
        assert r['physical_budget_pass']==b['budget_pass']=='True'
        assert r['bound_contradiction']==b['bound_contradiction']=='False'
        assert r['gap_contradiction']==b['gap_contradiction']=='False'
        ratios.append(float(r['work'])/float(b['work']))
        c=Fraction(r['objective_exact']);d=Fraction(b['objective_exact'])
        quality.append(float((c-d)/max(abs(d),Fraction(1))))
    gm=lambda values:math.exp(statistics.mean(math.log(v) for v in values))
    for name in sorted({r['instance'] for r in rows}):
        per.append({'instance':name,'pairs':3,'joint_contract_over_Budget_L2_work':gm([x for r,x in zip(rows,ratios) if r['instance']==name])})
    parent_sha=(HERE/'SHA256SUMS').read_text().split()[0]
    if (HERE/'oms-strengthening-artifact.zip').exists():assert sha(HERE/'oms-strengthening-artifact.zip')==parent_sha
    d={'comparison':'same six models, seeds 59/71/89, auto presolve, .01 MW/100 m3, common gamma1e-9; terminal-output comparisons, not equally certified gaps',
        'computed_after_both_campaigns_and_first_research_archive_closed':True,
        'joint_over_Budget_L2_geometric_work':gm(ratios),'maximum_relative_candidate_cost_excess':max(quality),
        'models_with_less_work':sum(r['joint_contract_over_Budget_L2_work']<1 for r in per),'per_model':per,
        'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [f,j]},
        'original_research_archive_sha256':parent_sha}
    (ROOT/'exploration/oms-joint-contracts-20261016/strong-control-addendum.json').write_text(json.dumps(d,indent=2)+'\n')
    print(json.dumps(d,indent=2))

if __name__=='__main__':main()
