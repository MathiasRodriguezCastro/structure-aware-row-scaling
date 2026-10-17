#!/usr/bin/env python3
"""Prepare exact, reviewable Zenodo upload files locally; never upload or publish."""
import hashlib
import argparse
import json
from pathlib import Path
import shutil

from oms_snapshot import ROOT, OUT, VERSION, REVISION_DATE


def main(metadata_only=False):
    release=OUT/'releases'/VERSION
    if not metadata_only and not (release/'VALIDATION.json').is_file():
        raise SystemExit('Freeze the validated current release before preparing deposit files.')
    if not metadata_only:
        validation=json.loads((release/'VALIDATION.json').read_text())
        assert validation['snapshot_version']==VERSION
    target=OUT/'zenodo-deposit'/VERSION;target.mkdir(parents=True,exist_ok=True)
    source=json.loads((ROOT/'.zenodo.json' if metadata_only else release/'zenodo-metadata.json').read_text())
    # Reuse the exact release metadata. A second narrative template had retained
    # an obsolete "adds no optimization calls" claim from an earlier revision.
    description=source['description']
    metadata={k:source[k] for k in ('title','upload_type','access_right','license','creators','keywords','related_identifiers','version')}
    metadata['description']=description
    (target/'ZENODO_METADATA.json').write_text(json.dumps({'metadata':metadata},indent=2,ensure_ascii=False)+'\n')
    if metadata_only:
        print('Prepared record metadata; awaiting reserved DOI and final validated files:',target/'ZENODO_METADATA.json')
        return
    for filename in ('reproducibility-artifact.zip','OMS_DATA_MANIFEST.json','SNAPSHOT.json'):
        shutil.copyfile(release/filename,target/filename)
    shutil.copyfile(ROOT/'LICENSE',target/'LICENSE')
    shutil.copyfile(ROOT/'DATA_LICENSE.md',target/'DATA_LICENSE.md')
    (target/'REPRODUCE.md').write_text(f'''# OMS software and data — {VERSION}

Snapshot date: {REVISION_DATE}. This folder prepares a Zenodo deposit and does
not itself create a public record or register a DOI. Use the reserved DOI of the
author's new-version draft when completing the publication process.

Extract reproducibility-artifact.zip and run from its root:

```bash
python3 -m pip install -r environment/research-requirements.txt
make research-oms-check
```

These commands verify saved results without optimizing or requiring a commercial
solver license. See the artifact README for optional fresh runs and the separately
archived historical bulk exports. ZENODO_METADATA.json contains record metadata;
SHA256SUMS and DEPOSIT_FILES.json identify the exact files prepared for upload.

Use a new-version draft of the historical record, preserving the published
baseline. Replace inherited draft files with this exact version's files where
appropriate; the baseline remains independently available at its version DOI.
Reserve the new DOI before finalizing citations and upload files. Publish only
after checking that the DOI, version and files agree. The DOI becomes registered
on publication; an unpublished draft is not a public data-availability link.

Official instructions:
https://help.zenodo.org/docs/deposit/describe-records/reserve-doi/
https://help.zenodo.org/docs/deposit/manage-records/
''')
    names=['reproducibility-artifact.zip','OMS_DATA_MANIFEST.json','SNAPSHOT.json',
           'LICENSE','DATA_LICENSE.md','ZENODO_METADATA.json','REPRODUCE.md']
    records=[]
    for name in names:
        data=(target/name).read_bytes()
        records.append({'file':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
                        'md5':hashlib.md5(data).hexdigest()})
    (target/'DEPOSIT_FILES.json').write_text(json.dumps({'version':VERSION,'files':records,
        'remote_upload_performed':False,'remote_publication_performed':False},indent=2)+'\n')
    names.append('DEPOSIT_FILES.json')
    (target/'SHA256SUMS').write_text(''.join(
        f'{hashlib.sha256((target/name).read_bytes()).hexdigest()}  {name}\n' for name in names))
    print('Prepared Zenodo upload files (no remote changes):',target)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--metadata-only',action='store_true')
    main(p.parse_args().metadata_only)
