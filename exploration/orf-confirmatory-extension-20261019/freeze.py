#!/usr/bin/env python3
"""Identify the immutable scientific parent and unchanged policy implementations."""
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()


def main():
    release=ROOT/'paper/submission/orf/releases/v1.5.0-orf-submission'
    record=json.loads((release/'VALIDATION.json').read_text())
    assert record['version']=='v1.5.0-orf-submission'
    assert record['verified_followup_replay']['status']=='passed'
    assert record['verified_followup_tables_regenerated_identically']==5
    assert all(v['passed'] for v in record['verified_followup_replay']['six_commands'].values())
    files=[ROOT/'exploration/oms-frontier-20261016/study.py',
        ROOT/'exploration/oms-followup-20261014/activation_study.py',
        ROOT/'exploration/orf-v15-verified-20261019/study.py',
        ROOT/'exploration/orf-v15-verified-20261019/export_selector.py',
        ROOT/'exploration/orf-v15-verified-20261019/export_selector_fast.py',
        ROOT/'scripts/research/budget_scaling.py',
        ROOT/'scripts/research/oms_dispatch_validation.py',
        ROOT/'scripts/validar_preprocesamiento.py']
    tracked=subprocess.check_output(['git','ls-files','code'],cwd=ROOT,text=True).splitlines()
    files += [ROOT/n for n in tracked if Path(n).suffix in ('.cpp','.h','.hpp','.cc','.tpp')]
    hashes={str(p.relative_to(ROOT)):sha(p) for p in files}
    for name,h in hashes.items():
        committed=subprocess.check_output(['git','show','2fbb5f14:'+name],cwd=ROOT)
        assert hashlib.sha256(committed).hexdigest()==h,'Policy changed since scientific parent: '+name
    evidence=ROOT/'exploration/orf-v15-verified-20261019/research-evidence.zip'
    assert sha(evidence)==record['verified_followup_replay']['archive_sha256']
    value=dict(parent_version=record['version'],parent_commit='2fbb5f14',
        parent_validation_sha256=sha(release/'VALIDATION.json'),
        parent_delivery_sha256=record['delivery']['sha256'],
        verified_evidence_sha256=sha(evidence),policy_source_sha256=hashes,
        earlier_six_replays_reused_for_byte_identical_evidence=True,
        policies=['Base','GM','L2','Ruiz-R4','Budget-L2','Export-Budget-L2','L2-NF3'],
        frozen_policy_parameters=dict(volume_m3=100,power_MW=.01,epsilon=1e-6,
            integer_distance=1e-9,coefficient_window=[1e-9,1e9],Ruiz_iterations=4),
        parent_modified=False)
    out=HERE/'FROZEN_POLICIES.json'
    content=json.dumps(value,indent=2,sort_keys=True)+'\n'
    if out.exists():assert out.read_text()==content,'Freeze record differs; retain the old record.'
    else:out.write_text(content)
    print('Policy freeze verified:',len(hashes),'unchanged source files; six prior replays passed.')


if __name__=='__main__':main()
