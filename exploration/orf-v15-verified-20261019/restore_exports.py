#!/usr/bin/env python3
"""Reconstruct immutable exports from the frozen rule and verify native-run hashes."""
import json
import shutil
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import study as s


def main():
    d=s.load(HERE/'design.json');a,front=s.old.modules();records={}
    for name in sorted(d['models']):
        base=s.PARENT/'models'/name/'Base.lp';parsed,_=a.original_rows(base)
        _,lp,_=a.campaign.afb.read_lp(base)
        required={(j['policy'],j['contract']) for j in d['jobs'] if j['instance']==name and j['policy'] not in ['Base','L2-NF3']}
        for policy,contract in sorted(required):
            key=name+'/'+policy+'/'+contract;folder=HERE/'models'/name/policy/contract;folder.mkdir(parents=True,exist_ok=True)
            jobs=[j for j in d['jobs'] if j['instance']==name and j['contract']==contract and
                (j['policy']==policy or policy=='L2' and j['policy']=='L2-NF3')]
            first=s.load(HERE/'runs'/jobs[0]['id']/'result.json')
            h=first.get('export_sha256');captured=HERE/'captured-exports'/f'{h}.lp'
            known=s.PARENT/'models'/name/(policy+'.lp')
            if captured.exists() or known.exists() and s.sha(known)==h:
                out=folder/'model.lp';shutil.copyfile(captured if captured.exists() else known,out)
                written,_=s.checker.parse(out);factors={}
                for n,row in parsed.items():
                    unit=next(j for j,v in row['terms'].items() if abs(v)==1)
                    factors[n]=float(written[n]['terms'][unit])/float(row['terms'][unit])
                info=dict(incompatible_count=0,incompatible=[],
                    factor_recovery='Every row has a +/-1 coefficient; its exported product identifies alpha exactly.')
            else:
                if policy=='L2':factors,info=front.choose(parsed,lp,None)
                else:factors,info=s.select(parsed,lp,s.CONTRACTS[contract],policy=='Export-Budget-L2')
            s.dump(folder/'factors.json',factors);s.dump(folder/'selection.json',info)
            if info['incompatible_count']:
                records[key]=dict(abstained=True,rows=len(parsed),incompatible=info['incompatible_count']);continue
            out=folder/'model.lp';a.export_scaled(base,out,factors);h=s.sha(out)
            for j in jobs:
                r=s.load(HERE/'runs'/j['id']/'result.json');assert not r['abstained'] and r['export_sha256']==h,j['id']
            records[key]=dict(abstained=False,sha256=h,native_runs_matched=len(jobs),rows=len(parsed),
                export=str(out.relative_to(HERE)),factors=str((folder/'factors.json').relative_to(HERE)))
        print('Reconstructed',name,flush=True)
    s.dump(HERE/'EXPORTS.json',dict(reconstructed_after_campaign=True,rule_and_source_design_frozen=True,
        records=records,all_existing_native_run_hashes_matched=True))


if __name__=='__main__':main()
