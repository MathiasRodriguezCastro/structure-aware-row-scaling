#!/usr/bin/env python3
"""Install the locked API wheels locally when the compute image has no pip."""
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import zipfile


def main():
    root=Path(sys.argv[1]);target=root/'python-deps-v1'
    assert sys.version_info[:2]==(3,11),'Wheels were locked for CPython 3.11'
    lock=json.loads((root/'cluster/WHEELS.json').read_text())
    assert not target.exists(),'Dependency installation is immutable; use a new target for a retry'
    with tempfile.TemporaryDirectory(prefix='.orf-wheel-install-',dir=root) as tmp:
        staging=Path(tmp)/'packages';staging.mkdir()
        for item in lock['wheels']:
            source=root/'cluster/wheels'/item['name']
            assert hashlib.sha256(source.read_bytes()).hexdigest()==item['sha256']
            with zipfile.ZipFile(source) as z:
                record=next(n for n in z.namelist() if n.endswith('.dist-info/RECORD'))
                for name,digest,_ in csv.reader(io.StringIO(z.read(record).decode())):
                    if not digest:continue
                    algorithm,value=digest.split('=',1);assert algorithm=='sha256'
                    got=base64.urlsafe_b64encode(hashlib.sha256(z.read(name)).digest()).decode().rstrip('=')
                    assert got==value,name
                for name in z.namelist():
                    dest=staging/name
                    assert dest.resolve().is_relative_to(staging.resolve()),name
                z.extractall(staging)
        staging.rename(target)
    (root/'DEPENDENCY_INSTALLATION.json').write_text(json.dumps(dict(
        status='installed',wheels=lock['wheels'],all_wheel_RECORD_hashes_checked=True,
        python=sys.version,relative_target='python-deps-v1'),indent=2)+'\n')


if __name__=='__main__':main()
