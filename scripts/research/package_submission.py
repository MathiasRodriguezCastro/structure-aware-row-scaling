#!/usr/bin/env python3
"""Build reviewable local archives. Does not publish or submit anything."""
import hashlib
import re
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'paper/submission'
# Bulk inputs of the fixed-basis audit: 4.6 GB of exported LP text and bases. They are the
# input of `make research-fixed-basis-check`, not something to attach to a submission, so the
# archive lists them with their hashes instead of carrying them.
BULK_DIRS = {'fresh', 'runs-raw', 'solver-robustness', 'benchmark-v1'}
MAX_FILE_BYTES = 20 * 1024 * 1024
EXCLUDED = []


def collect(folder, suffixes=None):
    for p in (ROOT/folder).rglob('*'):
        rel = p.relative_to(ROOT)
        if not p.is_file() or p.is_symlink():
            continue
        if any(x.startswith('build') or x in {'__pycache__', '.git', '.pytest_cache', 'rendered'}
               for x in rel.parts[:-1]):
            continue
        if set(rel.parts) & BULK_DIRS or p.stat().st_size > MAX_FILE_BYTES:
            EXCLUDED.append((rel, p.stat().st_size))
            continue
        if suffixes is None or p.suffix in suffixes or p.name in {'Makefile', 'README.md'}:
            yield rel


def archive(name, paths):
    paths = sorted(set(paths))
    with zipfile.ZipFile(OUT/name, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        hashes=[]
        for p in paths:
            content=(ROOT/p).read_bytes()
            z.writestr(str(p),content)
            hashes.append(f'{hashlib.sha256(content).hexdigest()}  {p}')
        z.writestr('CONTENTS.sha256','\n'.join(hashes)+'\n')
        if EXCLUDED:
            total=sum(s for _,s in EXCLUDED)
            z.writestr('EXCLUDED.txt',
                       f'{len(EXCLUDED)} files, {total/1e9:.2f} GB, left out of this archive.\n'
                       'They are bulk inputs, not results: exported LP text, bases and per-run\n'
                       'records that the analyses here read only through their summaries. They are\n'
                       'deposited as a single archive, fixed-basis-exports.tar.zst (337 MB\n'
                       'compressed, 5.18 GB in 11,585 files), whose checksum and contents are listed\n'
                       'in data-deposit/MANIFEST.json beside this package. Only\n'
                       '`make research-fixed-basis-check`, which rebuilds all 1,530 bases from the\n'
                       'LP text, needs the files themselves.\n\n'
                       + '\n'.join(f'{s:>12}  {q}' for q,s in sorted(EXCLUDED)) + '\n')
    return len(paths)


def coap_bundle():
    """Everything a COAP editor needs in one archive: sources, class files, PDF, letter."""
    coap = ROOT/'paper/coap'
    paths = [coap/n for n in ['main_coap.tex', 'abstract.tex', 'research-references.bib',
                             'main_coap.bbl', 'main_coap.pdf', 'cover-letter.pdf',
                             'cover-letter.tex', 'COAP_NOTES.md',
                             'svjour3.cls', 'svglov3.clo', 'spmpsci.bst', 'spbasic.bst']]
    paths += sorted(coap.glob('sections/*.tex')) + sorted(coap.glob('tables/*.tex'))
    paths += sorted(coap.glob('figs/*.pdf'))
    paths += [ROOT/'paper/supporting-information.tex', ROOT/'paper/supporting-information.pdf']          # Online Resource 1
    supplement = (ROOT/'paper/supporting-information.tex').read_text()
    supplement_inputs = re.findall(r'\\input\{([^}]+)\}', supplement)
    paths += [ROOT/'paper'/ (name + '.tex') for name in supplement_inputs
              if not (coap/(name + '.tex')).exists()]
    paths += [ROOT/'paper/figs/research/budget-compatibility.pdf']
    paths = list(dict.fromkeys(paths))
    missing = [p for p in paths if not p.exists()]
    if missing:
        raise SystemExit('missing for the COAP bundle: ' + ', '.join(str(m) for m in missing))
    with zipfile.ZipFile(OUT/'coap-submission.zip', 'w', compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as z:
        hashes = []
        for p in paths:
            rel = p.relative_to(coap) if coap in p.parents else p.relative_to(ROOT/'paper')
            content = p.read_bytes()
            z.writestr(str(rel), content)
            hashes.append(f'{hashlib.sha256(content).hexdigest()}  {rel}')
        z.writestr('CONTENTS.sha256', '\n'.join(hashes)+'\n')
    return len(paths)


def main():
    OUT.mkdir(exist_ok=True)
    paper=[Path('paper')/x for x in ['main.tex','main.bbl','supporting-information.tex','supporting-information.pdf',
                                     'research-references.bib','Makefile','README.md']]
    paper += list(collect('paper/sections',{'.tex'}))
    paper += list(collect('paper/tables',{'.tex'}))
    paper += list(collect('paper/figs/research',{'.pdf'}))
    artifact=paper+[Path(x) for x in ['README.md','Makefile','LICENSE','DATA_LICENSE.md','CITATION.cff','.zenodo.json','artifacts/README.md']]
    artifact += list(collect('environment',{'.txt','.md'}))
    artifact += list(collect('scripts',{'.py','.sh'}))
    artifact += list(collect('tests',{'.py','.cpp'}))
    artifact += list(collect('code',{'.cpp','.c','.h','.hpp','.mk','.md'}))
    artifact += list(collect('data'))
    artifact += list(collect('results-revision/research-audit'))
    artifact += list(collect('results-revision/attribution-controls'))
    artifact += list(collect('results-revision/fixed-basis'))
    artifact += list(collect('results-revision/r5-ablation'))
    artifact += [p.relative_to(ROOT) for p in (ROOT/'results-revision/final-variants').glob('*/resumen.csv')]
    artifact += list(collect('paper/validation', {'.md', '.json', '.csv'}))
    artifact += list(collect('results-revision/spectral-heterogeneous', {'.csv'}))
    artifact += [Path('paper/submission/README.md'), Path('paper/submission/SUBMISSION_CHECKLIST.md'),
                 Path('paper/submission/data-deposit/MANIFEST.json'),
                 Path('paper/submission/data-deposit/SHA256SUMS')]
    artifact += list(collect('paper/coap', {'.tex', '.bib', '.bst', '.cls', '.clo', '.md', '.pdf'}))
    n2=archive('reproducibility-artifact.zip',artifact)
    n3=coap_bundle()
    print(f'Prepared {n3} files for the COAP submission bundle')
    paths=[OUT/'reproducibility-artifact.zip',
           OUT/'coap-submission.zip',
           ROOT/'paper/supporting-information.pdf',
           ROOT/'paper/coap/main_coap.pdf',ROOT/'paper/coap/cover-letter.pdf']
    (OUT/'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(ROOT)}\n' for p in paths))
    print(f'Prepared {n2} artifact files in {OUT}')
    from prepare_editorial_uploads import main as prepare_uploads
    prepare_uploads()


if __name__=='__main__':
    main()
