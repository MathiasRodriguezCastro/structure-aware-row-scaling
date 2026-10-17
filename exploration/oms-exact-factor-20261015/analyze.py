#!/usr/bin/env python3
from collections import Counter
from pathlib import Path
from fractions import Fraction as Q
import gzip
import hashlib
import json
import statistics

HERE=Path(__file__).resolve().parent


def main():
    rows=json.loads(gzip.decompress((HERE/'decisions.json.gz').read_bytes()))
    stress=json.loads(gzip.decompress((HERE/'stress.json.gz').read_bytes()))
    summary=json.loads((HERE/'summary.json').read_text())
    checked=json.loads((HERE/'independent-verification.json').read_text())
    assert summary['counts']['only_power_two_exact_possible']==checked['only_power_two_exact_possible_corrected']
    pinned=json.loads((HERE/'outcomes-before-count-correction.json').read_text())
    for n,h in pinned.items():assert hashlib.sha256((HERE/n).read_bytes()).hexdigest()==h
    changed=Counter();unbounded=Counter();examples=[];improvements=[];permodel={}
    for r in rows:
        if r['scenario']!='Unbudgeted':continue
        one,exact=r['policies']['Pow2'],r['policies']['Exact']
        if one['alpha_hex']!=exact['alpha_hex']:
            changed[r['name'].split('(')[0]]+=1
            improvements.append(float(Q(exact['score_exact'])/Q(one['score_exact'])))
            if len(examples)<3:examples.append(r)
        if r['policies']['Rounded']['defect_exact'] is None:unbounded[r['name'].split('(')[0]]+=1
    for model in ['instance001','instance022','instance046']:
        modelrows=[r for r in rows if r['instance']==model and r['scenario']=='Unbudgeted']
        permodel[model]=dict(rows=len(modelrows),changed=sum(r['policies']['Pow2']['alpha_hex']!=r['policies']['Exact']['alpha_hex'] for r in modelrows))
    result=dict(summary,independent=checked,changed_row_families=dict(changed),
        unbounded_box_defect_families=dict(unbounded),per_model=permodel,
        changed_rows_score_ratio_median=statistics.median(improvements),examples=examples,
        outcome_files_unchanged_after_derived_count_correction=True,
        decisions='No new contract admissibility in actual scenarios; do not start a solver campaign or add to OMS')
    (HERE/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Analysis regenerated:',len(rows),'row/scenario records and',len(stress),'constructed intervals')


if __name__=='__main__':main()
