#!/usr/bin/env python3
"""Measure factor selection and round-trip export separately from optimization.

Common LP reading is excluded. Budget-specific unit lookup and rounding/export
reserves are included. Every timed export must match its frozen counterpart.
"""
import csv
from fractions import Fraction
import json
import math
from pathlib import Path
import statistics
import tempfile
import time

import numpy as np

import activation_study as study

HERE=Path(__file__).resolve().parent
BANK=HERE/'confirmation-bank'
F=Fraction.from_float


def factors(parsed,lp,gamma,budgeted):
    integer={n for n,k in zip(lp.col_names_,lp.integrality_) if str(k)!='HighsVarType.kContinuous'}
    boxes={n:max(abs(float(lo)),abs(float(hi))) for n,lo,hi in zip(lp.col_names_,lp.col_lower_,lp.col_upper_)}
    result={}
    for name,row in parsed.items():
        delta=1e100;reserve=0.
        if budgeted:
            physical=study.campaign.physical_spec(name,row['terms'])
            if physical:_,unit,conversion=physical
            elif study.activation_spec(name,row):unit,conversion='m3',1.
            else:unit=None
            if unit:
                delta=(.01 if unit=='MW' else 100.)*conversion
                e=F(gamma)*sum((F(abs(float(v))) for n,v in row['terms'].items() if n in integer),Fraction(0))
                d=Fraction(0)
                if study.ACT.fullmatch(name):d=F(2.**-52)*(sum((F(abs(float(v)))*F(boxes[n]) for n,v in row['terms'].items()),Fraction(0))+F(abs(float(row['rhs']))))
                reserve=float(e+d)
                if F(reserve)<e+d:reserve=math.nextafter(reserve,math.inf)
        decision=study.select_factor(list(row['terms'].values()),delta,kernel='l2',rounding_allowance=reserve)
        assert decision.factor is not None
        result[name]=decision.factor
    return result


def main():
    design=json.loads((BANK/'design.json').read_text());records=[]
    rng=np.random.default_rng(20261015)
    with tempfile.TemporaryDirectory(prefix='activation-factor-cost-') as temp:
        export=Path(temp)/'scaled.lp'
        for item in design['prepared']:
            instance=item['instance'];folder=BANK/'models'/instance
            parsed,_=study.parse(folder/'Base.lp');_,lp,_=study.campaign.afb.read_lp(folder/'Base.lp')
            for repeat in range(3):
                for budgeted in rng.permutation([False,True]):
                    policy='Budget-L2' if budgeted else 'L2-window'
                    start=time.perf_counter();chosen=factors(parsed,lp,item['guided_gamma'],bool(budgeted));selected=time.perf_counter()-start
                    start=time.perf_counter();study.export_scaled(folder/'Base.lp',export,chosen);written=time.perf_counter()-start
                    assert study.sha(export)==item['exports'][policy]
                    records.append({'instance':instance,'policy':policy,'repeat':repeat,
                        'selection_seconds':selected,'export_seconds':written,
                        'selection_export_seconds':selected+written,'export_sha256':study.sha(export)})
            print('Measured and matched',instance,flush=True)
    study.csvwrite(HERE/'factor-cost-runs.csv',records)
    summary=[]
    for instance in sorted({r['instance'] for r in records}):
        for policy in ('L2-window','Budget-L2'):
            chosen=[r for r in records if r['instance']==instance and r['policy']==policy]
            summary.append({'instance':instance,'policy':policy,'repeats':len(chosen),
                'median_selection_export_seconds':statistics.median(r['selection_export_seconds'] for r in chosen)})
    study.csvwrite(HERE/'factor-cost-summary.csv',summary)
    print('36 factor-selection/export measurements completed; all exports byte-identical',flush=True)


if __name__=='__main__':main()
