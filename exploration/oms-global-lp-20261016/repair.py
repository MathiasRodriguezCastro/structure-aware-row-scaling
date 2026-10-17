#!/usr/bin/env python3
"""Repair every pilot integer pattern; combine with genuinely global LP bounds."""
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import study as globalstudy
import exact_lp as exact

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
JOINT=ROOT/'exploration/oms-joint-contracts-20261016'
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')

def main():
    if (HERE/'repair-design.json').exists():raise RuntimeError('repair design exists')
    pilot=load(JOINT/'solve-design.json');assignments=[];unique={}
    for j in pilot['jobs']:
        data,base=globalstudy.data_for(j['instance']);_,lp,_=globalstudy.read_lp(base)
        integers={i for i,k in enumerate(lp.integrality_) if str(k)!='HighsVarType.kContinuous'}
        source=JOINT/'solve-runs'/j['id']/'solution.npz'
        with np.load(source,allow_pickle=False) as p:point=dict(zip(p['names'].tolist(),p['y'].tolist()))
        pattern={str(i):int(round(point[v['name']])) for i,v in enumerate(data['variables']) if i in integers}
        assert len(pattern)==1440
        h=hashlib.sha256(json.dumps(pattern,sort_keys=True).encode()).hexdigest()
        key=j['instance']+'/'+h[:20];unique.setdefault(key,{'instance':j['instance'],'pattern':pattern})
        assignments.append({**j,'key':key,'source_sha256':sha(source),'source':str(source.relative_to(ROOT))})
    deps=[Path(__file__),HERE/'study.py',HERE/'REPAIR_PROTOCOL.md',HERE/'VALIDATION.json']
    dump(HERE/'repair-design.json',{'assignments':assignments,'unique':unique,'limit_seconds':15.,
        'dependencies':{str(p.relative_to(ROOT)):sha(p) for p in deps},'all_18_outputs_included':True})
    results={};binary=ROOT/'exploration/oms-followup-20261014/tools/soplex-build/bin/soplex'
    for key,r in unique.items():
        data,base=globalstudy.data_for(r['instance']);_,lp,_=globalstudy.read_lp(base)
        for v,k in zip(data['variables'],lp.integrality_):
            if str(k)!='HighsVarType.kContinuous':v['type']='B'
        folder=HERE/'repairs'/key;folder.mkdir(parents=True)
        exact.dump(folder/'original-data.json.gz',data)
        results[key]=exact.acquire(data,r['pattern'],folder,binary,limit=15.)
        dump(HERE/'repair-results.json',results);print(key,results[key]['outcome'],flush=True)

if __name__=='__main__':main()
