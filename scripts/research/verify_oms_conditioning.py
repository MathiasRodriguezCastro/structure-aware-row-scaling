#!/usr/bin/env python3
"""Rebuild OMS named bases from preserved LP text and replay condition estimates."""
import csv
import gzip
import json
import math
from pathlib import Path
import tempfile
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from oms_dispatch_validation import OUT, POLICIES, dump
from solver_scaling_bridge import rebuild, equilibrate, kappa1

rows=list(csv.DictReader((OUT/'conditioning.csv').open()))
assert len(rows)==120
with tempfile.TemporaryDirectory(prefix='oms-bases-') as temp:
    temp=Path(temp)
    for rec in rows:
        folder=OUT/'exports'/rec['class']/rec['instance'];policy=rec['policy']
        (temp/'reference-basis.json').write_bytes((folder/'reference-basis.json').read_bytes())
        (temp/(policy+'.lp')).write_bytes(gzip.decompress((folder/(policy+'.lp.gz')).read_bytes()))
        basis=rebuild(temp,policy)
        for field,value in [('kappa1',kappa1(basis)),('kappa1_equilibrated10',kappa1(equilibrate(basis,10)))]:
            assert value is not None and math.isclose(value,float(rec[field]),rel_tol=1e-10),(rec['instance'],policy,field,value,rec[field])
summary=json.loads((OUT/'summary.json').read_text())
for rec in summary['comparison']:
    selected=[r for r in rows if r['class']==rec['class'] and r['policy']==rec['policy']]
    baseline={r['instance']:r for r in rows if r['class']==rec['class'] and r['policy']=='Base'}
    for source,target in [('kappa1','median_kappa_ratio'),('kappa1_equilibrated10','median_equilibrated_kappa_ratio')]:
        ratio=float(np.median([float(r[source])/float(baseline[r['instance']][source]) for r in selected]))
        assert math.isclose(ratio,rec[target],rel_tol=1e-12)
dump(OUT/'conditioning-verification.json',{'named_bases_rebuilt_from_text':120,'estimates_recomputed_before_and_after_equilibration':240,'paired_median_ratios_recomputed':True,'relative_replay_tolerance':1e-10})
print('OMS conditioning replay passed: 120 bases, 240 estimates')
