#!/usr/bin/env python3
"""Archive the two-line exploration and validate a clean, solver-free replay."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PREFIX='exploration/oms-preventive-dispatch-20261014/'


def sha(data):return hashlib.sha256(data).hexdigest()


def run(command,cwd):
    p=subprocess.run(command,cwd=cwd,capture_output=True,text=True)
    if p.returncode:raise RuntimeError(' '.join(command)+'\n'+p.stdout[-4000:]+p.stderr[-4000:])
    return p.stdout


def main():
    excluded={'preventive-dispatch-artifact.zip','MANIFEST.json','VALIDATION.json',
              'preventive-dispatch-note.aux','preventive-dispatch-note.log','preventive-dispatch-note.out',
              'pdf-build.log','package-validation.log'}
    files={}
    for p in HERE.rglob('*'):
        if p.is_file() and p.name not in excluded and not any(s in p.parts for s in ('__pycache__','.pytest_cache')):
            files[PREFIX+p.relative_to(HERE).as_posix()]=p.read_bytes()
    for r in json.loads((HERE/'preventive-results.json').read_text()):
        p=ROOT/r['input'];files[p.relative_to(ROOT).as_posix()]=p.read_bytes()
    files['LICENSE']=(ROOT/'LICENSE').read_bytes()
    files['README.md']=b'''# Preventive guarantees and dispatch cut filtering

Read exploration/oms-preventive-dispatch-20261014/README.md and its four-page PDF.
Separate from unchanged OMS v1.3.5, the six prior archives and thesis C++ sources.
Computable sufficient cofactor envelopes for eight rational models: conservative,
not claimed novel or practically useful. Three tiny complete-family checks.
45 Benders filtering arms on three stored eight-period dispatch LPs, two related.
1896 recourse calls, 237 masters, 24 shared-floor LPs, nine numerical references,
and three post-experiment rational LP attempts. No integer dispatch solve.
Filters did not outperform All; physical labels did not vary. Two exact reference
LP optima certified, one SoPlex unknown retained; no infeasibility inference.
Stored replay uses Python/NumPy/SymPy; tests also import gurobipy but do not construct
or solve native models. PDF uses pdflatex. Binaries and licenses excluded.
Root MANIFEST.json inventories this ZIP; VALIDATION.json is outside to avoid a
circular archive hash. MIT covers our code; third-party inputs and thesis-source
copies retain their original source attribution and conditions, not relicensed.
'''
    manifest={'version':'oms-preventive-dispatch-20261014-v1',
              'status':'independent research; conditional sufficient bounds and negative finite filtering experiment; no OMS incorporation',
              'benders_arms':45,'native_lp_calls_total':2169,'unknown_posthoc_reference':'rn8',
              'solver_calls_needed_for_replay':0,'solver_binaries_excluded':True,
              'files':[{'path':name,'sha256':sha(data),'bytes':len(data)} for name,data in sorted(files.items())]}
    raw=(json.dumps(manifest,indent=2)+'\n').encode();(HERE/'MANIFEST.json').write_bytes(raw)
    archive=HERE/'preventive-dispatch-artifact.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(files.items()):z.writestr(name,data)
        z.writestr('MANIFEST.json',raw)
    validation={'version':manifest['version'],'archive_sha256':sha(archive.read_bytes()),'archive_bytes':archive.stat().st_size,
                'inventoried_files':len(manifest['files']),'native_solver_calls_during_validation':0}
    print('Archive written; checking clean extraction',flush=True)
    with tempfile.TemporaryDirectory(prefix='oms-preventive-dispatch-replay-') as tmp:
        folder=Path(tmp)
        with zipfile.ZipFile(archive) as z:z.extractall(folder)
        def verify():
            for record in manifest['files']:
                assert sha((folder/record['path']).read_bytes())==record['sha256'],record['path']
        verify()
        run(['python3',PREFIX+'preventive.py'],folder)
        harness='''import builtins,runpy,sys,subprocess,os
original=builtins.__import__
def guard(name,*args,**kwargs):
    if name.split('.')[0] in {'gurobipy','highspy','pyscipopt'}:raise RuntimeError('native solver import in replay')
    return original(name,*args,**kwargs)
builtins.__import__=guard
def blocked(*args,**kwargs):raise RuntimeError('process execution in replay')
subprocess.Popen=blocked;os.system=blocked;os.posix_spawn=blocked;os.posix_spawnp=blocked
sys.path.insert(0,sys.argv[1]);runpy.run_path(sys.argv[1]+'/independent_check.py',run_name='__main__')
'''
        run(['python3','-c',harness,PREFIX.rstrip('/')],folder)
        print('Cofactor bounds, original MPS, exact cuts and filtering decisions verified',flush=True)
        test_harness='''import gurobipy as gp,sys
def blocked(*args,**kwargs):raise RuntimeError('native model creation in pure-math tests')
gp.Model=blocked;gp.Env=blocked
import pytest
raise SystemExit(pytest.main(sys.argv[1:]))
'''
        tests=run(['python3','-c',test_harness,'-q',PREFIX+'test_math.py'],folder);assert '6 passed' in tests
        run(['python3',PREFIX+'write_report.py'],folder);verify()
        print('Six tests passed; sources and derived tables regenerate identically',flush=True)
        study=folder/PREFIX;build=folder/'pdf-build';build.mkdir();shutil.copy2(study/'preventive-dispatch-note.tex',build/'preventive-dispatch-note.tex')
        for _ in range(2):run(['pdflatex','-halt-on-error','-interaction=nonstopmode','preventive-dispatch-note.tex'],build)
        log=(build/'preventive-dispatch-note.log').read_text();assert 'Overfull' not in log and 'undefined' not in log.lower()
        original=run(['pdftotext','-layout',str(study/'preventive-dispatch-note.pdf'),'-'],folder)
        rebuilt=run(['pdftotext','-layout',str(build/'preventive-dispatch-note.pdf'),'-'],folder);assert original==rebuilt
        info=run(['pdfinfo',str(build/'preventive-dispatch-note.pdf')],folder)
        assert any(line.split(':')[1].strip()=='4' for line in info.splitlines() if line.startswith('Pages:'))
        verify();details=json.loads((study/'independent-verification.json').read_text())
        assert details['benders_arms']==45 and details['exact_online_dual_or_ray_checks']==1896
        assert details['common_dual_nonemptiness_proofs']==8 and details['independent_preventive_exponent_checks']==8
        assert details['post_experiment_exact_lp_optima_certified']==2 and details['post_experiment_exact_lp_unknown']==['rn8']
        assert details['all_cut_filter_decisions_independently_replayed']
        for name in ('dispatch.py','preventive.py','PROTOCOL.md'):
            assert sha((study/name).read_bytes())==sha((study/('snapshot-'+name)).read_bytes())
        validation.update(all_hashes_verified_before_and_after_replay=True,
                          cofactor_bounds_and_complete_small_families_regenerated=True,
                          source_mps_models_independently_parsed=3,common_dual_hypotheses_verified=8,
                          exact_cut_checks=1896,all_filter_decisions_replayed=True,
                          native_imports_and_process_execution_blocked_during_replay=True,
                          native_model_construction_blocked_during_tests=True,tests_passed=6,
                          unknown_exact_reference_retained=True,pdf_recompiled_from_clean_extraction=True,
                          report_and_tables_regeneration_identical=True,pdf_text_identical=True,pdf_pages=4,
                          overfull_boxes=0,undefined_references=0,details=details)
    print('Four-page PDF rebuilt; checking OMS, six prior archives and thesis sources',flush=True)
    run(['sha256sum','-c','SHA256SUMS'],ROOT/'paper/submission/oms/releases/v1.3.5-oms-submission')
    previous=(('oms-certificate-feedback-20261014','feedback-artifact.zip'),
              ('oms-objective-budget-20261014','objective-artifact.zip'),
              ('oms-transfer-study-20261014','transfer-artifact.zip'),
              ('oms-quality-followup-20261014','quality-artifact.zip'),
              ('oms-decision-study-20261014','decision-artifact.zip'),
              ('oms-generalization-20261014','exploration-artifact.zip'))
    for name,archive_name in previous:
        p=ROOT/'exploration'/name;record=json.loads((p/'VALIDATION.json').read_text())
        assert sha((p/archive_name).read_bytes())==record['archive_sha256']
    thesis=Path('/home/mathiasr/Escritorio/proyectoTesis/Implementacion_Cpp/Codigo_Cpp')
    sources=('SystemController/Problema/BranchAndPrice/ANALISIS_BENDERS.md',
             'SystemController/Problema/BranchAndPrice/verify_benders4.py',
             'SystemController/Problema/BranchAndPrice/ProblemaBranchAndPrice.cpp',
             'reportes/seccion_descomposicion_matematica.tex')
    for source in sources:assert sha((thesis/source).read_bytes())==sha((HERE/'source-audit'/Path(source).name).read_bytes())
    for record in json.loads((HERE/'inputs/provenance.json').read_text()):
        assert sha(Path(record['source']).read_bytes())==record['source_sha256']
    validation.update(frozen_oms_v1_3_5_hashes_match=True,six_previous_research_archives_unchanged=True,
                      four_inspected_thesis_sources_unchanged=True,three_original_dispatch_mps_unchanged=True)
    (HERE/'VALIDATION.json').write_text(json.dumps(validation,indent=2)+'\n')
    print(json.dumps({k:v for k,v in validation.items() if k!='details'},indent=2),flush=True)


if __name__=='__main__':main()
