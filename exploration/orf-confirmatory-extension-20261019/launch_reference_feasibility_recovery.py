#!/usr/bin/env python3
"""Freeze and submit only the initially unknown reference cases, once."""
from datetime import datetime, timezone
import shlex
import subprocess
from runner import HERE,ROOT,load,save,sha


def main():
    initial = load(HERE/'CONFIRMATION_REFERENCE_REPORT.json')
    assert initial['status']=='completed' and initial['recorded_models']==160
    assert load(HERE/'STDLIB_REFERENCE_REPLAY.json')['status']=='passed'
    assert load(HERE/'PENDING_RAW_MANIFEST.json')['status']=='sealed'
    original_plan = load(HERE/'PENDING_VALIDATION_PLAN.json')
    statuses = {r['instance']:r['status'] for r in initial['records']}
    names = [n for n in original_plan['confirmation_instances'] if statuses[n]=='unknown']
    dependencies = dict(original_plan['dependencies'])
    for name in ['REFERENCE_FEASIBILITY_RECOVERY_PROTOCOL.md','REFERENCE_FEASIBILITY_RECOVERY_RULES.json','recover_confirmation_feasibility.py',
        'verify_reference_witnesses_stdlib.py','verify_recovered_references_stdlib.py',
        'launch_reference_feasibility_recovery.py','cluster/recover_confirmation_feasibility.slurm',
        'cluster/verify_recovered_references.slurm','CONFIRMATION_REFERENCE_REPORT.json',
        'STDLIB_REFERENCE_REPLAY.json','PENDING_RAW_MANIFEST.json']:
        path=HERE/name;dependencies[path.relative_to(ROOT).as_posix()]=sha(path)
    plan_path=HERE/'REFERENCE_FEASIBILITY_RECOVERY_PLAN.json'
    plan=dict(date='2026-10-20',models=names,dependencies=dependencies,
        trigger='Unknown after both registered Base acquisitions; no policy outcomes used.',
        additional_MIP_calls=0,maximum_additional_LP_calls=2*len(names),
        solver_limit_seconds=120,outer_limit_seconds=180,relative_cost_ceiling=.001,
        same_original_integer_patterns=True,original_benchmark_models_modified=False)
    if plan_path.exists():assert load(plan_path)==plan
    else:save(plan_path,plan)
    remote='/clusteruy/home/mathiasr/row-scaling-orf-extension-20261019'
    files=[plan_path]+[HERE/n for n in ['REFERENCE_FEASIBILITY_RECOVERY_PROTOCOL.md','REFERENCE_FEASIBILITY_RECOVERY_RULES.json',
        'recover_confirmation_feasibility.py','verify_recovered_references_stdlib.py',
        'launch_reference_feasibility_recovery.py','cluster/recover_confirmation_feasibility.slurm',
        'cluster/verify_recovered_references.slurm']]
    subprocess.run(['rsync','-rlt','--relative','-e','ssh -p 10022 -o BatchMode=yes -o ConnectTimeout=15',
        *[str(p.relative_to(ROOT)) for p in files],
        'mathiasr@cluster.uy:'+remote+'/repository/'],cwd=ROOT,check=True)
    receipt=HERE/'REFERENCE_FEASIBILITY_RECOVERY_SUBMISSION.json'
    state=load(receipt) if receipt.exists() else dict(plan_sha256=sha(plan_path),jobs={})
    assert state['plan_sha256']==sha(plan_path)
    if not names:
        save(HERE/'REFERENCE_FEASIBILITY_RECOVERY_REPORT.json',dict(status='completed',records=[],
            missing_models=[],additional_MIP_calls=0,additional_LP_calls=0,recovered_references=0))
        save(receipt,state);return
    for key in ['array','collection','replay']:
        if key in state['jobs']:continue
        cmd=['sbatch','--parsable','--chdir='+remote+'/repository',
             '--output='+remote+'/logs/reference-recovery-'+key+'-%A_%a.out',
             '--error='+remote+'/logs/reference-recovery-'+key+'-%A_%a.err']
        if key=='array':
            pending=load(HERE/'PENDING_VALIDATION_SUBMISSION.json')['jobs']
            cmd+=['--array=0-'+str(len(names)-1)+'%1','--dependency=afterok:'+pending['seal']['job_id']+':'+pending['stdlib_replay']['job_id']]
        else:
            previous='array' if key=='collection' else 'collection'
            cmd+=['--dependency='+('afterany' if key=='collection' else 'afterok')+':'+state['jobs'][previous]['job_id']]
        if key=='replay':
            cmd += [remote+'/repository/exploration/orf-confirmatory-extension-20261019/cluster/verify_recovered_references.slurm',remote+'/repository']
        else:
            cmd += [remote+'/repository/exploration/orf-confirmatory-extension-20261019/cluster/recover_confirmation_feasibility.slurm',remote+'/repository','worker' if key=='array' else 'collect']
        process=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',
            'mathiasr@login.cluster.uy',shlex.join(cmd)],text=True,capture_output=True,check=True)
        job=process.stdout.strip();assert job.isdigit()
        state['jobs'][key]=dict(job_id=job,command=cmd,submitted_utc=datetime.now(timezone.utc).isoformat())
        save(receipt,state);print(key,job,flush=True)


if __name__=='__main__':main()
