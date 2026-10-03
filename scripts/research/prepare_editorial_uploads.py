#!/usr/bin/env python3
"""Prepare separately uploaded Editorial Manager files without changing their contents."""
import hashlib
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'paper/submission/editorial-manager'
FILES = {
    'main_coap.pdf': ROOT / 'paper/coap/main_coap.pdf',
    'coap-submission.zip': ROOT / 'paper/submission/coap-submission.zip',
    'cover-letter.pdf': ROOT / 'paper/coap/cover-letter.pdf',
    'ESM_1.pdf': ROOT / 'paper/supporting-information.pdf',
    'ESM_2.zip': ROOT / 'paper/submission/reproducibility-artifact.zip',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    missing = [str(p) for p in FILES.values() if not p.is_file()]
    if missing:
        raise SystemExit('Build and package the manuscript first; missing: ' + ', '.join(missing))
    # Check against the verified source package before making any upload copies.
    manifest = ROOT / 'paper/submission/SHA256SUMS'
    expected = dict(line.split('  ', 1)[::-1] for line in manifest.read_text().splitlines())
    for src in FILES.values():
        rel = src.relative_to(ROOT).as_posix()
        if sha(src) != expected.get(rel):
            raise SystemExit('Source checksum mismatch: ' + rel)
    OUT.mkdir(parents=True, exist_ok=True)
    hashes = []
    for name, src in FILES.items():
        dst = OUT / name
        shutil.copy2(src, dst)
        digest = sha(dst)
        if digest != sha(src):
            raise SystemExit('Upload copy differs from source: ' + name)
        hashes.append(f'{digest}  {name}')
    (OUT / 'SHA256SUMS').write_text('\n'.join(hashes) + '\n')
    (OUT / 'UPLOAD_INSTRUCTIONS.md').write_text('''# Files to upload separately in Editorial Manager

Article: Pre-Export Row Scaling in Generated Mixed-Integer Programs: Mechanism Attribution and Residual-Budget Contracts
Journal: Computational Optimization and Applications
Author: Mathias Rodríguez Castro, Facultad de Ingeniería, Universidad de la República, Montevideo, Uruguay
Corresponding author: mathiasr@fing.edu.uy

| File | Upload role |
|---|---|
| main_coap.pdf | Manuscript |
| coap-submission.zip | Editable LaTeX sources |
| cover-letter.pdf | Cover letter |
| ESM_1.pdf | Supplementary material — Online Resource 1 |
| ESM_2.zip | Supplementary material — Online Resource 2 |

Upload ESM_1.pdf and ESM_2.zip as two separate supplementary files. Online Resource 2
is not inside coap-submission.zip. The supplement PDF included in that source bundle does
not replace its separate supplementary upload. Use each file once for its intended role.

Captions to paste into the supplementary-file fields:

Online Resource 1: Supplementary proofs, audit protocols and complete ranges, operational
reconstruction details, experiment protocols, arithmetic checks and reproduction instructions.

Online Resource 2: Source code and stored experiment data, with analysis and verification
scripts, manifests, checksums and reproduction instructions. The bulk fixed-basis inputs are
available separately through the archived repository and the linked GitHub release.

ESM_2.zip also contains paper/supporting-information.pdf, byte-identical to ESM_1.pdf.
ESM_1.pdf is byte-identical to supporting-information.pdf; ESM_2.zip is byte-identical
to reproducibility-artifact.zip. These are upload names, and the repository sources retain
their existing names. SHA256SUMS verifies all five upload files from this directory.

Guidelines: https://link.springer.com/journal/10589/submission-guidelines
Archived release: https://github.com/MathiasRodriguezCastro/structure-aware-row-scaling/releases/tag/v1.1.1-coap-submission
Zenodo concept DOI: https://doi.org/10.5281/zenodo.20648949
''')
    print('Prepared five separately uploaded files in', OUT.relative_to(ROOT))
    print('ESM_1.pdf and ESM_2.zip match the verified source files byte for byte.')


if __name__ == '__main__':
    main()
