#!/usr/bin/env python3
"""One registered recovery pass using only common Base acquisition artifacts."""
import shutil
import subprocess
import time
from fractions import Fraction as Q
import numpy as np
from runner import HERE,ROOT,load,save,sha,library,native


def main():
    out=HERE/'reference-recovery';out.mkdir(exist_ok=False)
    plan=load(HERE/'PILOT_PLAN.json')
    follow=library(ROOT/'exploration/orf-v15-verified-20261019/study.py','reference_recovery_helpers')
    exact=library(ROOT/'exploration/oms-followup-20261014/exact_dispatch_witness.py','reference_recovery_exact')
    independent=library(HERE/'replay_pilot.py','reference_recovery_independent')
    a,_=follow.old.modules();records=[]
    for block in plan['blocks']:
        name=block['instance'];source=HERE/'reference-acquisition'/name/'result.json'
        original=load(source)
        if original['status']=='verified_feasible':continue
        folder=out/name;folder.mkdir();save(folder/'original-acquisition-result.json',original)
        started=time.perf_counter();record=dict(instance=name,additional_MIP_calls=0,additional_LP_calls=0)
        base=HERE/'models'/name/'Base.lp';old=HERE/'references'/name
        try:
            rational=old/'rational-solution.txt'
            if rational.exists() and 'Primal solution (name, value):' in rational.read_text():
                # No LP rerun: validate the saved rational vector directly.
                proof=folder/'existing-vector';proof.mkdir()
                for filename in ['mapping.json','rational-solution.txt']:shutil.copyfile(old/filename,proof/filename)
                record['procedure']='independent recheck of saved rational vector'
            else:
                proof=folder/'exact-retry';proof.mkdir()
                if (old/'fixed-original-binary64.lp').exists():
                    for filename in ['mapping.json','fixed-original-binary64.lp']:shutil.copyfile(old/filename,proof/filename)
                    record['procedure']='same fixed-pattern LP with SoPlex simplifier disabled'
                else:
                    native_folder=folder/'Base-CPLEX';native_folder.mkdir()
                    _,lp,matrix=a.campaign.afb.read_lp(base);rows,_=follow.checker.parse(base)
                    job=dict(solver='cplex',policy='Base',seed=389,time_limit=120.)
                    record['additional_MIP_calls']=1
                    outcome,points,events,parameters,imported,errors=native(base,native_folder,job,started,lp,rows,follow,matrix)
                    save(native_folder/'native-result.json',dict(outcome=outcome,events=events,parameters=parameters,native_import=imported,errors=errors))
                    np.savez_compressed(native_folder/'candidates.npz',names=np.array(lp.col_names_),x=np.array(points).reshape(-1,len(lp.col_names_)))
                    assert points and not errors,'Base CPLEX did not supply a candidate'
                    solution=native_folder/'solution.npz';np.savez_compressed(solution,names=np.array(lp.col_names_),x=np.array(points[-1]))
                    exact.prepare(proof,base,solution)
                    record['procedure']='Base CPLEX, same acquisition gap/tolerances/seed/cap; fixed-pattern LP with simplifier disabled'
                settings=proof/'exact.set'
                settings.write_text('int:syncmode = 1\nint:readmode = 1\nint:solvemode = 2\nint:checkmode = 2\nint:simplifier = 0\nreal:feastol = 0\nreal:opttol = 0\nreal:timelimit = 120\n')
                binary=ROOT/'exploration/oms-followup-20261014/tools/soplex-build/bin/soplex'
                command=[str(binary),'--loadset='+str(settings),'-X='+str(proof/'rational-solution.txt'),str(proof/'fixed-original-binary64.lp')]
                record['additional_LP_calls']=1
                with (proof/'soplex.log').open('w') as log:
                    process=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=180)
                save(proof/'solver-provenance.json',dict(command=command,returncode=process.returncode,binary_sha256=sha(binary),settings_sha256=sha(settings)))
            exact.check(proof)
            certificate=load(proof/'independent-certificate.json')
            values={n:Q(v) for n,v in load(proof/'exact-witness.json').items()}
            assert independent.exact_feasible(follow.checker.canonical(base),values)
            old.mkdir(exist_ok=True)
            for filename in ['exact-witness.json','independent-certificate.json']:shutil.copyfile(proof/filename,old/filename)
            elapsed=time.perf_counter()-started
            recovered={**original,'status':'verified_feasible','objective_exact':certificate['objective_exact_fraction'],
                'total_seconds':original['total_seconds']+elapsed,'initial_acquisition_status':original['status'],
                'recovery':dict(procedure=record['procedure'],additional_seconds=elapsed,
                    provenance=str(proof.relative_to(ROOT)),original_result_sha256=sha(folder/'original-acquisition-result.json'))}
            save(source,recovered)
            record.update(status='verified_feasible',witness_sha256=certificate['witness_sha256'],original_model_sha256=certificate['original_model_sha256'])
        except Exception as error:
            record.update(status='unknown_retained_failure',error=type(error).__name__+': '+str(error))
        record['additional_seconds']=time.perf_counter()-started;records.append(record)
        save(out/'RECOVERY.json',dict(status='completed',policy_outcomes_used=False,records=records,
            additional_MIP_calls=sum(r['additional_MIP_calls'] for r in records),
            additional_LP_calls=sum(r['additional_LP_calls'] for r in records),
            recovered_references=sum(r['status']=='verified_feasible' for r in records)))
        print(name,record['status'],flush=True)


if __name__=='__main__':main()
