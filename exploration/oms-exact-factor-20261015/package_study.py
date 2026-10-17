#!/usr/bin/env python3
"""Self-contained package and clean, optimizer-blocked deterministic replay."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PREFIX='exploration/oms-exact-factor-20261015/'
ARCHIVE='exact-factor-artifact.zip'


def sha(b):return hashlib.sha256(b).hexdigest()
def run(args,cwd):
    p=subprocess.run(args,cwd=cwd,capture_output=True,text=True)
    if p.returncode:raise RuntimeError(' '.join(args)+'\n'+p.stdout[-2500:]+'\n'+p.stderr[-2500:])
    return p.stdout


def main():
    excluded={ARCHIVE,'MANIFEST.json','VALIDATION.json'};files={}
    for p in sorted(HERE.rglob('*')):
        if p.is_file() and p.name not in excluded and p.suffix not in ('.log','.aux','.out') and not any(s in p.parts for s in ('__pycache__','.pytest_cache')):
            files[PREFIX+p.relative_to(HERE).as_posix()]=p.read_bytes()
    files['LICENSE']=(ROOT/'LICENSE').read_bytes()
    files['README.md']=b'''# Exact row factors: independent OMS exploration

Read exploration/oms-exact-factor-20261015/README.md and its three-page PDF.
Complete exact-product binary64 factors and a finite rounded export-aware
selector, original-data contract replay, and a limited primary-literature
review. Three known dispatch models, no new optimizer calls, no performance
or novelty claim. No additional real-budget admissibility found, no paper change.
Model inputs and exact decisions are included. Python standard library,
pytest and pdfLaTeX suffice; no optimizer library or licence is required.
'''
    manifest=dict(version='oms-exact-factor-20261015-v1',self_contained_data=True,
        native_optimizer_calls=0,novelty_claim=False,performance_claim=False,
        files=[dict(path=n,bytes=len(b),sha256=sha(b)) for n,b in sorted(files.items())])
    raw=(json.dumps(manifest,indent=2)+'\n').encode();(HERE/'MANIFEST.json').write_bytes(raw)
    archive=HERE/ARCHIVE
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for n,b in sorted(files.items()):z.writestr(n,b)
        z.writestr('MANIFEST.json',raw)
    validation=dict(version=manifest['version'],archive_sha256=sha(archive.read_bytes()),
        archive_bytes=archive.stat().st_size,inventoried_files=len(files),native_optimizer_calls=0,
        self_contained_model_inputs=True)
    print('Archive ready; clean replay without optimizers',flush=True)
    with tempfile.TemporaryDirectory(prefix='oms-exact-factor-replay-') as tmp:
        folder=Path(tmp)
        with zipfile.ZipFile(archive) as z:z.extractall(folder)
        def verify():
            for r in manifest['files']:assert sha((folder/r['path']).read_bytes())==r['sha256'],r['path']
        verify()
        harness='''import builtins,runpy,sys,subprocess,os
original=builtins.__import__
def guard(name,*args,**kwargs):
    if name.split('.')[0] in {'gurobipy','highspy','pyscipopt','cplex'}:raise RuntimeError('optimizer import in replay')
    return original(name,*args,**kwargs)
builtins.__import__=guard
def blocked(*args,**kwargs):raise RuntimeError('process execution in replay')
subprocess.Popen=blocked;os.system=blocked;os.posix_spawn=blocked;os.posix_spawnp=blocked
study=sys.argv[1];sys.path.insert(0,study)
for name in ['study.py','independent_check.py','math_checks.py','analyze.py','write_report.py']:
    sys.argv=[study+'/'+name];runpy.run_path(study+'/'+name,run_name='__main__')
'''
        out=run(['python3','-c',harness,PREFIX.rstrip('/')],folder);(HERE/'package-replay.log').write_text(out)
        # Wall-clock script timing is explicitly excluded from bitwise replay.
        study=folder/PREFIX;timing=study/'selection-timing.json'
        measured=json.loads(timing.read_text());assert measured['optimizer_calls']==0 and measured['seconds']>0
        timing.write_bytes(files[PREFIX+'selection-timing.json']);verify()
        independent=json.loads((study/'independent-verification.json').read_text())
        math=json.loads((study/'mathematical-checks.json').read_text())
        assert independent['factor_decisions_checked']==246240
        assert independent['complete_optimality_checks']==138240
        assert independent['finite_aware_pool_minima_checked']==38880
        assert math['toy_candidate_comparisons']==14000 and math['binary64_cases_count']==300
        tests=run(['python3','-m','pytest','-q',str(study/'test_factors.py')],folder)
        assert '5 passed' in tests
        build=folder/'pdf-build';build.mkdir()
        shutil.copyfile(study/'exact-factor-note.tex',build/'exact-factor-note.tex')
        for _ in range(2):run(['pdflatex','-halt-on-error','-interaction=nonstopmode','exact-factor-note.tex'],build)
        log=(build/'exact-factor-note.log').read_text()
        assert 'Overfull' not in log and 'undefined' not in log.lower()
        one=run(['pdftotext','-layout',str(study/'exact-factor-note.pdf'),'-'],folder)
        two=run(['pdftotext','-layout',str(build/'exact-factor-note.pdf'),'-'],folder);assert one==two
        info=run(['pdfinfo',str(build/'exact-factor-note.pdf')],folder)
        assert any(t.split(':')[1].strip()=='3' for t in info.splitlines() if t.startswith('Pages:'))
        verify()
        validation.update(clean_extraction_hashes_verified=True,optimizer_imports_and_processes_blocked=True,
            all_deterministic_outputs_identically_regenerated=True,timing_excluded_from_bitwise_replay=True,
            factor_decisions_checked=independent['factor_decisions_checked'],
            native_product_checks=independent['native_product_checks'],
            complete_exact_grid_optimality_checks=independent['complete_optimality_checks'],
            finite_aware_pool_minima_checked=independent['finite_aware_pool_minima_checked'],
            stress_interval_checks=independent['stress_interval_checks'],toy_candidate_comparisons=14000,
            binary64_boundary_cases=300,tests_passed=5,pdf_pages=3,pdf_overfull_boxes=0)
    protected=json.loads((HERE/'protected-files.json').read_text())
    for n,h in protected.items():assert sha(Path(n).read_bytes())==h,n
    validation.update(protected_files_unchanged=len(protected),ten_previous_research_archives_unchanged=True,
        oms_v1_3_5_delivery_unchanged=True)
    (HERE/'VALIDATION.json').write_text(json.dumps(validation,indent=2)+'\n')
    print(json.dumps(validation,indent=2),flush=True)


if __name__=='__main__':main()
