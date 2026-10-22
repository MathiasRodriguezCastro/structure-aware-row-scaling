#!/usr/bin/env python3
"""Lossless archive of the closed confirmation and its prerequisite evidence."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile

SUB = Path('exploration/orf-confirmatory-extension-20261019')
SEALS = {'CONFIRMATION_RAW_MANIFEST.json': Path('.'),
         'CONFIRMATION_ANALYSIS_VALIDATION_MANIFEST.json': Path('.'),
         'PENDING_RAW_MANIFEST.json': SUB,
         'REFERENCE_RECOVERY_RAW_MANIFEST.json': SUB,
         'PILOT_RAW_MANIFEST.json': SUB}


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def inventory(root):
    files = {}
    seals = {}
    for name, base in SEALS.items():
        path = root/SUB/name
        manifest = json.loads(path.read_text())
        seals[name] = sha(path)
        for row in manifest['files']:
            relative = (base/row['path']).as_posix()
            value = dict(path=relative, bytes=row['bytes'], sha256=row['sha256'])
            assert relative not in files or files[relative] == value, relative
            files[relative] = value
    extras = [p for p in (root/SUB).iterdir() if p.is_file() and
              p.suffix in ('.py', '.json', '.md', '.csv', '.sha256')]
    extras += [p for p in (root/SUB/'cluster').iterdir() if p.suffix in ('.slurm', '.sh')]
    extras += [root/'scripts/research/orf_confirmation_evidence.py']
    # Keep infrastructure history and provenance documents; the closed final
    # campaign, pilot and reference data themselves are selected by their seals.
    extras += [p for p in (root/SUB/'setup-evidence').rglob('*') if p.is_file() and
               p.suffix in ('.json', '.md', '.csv', '.sha256', '.py')]
    for path in extras:
        relative = path.relative_to(root).as_posix()
        row = dict(path=relative, bytes=path.stat().st_size, sha256=sha(path))
        assert relative not in files or files[relative] == row, relative
        files[relative] = row
    for relative, row in files.items():
        path = (root/relative).resolve()
        assert path.is_relative_to(root.resolve()) and path.is_file(), relative
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], relative
    return dict(scope='Final 3840-run confirmation, corrected resource pilot, reference acquisition/recovery, provenance and replay sources.',
                infrastructure_attempt_raw_data_included=False,
                original_seals_sha256=seals, optimizer_calls=0,
                files=[files[n] for n in sorted(files)])


def build(root, output):
    assert not output.exists(), 'Do not overwrite an existing evidence archive'
    listing = inventory(root)
    seen = {}
    temporary = output.with_suffix(output.suffix+'.part')
    output.parent.mkdir(parents=True, exist_ok=True)
    assert not temporary.exists()
    print('All sealed inputs checked; writing the lossless archive.', flush=True)
    with tarfile.open(temporary, 'w:xz', preset=6, dereference=True) as archive:
        for row in listing['files']:
            info = archive.gettarinfo(str(root/row['path']), arcname=row['path'])
            assert info.isfile()
            info.uid = info.gid = 0
            info.uname = info.gname = ''
            info.mode = 0o755 if info.mode & 0o111 else 0o644
            identity = (row['bytes'], row['sha256'])
            if identity in seen:
                info.type = tarfile.LNKTYPE
                info.linkname = seen[identity]
                info.size = 0
                archive.addfile(info)
            else:
                with (root/row['path']).open('rb') as stream:
                    archive.addfile(info, stream)
                seen[identity] = row['path']
        listing['file_count'] = len(listing['files'])
        listing['logical_bytes'] = sum(r['bytes'] for r in listing['files'])
        listing['unique_contents'] = len(seen)
        payload = (json.dumps(listing, indent=2)+'\n').encode()
        info = tarfile.TarInfo('CONFIRMATION_ARCHIVE_CONTENTS.json')
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    temporary.rename(output)
    checked = verify(output)
    (output.parent/'CONFIRMATION_ARCHIVE_VALIDATION.json').write_text(json.dumps(checked, indent=2)+'\n')
    print(json.dumps(checked, indent=2), flush=True)


def verify(path):
    checked = {}
    listing = None
    with tarfile.open(path, 'r|xz') as archive:
        for item in archive:
            name = Path(item.name)
            assert not name.is_absolute() and '..' not in name.parts
            assert item.name not in checked
            if item.name == 'CONFIRMATION_ARCHIVE_CONTENTS.json':
                listing = json.load(archive.extractfile(item))
                continue
            if item.islnk():
                assert item.linkname in checked, item.linkname
                checked[item.name] = dict(checked[item.linkname], path=item.name)
            else:
                assert item.isfile(), item.name
                h = hashlib.sha256()
                count = 0
                stream = archive.extractfile(item)
                for block in iter(lambda: stream.read(1048576), b''):
                    count += len(block)
                    h.update(block)
                assert count == item.size
                checked[item.name] = dict(path=item.name, bytes=count, sha256=h.hexdigest())
    assert listing and len(checked) == listing['file_count']
    assert [checked[n] for n in sorted(checked)] == listing['files']
    return dict(status='passed', archive_sha256=sha(path), archive_bytes=path.stat().st_size,
                file_count=len(checked), logical_bytes=listing['logical_bytes'],
                unique_contents=listing['unique_contents'], original_seals_sha256=listing['original_seals_sha256'],
                full_stream_read_and_checksums=True, optimizer_calls=0,
                source_sha256=sha(Path(__file__)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['build', 'check'])
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--archive', type=Path, required=True)
    args = parser.parse_args()
    if args.stage == 'build':
        build(args.root, args.archive)
    else:
        print(json.dumps(verify(args.archive), indent=2))
