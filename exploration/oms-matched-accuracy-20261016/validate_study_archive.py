#!/usr/bin/env python3
"""Clean extraction, checksums, optimizer-blocked replay and identical regeneration."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent;REL=Path('exploration/oms-matched-accuracy-20261016')


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    target=HERE/'matched-accuracy-artifact.zip'
    with tempfile.TemporaryDirectory(prefix='oms-matched-replay-') as tmp:
        root=Path(tmp)
        with zipfile.ZipFile(target) as z:z.extractall(root)
        for line in (root/'CONTENTS.sha256').read_text().splitlines():
            h,name=line.split('  ',1);assert sha(root/name)==h,name
        manifest=json.loads((root/REL/'MANIFEST.json').read_text())
        guard=r'''
import builtins,runpy,subprocess,sys,unittest
from pathlib import Path
original=builtins.__import__
def safe_import(name,*args,**kwargs):
    if name.split('.')[0] in ('gurobipy','cplex','pyscipopt'):
        raise AssertionError('commercial solver import blocked: '+name)
    return original(name,*args,**kwargs)
builtins.__import__=safe_import
import highspy
def forbidden(*args,**kwargs):raise AssertionError('optimizer or external process blocked')
highspy.Highs.run=forbidden
subprocess.Popen=forbidden
h=Path('exploration/oms-matched-accuracy-20261016')
runpy.run_path(str(h/'independent_check.py'),run_name='__main__')
runpy.run_path(str(h/'write_report.py'),run_name='__main__')
suite=unittest.defaultTestLoader.discover(str(h),pattern='test_endpoints.py')
result=unittest.TextTestRunner().run(suite)
assert result.wasSuccessful() and result.testsRun==4
'''
        r=subprocess.run([sys.executable,'-c',guard],cwd=root,capture_output=True,text=True,
            env={**__import__('os').environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'})
        (HERE/'package-replay.log').write_text(r.stdout+r.stderr)
        assert r.returncode==0,(r.stdout+r.stderr)[-6000:]
        for item in manifest['files']:
            p=root/item['path'];assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256'],item['path']
        details=json.loads((root/REL/'VALIDATION.json').read_text())
    report={'archive_sha256':sha(target),'archive_bytes':target.stat().st_size,
        'clean_extraction_checksums_verified':True,'commercial_solver_imports_blocked':True,
        'highs_optimizer_run_blocked':True,'external_processes_blocked_during_numerical_replay':True,
        'all_inventoried_files_identical_after_replay_and_report_regeneration':True,
        'endpoint_tests_passed':4,'independent_replay':details}
    (HERE/'PACKAGE_VALIDATION.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
