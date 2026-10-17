#!/usr/bin/env python3
"""Create the separate research artifact and replay it from a clean extraction."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PREFIX='exploration/oms-quality-followup-20261014/'
PREVIOUS=ROOT/'exploration/oms-decision-study-20261014'
PILOT=ROOT/'exploration/oms-generalization-20261014'


def sha(content):return hashlib.sha256(content).hexdigest()


def run(command,cwd):
    p=subprocess.run(command,cwd=cwd,capture_output=True,text=True)
    if p.returncode:raise RuntimeError(' '.join(command)+'\n'+p.stdout[-4000:]+p.stderr[-2000:])
    return p.stdout


def main():
    files={};excluded={'quality-artifact.zip','MANIFEST.json','VALIDATION.json','quality-note.aux',
                       'quality-note.out','quality-note.log','pdf-build.log','package-validation.log'}
    for p in HERE.rglob('*'):
        if not p.is_file() or p.name in excluded or any(x in p.parts for x in ('__pycache__','.pytest_cache')):continue
        files[PREFIX+p.relative_to(HERE).as_posix()]=p.read_bytes()
    def add(path):files[path.relative_to(ROOT).as_posix()]=path.read_bytes()
    for name in ('repair.py','independent_check.py','MANIFEST.json'):add(PREVIOUS/name)
    # Minimal pinned inputs also allow source preparation to locate its lineage.
    for name in ('control30-3-2-3','neos-3421095-cinca','ta1-UUM'):
        for file in ('original-model.json','factors.json'):add(PREVIOUS/'confirmation/models'/name/file)
    add(PREVIOUS/'development-repair/exact/rational-point.json')
    add(PREVIOUS/'confirmation/runs/ta1-UUM/Base-check-repair-s23/repair-floating/rational-point.json')
    for name in ('generalization_study.py','PILOT_PROTOCOL.md','MIPLIB_SELECTION.json'):add(PILOT/name)
    for p in (PILOT/'sources').rglob('*'):
        if p.is_file():add(p)
    for name in ('scripts/research/budget_scaling.py','LICENSE'):add(ROOT/name)
    files['README.md']=b'''# Quality, warm-start and representation follow-up

Independent research outside OMS submission v1.3.5.
Read exploration/oms-quality-followup-20261014/README.md and RESULTADOS.md.
The five-page PDF summarizes 48 prospective treatments and a separately frozen
14-treatment post-observation mechanism crossover. All adverse data are kept.
The artifact contains 90 native MIP calls, 60 checked deliveries, exact witnesses,
protocols, frozen sources, original MPS inputs and independent replay scripts.
Root MANIFEST.json inventories this archive. A prior study manifest only pins
the independent arithmetic dependency; it is not this archive's inventory.
Python/NumPy and pytest suffice for stored verification, without solver calls.
Solver binaries, commercial licenses and dependency installations are excluded.
Original source attribution and third-party STN MIT licensing are preserved.
No global optimality certificate, public DOI or paper release is claimed here.
'''
    manifest={'version':'oms-quality-followup-20261014-v1','status':'separate preliminary research; no paper incorporation or publication',
              'oms_submission_unchanged':'v1.3.5-oms-submission','prospective_treatments':48,'mechanism_treatments':14,
              'files':[{'path':name,'sha256':sha(data),'bytes':len(data)} for name,data in sorted(files.items())],
              'native_solver_calls_needed_for_replay':0,'solver_builds_excluded':True}
    data=(json.dumps(manifest,indent=2)+'\n').encode();(HERE/'MANIFEST.json').write_bytes(data)
    archive=HERE/'quality-artifact.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,content in sorted(files.items()):z.writestr(name,content)
        z.writestr('MANIFEST.json',data)
    validation={'version':manifest['version'],'archive_sha256':sha(archive.read_bytes()),
                'archive_bytes':archive.stat().st_size,'inventoried_files':len(manifest['files']),
                'native_solver_calls_during_validation':0}
    with tempfile.TemporaryDirectory(prefix='oms-quality-replay-') as tmp:
        folder=Path(tmp)
        with zipfile.ZipFile(archive) as z:z.extractall(folder)
        def verify():
            for r in manifest['files']:assert sha((folder/r['path']).read_bytes())==r['sha256'],r['path']
        verify()
        run(['python3',PREFIX+'independent_check.py'],folder)
        run(['python3',PREFIX+'check_ablation.py'],folder)
        tests=run(['python3','-m','pytest','-q',PREFIX+'test_controller.py',PREFIX+'test_report_gate.py'],folder)
        assert '9 passed' in tests
        run(['python3',PREFIX+'write_report.py'],folder);verify()
        build=folder/'pdf-build';build.mkdir();shutil.copy2(folder/PREFIX/'quality-note.tex',build/'quality-note.tex')
        for _ in range(2):run(['pdflatex','-halt-on-error','-interaction=nonstopmode','quality-note'],build)
        log=(build/'quality-note.log').read_text();assert 'Overfull' not in log and 'undefined' not in log.lower()
        original=run(['pdftotext','-layout',str(folder/PREFIX/'quality-note.pdf'),'-'],folder)
        rebuilt=run(['pdftotext','-layout',str(build/'quality-note.pdf'),'-'],folder);assert original==rebuilt
        info=run(['pdfinfo',str(build/'quality-note.pdf')],folder)
        assert any(x.split(':')[1].strip()=='5' for x in info.splitlines() if x.startswith('Pages:'))
        validation.update(all_hashes_verified_before_and_after_replay=True,independent_arithmetic_passed=True,
                          tests_passed=9,report_regeneration_identical=True,pdf_recompiled_from_clean_extraction=True,
                          pdf_text_identical=True,pdf_pages=5,overfull_boxes=0,undefined_references=0,
                          main_details=json.loads((folder/PREFIX/'confirmation/independent-verification.json').read_text()),
                          ablation_details=json.loads((folder/PREFIX/'ablation/independent-verification.json').read_text()))
    run(['sha256sum','-c','SHA256SUMS'],ROOT/'paper/submission/oms/releases/v1.3.5-oms-submission')
    for p in (PREVIOUS,PILOT):
        prior=json.loads((p/'VALIDATION.json').read_text())
        name='decision-artifact.zip' if p==PREVIOUS else 'exploration-artifact.zip'
        assert sha((p/name).read_bytes())==prior['archive_sha256']
    validation.update(frozen_oms_v1_3_5_hashes_match=True,previous_research_archives_unchanged=True)
    (HERE/'VALIDATION.json').write_text(json.dumps(validation,indent=2)+'\n');print(json.dumps(validation,indent=2))


if __name__=='__main__':main()
