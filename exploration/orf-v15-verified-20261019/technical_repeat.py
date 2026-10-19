#!/usr/bin/env python3
"""One predeclared technical timing repetition after the 630 assignments."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import numpy as np

HERE=Path(__file__).resolve().parent


def main():
    if len(sys.argv)>1 and sys.argv[1]=='worker':
        import study
        study.HERE=HERE/'technical-repeat'
        plan=json.loads((HERE/'TECHNICAL_REPEAT_PLAN.json').read_text())
        study.worker(plan['job']['id']);return
    timing=json.loads((HERE/'timing.json').read_text());assert len(timing)==630
    out=HERE/'technical-repeat';assert not out.exists();out.mkdir()
    shutil.copyfile(HERE/'design.json',out/'design.json')
    start=time.perf_counter()
    with (out/'execution.log').open('w') as f:
        r=subprocess.run([sys.executable,str(Path(__file__)),'worker'],stdout=f,stderr=subprocess.STDOUT,
            env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','ORF_FOLLOWUP_LAUNCHED':str(start)},timeout=180)
    assert r.returncode==0
    plan=json.loads((HERE/'TECHNICAL_REPEAT_PLAN.json').read_text());jid=plan['job']['id']
    old=json.loads((HERE/'runs'/jid/'result.json').read_text());new=json.loads((out/'runs'/jid/'result.json').read_text())
    with np.load(HERE/'runs'/jid/'candidates.npz') as a,np.load(out/'runs'/jid/'candidates.npz') as b:
        same_vectors=np.array_equal(a['x'],b['x']) and np.array_equal(a['names'],b['names'])
    same_outcomes=all(old['outcome'][k]==new['outcome'][k] for k in ['status','solutions','work','objective','bound','nodes'])
    same_first=all((old['first_qualified'][str(t)] or {}).get('index')==(new['first_qualified'][str(t)] or {}).get('index') for t in [.001,.01])
    report=dict(status='passed',additional_MIP_calls=1,job_id=jid,same_candidate_vectors=same_vectors,
        same_non_timing_endpoints=same_outcomes,same_first_target_indices=same_first,
        standardized_timing_replacement_permitted=same_vectors and same_outcomes and same_first,
        original_retained=True,independent_observations_added=0,total_seconds=time.perf_counter()-start)
    (HERE/'TECHNICAL_REPEAT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
