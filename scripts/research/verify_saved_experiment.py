#!/usr/bin/env python3
"""Independent saved-data audit: no solver or experimental runner is imported."""
import argparse
import csv
from fractions import Fraction as F
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,default=Path('results-revision/research-audit/budget-final'))
    args=ap.parse_args()
    protocol=json.loads((args.root/'protocol.json').read_text())
    models={}
    for path in sorted((args.root/'models').glob('*.npz')):
        with np.load(path) as a:
            A,b,c,delta=a['A'],a['b'],a['c'],a['delta']
            assert np.all(A==np.rint(A)) and np.all(c==np.rint(c))
            assert np.max(abs(A))*A.shape[1] < 2**62
            choices=((np.arange(2**A.shape[1])[:,None] >> np.arange(A.shape[1]))&1).astype(np.int64)
            # A is integer in these saved instances; integer activities <= b iff <= floor(b).
            ai=A.astype(np.int64);ci=c.astype(np.int64)
            feasible=np.all(choices@ai.T <= np.floor(b).astype(np.int64),axis=1)
            optimum=int((choices[feasible]@ci).max())
            assert optimum==int(a['optimum'])
            models[path.stem]=(A,b,c,delta,ai,ci,optimum)
    keys=set();dyadic=0;abstain=0;verified=0
    rows=list(csv.DictReader((args.root/'runs.csv').open()))
    for row in rows:
        key=(row['family'],int(row['seed']),int(row['exponent']),row['presolve']=='True',row['method'],row['solver'])
        assert key not in keys
        keys.add(key)
        A,b,c,delta,ai,ci,optimum=models[row['model_id']]
        assert int(row['true_optimum'])==optimum
        x=json.loads(row['x']); ds=json.loads(row['factors'])
        if row['status']=='ABSTAIN':
            abstain+=1
            assert x is None and ds is None and row['method']=='Budget-round'
            assert any(F.from_float(1e-6)*sum(F.from_float(float(abs(v))) for v in ar)>=F.from_float(float(dr))
                       for ar,dr in zip(A,delta))
        if ds is not None and row['method'] in {'Dyadic-GM','Budget-dyadic'}:
            for ar,br,dsr in zip(A,b,ds):
                for z in [*ar,br]:
                    assert F.from_float(float(dsr*z)) == F.from_float(dsr)*F.from_float(float(z))
            dyadic+=1
        if ds is not None and row['method'] in {'Budget-GM','Budget-dyadic','Budget-round'}:
            for ar,dr,dsr in zip(A,delta,ds):
                available=F.from_float(float(dr))
                if row['method']=='Budget-round':
                    available-=F.from_float(1e-6)*sum(F.from_float(float(abs(z))) for z in ar)
                assert F.from_float(dsr)*available>=F.from_float(1e-6)
                for z in ar:
                    if z:
                        v=F.from_float(dsr)*F.from_float(float(abs(z)))
                        assert F.from_float(1e-9)<=v<=F.from_float(1e9)
        accepted=False
        if x is not None:
            rounded=np.rint(x).astype(np.int64)
            feasible=bool(np.all((rounded>=0)&(rounded<=1)) and np.all(ai@rounded<=np.floor(b)))
            bounds=all(-1e-9<=z<=1.+1e-9 for z in x)
            near=all(abs(z-int(r))<=1e-9 for z,r in zip(x,rounded))
            accepted=bool(feasible and bounds and near and int(ci@rounded)==optimum)
        assert accepted==(row['rounded_optimal']=='True'), key
        verified+=1
    expected=set(itertools.product(protocol['families'],protocol['seeds'],protocol['exponents'],
                                   protocol['presolve'],protocol['methods'],protocol['solvers']))
    assert keys==expected
    result={'models_independently_enumerated':len(models),'configurations_audited':verified,
            'exact_dyadic_exports_checked':dyadic,'abstentions_verified':abstain,
            'runs_sha256':hashlib.sha256((args.root/'runs.csv').read_bytes()).hexdigest(),
            'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (args.root/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
