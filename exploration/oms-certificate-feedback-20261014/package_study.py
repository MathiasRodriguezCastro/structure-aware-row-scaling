#!/usr/bin/env python3
"""Package this closed study and validate it from a clean, solver-free extraction."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PREFIX='exploration/oms-certificate-feedback-20261014/'
OBJECTIVE=ROOT/'exploration/oms-objective-budget-20261014'
TRANSFER=ROOT/'exploration/oms-transfer-study-20261014'
ARITH=ROOT/'exploration/oms-decision-study-20261014'


def sha(data):return hashlib.sha256(data).hexdigest()


def run(command,cwd):
    p=subprocess.run(command,cwd=cwd,capture_output=True,text=True)
    if p.returncode:raise RuntimeError(' '.join(command)+'\n'+p.stdout[-5000:]+p.stderr[-3000:])
    return p.stdout


def main():
    files={}
    excluded={'feedback-artifact.zip','MANIFEST.json','VALIDATION.json','feedback-note.aux',
              'feedback-note.log','feedback-note.out','pdf-build.log','package-validation.log'}
    for path in HERE.rglob('*'):
        if path.is_file() and path.name not in excluded and not any(p in path.parts for p in ('__pycache__','.pytest_cache')):
            files[PREFIX+path.relative_to(HERE).as_posix()]=path.read_bytes()
    def add(path):files[path.relative_to(ROOT).as_posix()]=path.read_bytes()
    for name in ('build_lp.py','rational_lp.py','independent_check.py','policy.py','MANIFEST.json','design.json'):
        add(OBJECTIVE/name)
    previous_design=json.loads((OBJECTIVE/'design.json').read_text())
    for p in previous_design['patterns']:
        if p['model']!='neos-3083784-nive':continue
        folder=OBJECTIVE/'characterization'/p['id']/'cost-0'
        for name in ('model.json','certificate.json','dual.json','ray.json','primal.json'):
            path=folder/name
            if path.exists():add(path)
    # Kept for prepare/preflight source paths, although stored replay uses the
    # new study's own canonical inputs and never re-runs a native importer.
    for name in ('original-model.json','neos-3083784-nive.mps.gz'):
        add(OBJECTIVE/'inputs/models/neos-3083784-nive'/name)
    add(TRANSFER/'confirmation/models/neos-3083784-nive/factors.json')
    for folder,names in ((ARITH,('independent_check.py','MANIFEST.json')),
                         (TRANSFER,('mps_check.py','MANIFEST.json'))):
        for name in names:add(folder/name)
    for name in ('provenance.json','neos-3083784-nive.mps.gz'):
        add(TRANSFER/'sources/miplib-models'/name)
    for path in (ROOT/'exploration/oms-generalization-20261014/generalization_study.py',
                 ROOT/'scripts/research/budget_scaling.py',ROOT/'LICENSE'):add(path)
    files['README.md']=b'''# Exact-certificate feedback: a closed finite experiment

Read exploration/oms-certificate-feedback-20261014/README.md and feedback-note.pdf.
Separate from unchanged OMS submission v1.3.5 and the thesis C++ implementation.
42 strategy outcomes, 60 native MIP calls, 51 exact LP calls; 24 inherited and
24 online global cut proofs. Feedback did not improve exact backed cost over
repair or matched restart in this selected model and three-seed experiment.
No global MIP optimality, complete unknown-pattern coverage or novelty claimed.
The preventive note states sufficient conditions with COMPLETE dual/ray families,
not supplied by this experiment. The dispatch-cut-selection note is a proposal.
The root MANIFEST.json inventories this archive; older manifests pin dependencies.
Stored replay needs Python/NumPy, tests pytest, plots Matplotlib, PDF pdflatex.
No solver binaries or licenses included. MIT applies to our code; third-party
MIPLIB inputs retain their own source attribution and data conditions.
VALIDATION.json is produced outside the ZIP to avoid a circular archive hash.
'''
    manifest={'version':'oms-certificate-feedback-20261014-v1',
              'status':'closed independent research; negative comparative result; no OMS incorporation',
              'strategy_results':42,'native_mip_calls':60,'exact_lp_calls':51,
              'global_cut_proofs':48,'solver_calls_needed_for_replay':0,
              'solver_binaries_excluded':True,
              'files':[{'path':name,'sha256':sha(content),'bytes':len(content)} for name,content in sorted(files.items())]}
    data=(json.dumps(manifest,indent=2)+'\n').encode();(HERE/'MANIFEST.json').write_bytes(data)
    archive=HERE/'feedback-artifact.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,content in sorted(files.items()):z.writestr(name,content)
        z.writestr('MANIFEST.json',data)
    validation={'version':manifest['version'],'archive_sha256':sha(archive.read_bytes()),
                'archive_bytes':archive.stat().st_size,'inventoried_files':len(manifest['files']),
                'native_solver_calls_during_validation':0}
    print('Archive written; checking a clean extraction',flush=True)
    with tempfile.TemporaryDirectory(prefix='oms-feedback-replay-') as tmp:
        folder=Path(tmp)
        with zipfile.ZipFile(archive) as z:z.extractall(folder)
        def verify():
            for record in manifest['files']:
                assert sha((folder/record['path']).read_bytes())==record['sha256'],record['path']
        verify()
        # Reject native interfaces and process execution during the replay.
        # This supplements inspection of a replay which calls no solver adapters.
        harness='''import builtins,runpy,sys,subprocess,os
original_import=builtins.__import__
def guarded(name,*args,**kwargs):
    if name.split('.')[0] in {'gurobipy','highspy','pyscipopt'}:
        raise RuntimeError('native solver import during replay: '+name)
    return original_import(name,*args,**kwargs)
builtins.__import__=guarded
def blocked(*args,**kwargs):raise RuntimeError('process execution during replay')
subprocess.Popen=blocked;os.system=blocked;os.posix_spawn=blocked;os.posix_spawnp=blocked
sys.path.insert(0,sys.argv[1])
runpy.run_path(sys.argv[1]+'/independent_check.py',run_name='__main__')
'''
        run(['python3','-c',harness,PREFIX.rstrip('/')],folder)
        print('Source constructions, rational certificates and temporal use checked',flush=True)
        study=folder/PREFIX
        checks=json.loads((study/'independent-verification.json').read_text())
        assert checks['strategy_results']==42 and checks['native_mip_calls']==60 and checks['exact_lp_calls']==51
        assert checks['online_global_cut_proofs']==24 and sum(checks['preflight_global_cut_proofs'].values())==24
        assert checks['C_better_upper_than_matched_restart']==0 and checks['C_target_gains_over_matched_restart']==0
        assert checks['only_temporally_available_proofs_used_for_cuts'] and checks['matched_starts_and_best_retention_checked']
        assert not checks['execution_errors'] and checks['global_mip_optimality_status']=='unverified'
        tests=run(['python3','-m','pytest','-q',PREFIX+'test_cuts.py',PREFIX+'test_verifier.py'],folder)
        assert '6 passed' in tests
        run(['python3',PREFIX+'write_report.py'],folder);verify()
        print('Six tests passed; report sources and figure regenerate identically',flush=True)
        build=folder/'pdf-build';build.mkdir()
        for name in ('feedback-note.tex','cut-transfer.pdf'):shutil.copy2(study/name,build/name)
        for _ in range(2):run(['pdflatex','-halt-on-error','-interaction=nonstopmode','feedback-note.tex'],build)
        log=(build/'feedback-note.log').read_text();assert 'Overfull' not in log and 'undefined' not in log.lower()
        original=run(['pdftotext','-layout',str(study/'feedback-note.pdf'),'-'],folder)
        rebuilt=run(['pdftotext','-layout',str(build/'feedback-note.pdf'),'-'],folder)
        assert original==rebuilt
        info=run(['pdfinfo',str(build/'feedback-note.pdf')],folder)
        assert any(line.split(':')[1].strip()=='4' for line in info.splitlines() if line.startswith('Pages:'))
        verify()
        validation.update(all_hashes_verified_before_and_after_replay=True,
                          independent_lp_construction_and_rational_proofs_passed=True,
                          native_solver_imports_and_process_execution_blocked_during_replay=True,
                          temporal_proof_availability_and_matched_starts_checked=True,
                          tests_passed=6,report_sources_and_figure_regeneration_identical=True,
                          pdf_recompiled_from_clean_extraction=True,pdf_text_identical=True,
                          pdf_pages=4,overfull_boxes=0,undefined_references=0,details=checks)
    print('Four-page PDF rebuilt; checking the frozen submission and prior archives',flush=True)
    run(['sha256sum','-c','SHA256SUMS'],ROOT/'paper/submission/oms/releases/v1.3.5-oms-submission')
    previous=(('oms-objective-budget-20261014','objective-artifact.zip'),
              ('oms-transfer-study-20261014','transfer-artifact.zip'),
              ('oms-quality-followup-20261014','quality-artifact.zip'),
              ('oms-decision-study-20261014','decision-artifact.zip'),
              ('oms-generalization-20261014','exploration-artifact.zip'))
    for name,archive_name in previous:
        folder=ROOT/'exploration'/name;record=json.loads((folder/'VALIDATION.json').read_text())
        assert sha((folder/archive_name).read_bytes())==record['archive_sha256']
    validation.update(frozen_oms_v1_3_5_hashes_match=True,five_previous_research_archives_unchanged=True)
    (HERE/'VALIDATION.json').write_text(json.dumps(validation,indent=2)+'\n')
    print(json.dumps({k:v for k,v in validation.items() if k!='details'},indent=2),flush=True)


if __name__=='__main__':main()
