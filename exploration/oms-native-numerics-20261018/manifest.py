"""Check exact provenance across the numerical and incidence notes, without solves."""
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
THEORY=ROOT/'exploration/oms-incidence-spectral-20261018'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    for name,expected in json.loads((HERE/'dependencies.json').read_text()).items():
        assert digest(ROOT/name)==expected,name
    for entry in json.loads((HERE/'sources/manifest.json').read_text()):
        assert digest(HERE/'sources'/entry['file'])==entry['sha256']
    retention=json.loads((HERE/'contracts.retention.json').read_text())
    payload=gzip.decompress((HERE/'contracts.csv.gz').read_bytes())
    assert hashlib.sha256(payload).hexdigest()==retention['original_csv_sha256']
    assert len(payload)==retention['uncompressed_bytes']
    call_count=0
    for stage in ('b','c','b2'):
        design=json.loads((HERE/f'stage-{stage}-design.json').read_text())
        exports=json.loads((HERE/f'stage-{stage}-exports.json').read_text())
        expected={(r['instance'],r['policy']):r for r in exports}
        calls=list((HERE/f'stage-{stage}').glob('*/*/run.json'))
        assert len(calls)==len(design['selected'])*len(design['policies'])
        for path in calls:
            record=json.loads(path.read_text());name=record['instance'];policy=record['policy']
            export='Base' if policy.startswith('Base') else 'Budget-L2' if policy=='Budget-L2' else 'Dyadic-L2'
            spec=expected[name,export]
            assert record['export_sha256']==spec['export_sha256']==digest(HERE/'exports'/name/(export+'.lp.gz'))
            assert spec['factors_sha256']==digest(HERE/'exports'/name/(export+'-factors.json'))
            if record['sol_count']:assert record['point_sha256']==digest(path.parent/'point.json.gz')
        call_count+=len(calls)
    assert call_count==57
    for choice in json.loads((HERE/'exact-pattern-choices.json').read_text()):
        path=HERE/f'stage-{choice["stage"]}'/choice['instance']/choice['policy']/'point.json.gz'
        assert digest(path)==choice['source_point_sha256']
    destination=HERE/'MANIFEST.json'
    files={str(p.relative_to(ROOT)):digest(p) for folder in (HERE,THEORY) for p in sorted(folder.rglob('*'))
        if p.is_file() and p!=destination and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.aux','.out','.toc')}
    if '--write' in sys.argv:destination.write_text(json.dumps(dict(sha256=files),indent=2)+'\n')
    expected=json.loads(destination.read_text())['sha256']
    assert files==expected,dict(missing=sorted(set(expected)-set(files)),extra=sorted(set(files)-set(expected)),
        changed=[n for n in files.keys()&expected.keys() if files[n]!=expected[n]])
    print('Verified',len(files),'scientific files;',call_count,'MIP calls')


if __name__=='__main__':main()
