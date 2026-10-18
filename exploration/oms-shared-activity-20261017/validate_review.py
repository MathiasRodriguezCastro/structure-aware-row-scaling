"""Extract the review bundle and replay all scientific checks without a solver."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import zipfile

HERE=Path(__file__).resolve().parent
ARCHIVE=HERE.parents[1].parent/'oms-activity-research-20261017.zip'
PREFIX=Path('exploration/oms-shared-activity-20261017')


def main():
    logs=HERE/'clean-replay';logs.mkdir(exist_ok=True);records=[]
    with tempfile.TemporaryDirectory(prefix='oms-activity-review-') as tmp:
        root=Path(tmp)
        with zipfile.ZipFile(ARCHIVE) as archive:
            assert archive.testzip() is None
            archive.extractall(root)
        def run(file):
            started=time.perf_counter();label=Path(file).stem+('-followup' if 'centered-followup' in str(file) else '')
            with (logs/(label+'.log')).open('w') as stream:
                proc=subprocess.run([sys.executable,str(file)],cwd=root,stdout=stream,stderr=subprocess.STDOUT)
            record={'script':str(file),'returncode':proc.returncode,'seconds':time.perf_counter()-started}
            print(json.dumps(record),flush=True);assert proc.returncode==0,str(file)
            return record
        initial=[Path('exploration/oms-budget-reformulation-20261017/verify.py'),
                 PREFIX/'test_activity.py',PREFIX/'test_boundary_certificates.py',PREFIX/'verify_scope.py',
                 PREFIX/'verify_certificates.py',PREFIX/'centered-followup/test_method.py']
        for file in initial:records.append(run(file))
        with ThreadPoolExecutor(max_workers=2) as pool:
            records.extend(pool.map(run,[PREFIX/'verify.py',PREFIX/'centered-followup/verify_results.py']))
        for file in (PREFIX/'analyze_primary.py',PREFIX/'centered-followup/summarize.py',
                     PREFIX/'centered-followup/check_nonmonotonicity.py',PREFIX/'check_manifest.py'):
            records.append(run(file))
        manifest=json.loads((root/PREFIX/'MANIFEST.json').read_text())
        result={'review_zip_scientific_payload_sha256':hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
                'extracted_without_repository_dependencies':True,'new_optimizer_calls':0,
                'all_checks_pass':True,'checks':records,'immutable_payload_files_checked':len(manifest['immutable_files']),
                'primary_completed':json.loads((root/PREFIX/'VALIDATION.json').read_text())['completed_calls'],
                'followup_completed':json.loads((root/PREFIX/'centered-followup/VALIDATION.json').read_text())['completed_attempts'],
                'note':'The final ZIP may additionally include this replay report/script/logs; scientific inputs, frozen code and raw native results are unchanged.'}
    (HERE/'CLEAN_REPLAY_VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'all_checks_pass':True,'scripts':len(records),'optimizer_calls':0}),flush=True)


if __name__=='__main__':main()
