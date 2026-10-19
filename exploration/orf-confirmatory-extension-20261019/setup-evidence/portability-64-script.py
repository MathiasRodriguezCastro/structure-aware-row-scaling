#!/usr/bin/env python3
"""Reproduce every pilot scaled export under an explicit BLAS kernel, no solves."""
import os
import sys
from runner import HERE,ROOT,load,save,sha,library


def main():
    label=sys.argv[1];out=HERE/'factor-portability'/label
    out.mkdir(parents=True,exist_ok=False)
    plan=load(HERE/'PILOT_PLAN.json');metadata=load(HERE/'MODEL_PREPARATION.json')['models']
    follow=library(ROOT/'exploration/orf-v15-verified-20261019/study.py','portable_frozen_helpers')
    a,front=follow.old.modules();records=[]
    for block in plan['blocks']:
        name=block['instance'];base=HERE/'models'/name/'Base.lp'
        assert sha(base)==metadata[name]['base_sha256']
        rows,_=a.original_rows(base);_,lp,_=a.campaign.afb.read_lp(base)
        folder=out/name;folder.mkdir()
        for policy,budget in [('L2',None),('Budget-L2',100)]:
            factors,decision=front.choose(rows,lp,budget)
            assert not decision['incompatible_count']
            export=folder/(policy+'.lp');a.export_scaled(base,export,factors)
            expected=metadata[name]['policies'][policy]['export_sha256']
            records.append(dict(instance=name,policy=policy,expected_sha256=expected,
                actual_sha256=sha(export),byte_identical=sha(export)==expected))
        print('Checked frozen exports:',name,flush=True)
    status='passed' if all(r['byte_identical'] for r in records) and len(records)==64 else 'failed'
    save(HERE/('FACTOR_PORTABILITY-'+label+'.json'),dict(status=status,
        OPENBLAS_CORETYPE=os.environ.get('OPENBLAS_CORETYPE'),exports_checked=len(records),
        byte_identical_exports=sum(r['byte_identical'] for r in records),records=records,
        optimizer_calls=0,policy_implementation_changed=False))
    print(status,len(records),'exports; zero solver calls',flush=True)
    if status!='passed':raise SystemExit(1)


if __name__=='__main__':main()
