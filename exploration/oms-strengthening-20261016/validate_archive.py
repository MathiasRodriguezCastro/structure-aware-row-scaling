#!/usr/bin/env python3
"""Clean saved-data replay with commercial imports and optimization blocked."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    archive=HERE/'oms-strengthening-artifact.zip'
    commands=[
        ('exploration/oms-frontier-20261016/independent_check.py',['--allow-absent-historical']),
        ('exploration/oms-native-selector-20261016/independent_check.py',[]),
        ('exploration/oms-joint-contracts-20261016/independent_check.py',['--allow-absent-historical']),
        ('exploration/oms-joint-contracts-20261016/check_solves.py',[]),
        ('exploration/oms-joint-contracts-20261016/check_ablation.py',[]),
        ('exploration/oms-global-lp-20261016/independent_check.py',[]),
        ('exploration/oms-global-lp-20261016/check_repairs.py',[]),
        ('scripts/research/oms_frontier_tables.py',[])]
    with tempfile.TemporaryDirectory(prefix='oms-new-research-') as temp:
        folder=Path(temp)
        with zipfile.ZipFile(archive) as z:z.extractall(folder)
        manifest=json.loads((folder/'exploration/oms-strengthening-20261016/MANIFEST.json').read_text())
        for r in manifest['files']:assert sha(folder/r['path'])==r['sha256'],r['path']
        for script,args in commands:
            # A separate clean process avoids module-name collisions between
            # independent study checkers called independent_check.py.
            code='''import importlib.abc,sys,runpy,subprocess
from pathlib import Path
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,name,path=None,target=None):
  if name.split('.')[0] in {'gurobipy','cplex','pyscipopt'}:raise RuntimeError('Commercial optimizer import blocked: '+name)
sys.meta_path.insert(0,Block())
import highspy
def blocked(*a,**k):raise RuntimeError('Optimization/process invocation blocked')
highspy.Highs.run=blocked
subprocess.run=blocked
subprocess.Popen=blocked
script=sys.argv[1];sys.argv=sys.argv[1:];sys.path.insert(0,str(Path(script).resolve().parent))
runpy.run_path(script,run_name='__main__')
'''
            with (HERE/'archive-validation.log').open('a') as log:
                p=subprocess.run([sys.executable,'-c',code,script,*args],cwd=folder,stdout=log,stderr=subprocess.STDOUT)
            assert p.returncode==0,script
            print('Clean replay passed:',script,flush=True)
        for r in manifest['files']:assert sha(folder/r['path'])==r['sha256'],'Replay changed inventoried file: '+r['path']
    result={'archive_sha256':sha(archive),'inventoried_files':len(manifest['files']),
        'eight_commands_passed':True,'commercial_optimizer_imports_blocked':True,
        'highs_optimization_blocked':True,'subprocesses_blocked_in_replays':True,
        'all_inventoried_files_identical_after_replay':True}
    (HERE/'ARCHIVE_VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()
