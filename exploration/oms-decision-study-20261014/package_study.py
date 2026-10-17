#!/usr/bin/env python3
"""Package this separate study and validate it in a fresh, solver-free extraction."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREFIX = 'exploration/oms-decision-study-20261014/'
PILOT = ROOT / 'exploration/oms-generalization-20261014'
PILOT_PREFIX = 'exploration/oms-generalization-20261014/'


def sha(content):
    return hashlib.sha256(content).hexdigest()


def run(command, cwd):
    p = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(' '.join(command) + '\n' + p.stdout[-4000:] + p.stderr[-2000:])
    return p.stdout


def main():
    files = {}; excluded = {'decision-artifact.zip', 'MANIFEST.json', 'VALIDATION.json',
                           'decision-note.aux', 'decision-note.out', 'decision-note.log', 'pdf-build.log', 'package-validation.log'}
    for path in HERE.rglob('*'):
        if not path.is_file() or path.name in excluded or any(v in path.parts for v in ('__pycache__', '.pytest_cache')):
            continue
        files[PREFIX + path.relative_to(HERE).as_posix()] = path.read_bytes()
    for name in ('generalization_study.py', 'PILOT_PROTOCOL.md', 'MIPLIB_SELECTION.json'):
        files[PILOT_PREFIX + name] = (PILOT / name).read_bytes()
    for path in (PILOT / 'sources').rglob('*'):
        if path.is_file():
            files[PILOT_PREFIX + path.relative_to(PILOT).as_posix()] = path.read_bytes()
    for name in ('control30-3-2-3', 'neos-3421095-cinca', 'ta1-UUM'):
        relative = f'pilot/models/{name}/original-model.json'
        files[PILOT_PREFIX + relative] = (PILOT / relative).read_bytes()
    for name in ('scripts/research/budget_scaling.py', 'LICENSE'):
        files[name] = (ROOT / name).read_bytes()
    files['README.md'] = b'''# Independent acceptance/repair follow-up

Separate preliminary research, outside OMS submission v1.3.5.
Read exploration/oms-decision-study-20261014/README.md and RESULTADOS.md.
The folder contains the four-page PDF, frozen design, 80 treatment records,
78 source points, 71 checked deliveries, repair certificates and exact checks.
The original pilot helper/kernel and source generator/MPS inputs are included.
MANIFEST.json inventories every byte. Stored verification needs Python/NumPy;
tests need pytest. No solver or commercial license is needed for replay.
Third-party STN MIT licensing is retained, as is MIPLIB source attribution.
No software binary, dependency installation, paper release or public DOI is bundled.
'''
    manifest = {'version': 'oms-decision-study-20261014-v1',
                'status': 'preliminary separate study; not incorporated into paper or published',
                'oms_submission_unchanged': 'v1.3.5-oms-submission',
                'files': [{'path': name, 'sha256': sha(data), 'bytes': len(data)} for name, data in sorted(files.items())],
                'assigned_treatments': 80, 'native_calls_in_experiment': 78,
                'solver_calls_needed_for_stored_verification': 0,
                'solver_binaries_and_dependency_builds_excluded': True}
    manifest_bytes = (json.dumps(manifest, indent=2) + '\n').encode()
    (HERE / 'MANIFEST.json').write_bytes(manifest_bytes)
    archive = HERE / 'decision-artifact.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for name, data in sorted(files.items()):
            bundle.writestr(name, data)
        bundle.writestr('MANIFEST.json', manifest_bytes)
    validation = {'version': manifest['version'], 'archive_sha256': sha(archive.read_bytes()),
                  'archive_bytes': archive.stat().st_size, 'inventoried_files': len(manifest['files']),
                  'native_solver_calls_during_validation': 0}
    with tempfile.TemporaryDirectory(prefix='oms-decision-study-replay-') as tmp:
        folder = Path(tmp)
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(folder)
        def verify():
            for row in manifest['files']:
                assert sha((folder / row['path']).read_bytes()) == row['sha256'], row['path']
        verify()
        run(['python3', PREFIX + 'independent_check.py'], folder)
        test_output = run(['python3', '-m', 'pytest', '-q', PREFIX + 'test_repair.py'], folder)
        assert '5 passed' in test_output
        run(['python3', PREFIX + 'write_report.py'], folder)
        verify()
        build = folder / 'pdf-build'; build.mkdir()
        shutil.copy2(folder / PREFIX / 'decision-note.tex', build / 'decision-note.tex')
        for _ in range(2):
            run(['pdflatex', '-halt-on-error', '-interaction=nonstopmode', 'decision-note'], build)
        log = (build / 'decision-note.log').read_text()
        assert 'Overfull' not in log and 'undefined' not in log.lower()
        original_text = run(['pdftotext', '-layout', str(folder / PREFIX / 'decision-note.pdf'), '-'], folder)
        rebuilt_text = run(['pdftotext', '-layout', str(build / 'decision-note.pdf'), '-'], folder)
        assert original_text == rebuilt_text
        pdf_info = run(['pdfinfo', str(build / 'decision-note.pdf')], folder)
        assert any(line.split(':')[1].strip() == '4' for line in pdf_info.splitlines() if line.startswith('Pages:'))
        validation.update(all_hashes_verified_before_and_after_replay=True,
                          independent_original_arithmetic_passed=True, tests_passed=5,
                          report_regeneration_identical=True, pdf_recompiled_from_clean_extraction=True,
                          pdf_text_identical=True, pdf_pages=4, overfull_boxes=0, undefined_references=0,
                          details=json.loads((folder / PREFIX / 'confirmation/independent-verification.json').read_text()))
    release = ROOT / 'paper/submission/oms/releases/v1.3.5-oms-submission'
    run(['sha256sum', '-c', 'SHA256SUMS'], release)
    validation['frozen_oms_v1_3_5_hashes_still_match'] = True
    (HERE / 'VALIDATION.json').write_text(json.dumps(validation, indent=2) + '\n')
    print(json.dumps(validation, indent=2))


if __name__ == '__main__':
    main()
