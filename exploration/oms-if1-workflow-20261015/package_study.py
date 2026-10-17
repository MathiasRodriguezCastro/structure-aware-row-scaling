#!/usr/bin/env python3
"""Self-contained data/source package with clean-extraction numerical replay."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
ARCHIVE='if1-workflow-artifact.zip'
PREFIX=HERE.relative_to(ROOT)


def digest(b):return hashlib.sha256(b).hexdigest()


def main():
    files={}
    excluded={ARCHIVE,'MANIFEST.json','PACKAGE_VALIDATION.json','package-validation.log',
        'package-replay.log','pdf-build.log','workflow-note.log','independent-check.log'}
    def add(p):files[str(p.relative_to(ROOT))]=p.read_bytes()
    for p in HERE.rglob('*'):
        if p.is_file() and p.name not in excluded and p.suffix not in ('.aux','.out') and not any(t in p.parts for t in ('__pycache__','.pytest_cache')):add(p)
    d=json.loads((HERE/'design.json').read_text())
    for rel in d['dependencies']:
        if rel!='code/build-audit/SistemaElectrico':add(ROOT/rel)
    add(ROOT/d['source_input'])
    for folder in ('scripts','code'):
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and p.suffix in ('.py','.cpp','.c','.h','.hpp','.mk') and not any(t.startswith('build') or t=='__pycache__' for t in p.relative_to(ROOT/folder).parts):add(p)
    for rel in ('LICENSE','code/Makefile','environment/research-requirements.txt'):
        add(ROOT/rel)
    manifest=dict(version='oms-if1-workflow-20261015-v1',principal_calls=12,
        first_pass_calls=12,new_milp_calls=24,new_lp_calls=0,
        offline_generator_binary_supplied=False,
        files=[dict(path=n,bytes=len(b),sha256=digest(b)) for n,b in sorted(files.items())])
    raw=(json.dumps(manifest,indent=2)+'\n').encode();(HERE/'MANIFEST.json').write_bytes(raw)
    archive=HERE/ARCHIVE
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for n,b in sorted(files.items()):z.writestr(n,b)
        z.writestr('MANIFEST.json',raw)
    print('Package prepared; validating clean extraction',flush=True)
    with tempfile.TemporaryDirectory(prefix='oms-if1-replay-') as temp:
        root=Path(temp)
        with zipfile.ZipFile(archive) as z:z.extractall(root)
        def verify():
            for entry in manifest['files']:
                assert digest((root/entry['path']).read_bytes())==entry['sha256'],entry['path']
        verify()
        guard='''import builtins,os,runpy,subprocess,sys
original=builtins.__import__
def safe(name,*args,**kw):
    if name.split('.')[0] in {'gurobipy','cplex','pyscipopt'}:raise RuntimeError('commercial optimizer imported during replay')
    return original(name,*args,**kw)
builtins.__import__=safe
def blocked(*args,**kw):raise RuntimeError('external process during replay')
subprocess.Popen=blocked;os.system=blocked;os.posix_spawn=blocked;os.posix_spawnp=blocked
import highspy
highspy.Highs.run=blocked
folder=sys.argv[1];sys.path.insert(0,folder)
for filename in ('independent_check.py','write_report.py'):
    sys.argv=[folder+'/'+filename];runpy.run_path(folder+'/'+filename,run_name='__main__')
'''
        env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'}
        r=subprocess.run(['python3','-c',guard,str(PREFIX)],cwd=root,env=env,capture_output=True,text=True)
        (HERE/'package-replay.log').write_text(r.stdout+r.stderr)
        assert r.returncode==0,(r.stdout+r.stderr)[-3000:]
        verify()
        r=subprocess.run(['python3','-m','pytest','-q',str(PREFIX/'test_verification.py')],cwd=root,env=env,capture_output=True,text=True)
        assert r.returncode==0 and '4 passed' in r.stdout,r.stdout+r.stderr
        study=root/PREFIX
        for _ in range(2):
            r=subprocess.run(['pdflatex','-halt-on-error','-interaction=nonstopmode','workflow-note.tex'],cwd=study,capture_output=True,text=True)
            assert r.returncode==0,r.stdout[-2000:]
        log=(study/'workflow-note.log').read_text()
        assert 'Overfull' not in log and 'undefined' not in log.lower()
        before=subprocess.check_output(['pdftotext','-layout',str(HERE/'workflow-note.pdf'),'-'],text=True)
        after=subprocess.check_output(['pdftotext','-layout',str(study/'workflow-note.pdf'),'-'],text=True)
        assert before==after
        # PDFs embed build timestamps; numerical files and source must match exactly.
        for entry in manifest['files']:
            if entry['path']!=str(PREFIX/'workflow-note.pdf'):
                assert digest((root/entry['path']).read_bytes())==entry['sha256'],entry['path']
    baseline=json.loads((HERE/'protected-baseline.json').read_text())
    frozen={p:h for p,h in baseline.items() if p.startswith('paper/submission/oms/releases/') or p.startswith('exploration/')}
    for p,h in frozen.items():assert digest((ROOT/p).read_bytes())==h,p
    report=dict(version=manifest['version'],archive_sha256=digest(archive.read_bytes()),
        archive_bytes=archive.stat().st_size,inventoried_files=len(files),
        clean_extraction_replay=True,all_numerical_outputs_identically_regenerated=True,
        commercial_optimizer_imports_and_solver_calls_blocked=True,external_processes_blocked_during_replay=True,
        tests_passed=4,note_pdf_rebuilt_without_overfull_or_undefined=True,
        frozen_releases_and_old_research_archives_unchanged=len(frozen),
        new_milp_calls=24,new_lp_calls=0)
    (HERE/'PACKAGE_VALIDATION.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
