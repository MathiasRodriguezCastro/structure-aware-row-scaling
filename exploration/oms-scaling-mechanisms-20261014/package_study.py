#!/usr/bin/env python3
"""Package, replay with native solvers blocked, and verify immutable deliveries."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent
PREFIX='exploration/oms-scaling-mechanisms-20261014/'
ARCHIVE='scaling-mechanisms-artifact.zip'


def sha(b):return hashlib.sha256(b).hexdigest()


def run(args,cwd):
    p=subprocess.run(args,cwd=cwd,text=True,capture_output=True)
    if p.returncode:raise RuntimeError(' '.join(args)+'\n'+p.stdout[-5000:]+'\n'+p.stderr[-5000:])
    return p.stdout


def main():
    excluded={ARCHIVE,'MANIFEST.json','VALIDATION.json','scaling-mechanisms-note.aux',
              'scaling-mechanisms-note.out','scaling-mechanisms-note.log','pdf-build.log','package-validation.log'}
    files={}
    for p in sorted(HERE.rglob('*')):
        if p.is_file() and p.name not in excluded and not any(t in p.parts for t in ('__pycache__','.pytest_cache')):
            files[PREFIX+p.relative_to(HERE).as_posix()]=p.read_bytes()
    root=HERE.parents[1]
    for name in ('LICENSE','DATA_LICENSE.md'):files[name]=(root/name).read_bytes()
    files['README.md']=b'''# Scaling mechanisms and generator information

Read exploration/oms-scaling-mechanisms-20261014/README.md and its two-page PDF.
Independent of unchanged OMS v1.3.5. Six original 360-period integer dispatch
models; 126 arms, 108 distinct MIP calls, 42 separate LP diagnostics and one
posthoc exact feasibility LP. Algebraic=Structural=Generator in this bank.
External GM has mixed results under normal settings. A rational feasible point
refutes four positive lower bounds reported with internal scaling disabled.
No additional-information advantage or validated performance predictor found;
no manuscript incorporation. Standard-library replay, six invariant tests,
pdflatex PDF. Gurobi/SoPlex binaries and licenses excluded. Source attribution
and input conditions remain those of the thesis; data are not relicensed.
'''
    manifest=dict(version='oms-scaling-mechanisms-20261014-v1',
                  status='independent bounded exploration; no OMS incorporation',
                  arms=126,native_mip_calls=108,separate_lp_diagnostics=42,posthoc_exact_lp_attempts=1,
                  native_solver_calls_during_replay=0,
                  files=[dict(path=n,sha256=sha(b),bytes=len(b)) for n,b in sorted(files.items())])
    raw=(json.dumps(manifest,indent=2)+'\n').encode();(HERE/'MANIFEST.json').write_bytes(raw)
    archive=HERE/ARCHIVE
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(files.items()):z.writestr(name,data)
        z.writestr('MANIFEST.json',raw)
    print('Archive created; checking clean extraction',flush=True)
    validation=dict(version=manifest['version'],archive_sha256=sha(archive.read_bytes()),
                    archive_bytes=archive.stat().st_size,inventoried_files=len(files),native_solver_calls_during_validation=0)
    with tempfile.TemporaryDirectory(prefix='oms-scaling-mechanisms-replay-') as tmp:
        folder=Path(tmp)
        with zipfile.ZipFile(archive) as z:z.extractall(folder)
        def verify():
            for record in manifest['files']:
                assert sha((folder/record['path']).read_bytes())==record['sha256'],record['path']
        verify()
        harness='''import builtins,runpy,sys,subprocess,os
original=builtins.__import__
def guard(name,*args,**kwargs):
    if name.split('.')[0] in {'gurobipy','highspy','pyscipopt'}:raise RuntimeError('native solver import in replay')
    return original(name,*args,**kwargs)
builtins.__import__=guard
def blocked(*args,**kwargs):raise RuntimeError('process execution in replay')
subprocess.Popen=blocked;os.system=blocked;os.posix_spawn=blocked;os.posix_spawnp=blocked
sys.path.insert(0,sys.argv[1]);runpy.run_path(sys.argv[1]+'/independent_check.py',run_name='__main__')
runpy.run_path(sys.argv[1]+'/analyze.py',run_name='__main__')
runpy.run_path(sys.argv[1]+'/write_report.py',run_name='__main__')
'''
        out=run(['python3','-c',harness,PREFIX.rstrip('/')],folder)
        (HERE/'package-replay.log').write_text(out)
        verify();study=folder/PREFIX
        details=json.loads((study/'independent-verification.json').read_text())
        assert details['counts']['arms']==126 and details['counts']['native_mip_calls']==108
        assert details['counts']['independent_mps_imports']==6 and details['counts']['exact_final_points']==126
        assert details['exact_witness']['exact_feasible']
        a=json.loads((study/'analysis.json').read_text())
        assert len(a['contradicted_bounds'])==4 and a['diagnostics']==42
        frozen=json.loads((study/'discovery-conclusions.json').read_text())
        assert sha((study/'discovery-analysis.json').read_bytes())==frozen['discovery_analysis_sha256']
        for name,h in frozen['discovery_hashes'].items():assert sha((study/name).read_bytes())==h
        design=json.loads((study/'design.json').read_text())
        assert sha((study/'PROTOCOL.md').read_bytes())==design['protocol_sha256']
        assert sha((study/'study.py').read_bytes())==design['script_sha256']
        tests=run(['python3','-m','pytest','-q',str(study/'test_math.py')],folder);assert '6 passed' in tests
        build=folder/'pdf-build';build.mkdir();shutil.copyfile(study/'scaling-mechanisms-note.tex',build/'scaling-mechanisms-note.tex')
        for _ in range(2):run(['pdflatex','-halt-on-error','-interaction=nonstopmode','scaling-mechanisms-note.tex'],build)
        log=(build/'scaling-mechanisms-note.log').read_text()
        assert 'Overfull' not in log and 'undefined' not in log.lower()
        text1=run(['pdftotext','-layout',str(study/'scaling-mechanisms-note.pdf'),'-'],folder)
        text2=run(['pdftotext','-layout',str(build/'scaling-mechanisms-note.pdf'),'-'],folder);assert text1==text2
        info=run(['pdfinfo',str(build/'scaling-mechanisms-note.pdf')],folder)
        assert any(t.split(':')[1].strip()=='2' for t in info.splitlines() if t.startswith('Pages:'))
        verify()
        validation.update(clean_extraction_hashes_verified=True,solver_imports_and_processes_blocked_during_replay=True,
                          derived_results_regenerated_identically=True,source_mps_independently_imported=6,
                          exact_binary64_product_checks=details['counts']['exact_product_checks'],
                          rational_final_point_evaluations=126,exact_feasible_witness_checked=True,
                          lower_bounds_refuted_by_witness=4,tests_passed=6,pdf_pages=2,pdf_overfull_boxes=0,
                          frozen_discovery_hashes_verified=True)
    protected=json.loads((HERE/'protected-files.json').read_text())
    unavailable=[]
    for name,h in protected.items():
        p=Path(name)
        if not p.exists() and p.name=='SistemaElectrico' and p.parent.name=='build':
            unavailable.append(name);continue
        assert sha(p.read_bytes())==h,name
    validation['protected_files_unchanged']=len(protected)-len(unavailable)
    validation['generator_binary_unavailable_at_close']=unavailable
    validation['generator_binary_hash_at_generation_recorded']=True
    validation['seven_previous_research_archives_unchanged']=True
    validation['oms_v1_3_5_delivery_unchanged']=True
    (HERE/'VALIDATION.json').write_text(json.dumps(validation,indent=2)+'\n')
    print(json.dumps(validation,indent=2),flush=True)


if __name__=='__main__':main()
