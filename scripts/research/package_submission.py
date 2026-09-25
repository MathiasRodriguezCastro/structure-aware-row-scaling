#!/usr/bin/env python3
"""Build reviewable local archives. Does not publish or submit anything."""
import hashlib
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
               for x in rel.parts):
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
                       'They are bulk inputs (exported LP text, bases, per-run logs) kept in the\n'
                       'repository and the data record; the analyses here read their summaries.\n\n'
                       + '\n'.join(f'{s:>12}  {q}' for q,s in sorted(EXCLUDED)) + '\n')
    return len(paths)


def mpc_bundle():
    """Everything an MPC editor needs in one archive: sources, class files, PDF, letter."""
    mpc = ROOT/'paper/mpc'
    paths = [mpc/n for n in ['main_mpc.tex', 'abstract.tex', 'research-references.bib',
                             'main_mpc.bbl', 'main_mpc.pdf', 'cover-letter.pdf',
                             'cover-letter.tex', 'MPC_NOTES.md',
                             'svjour3.cls', 'svglov3.clo', 'spmpsci.bst', 'spbasic.bst']]
    paths += sorted(mpc.glob('sections/*.tex')) + sorted(mpc.glob('tables/*.tex'))
    paths += sorted(mpc.glob('figs/*.pdf'))
    paths += [ROOT/'paper/supporting-information.pdf']          # Online Resource 1
    missing = [p for p in paths if not p.exists()]
    if missing:
        raise SystemExit('missing for the MPC bundle: ' + ', '.join(str(m) for m in missing))
    with zipfile.ZipFile(OUT/'mpc-submission.zip', 'w', compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as z:
        hashes = []
        for p in paths:
            rel = p.relative_to(mpc) if mpc in p.parents else Path(p.name)
            content = p.read_bytes()
            z.writestr(str(rel), content)
            hashes.append(f'{hashlib.sha256(content).hexdigest()}  {rel}')
        z.writestr('CONTENTS.sha256', '\n'.join(hashes)+'\n')
    return len(paths)


def main():
    OUT.mkdir(exist_ok=True)
    paper=[Path('paper')/x for x in ['main.tex','main.bbl','supporting-information.tex',
                                     'research-references.bib','Makefile','README.md']]
    paper += list(collect('paper/sections',{'.tex'}))
    paper += list(collect('paper/tables',{'.tex'}))
    paper += list(collect('paper/figs/research',{'.pdf'}))
    n1=archive('manuscript-sources.zip',paper)
    artifact=paper+[Path(x) for x in ['README.md','Makefile','LICENSE','DATA_LICENSE.md','CITATION.cff','.zenodo.json']]
    artifact += list(collect('environment',{'.txt','.md'}))
    artifact += list(collect('scripts',{'.py','.sh'}))
    artifact += list(collect('tests',{'.py','.cpp'}))
    artifact += list(collect('code',{'.cpp','.c','.h','.hpp','.mk','.md'}))
    artifact += list(collect('data'))
    artifact += list(collect('results-revision/research-audit'))
    artifact += list(collect('results-revision/attribution-controls'))
    artifact += [p.relative_to(ROOT) for p in (ROOT/'results-revision/final-variants').glob('*/resumen.csv')]
    artifact += list(collect('paper/research-audit',{'.md','.json','.csv','.txt'}))
    artifact += list(collect('paper/research-audit/baseline-20260908',{'.tex','.pdf','.bib','.cpp'}))
    artifact += [Path('paper/submission/README.md'), Path('paper/submission/cover-letter.txt')]
    n2=archive('reproducibility-artifact.zip',artifact)
    n3=mpc_bundle()
    print(f'Prepared {n3} files for the MPC submission bundle')
    paths=[OUT/'manuscript-sources.zip', OUT/'reproducibility-artifact.zip',
           OUT/'mpc-submission.zip',
           ROOT/'paper/main.pdf',ROOT/'paper/supporting-information.pdf',OUT/'cover-letter.txt']
    (OUT/'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(ROOT)}\n' for p in paths))
    print(f'Prepared {n1} manuscript files and {n2} artifact files in {OUT}')


if __name__=='__main__':
    main()
