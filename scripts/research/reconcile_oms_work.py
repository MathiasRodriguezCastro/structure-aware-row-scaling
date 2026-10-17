#!/usr/bin/env python3
"""Reconcile geometric-mean and median Work against native per-seed records."""
import csv
import json
from pathlib import Path
import statistics

ROOT=Path(__file__).resolve().parents[2]
PRIOR=ROOT/'exploration/oms-followup-20261014/presolve-off-followup'
FOLLOWUP=ROOT/'exploration/oms-if1-workflow-20261015'


def main():
    old=[r for r in csv.DictReader((PRIOR/'runs.csv').open()) if r['policy']=='Budget-L2']
    new=list(csv.DictReader((FOLLOWUP/'verified-runs.csv').open()))
    design=json.loads((FOLLOWUP/'design.json').read_text())
    prior_design=json.loads((PRIOR/'design.json').read_text())
    assert design['exports']['Budget-L2']==prior_design['prepared'][0]['exports']['Budget-L2']
    assert sorted(int(r['seed']) for r in old)==[11,23,47]
    records=[]
    for row in sorted(old,key=lambda r:int(r['seed'])):
        seed=int(row['seed']);work=float(row['work'])
        prior=json.loads((PRIOR/f'runs/instance046/Budget-L2-s{seed}/parameters.json').read_text())
        prior.setdefault('IntegralityFocus',0)
        for focus in (0,1):
            saved=json.loads((FOLLOWUP/f'runs/Budget-L2-IF{focus}-s{seed}/result.json').read_text())
            current=next(r for r in new if r['policy']=='Budget-L2' and int(r['focus'])==focus and int(r['seed'])==seed)
            assert float(current['work'])==saved['outcome']['work']==work
            expected={**prior,'IntegralityFocus':focus}
            assert saved['parameters']==expected
        records.append({'seed':seed,'historical_work':work,'workflow_if0_work':work,'workflow_if1_work':work})
    values=[r['historical_work'] for r in records]
    geometric=statistics.geometric_mean(values);median=statistics.median(values)
    assert f'{geometric:.3f}'=='4.485' and f'{median:.3f}'=='4.975'
    summary=list(csv.DictReader((FOLLOWUP/'verified-summary.csv').open()))
    assert all(float(r['median_work'])==median for r in summary if r['policy']=='Budget-L2')
    historical_table=(ROOT/'paper/tables/activation-summary.tex').read_text()
    supplementary_table=(ROOT/'paper/tables/activation-fresh-seeds.tex').read_text()
    assert all(f'& 2 & 0 & {geometric:.3f}' in table for table in (historical_table,supplementary_table))
    report={'scope':'same instance046, policy and per-seed Work; different aggregation',
        'rows':records,'geometric_mean':geometric,'median':median,
        'table_s12_and_historical_v1_3_8_main_table_11':{'aggregation':'geometric mean','display':f'{geometric:.3f}'},
        'table_s15_and_workflow_note':{'aggregation':'median','display':f'{median:.3f}'},
        'same_native_model_sha256':design['exports']['Budget-L2'],
        'parameters_match_except_declared_integrality_focus':True,
        'new_optimizer_calls':0}
    target=ROOT/'paper/validation/oms-work-reconciliation.json'
    target.write_text(json.dumps(report,indent=2)+'\n')
    print(f'Work reconciled: geometric mean {geometric:.10f}; median {median:.10f}; no new solves')


if __name__=='__main__':main()
