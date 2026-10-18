"""Matched original-objective target replication of the complete preselected R set."""
from fractions import Fraction as F
import gzip
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import time

from pilot import ARMS, worker, write_lp
from screen import HERE, csvwrite, digest, dump

SEEDS=(227,229,233)


def prepare():
    assert not (HERE/'replication-design.json').exists()
    models=[m for m in json.loads((HERE/'models.json').read_text()) if m['family']=='R-fixed-charge']
    assert len(models)==6
    references={}
    for model in models:
        candidates=[]
        for path in (HERE/'runs'/model['name']).glob('*/verification.json'):
            verification=json.loads(path.read_text())
            if verification['exactly_feasible_decoded']:
                candidates.append((F(verification['rounded_objective_exact']),path))
        value,path=min(candidates)
        target=value*F(101,100)
        inward=float(target)
        if F(inward)>target:inward=math.nextafter(inward,-math.inf)
        references[model['name']]=dict(exact_feasible_objective=str(value),target_exact=str(target),
            target_inward_float=inward,reference_verification=str(path.relative_to(HERE)),
            reference_sha256=digest(path.read_bytes()),claim='observed exact feasible objective, not certified global optimum')
    order=[dict(instance=m['name'],policy=p,seed=s) for m in models for p in ARMS for s in SEEDS]
    random.Random(227).shuffle(order)
    dump(HERE/'replication-design.json',dict(seeds=list(SEEDS),order=order,references=references,
        rationale='R collection as a whole finished in pilot; distinguish effort at a common independently verified quality goal from different native bound-closing effort',
        selection='all six R instances fixed before the pilot; no individual outcome exclusions',
        endpoint='first termination with original rounded objective <= 1.01 times a pilot exact feasible reference and verified primal residual <= 1e-5; BestObjStop common across policies',
        controls='same seven arms and common parameters as pilot, except seeds and common BestObjStop',
        timings='report preparation, read/solve, and their sum separately; no repeated solver imports inside measured preparation',
        manuscript='no manuscript changes without substantial verified value',
        pilot_design_sha256=digest((HERE/'pilot-design.json').read_bytes())))
    # Registration above precedes all new optimizer calls and preparation measurements.
    jobs=[(m,p,s) for m in models for p in ARMS[:5] for s in SEEDS]
    random.Random(229).shuffle(jobs)
    measurements=[]
    with tempfile.TemporaryDirectory(prefix='oms-structure-timing-') as directory:
        for model,policy,seed in jobs:
            path=Path(directory)/'export.lp.gz'
            started=time.perf_counter();write_lp(model,policy,path);elapsed=time.perf_counter()-started
            measurements.append(dict(instance=model['name'],policy=policy,seed=seed,
                preparation_seconds=elapsed,uncompressed_sha256=digest(gzip.decompress(path.read_bytes()))))
    csvwrite(HERE/'preparation-times.csv',measurements)


def run():
    design=json.loads((HERE/'replication-design.json').read_text())
    for i,record in enumerate(design['order']):
        instance,policy,seed=record['instance'],record['policy'],record['seed']
        folder=HERE/'replication'/instance/policy/f'seed-{seed}'
        if (folder/'run.json').exists():continue
        folder.mkdir(parents=True,exist_ok=True)
        assert not (folder/'attempt-start.json').exists(),'retain and diagnose incomplete attempt'
        dump(folder/'attempt-start.json',dict(unix=time.time(),pid=os.getpid(),**record))
        started=time.perf_counter()
        with (folder/'process.log').open('w') as log:
            result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'worker',instance,policy,str(seed)],
                stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'})
        dump(folder/'process.json',dict(returncode=result.returncode,wall_seconds=time.perf_counter()-started))
        if result.returncode:raise RuntimeError('worker failed '+str(folder))
        row=json.loads((folder/'run.json').read_text())
        print(i+1,'/',len(design['order']),instance,policy,seed,row['status'],round(row['work'],6),flush=True)


if __name__=='__main__':
    if sys.argv[1]=='worker':worker(sys.argv[2],sys.argv[3],'replication',int(sys.argv[4]))
    else:globals()[sys.argv[1]]()
