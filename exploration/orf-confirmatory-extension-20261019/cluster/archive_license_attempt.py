#!/usr/bin/env python3
"""Preserve the cancelled infrastructure attempt on a compute node."""
import hashlib
import json
from pathlib import Path
import shutil
import sys


def main():
    here=Path(sys.argv[1]);target=here/'infrastructure-attempts/limited-license-6068550'
    assert not target.exists()
    assert not (here/'pilot-runs').exists(),'Comparative pilot unexpectedly started'
    target.mkdir(parents=True)
    for name in ['reference-acquisition','references']:
        source=here/name
        if source.exists():source.rename(target/name)
    shutil.copyfile(here/'pilot-plan-drafts/before-explicit-license-environment.json',target/'PILOT_PLAN.json')
    records=[]
    for folder in sorted((target/'reference-acquisition').iterdir()):
        result=folder/'result.json';native=folder/'native-result.json'
        record=dict(instance=folder.name,result_persisted=result.exists(),native_result_persisted=native.exists())
        if result.exists():record.update(json.loads(result.read_text()))
        records.append(record)
    files={str(p.relative_to(target)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in target.rglob('*') if p.is_file()}
    report=dict(status='retained_infrastructure_attempt',initial_reference_array='6068550',
        acquisition_folders=len(records),recorded_results=sum(r['result_persisted'] for r in records),
        persisted_native_outcomes=sum(r['native_result_persisted'] for r in records),
        verified_feasible_references=sum(r.get('status')=='verified_feasible' for r in records),
        comparative_assignments_started=0,all_attempts_retained=True,records=records,sha256=files)
    (target/'ARCHIVE.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Infrastructure archive retained:',len(records),'acquisition folders; zero comparative assignments.')


if __name__=='__main__':main()
