#!/usr/bin/env python3
"""Freeze the finite frontier study and verify a clean solver-free replay."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PREFIX='exploration/oms-precision-work-20261015/'
ARCHIVE='precision-work-artifact.zip'


def sha(b):return hashlib.sha256(b).hexdigest()


def run(args,cwd):
    p=subprocess.run(args,cwd=cwd,capture_output=True,text=True)
    if p.returncode:raise RuntimeError(' '.join(args)+'\n'+p.stdout[-5000:]+'\n'+p.stderr[-5000:])
    return p.stdout


def main():
    excluded={ARCHIVE,'MANIFEST.json','VALIDATION.json','precision-work-note.aux','precision-work-note.out',
              'precision-work-note.log','pdf-build.log','package-validation.log','package-replay.log'}
    files={}
    for p in sorted(HERE.rglob('*')):
        if p.is_file() and p.name not in excluded and not any(s in p.parts for s in ('__pycache__','.pytest_cache')):
            files[PREFIX+p.relative_to(HERE).as_posix()]=p.read_bytes()
    for name in ('LICENSE','DATA_LICENSE.md'):files[name]=(ROOT/name).read_bytes()
    files['README.md']=b'''# Precision/work with a common quality target

Read exploration/oms-precision-work-20261015/README.md and its three-page PDF.
Separate from unchanged OMS v1.3.5. Three known integer 360-period hydro models,
90 arms, 63 distinct MILP calls, 1093 candidates, three exact prior references,
25 posthoc rational pattern LPs. With each policy fixed, first arrivals coincide
across acceptance precisions; reselecting factors can change search behavior.
Objective quality discriminates delivery. Budget has a small local
advantage in 001, loses elsewhere, and is not incorporated into the paper.
Replay needs Python/NumPy; figures need Matplotlib; tests pytest; PDF pdflatex.
Gurobi and SoPlex are only for new optimization calls, never the stored replay.
Binaries/licenses excluded. Own code uses repo license; original thesis inputs
keep their provenance and conditions and are not relicensed here.
'''
    manifest=dict(version='oms-precision-work-20261015-v1',status='independent research; no OMS incorporation',
                  arms=90,native_mip_calls=63,candidate_events=1093,prior_reference_lp_calls=3,posthoc_rational_lp_calls=25,
                  files=[dict(path=n,bytes=len(b),sha256=sha(b)) for n,b in sorted(files.items())])
    raw=(json.dumps(manifest,indent=2)+'\n').encode();(HERE/'MANIFEST.json').write_bytes(raw)
    archive=HERE/ARCHIVE
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for n,b in sorted(files.items()):z.writestr(n,b)
        z.writestr('MANIFEST.json',raw)
    validation=dict(version=manifest['version'],archive_sha256=sha(archive.read_bytes()),archive_bytes=archive.stat().st_size,
                    inventoried_files=len(files),native_solver_calls_during_validation=0)
    print('Archive created; checking clean extraction',flush=True)
    with tempfile.TemporaryDirectory(prefix='oms-precision-work-replay-') as tmp:
        folder=Path(tmp)
        with zipfile.ZipFile(archive) as z:z.extractall(folder)
        def verify():
            for r in manifest['files']:assert sha((folder/r['path']).read_bytes())==r['sha256'],r['path']
        verify()
        harness='''import builtins,runpy,sys,subprocess,os
original=builtins.__import__
def guard(name,*args,**kwargs):
    if name.split('.')[0] in {'gurobipy','highspy','pyscipopt'}:raise RuntimeError('native solver import during replay')
    return original(name,*args,**kwargs)
builtins.__import__=guard
def blocked(*args,**kwargs):raise RuntimeError('child process during replay')
subprocess.Popen=blocked;os.system=blocked;os.posix_spawn=blocked;os.posix_spawnp=blocked
sys.path.insert(0,sys.argv[1])
for name in ['independent_check.py','analyze.py','write_report.py']:
    runpy.run_path(sys.argv[1]+'/'+name,run_name='__main__')
'''
        out=run(['python3','-c',harness,PREFIX.rstrip('/')],folder)
        (HERE/'package-replay.log').write_text(out);verify()
        study=folder/PREFIX;details=json.loads((study/'independent-verification.json').read_text())
        counts=details['counts'];assert counts['native_mip_calls']==63 and counts['candidate_vectors_checked']==1093
        assert counts['arms_checked']==90 and counts['original_lp_imports']==3
        assert counts['posthoc_exact_optimum_certificates_checked']==counts['posthoc_exact_feasible_patterns']==25
        a=json.loads((study/'analysis.json').read_text())
        assert a['arms_with_identical_first_hits_across_precision_scenarios']==90
        assert sum(r['budget_supported_faster'] for r in a['matched_comparisons'])==3
        tests=run(['python3','-m','pytest','-q',str(study/'test_math.py')],folder);assert '6 passed' in tests
        build=folder/'pdf-build';build.mkdir()
        for name in ['precision-work-note.tex','work-to-target.pdf']:shutil.copyfile(study/name,build/name)
        for _ in range(2):run(['pdflatex','-halt-on-error','-interaction=nonstopmode','precision-work-note.tex'],build)
        log=(build/'precision-work-note.log').read_text();assert 'Overfull' not in log and 'undefined' not in log.lower()
        text1=run(['pdftotext','-layout',str(study/'precision-work-note.pdf'),'-'],folder)
        text2=run(['pdftotext','-layout',str(build/'precision-work-note.pdf'),'-'],folder);assert text1==text2
        info=run(['pdfinfo',str(build/'precision-work-note.pdf')],folder)
        assert any(t.split(':')[1].strip()=='3' for t in info.splitlines() if t.startswith('Pages:'))
        verify()
        validation.update(clean_extraction_hashes_verified=True,native_solver_imports_and_processes_blocked=True,
                          derived_outputs_and_figures_identically_regenerated=True,original_lp_imports=3,
                          rational_candidate_evaluations=1093,exact_product_checks=counts['exact_product_checks'],
                          exact_reference_certificates=3,exact_pattern_lp_optima=25,
                          tests_passed=6,pdf_pages=3,pdf_overfull_boxes=0)
    protected=json.loads((HERE/'protected-files.json').read_text())
    for n,h in protected.items():assert sha(Path(n).read_bytes())==h,n
    validation.update(protected_files_unchanged=len(protected),eight_previous_research_archives_unchanged=True,oms_v1_3_5_delivery_unchanged=True)
    (HERE/'VALIDATION.json').write_text(json.dumps(validation,indent=2)+'\n')
    print(json.dumps(validation,indent=2),flush=True)


if __name__=='__main__':main()
