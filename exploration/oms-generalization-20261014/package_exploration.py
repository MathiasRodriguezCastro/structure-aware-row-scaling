#!/usr/bin/env python3
"""Package and replay the separate pilot from a clean extraction."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PREFIX='exploration/oms-generalization-20261014/'


def sha(content):return hashlib.sha256(content).hexdigest()


def run(command,cwd):
    result=subprocess.run(command,cwd=cwd,capture_output=True,text=True)
    if result.returncode:raise RuntimeError(' '.join(command)+'\n'+result.stdout[-4000:]+result.stderr[-2000:])
    return result.stdout


def main():
    excluded={'exploration-artifact.zip','MANIFEST.json','VALIDATION.json',
              'exploration-note.aux','exploration-note.out','exploration-note.log'}
    files={}
    for path in HERE.rglob('*'):
        if not path.is_file() or any(p in path.parts for p in ('.deps','__pycache__','.pytest_cache')):
            continue
        if path.name in excluded:continue
        files[PREFIX+path.relative_to(HERE).as_posix()]=path.read_bytes()
    files['scripts/research/budget_scaling.py']=(ROOT/'scripts/research/budget_scaling.py').read_bytes()
    files['LICENSE']=(ROOT/'LICENSE').read_bytes()
    files['README.md']=b'''# Independent precision-contract pilot

Separate preliminary research, not an OMS submission supplement or published release.
Read exploration/oms-generalization-20261014/README.md and RESULTADOS.md.
That folder contains the standalone PDF, protocols, original sources, native logs,
all 55 arm records, 52 points, exact factor incompatibility certificates and replays.
MANIFEST.json inventories all bytes. Python/NumPy and pytest suffice for verification;
commercial solvers and isolated Pyomo dependencies are only needed for fresh experiments.
Third-party STN MIT license is preserved; MIPLIB originals retain their source attribution.
'''
    manifest={'version':'oms-generalization-20261014-pilot-v1','status':'preliminary separate research; no journal incorporation or publication',
        'oms_submission_unchanged':'v1.3.5-oms-submission',
        'files':[{'path':p,'sha256':sha(c),'bytes':len(c)} for p,c in sorted(files.items())],
        'dependency_builds_excluded':True,'pilot_assigned_arms':55,'stored_points':52,
        'replay_requires_commercial_solver':False}
    manifest_content=(json.dumps(manifest,indent=2)+'\n').encode()
    (HERE/'MANIFEST.json').write_bytes(manifest_content)
    archive=HERE/'exploration-artifact.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as bundle:
        for name,content in sorted(files.items()):bundle.writestr(name,content)
        bundle.writestr('MANIFEST.json',manifest_content)
    result={'version':manifest['version'],'archive_sha256':sha(archive.read_bytes()),
        'inventoried_files':len(manifest['files']),'commercial_solver_calls':0}
    with tempfile.TemporaryDirectory(prefix='oms-generalization-replay-') as tmp:
        folder=Path(tmp)
        with zipfile.ZipFile(archive) as bundle:bundle.extractall(folder)
        def verify():
            for row in manifest['files']:assert sha((folder/row['path']).read_bytes())==row['sha256'],row['path']
        verify()
        run(['python3',PREFIX+'generalization_study.py','verify'],folder)
        run(['python3',PREFIX+'independent_check.py'],folder)
        run(['python3',PREFIX+'certifying_workflow.py'],folder)
        test_output=run(['python3','-m','pytest','-q',PREFIX+'test_certifying_workflow.py'],folder)
        assert '7 passed' in test_output
        run(['python3',PREFIX+'write_exploration_report.py'],folder)
        verify()
        result.update(all_checksums_verified=True,all_checksums_identical_after_replay=True,
            saved_point_replay_passed=True,independent_arithmetic_passed=True,decision_loop_replay_passed=True,
            tests_passed=7,report_regeneration_identical=True)
        build=folder/'note-build';build.mkdir()
        shutil.copy2(folder/PREFIX/'exploration-note.tex',build/'exploration-note.tex')
        for _ in range(2):run(['pdflatex','-halt-on-error','-interaction=nonstopmode','exploration-note'],build)
        log=(build/'exploration-note.log').read_text()
        assert 'Overfull' not in log and 'undefined' not in log.lower()
        original=run(['pdftotext','-layout',str(folder/PREFIX/'exploration-note.pdf'),'-'],folder)
        rebuilt=run(['pdftotext','-layout',str(build/'exploration-note.pdf'),'-'],folder)
        assert original==rebuilt
        result.update(pdf_recompiled_from_extracted_source=True,pdf_text_identical=True,overfull_boxes=0,undefined_references=0)
        result['independent_details']=json.loads((folder/PREFIX/'pilot/independent-verification.json').read_text())
    (HERE/'VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
