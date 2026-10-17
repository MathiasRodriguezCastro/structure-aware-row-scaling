#!/usr/bin/env python3
"""Regenerate the SI common-incumbent table directly from frozen native records."""
import gzip
import json
from pathlib import Path
import statistics

ROOT=Path(__file__).resolve().parents[2]
STUDY=ROOT/'exploration/oms-root-attribution-20261015'


def read(path):
    raw=path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix=='.gz' else raw)


def main():
    design=read(STUDY/'design.json');schedule=read(STUDY/'run-design.json')['schedule']
    analysis=read(STUDY/'analysis.json');verified=read(STUDY/'independent-verification.json')
    assert len(schedule)==36 and verified['loaded_common_start_pattern_cost_checks']==18
    assert verified['reference_optimum_certified']==3 and verified['final_pattern_unknown']==2
    assert analysis['printed_root_pairs']==analysis['printed_root_pairs_matching']==15
    rows=[]
    for case in design['instances']:
        for mode in design['starts']:
            fields=[]
            for policy in design['policies']:
                jobs=[j for j in schedule if j['instance']==case and j['start']==mode and j['policy']==policy]
                assert len(jobs)==3 and {j['seed'] for j in jobs}=={503,509,521}
                native=[]
                for job in jobs:
                    name='{instance}-{policy}-{start}-s{seed}'.format(**job)
                    r=read(STUDY/'runs'/name/'run.json');assert r['job']==job
                    native.append(r)
                completed=sum(r['status']==2 for r in native);work=statistics.median(r['work'] for r in native)
                assert completed==analysis['groups'][case][mode][policy]['native_completions']
                assert work==analysis['groups'][case][mode][policy]['median_work']
                fields.extend([f'{completed}/3',f'{work:.4f}'])
            rows.append(' & '.join([case.replace('instance',''),mode,*fields])+r' \\')
    table='\n'.join([r'\begin{tabular}{llrrrr}',r'\toprule',
        r'Case & Initialization & Base completes & Base work & GM completes & GM work \\',
        r'\midrule',*rows,r'\bottomrule',r'\end{tabular}',''])
    target=ROOT/'paper/tables/incumbent-initialization.tex'
    target.write_text(table)
    print('Regenerated Table S14 from 36 frozen native runs; 18 loaded common starts verified')


if __name__=='__main__':main()
