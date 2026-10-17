#!/usr/bin/env python3
"""Close a self-contained saved-point replay; refuse to replace a closed archive."""
from pathlib import Path
import hashlib
import json
import zipfile

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    target=HERE/'matched-accuracy-artifact.zip'
    if target.exists():raise RuntimeError('closed archive exists; do not overwrite')
    d=json.loads((HERE/'design.json').read_text())
    assert json.loads((HERE/'VALIDATION.json').read_text())['checked_milp_calls']==144
    paths={ROOT/p for p in d['dependencies']}
    paths.update(p for p in HERE.rglob('*') if p.is_file() and p.suffix not in ('.zip','.aux','.out','.pyc')
        and '__pycache__' not in p.parts and p.name not in ('MANIFEST.json','PACKAGE_VALIDATION.json','package-replay.log','pdf-build.log','matched-accuracy-note.log'))
    paths.update((ROOT/'scripts').rglob('*.py'))
    paths.update(ROOT/p for p in ('LICENSE','DATA_LICENSE.md','environment/research-requirements.txt',
        'exploration/oms-if1-workflow-20261015/independent_check.py',
        'exploration/oms-if1-workflow-20261015/test_verification.py'))
    files=sorted(paths)
    manifest={'scope':'144 terminal comparisons plus one externally interrupted attempt; saved-point replay without optimization',
        'native_gurobi_and_cpp_binary_not_required_for_replay':True,
        'files':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size} for p in files]}
    (HERE/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    files.append(HERE/'MANIFEST.json')
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in files:z.write(p,str(p.relative_to(ROOT)))
        z.writestr('CONTENTS.sha256',''.join(f'{sha(p)}  {p.relative_to(ROOT)}\n' for p in files))
    print(json.dumps({'archive':str(target),'bytes':target.stat().st_size,'sha256':sha(target),'files':len(files)},indent=2))


if __name__=='__main__':main()
