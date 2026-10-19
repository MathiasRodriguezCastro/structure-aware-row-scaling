#!/usr/bin/env python3
"""Read/count large pools on a compute node; select parents without solver outcomes."""
import csv
import hashlib
import json
import os
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=HERE.parent
SALT='orf-extension-20261019-parent-split-v1'


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    home=Path.home()
    shared=Path('/clusteruy/home/Grupos/UTE_FING/mathiasr/soluciones_seccion45')
    paths={k:shared/k/'instancias' for k in ['simple','sgtm','completo']}
    paths.update(simple10000=shared/'simple/banco_10000/instancias',
                 simple100000=home/'tesis_maestria/Codigo_Cpp/ejecuciones/simple100k/instancias')
    reports={};selected=[]
    for name,root in paths.items():
        candidates=sorted(root.glob('*.txt')) if root.exists() else []
        metadata={}
        for p in [root/'metadata.json',root.parent/'metadata.json',root.parent.parent/'metadata.json']:
            if p.is_file():metadata[str(p)]={'sha256':digest(p),'content':json.loads(p.read_text())}
        reports[name]=dict(root=str(root),exists=root.exists(),text_files=len(candidates),metadata=metadata)
        if name not in ['simple','sgtm','completo']:continue
        pilot,confirm={'simple':(3,14),'sgtm':(3,13),'completo':(2,13)}[name]
        assert len(candidates)>=pilot+confirm,name
        candidates.sort(key=lambda p:hashlib.sha256(f'{SALT}|{name}|{p.name}'.encode()).hexdigest())
        for i,p in enumerate(candidates[:pilot+confirm]):
            selected.append(dict(family=name,parent_id=f'{name}-{p.stem}',
                role='pilot' if i<pilot else 'confirmation',rank=i,remote_path=str(p),
                sha256=digest(p),bytes=p.stat().st_size))
    assert len(selected)==48
    record=dict(status='inventoried_not_claimed_independent',hostname=os.uname().nodename,
        slurm_job=os.environ.get('SLURM_JOB_ID'),selection_salt=SALT,pools=reports,
        selected_parents=selected,selection_uses_solver_results=False,
        pilot_parents=8,confirmation_parents=40,observed_operational_independence_verified=False)
    (OUT/'REMOTE_INVENTORY.json').write_text(json.dumps(record,indent=2)+'\n')
    with (OUT/'selected-parents.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(selected[0]));w.writeheader();w.writerows(selected)
    # File-list download via the transfer port; no compression on login.
    (OUT/'selected-files.txt').write_text(''.join(r['remote_path'].lstrip('/')+'\n' for r in selected))
    print(json.dumps({n:v['text_files'] for n,v in reports.items()}),flush=True)
    print('Selected eight pilot and forty confirmation parents, without outcomes.',flush=True)


if __name__=='__main__':main()
