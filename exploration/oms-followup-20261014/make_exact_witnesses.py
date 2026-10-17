#!/usr/bin/env python3
"""Produce exact witnesses for the actual imported confirmation exports.

All supplied certificates can later be checked without SoPlex or optimization.
Witness selection concerns existence of feasible points, not a performance sample.
"""
import csv
import json
from pathlib import Path
import sys

import numpy as np

import exact_dispatch_witness as witness

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BANK=HERE/'confirmation-bank'
OUT=HERE/'exact-witnesses'


def main():
    binary=HERE/'tools/soplex-build/bin/soplex'
    design=json.loads((BANK/'design.json').read_text())
    candidates=[]
    for folder in ('confirmation-bank','confirmation-mechanism','pilot-activation','presolve-off-followup'):
        path=HERE/folder
        if not (path/'runs.csv').exists():continue
        for row in csv.DictReader((path/'runs.csv').open()):
            solution=path/'runs'/row['instance']/(row['policy']+'-s'+row['seed'])/'solution.npz'
            if solution.exists():candidates.append((row,solution))
    records=[]
    for item in design['instances']:
        instance=item['instance'];base=BANK/'models'/instance/'Base.lp'
        _,lp,_=witness.afb.read_lp(base)
        integers={name for name,kind in zip(lp.col_names_,lp.integrality_)
                  if str(kind)!='HighsVarType.kContinuous'}
        eligible=[]
        for row,path in candidates:
            if row['instance']!=instance:continue
            with np.load(path,allow_pickle=False) as sol:
                point=dict(zip(sol['names'].tolist(),sol['x'].tolist()))
            if all(point[n]==round(point[n]) for n in integers):eligible.append((row,path))
        assert eligible,instance
        row,solution=min(eligible,key=lambda x:float(x[0]['objective']))
        sources=['GM','L2-window','Budget-L2']+(['Base'] if instance=='instance046' else [])
        for source in sources:
            model=BANK/'models'/instance/(source+'.lp')
            folder=OUT/instance/source
            if (folder/'independent-certificate.json').exists():
                witness.check(folder)
            else:
                witness.prepare(folder,model,solution)
                witness.solve(folder,binary)
                witness.check(folder)
            certificate=json.loads((folder/'independent-certificate.json').read_text())
            assert certificate['original_model_sha256']==witness.sha(model)
            records.append({'instance':instance,'source':source,
                'model':str(model.relative_to(ROOT)),'model_sha256':witness.sha(model),
                'certificate':str((folder/'independent-certificate.json').relative_to(ROOT)),
                'witness':str((folder/'exact-witness.json').relative_to(ROOT)),
                'chosen_integer_pattern_policy':row['policy'],'chosen_integer_pattern_seed':int(row['seed']),
                'objective_float_for_display':certificate['objective_float_for_display']})
            OUT.mkdir(parents=True,exist_ok=True)
            witness.dump(OUT/'index.json',records)
            print('Exact native-export witness',instance,source,certificate['objective_float_for_display'],flush=True)
    assert len(records)==19
    print('All 19 exact native-export witnesses independently verified',flush=True)


if __name__=='__main__':main()
