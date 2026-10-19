#!/usr/bin/env python3
"""Freeze only a validated ORF delivery; prepare local portal/deposit copies."""
import json
from pathlib import Path
import shutil
import tempfile
from orf_config import ROOT, OUT, VERSION, sha


def main():
    validation=json.loads((OUT/'VALIDATION.json').read_text())
    assert validation['version']==VERSION
    assert validation['delivery']['sha256']==sha(OUT/'orf-delivery.zip')
    assert validation['canonical_editorial_regeneration_identical']
    assert all(v['passed'] for v in validation['replay']['four_standard_commands'].values())
    files={p.name:p for p in (OUT/'uploads').iterdir() if p.is_file() and p.name!='SHA256SUMS'}
    files.update({'orf-delivery.zip':OUT/'orf-delivery.zip','VALIDATION.json':OUT/'VALIDATION.json',
                  'SNAPSHOT.json':OUT/'SNAPSHOT.json','CITATION.cff':ROOT/'CITATION.cff',
                  'zenodo-metadata.json':ROOT/'.zenodo.json'})
    release=OUT/'releases'/VERSION
    if release.exists():
        assert all(sha(release/n)==sha(p) for n,p in files.items()),'Frozen ORF release differs'
    else:
        release.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.orf-freeze-',dir=release.parent) as tmp:
            staging=Path(tmp)/VERSION;staging.mkdir()
            for n,p in files.items():
                shutil.copyfile(p,staging/n);assert sha(staging/n)==sha(p)
            (staging/'SHA256SUMS').write_text(''.join(f'{sha(staging/n)}  {n}\n' for n in sorted(files)))
            staging.rename(release)
        for p in release.iterdir():p.chmod(0o444)
    # These are local, reviewable preparations. No remote upload or publication.
    portal=OUT/'portal-preparation'/VERSION;portal.mkdir(parents=True,exist_ok=True)
    for n in ('FORM_FIELDS.json','UPLOAD_INSTRUCTIONS.md','ONLINE_RESOURCE_CAPTIONS.txt'):
        shutil.copyfile(release/n,portal/n)
    deposit=OUT/'zenodo-deposit'/VERSION;deposit.mkdir(parents=True,exist_ok=True)
    for n in ('ESM_2.zip','SNAPSHOT.json','CITATION.cff','zenodo-metadata.json','REPRODUCTION-VALIDATION.json'):
        shutil.copyfile(release/n,deposit/n)
    for n in ('LICENSE','DATA_LICENSE.md'):shutil.copyfile(ROOT/n,deposit/n)
    (deposit/'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.name}\n' for p in sorted(deposit.iterdir()) if p.name!='SHA256SUMS'))
    print('Frozen ORF delivery:',release)
    print('Prepared local portal and Zenodo files; no remote changes.')


if __name__=='__main__':main()
