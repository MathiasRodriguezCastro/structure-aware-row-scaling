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
BULK_DIRS = {'fresh', 'runs-raw'}
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
    # Campaign: pre-registration, split, run tables and aggregates; the per-run records
    # (runs-raw) stay out, they are several gigabytes of logs.
    artifact += list(collect('results-revision/solver-robustness'))
    artifact += [p.relative_to(ROOT) for p in (ROOT/'results-revision/final-variants').glob('*/resumen.csv')]
    artifact += list(collect('paper/research-audit',{'.md','.json','.csv','.txt'}))
    artifact += list(collect('paper/research-audit/baseline-20260908',{'.tex','.pdf','.bib','.cpp'}))
    artifact += [Path('paper/submission/README.md'), Path('paper/submission/cover-letter.txt')]
    n2=archive('reproducibility-artifact.zip',artifact)
    paths=[OUT/'manuscript-sources.zip', OUT/'reproducibility-artifact.zip',
           ROOT/'paper/main.pdf',ROOT/'paper/supporting-information.pdf',OUT/'cover-letter.txt']
    (OUT/'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(ROOT)}\n' for p in paths))
    print(f'Prepared {n1} manuscript files and {n2} artifact files in {OUT}')


if __name__=='__main__':
    main()
