#!/usr/bin/env python3
"""Retain the complete pre-portability pilot before any corrected repetition."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import sys

here=Path(sys.argv[1]);target=here/'infrastructure-attempts/blas-runtime-6068582'
assert not target.exists();target.mkdir(parents=True)
report=json.loads((here/'PILOT_RESOURCE_REPORT.json').read_text())
assert report['recorded_assignments']==118 and len(report['failed_jobs'])==20
for name in ['pilot-runs','pilot-execution-logs']:(here/name).rename(target/name)
for name in ['PILOT_PLAN.json','PILOT_RESOURCE_REPORT.json','PILOT_REPLAY.json','runner.py','PROTOCOL.md']:
    shutil.copyfile(here/name,target/name)
statuses=[]
for p in sorted((here/'reference-acquisition').glob('*/result.json')):
    value=json.loads(p.read_text());statuses.append({k:value[k] for k in ['instance','status','total_seconds']})
records=[json.loads(p.read_text()) for p in (target/'pilot-runs').glob('*/result.json')]
files={str(p.relative_to(target)):hashlib.sha256(p.read_bytes()).hexdigest()
    for p in target.rglob('*') if p.is_file()}
result=dict(status='retained_before_runtime_correction',initial_pilot_array='6068582',
    recorded_assignments=len(records),outcomes=dict(Counter(r['status'] for r in records)),
    not_attempted_assignments=len(report['missing_jobs']),reference_statuses=statuses,
    scaling_policies_changed=False,comparative_policy_ranking_used=False,
    sha256=files,source_commit='427ffc9f')
(target/'ARCHIVE.json').write_text(json.dumps(result,indent=2)+'\n')
print('Archived initial pilot:',len(records),'recorded assignments; all outputs retained.')
