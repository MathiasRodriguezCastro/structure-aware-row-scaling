"""Fetch immutable native archives and list their contents; no optimizer calls."""
import hashlib
import json
from pathlib import Path
import tarfile
import urllib.request
import zipfile

HERE = Path(__file__).resolve().parent
SOURCES = {
    'R.tgz': 'https://commalab.di.unipi.it/files/Data/MMCF/R.tgz',
    'gunluk.tar.gz': 'https://commalab.di.unipi.it/files/Data/MMCF/gunluk.tar.gz',
    'sslp.zip': 'https://www2.isye.gatech.edu/~sahmed/siplib/sslp/sslp.zip',
}


def main():
    folder = HERE / 'sources'
    folder.mkdir(exist_ok=True)
    if (folder/'manifest.json').exists():
        for item in json.loads((folder/'manifest.json').read_text()):
            assert hashlib.sha256((folder/item['file']).read_bytes()).hexdigest()==item['sha256']
        print('Existing immutable source archives verified; no downloads needed')
        return
    manifest = []
    for name, url in SOURCES.items():
        path = folder / name
        if not path.exists():
            request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(request, timeout=60) as response:
                content = response.read()
            path.write_bytes(content)
        content = path.read_bytes()
        members = []
        if name.endswith(('.tgz', '.tar.gz')):
            with tarfile.open(path) as archive:
                members = [{'name': m.name, 'bytes': m.size} for m in archive if m.isfile()]
        elif name.endswith('.zip'):
            with zipfile.ZipFile(path) as archive:
                members = [{'name': m.filename, 'bytes': m.file_size}
                           for m in archive.infolist() if not m.is_dir()]
        manifest.append(dict(file=name, url=url, bytes=len(content),
                             sha256=hashlib.sha256(content).hexdigest(), members=members))
        print(name, len(content), len(members), flush=True)
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
