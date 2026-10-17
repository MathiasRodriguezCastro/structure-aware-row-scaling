#!/usr/bin/env python3
"""Replay the Farkas rays already saved by the 16-pattern cost audit. No solves."""
import json
from pathlib import Path
from fractions import Fraction
import hashlib
import numpy as np
from farkas_certificate import verify

HERE=Path(__file__).resolve().parent


def main():
    load=lambda p:json.loads(p.read_text())
    model=load(HERE/'confirmation/models/neos-3083784-nive/original-model.json')
    design=load(HERE/'cost-audit/design.json');records=[]
    for task in design['queue']:
        folder=HERE/'cost-audit/runs'/f"{task['arm']}-s{task['seed']}";path=folder/'dual.txt'
        if not path.exists():continue
        ray={};active=False;found=False
        for line in path.read_text().splitlines():
            if 'Dual ray (name, value):' in line:active=found=True;continue
            if active and line.startswith('All other'):break
            t=line.split()
            if active and len(t)==2 and t[0].startswith('r') and t[0][1:].isdigit():ray[t[0][1:]]=str(Fraction(t[1]))
        if not found:continue
        source=HERE/task['source_path']/'delivered-point.npz'
        assert hashlib.sha256(source.read_bytes()).hexdigest()==task['delivered_sha256']
        with np.load(source,allow_pickle=False) as z:delivered=list(z['x'])
        certificate=verify(model,delivered,ray)
        record={**{k:task[k] for k in ('arm','seed')},'dual_file_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),**certificate}
        records.append(record)
    result={'available_rays_checked':len(records),'fixed_pattern_infeasibilities_verified':sum(r['fixed_pattern_infeasible_certified'] for r in records),
            'global_mip_infeasibilities_certified':False,'solver_calls':0,'stage':'posthoc verification of existing dual rays; no additional optimization calls','records':records}
    (HERE/'cost-audit/farkas-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
