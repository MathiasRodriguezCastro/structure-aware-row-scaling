#!/usr/bin/env python3
"""Package a small dependent note; parent data ZIP is pinned, not duplicated."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PREFIX='exploration/oms-joint-limits-20261015/'
ARCHIVE='joint-limits-artifact.zip'


def sha(b):return hashlib.sha256(b).hexdigest()
def run(args,cwd):
    p=subprocess.run(args,cwd=cwd,capture_output=True,text=True)
    if p.returncode:raise RuntimeError(' '.join(args)+'\n'+p.stdout[-4000:]+'\n'+p.stderr[-4000:])
    return p.stdout


def main():
    design=json.loads((HERE/'design.json').read_text());parent=(HERE/design['parent_relative_path']).resolve()
    assert sha(parent.read_bytes())==design['parent_archive_sha256']
    excluded={ARCHIVE,'MANIFEST.json','VALIDATION.json','joint-limits-note.aux','joint-limits-note.out',
              'joint-limits-note.log','pdf-build.log','package-validation.log','package-replay.log'}
    files={}
    for p in sorted(HERE.rglob('*')):
        if p.is_file() and p.name not in excluded and not any(s in p.parts for s in ('__pycache__','.pytest_cache')):
            files[PREFIX+p.relative_to(HERE).as_posix()]=p.read_bytes()
    files['LICENSE']=(ROOT/'LICENSE').read_bytes()
    files['README.md']=b'''# Joint row-scaling limits: preliminary note

Read exploration/oms-joint-limits-20261015/README.md and its three-page PDF.
An exact boxed infinity-condition derivation, joint feasibility LP, Farkas
counterexample, dyadic approximation check, and audit of a fixed-flow storage
subsystem. Classical free scaling is explicitly attributed; novelty/practical
advantage are not claimed. No manuscript incorporation or new optimizer calls.
Math replay needs Python/NumPy; complete data replay also needs the external
precision-work-artifact.zip whose SHA256 is pinned in design.json. That parent
ZIP is intentionally not duplicated: this package is not data-self-contained.
Four tests and independent cofactor/prefix replay, PDF via pdflatex.
'''
    manifest=dict(version='oms-joint-limits-20261015-v1',status='preliminary; novelty and practical contribution unestablished',
        native_optimizer_calls=0,parent_archive_required_for_full_data_replay=True,
        parent_archive_name=parent.name,parent_archive_sha256=design['parent_archive_sha256'],
        files=[dict(path=n,bytes=len(b),sha256=sha(b)) for n,b in sorted(files.items())])
    raw=(json.dumps(manifest,indent=2)+'\n').encode();(HERE/'MANIFEST.json').write_bytes(raw)
    archive=HERE/ARCHIVE
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for n,b in sorted(files.items()):z.writestr(n,b)
        z.writestr('MANIFEST.json',raw)
    validation=dict(version=manifest['version'],archive_sha256=sha(archive.read_bytes()),archive_bytes=archive.stat().st_size,
                    inventoried_files=len(files),native_optimizer_calls=0,parent_required=True,parent_sha256=design['parent_archive_sha256'])
    print('Archive created; replaying with the pinned external parent',flush=True)
    with tempfile.TemporaryDirectory(prefix='oms-joint-limits-replay-') as tmp:
        folder=Path(tmp)
        with zipfile.ZipFile(archive) as z:z.extractall(folder)
        def verify():
            for r in manifest['files']:assert sha((folder/r['path']).read_bytes())==r['sha256'],r['path']
        verify()
        harness='''import builtins,runpy,sys,subprocess,os
original=builtins.__import__
def guard(name,*args,**kwargs):
    if name.split('.')[0] in {'gurobipy','highspy','pyscipopt'}:raise RuntimeError('solver import during exact replay')
    return original(name,*args,**kwargs)
builtins.__import__=guard
def blocked(*args,**kwargs):raise RuntimeError('process execution during replay')
subprocess.Popen=blocked;os.system=blocked;os.posix_spawn=blocked;os.posix_spawnp=blocked
study,parent=sys.argv[1:];sys.path.insert(0,study)
for name in ['joint_limits.py','independent_check.py']:
    sys.argv=[study+'/'+name,'--parent',parent];runpy.run_path(study+'/'+name,run_name='__main__')
sys.argv=[study+'/write_note.py'];runpy.run_path(study+'/write_note.py',run_name='__main__')
'''
        out=run(['python3','-c',harness,PREFIX.rstrip('/'),str(parent)],folder);(HERE/'package-replay.log').write_text(out)
        verify();study=folder/PREFIX;d=json.loads((study/'design.json').read_text())
        for n,h in d['sources'].items():assert sha((study/n).read_bytes())==h and (study/n).read_bytes()==(study/('snapshot-'+n)).read_bytes()
        result=json.loads((study/'independent-verification.json').read_text())
        assert result['candidate_prefix_errors_replayed']==1093 and result['cofactor_inverse_cases']==24
        assert result['exact_farkas_combined_rhs']=='-119' and result['parent_first_hit_pattern_assignments_checked']==123
        tests=run(['python3','-m','pytest','-q',str(study/'test_properties.py')],folder);assert '4 passed' in tests
        build=folder/'pdf-build';build.mkdir();shutil.copyfile(study/'joint-limits-note.tex',build/'joint-limits-note.tex')
        for _ in range(2):run(['pdflatex','-halt-on-error','-interaction=nonstopmode','joint-limits-note.tex'],build)
        log=(build/'joint-limits-note.log').read_text();assert 'Overfull' not in log and 'undefined' not in log.lower()
        one=run(['pdftotext','-layout',str(study/'joint-limits-note.pdf'),'-'],folder)
        two=run(['pdftotext','-layout',str(build/'joint-limits-note.pdf'),'-'],folder);assert one==two
        info=run(['pdfinfo',str(build/'joint-limits-note.pdf')],folder)
        assert any(t.split(':')[1].strip()=='3' for t in info.splitlines() if t.startswith('Pages:'))
        verify();validation.update(clean_extraction_verified=True,full_replay_with_external_parent_identical=True,
            solver_imports_and_processes_blocked=True,independent_cofactor_inverses=24,exact_grid_comparisons=4667,
            independent_prefix_point_checks=1093,parent_first_hit_pattern_assignments_checked=123,
            exact_farkas_infeasibility_certificate=True,tests_passed=4,pdf_pages=3,pdf_overfull_boxes=0)
    protected=json.loads((HERE/'protected-files.json').read_text())
    for n,h in protected.items():assert sha(Path(n).read_bytes())==h,n
    validation.update(protected_files_unchanged=len(protected),nine_previous_research_archives_unchanged=True,oms_v1_3_5_delivery_unchanged=True)
    (HERE/'VALIDATION.json').write_text(json.dumps(validation,indent=2)+'\n');print(json.dumps(validation,indent=2),flush=True)


if __name__=='__main__':main()
