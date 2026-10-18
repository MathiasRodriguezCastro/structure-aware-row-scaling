"""Create a self-contained review ZIP with scientific inputs and raw outputs."""
import hashlib
import json
from pathlib import Path
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
RELEASE=ROOT/'paper/submission/oms/releases/v1.3.14-oms-submission'
TARGET=ROOT.parent/'oms-activity-research-20261017.zip'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def files():
    paths=set()
    for p in HERE.rglob('*'):
        if not p.is_file() or '__pycache__' in p.parts:continue
        if p.suffix in ('.pyc','.aux','.out','.toc','.tmp'):continue
        if p.name in ('MANIFEST.json','review-package.json','research-note.log','note-build.log'):continue
        paths.add(p)
    dependency=ROOT/'exploration/oms-budget-reformulation-20261017'
    paths.add(dependency/'verify.py')
    for p in (dependency/'diagnostic').rglob('*.json'):paths.add(p)
    for p in (dependency/'diagnostic').glob('*/certificate.json'):
        paths.add(ROOT/json.loads(p.read_text())['source'])
    primary=json.loads((HERE/'pilot/design.json').read_text())
    for item in primary['models']:
        if item['source']:paths.add(ROOT/item['source'])
    return sorted(paths)


def mutable(path):
    relative=path.relative_to(HERE) if path.is_relative_to(HERE) else None
    # These are replay outputs, never solver-measured execution records.
    return relative is not None and ((relative.parts[:2]==('pilot','runs') and path.name=='verification.json') or
           str(relative) in ('pilot/RESULTS.json','PRIMARY_RESULTS.json','PRIMARY_RESULTS.md','primary-unit-zero.csv','VALIDATION.json'))


def main():
    validation=json.loads((HERE/'centered-followup/VALIDATION.json').read_text())
    assert validation['all_complete'] and not validation['failed_processes']
    selected=files()
    manifest={'format':1,'root':'repository-relative paths','immutable_files':[],
              'recomputed_outputs':[],'completed_primary_configurations':195,'completed_followup_calls':360,
              'historical_release':'v1.3.14-oms-submission','historical_pdfs':{},
              'scope':'Research review bundle; paper unchanged. Solver calls require a licensed solver; checks do not.'}
    for p in selected:
        item={'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)}
        manifest['recomputed_outputs' if mutable(p) else 'immutable_files'].append(item)
    for name in ('main_oms.pdf','supplementary-material-1.pdf','cover-letter.pdf'):
        manifest['historical_pdfs'][name]=sha(RELEASE/name)
    (HERE/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # Paper PDFs are convenient for review, not dependencies of the new experiment.
    entries=[(p,str(p.relative_to(ROOT))) for p in selected]
    entries.append((HERE/'MANIFEST.json',str((HERE/'MANIFEST.json').relative_to(ROOT))))
    entries.extend((RELEASE/name,'paper-review/'+name) for name in manifest['historical_pdfs'])
    with zipfile.ZipFile(TARGET,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for p,name in entries:archive.write(p,name)
    with zipfile.ZipFile(TARGET) as archive:
        assert archive.testzip() is None
        for p,name in entries:assert hashlib.sha256(archive.read(name)).hexdigest()==sha(p)
    result={'zip':str(TARGET),'bytes':TARGET.stat().st_size,'sha256':sha(TARGET),'members':len(entries),
            'immutable_files':len(manifest['immutable_files']),'recomputed_outputs':len(manifest['recomputed_outputs']),
            'all_zip_members_checked':True}
    TARGET.with_suffix('.zip.sha256').write_text(result['sha256']+'  '+TARGET.name+'\n')
    (HERE/'review-package.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
