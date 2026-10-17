#!/usr/bin/env python3
"""Archive and clean-replay the separate objective-budget investigation."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PREFIX='exploration/oms-objective-budget-20261014/'
OLD=ROOT/'exploration/oms-transfer-study-20261014'
ARITH=ROOT/'exploration/oms-decision-study-20261014'


def sha(data):return hashlib.sha256(data).hexdigest()


def run(command,cwd):
    result=subprocess.run(command,cwd=cwd,capture_output=True,text=True)
    if result.returncode:raise RuntimeError(' '.join(command)+'\n'+result.stdout[-5000:]+result.stderr[-3000:])
    return result.stdout


def main():
    files={};excluded={'objective-artifact.zip','MANIFEST.json','VALIDATION.json','objective-note.aux',
                       'objective-note.out','objective-note.log','pdf-build.log','package-validation.log'}
    for path in HERE.rglob('*'):
        if not path.is_file() or path.name in excluded or any(p in path.parts for p in ('__pycache__','.pytest_cache')):continue
        files[PREFIX+path.relative_to(HERE).as_posix()]=path.read_bytes()
    def add(path):files[path.relative_to(ROOT).as_posix()]=path.read_bytes()
    for name in ('mps_check.py','MANIFEST.json','VALIDATION.json'):add(OLD/name)
    for path in (OLD/'sources/miplib-models').iterdir():
        if path.is_file():add(path)
    for name in ('independent_check.py','MANIFEST.json'):add(ARITH/name)
    add(ROOT/'LICENSE')
    files['README.md']=b'''# Objective-budget sensitivity and certified candidate acceptance

Independent research, outside unchanged OMS submission v1.3.5.
Read exploration/oms-objective-budget-20261014/README.md and objective-note.pdf.
The four-page report covers 41 unique integer patterns from 72 stored deliveries,
208 exact LP calls, post-observation selective budgets and solver-free cost gates.
Ten row-only budget proofs reuse existing dual/primal certificates without solves.
Every statement is conditional on its fixed integer assignment. Potential budget
vulnerability is distinguished from the observed errors of native MIP outputs.
No new MIP solves, global optimality or superiority over exact repair is claimed.
The numerical LP failure and pre-solve construction correction are retained.
Root MANIFEST.json inventories the archive. Older manifests only pin dependencies.
Python/NumPy suffice for stored replay; pytest for tests; Matplotlib for figures.
Solver binaries and licenses are excluded. Code retains its MIT LICENSE;
third-party MIPLIB inputs retain attribution and are not relicensed as code.
'''
    manifest={'version':'oms-objective-budget-20261014-v1','status':'independent retrospective research; no OMS incorporation',
              'original_mip_treatments_reused':80,'new_mip_calls':0,'unique_integer_patterns':41,'new_lp_calls':208,
              'files':[{'path':name,'sha256':sha(content),'bytes':len(content)} for name,content in sorted(files.items())],
              'solver_calls_needed_for_replay':0,'solver_binaries_excluded':True}
    data=(json.dumps(manifest,indent=2)+'\n').encode();(HERE/'MANIFEST.json').write_bytes(data)
    archive=HERE/'objective-artifact.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,content in sorted(files.items()):z.writestr(name,content)
        z.writestr('MANIFEST.json',data)
    validation={'version':manifest['version'],'archive_sha256':sha(archive.read_bytes()),'archive_bytes':archive.stat().st_size,
                'inventoried_files':len(manifest['files']),'native_solver_calls_during_validation':0}
    print('Archive written; starting clean extraction replay',flush=True)
    with tempfile.TemporaryDirectory(prefix='oms-objective-replay-') as tmp:
        folder=Path(tmp)
        with zipfile.ZipFile(archive) as z:z.extractall(folder)
        def verify():
            for record in manifest['files']:assert sha((folder/record['path']).read_bytes())==record['sha256'],record['path']
        verify();run(['python3',PREFIX+'independent_check.py'],folder)
        print('All LP constructions and rational certificates checked',flush=True)
        tests=run(['python3','-m','pytest','-q',PREFIX+'test_rational_lp.py',PREFIX+'test_policy.py'],folder);assert '6 passed' in tests
        study=folder/PREFIX
        rowonly=json.loads((study/'row-only-proofs.json').read_text())
        selective=json.loads((study/'selective-design.json').read_text())['queue']
        assert len(rowonly)==10
        for r in rowonly:
            assert r['factor_exact']==next(s['factor'] for s in selective if s['pattern']==r['pattern'])
            assert r['changed_rows']==40 and r['changed_bound_variables']==0 and r['one_sided_cost_protection_certified']
        original_design=json.loads((study/'design-before-first-lp.json').read_text())
        assert sha((study/'pre-solve-build-before.py.txt').read_bytes())==original_design['source_hashes'][PREFIX+'build_lp.py']
        run(['python3',PREFIX+'write_report.py'],folder);verify()
        build=folder/'pdf-build';build.mkdir()
        for name in ('objective-note.tex','objective-sensitivity.pdf'):shutil.copy2(study/name,build/name)
        for _ in range(2):run(['pdflatex','-halt-on-error','-interaction=nonstopmode','objective-note.tex'],build)
        log=(build/'objective-note.log').read_text();assert 'Overfull' not in log and 'undefined' not in log.lower()
        original=run(['pdftotext','-layout',str(study/'objective-note.pdf'),'-'],folder)
        rebuilt=run(['pdftotext','-layout',str(build/'objective-note.pdf'),'-'],folder);assert original==rebuilt
        info=run(['pdfinfo',str(build/'objective-note.pdf')],folder)
        assert any(line.split(':')[1].strip()=='4' for line in info.splitlines() if line.startswith('Pages:'))
        verify();details=json.loads((study/'independent-verification.json').read_text())
        assert details['new_lp_calls']==208 and details['row_only_protection_certificates']==10
        validation.update(all_hashes_verified_before_and_after_replay=True,independent_lp_constructions_and_certificates_passed=True,
                          tests_passed=6,report_and_figure_regeneration_identical=True,pdf_recompiled_from_clean_extraction=True,
                          pdf_text_identical=True,pdf_pages=4,overfull_boxes=0,undefined_references=0,
                          row_only_factor_compatibility_inherited_from_identical_selective_row_factors=True,
                          pre_solve_original_source_hash_matches=True,details=details)
    run(['sha256sum','-c','SHA256SUMS'],ROOT/'paper/submission/oms/releases/v1.3.5-oms-submission')
    for name,archive_name in (('oms-transfer-study-20261014','transfer-artifact.zip'),('oms-quality-followup-20261014','quality-artifact.zip'),
                              ('oms-decision-study-20261014','decision-artifact.zip'),('oms-generalization-20261014','exploration-artifact.zip')):
        folder=ROOT/'exploration'/name;previous=json.loads((folder/'VALIDATION.json').read_text())
        assert sha((folder/archive_name).read_bytes())==previous['archive_sha256']
    validation.update(frozen_oms_v1_3_5_hashes_match=True,four_previous_research_archives_unchanged=True)
    (HERE/'VALIDATION.json').write_text(json.dumps(validation,indent=2)+'\n')
    print(json.dumps({k:v for k,v in validation.items() if k!='details'},indent=2),flush=True)


if __name__=='__main__':main()
