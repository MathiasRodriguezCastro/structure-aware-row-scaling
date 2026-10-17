#!/usr/bin/env python3
"""Package only this study and its pinned dependencies, then replay cleanly."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PREFIX='exploration/oms-transfer-study-20261014/'
PREVIOUS=ROOT/'exploration/oms-decision-study-20261014'
PILOT=ROOT/'exploration/oms-generalization-20261014'
QUALITY=ROOT/'exploration/oms-quality-followup-20261014'


def sha(content):return hashlib.sha256(content).hexdigest()


def run(command,cwd):
    result=subprocess.run(command,cwd=cwd,capture_output=True,text=True)
    if result.returncode:
        raise RuntimeError(' '.join(command)+'\n'+result.stdout[-5000:]+result.stderr[-2000:])
    return result.stdout


def main():
    files={};excluded={'transfer-artifact.zip','MANIFEST.json','VALIDATION.json',
                       'transfer-note.aux','transfer-note.out','transfer-note.log',
                       'pdf-build.log','package-validation.log'}
    for path in HERE.rglob('*'):
        if not path.is_file() or path.name in excluded or any(p in path.parts for p in ('__pycache__','.pytest_cache')):continue
        files[PREFIX+path.relative_to(HERE).as_posix()]=path.read_bytes()
    def add(path):files[path.relative_to(ROOT).as_posix()]=path.read_bytes()
    for name in ('repair.py','independent_check.py','MANIFEST.json'):add(PREVIOUS/name)
    add(QUALITY/'controller.py')
    add(QUALITY/'confirmation/runs/control30-3-2-3/Cold-IF1-s31/final-exact-audit/rational-point.json')
    for name in ('generalization_study.py','PILOT_PROTOCOL.md','MIPLIB_SELECTION.json'):add(PILOT/name)
    # Only the prior reference input is needed by the frozen preparation lineage.
    for name in ('control30-3-2-3.mps.gz','provenance.json'):add(PILOT/'sources/miplib-models'/name)
    for name in ('scripts/research/budget_scaling.py','LICENSE'):add(ROOT/name)
    files['README.md']=b'''# Transfer and fixed-integer objective audit

Independent research outside OMS submission v1.3.5.
Read exploration/oms-transfer-study-20261014/README.md and transfer-note.pdf.
The four-page report covers 80 prospectively frozen treatments on four previously
unused explicitly labeled MIPLIB groups, a known reference, and two solvers.
A separate post-observation audit checks all 16 nive integer assignments:
12 exact primal/dual LP optimality certificates and 4 exact infeasibility rays.
Every certificate is restricted to its fixed integer pattern, never the full MIP.
All adverse data, timing overruns, source MPS and frozen protocols are retained.
Root MANIFEST.json inventories this ZIP; the prior manifest only pins a checker.
Python/NumPy and pytest suffice for stored verification without solver calls.
Solver binaries, commercial licenses and dependency installations are excluded.
Code has its MIT LICENSE. Third-party MIPLIB inputs retain their attribution;
the code license does not relicense those inputs. No paper publication is implied.
'''
    manifest={'version':'oms-transfer-study-20261014-v1',
              'status':'separate research; no manuscript incorporation or public publication',
              'oms_submission_unchanged':'v1.3.5-oms-submission',
              'prospective_treatments':80,'posthoc_fixed_pattern_lp_calls':16,
              'files':[{'path':name,'sha256':sha(content),'bytes':len(content)} for name,content in sorted(files.items())],
              'native_solver_calls_needed_for_replay':0,'solver_builds_excluded':True}
    data=(json.dumps(manifest,indent=2)+'\n').encode();(HERE/'MANIFEST.json').write_bytes(data)
    archive=HERE/'transfer-artifact.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,content in sorted(files.items()):z.writestr(name,content)
        z.writestr('MANIFEST.json',data)
    validation={'version':manifest['version'],'archive_sha256':sha(archive.read_bytes()),
                'archive_bytes':archive.stat().st_size,'inventoried_files':len(manifest['files']),
                'native_solver_calls_during_validation':0}
    print('Archive written; validating clean extraction',flush=True)
    with tempfile.TemporaryDirectory(prefix='oms-transfer-replay-') as tmp:
        folder=Path(tmp)
        with zipfile.ZipFile(archive) as z:z.extractall(folder)
        def verify():
            for record in manifest['files']:
                assert sha((folder/record['path']).read_bytes())==record['sha256'],record['path']
        verify()
        run(['python3',PREFIX+'independent_check.py'],folder)
        print('80-treatment independent arithmetic passed',flush=True)
        run(['python3',PREFIX+'cost_audit.py','replay'],folder)
        run(['python3',PREFIX+'check_cost_rays.py'],folder)
        print('12 primal/dual and 4 Farkas certificates passed',flush=True)
        tests=run(['python3','-m','pytest','-q',PREFIX+'test_cost_certificate.py',PREFIX+'test_farkas_certificate.py'],folder)
        assert '6 passed' in tests
        run(['python3',PREFIX+'write_report.py'],folder);verify()
        build=folder/'pdf-build';build.mkdir();shutil.copy2(folder/PREFIX/'transfer-note.tex',build/'transfer-note.tex')
        for _ in range(2):run(['pdflatex','-halt-on-error','-interaction=nonstopmode','transfer-note.tex'],build)
        log=(build/'transfer-note.log').read_text();assert 'Overfull' not in log and 'undefined' not in log.lower()
        original=run(['pdftotext','-layout',str(folder/PREFIX/'transfer-note.pdf'),'-'],folder)
        rebuilt=run(['pdftotext','-layout',str(build/'transfer-note.pdf'),'-'],folder);assert original==rebuilt
        info=run(['pdfinfo',str(build/'transfer-note.pdf')],folder)
        assert any(line.split(':')[1].strip()=='4' for line in info.splitlines() if line.startswith('Pages:'))
        verify()
        load=lambda p:json.loads((folder/PREFIX/p).read_text())
        main=load('confirmation/independent-verification.json');cost=load('cost-audit/independent-verification.json');rays=load('cost-audit/farkas-verification.json')
        assert main['native_calls']==80 and main['execution_errors']==0
        assert cost['primal_dual_optimum_certificates']==12 and rays['fixed_pattern_infeasibilities_verified']==4
        validation.update(all_hashes_verified_before_and_after_replay=True,independent_arithmetic_passed=True,
                          tests_passed=6,report_regeneration_identical=True,pdf_recompiled_from_clean_extraction=True,
                          pdf_text_identical=True,pdf_pages=4,overfull_boxes=0,undefined_references=0,
                          main_details=main,cost_details=cost,farkas_details=rays)
    run(['sha256sum','-c','SHA256SUMS'],ROOT/'paper/submission/oms/releases/v1.3.5-oms-submission')
    for path,name in ((PREVIOUS,'decision-artifact.zip'),(PILOT,'exploration-artifact.zip'),(QUALITY,'quality-artifact.zip')):
        previous=json.loads((path/'VALIDATION.json').read_text())
        assert sha((path/name).read_bytes())==previous['archive_sha256']
    validation.update(frozen_oms_v1_3_5_hashes_match=True,three_previous_research_archives_unchanged=True)
    (HERE/'VALIDATION.json').write_text(json.dumps(validation,indent=2)+'\n')
    print(json.dumps({k:v for k,v in validation.items() if not k.endswith('_details')},indent=2),flush=True)


if __name__=='__main__':main()
