"""Index immutable records, inputs and sources; omit regenerable replay outputs."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FOLDERS=('oms-minimal-change-20261017','oms-budget-reformulation-20261017',
         'oms-activity-scaling-20261017','oms-integer-embedding-20261017','oms-method-search-20261017')
DERIVED={'MANIFEST.json','VALIDATION.json','RESULTS.json','SUMMARY.json','SUMMARY.csv','verification.json','STATIC_TESTS.json'}


def main():
    files=[]
    for folder in FOLDERS:
        for p in sorted((HERE.parent/folder).rglob('*')):
            if not p.is_file() or '__pycache__' in p.parts or p.name in DERIVED:continue
            if p.suffix in ('.aux','.out','.pyc') or p.name=='research-note.log':continue
            files.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,
                          'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    result={'scope':'immutable candidate sources, protocols, native exports, certificates and saved run records; regenerated replay outputs excluded',
            'files':files,'file_count':len(files),'total_bytes':sum(p['bytes'] for p in files)}
    (HERE/'MANIFEST.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='files'}))


if __name__=='__main__':main()
