"""One-command solver-free replay of the four candidate studies."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def main():
    manifest=HERE/'MANIFEST.json'
    if manifest.exists():
        for row in json.loads(manifest.read_text())['files']:
            path=ROOT/row['path']
            assert path.stat().st_size==row['bytes']
            assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'],row['path']
    scripts=[('oms-minimal-change-20261017','test_selector.py'),('oms-minimal-change-20261017','verify.py'),
             ('oms-budget-reformulation-20261017','verify.py'),('oms-activity-scaling-20261017','test_method.py'),
             ('oms-activity-scaling-20261017','verify.py'),('oms-integer-embedding-20261017','test_method.py'),
             ('oms-integer-embedding-20261017','verify.py'),('oms-method-search-20261017','analyze.py')]
    for folder,script in scripts:
        path=HERE.parent/folder/script
        result=subprocess.run([sys.executable,str(path)],cwd=ROOT,capture_output=True,text=True)
        assert result.returncode==0,(script,result.stdout,result.stderr)
        print(folder+'/'+script+': PASS',flush=True)
    result={'replay_commands_passed':len(scripts),'new_optimizer_calls':0,'manifest_checked':manifest.exists()}
    (HERE/'VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
