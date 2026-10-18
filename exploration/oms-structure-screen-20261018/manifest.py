"""Bind scientific records to exact hashes; default checks without modifying files."""
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent


def main():
    root=HERE.parents[1]
    for name,expected in json.loads((HERE/'dependencies.json').read_text()).items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected,name
    for source in json.loads((HERE/'sources/manifest.json').read_text()):
        assert hashlib.sha256((HERE/'sources'/source['file']).read_bytes()).hexdigest()==source['sha256']
    pilot=json.loads((HERE/'pilot-design.json').read_text())
    replication=json.loads((HERE/'replication-design.json').read_text())
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    assert pilot['models_sha256']==sha(HERE/'models.json')
    assert pilot['protocol_sha256']==sha(HERE/'PROTOCOL.md')
    assert replication['pilot_design_sha256']==sha(HERE/'pilot-design.json')
    expected={(r['instance'],r['policy']):r['export_sha256'] for r in pilot['exports']}
    calls=list((HERE/'runs').glob('*/*/run.json'))+list((HERE/'replication').glob('*/*/*/run.json'))
    assert len(calls)==210
    for path in calls:
        call=json.loads(path.read_text())
        policy='Flat-L2' if call['policy'] in ('Flat-L2-tight','Flat-L2-NF3') else call['policy']
        source=HERE/'exports'/call['instance']/(policy+'.lp.gz')
        assert call['export_sha256']==expected[call['instance'],policy]==sha(source)
        assert call['point_sha256']==sha(path.parent/'point.json.gz')
    destination=HERE/'MANIFEST.json'
    files={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest()
           for p in sorted(HERE.rglob('*')) if p.is_file() and p!=destination
           and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.aux','.out','.toc')}
    if '--write' in sys.argv:
        destination.write_text(json.dumps(dict(sha256=files),indent=2)+'\n')
    expected=json.loads(destination.read_text())['sha256']
    assert files==expected,dict(missing=sorted(set(expected)-set(files)),
        extra=sorted(set(files)-set(expected)),changed=[k for k in files.keys()&expected.keys() if files[k]!=expected[k]])
    print('Verified',len(files),'scientific files')


if __name__=='__main__':
    main()
