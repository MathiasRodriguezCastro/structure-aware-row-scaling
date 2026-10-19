#!/usr/bin/env python3
"""Recheck amended provenance and deployment files without optimization calls."""
from runner import HERE,ROOT,load,save,sha


def main():
    assert load(HERE/'DEPLOYMENT_GATE.json')['status']=='passed'
    assert load(HERE/'NATIVE_TEST.json')['status']=='passed'
    assert load(HERE/'HELD_OUT_AUDIT.json')['status']=='passed'
    assert load(HERE/'PRIOR_POLICY_EXPOSURE.json')['selection_unchanged']
    assert load(HERE/'PREFLIGHT-license-fixed.json')['status']=='passed'
    assert load(HERE/'infrastructure-attempts/limited-license-6068550/ARCHIVE.json')['comparative_assignments_started']==0
    assert load(HERE/'infrastructure-attempts/blas-runtime-6068582/ARCHIVE.json')['recorded_assignments']==118
    assert load(HERE/'FACTOR_PORTABILITY-Haswell.json')['byte_identical_exports']==64
    count=0
    for line in (HERE/'TRANSFER_CONTENTS.sha256').read_text().splitlines():
        expected,name=line.split('  ',1);assert sha(ROOT/name)==expected,name;count+=1
    for name,digest in load(HERE/'PILOT_PLAN.json')['dependencies'].items():
        assert sha(ROOT/name)==digest,name
    save(HERE/'DEPLOYMENT_RECHECK.json',dict(status='passed',optimizer_calls=0,
        pilot_plan_sha256=sha(HERE/'PILOT_PLAN.json'),transferred_files_checked=count,
        initial_deployment_gate_sha256=sha(HERE/'DEPLOYMENT_GATE.json'),
        transfer_manifest_sha256=sha(HERE/'TRANSFER_CONTENTS.sha256'),
        prior_policy_exposure_explicit=True,selection_unchanged=True))
    print('Amended provenance and deployment hashes passed; zero optimization calls.')


if __name__=='__main__':main()
