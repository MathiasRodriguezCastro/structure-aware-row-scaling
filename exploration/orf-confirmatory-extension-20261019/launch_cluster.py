#!/usr/bin/env python3
"""Submit only the registered deployment gate and resource pilot, with receipts."""
import argparse
from datetime import datetime, timezone
import shlex
import subprocess
from runner import HERE, load, save, sha

HOST='mathiasr@login.cluster.uy'
REMOTE='/clusteruy/home/mathiasr/row-scaling-orf-extension-20261019'
TASK_ROOT=REMOTE+'/repository'
SUB='exploration/orf-confirmatory-extension-20261019'


def control(args):
    result=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',
        HOST,shlex.join(args)],text=True,capture_output=True,timeout=60,check=True)
    return result.stdout.strip()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['deployment','recheck','pilot'])
    args=ap.parse_args();target=HERE/'SLURM_SUBMISSION.json'
    plan_hash=sha(HERE/'PILOT_PLAN.json')
    record=load(target) if target.exists() else dict(
        pilot_plan_sha256=plan_hash,remote_repository=TASK_ROOT,jobs={},
        confirmation_assignments_submitted=0,main_campaign_launched=False,
        resource_pilot_used_for_policy_selection=False,commands=[])
    assert record['pilot_plan_sha256']==plan_hash
    control(['mkdir','-p',REMOTE+'/logs'])

    def submit(name,script,extra,script_args):
        if name in record['jobs']:return record['jobs'][name]['job_id']
        command=['sbatch','--parsable','--chdir='+TASK_ROOT,
            '--output='+REMOTE+'/logs/'+name+'-%A_%a.out',
            '--error='+REMOTE+'/logs/'+name+'-%A_%a.err',*extra,
            TASK_ROOT+'/'+SUB+'/cluster/'+script,TASK_ROOT,*script_args]
        response=control(command);job=response.split(';')[0]
        assert job.isdigit(),response
        record['jobs'][name]=dict(job_id=job,submitted_utc=datetime.now(timezone.utc).isoformat())
        record['commands'].append(command);save(target,record)
        print(name,job,flush=True)
        return job

    if args.stage=='deployment':
        assert not record['jobs'],'Do not resubmit an existing deployment attempt'
        submit('deployment','deployment.slurm',[],[])
    else:
        gate=record['jobs']['deployment']['job_id']
        states=control(['sacct','-X','-n','-P','-j',gate,'--format=State']).splitlines()
        assert states and all(s.split('|')[0].strip()=='COMPLETED' for s in states),states
        assert load(HERE/'DEPLOYMENT_GATE.json')['status']=='passed'
        assert load(HERE/'NATIVE_TEST-remote.json')['status']=='passed'
        if args.stage=='recheck':
            submit('recheck','recheck.slurm',[],[])
            return
        if record.get('pre_execution_amendments'):
            recheck=record['jobs']['recheck']['job_id']
            states=control(['sacct','-X','-n','-P','-j',recheck,'--format=State']).splitlines()
            assert states and all(s.split('|')[0].strip()=='COMPLETED' for s in states),states
            assert load(HERE/'DEPLOYMENT_RECHECK.json')['pilot_plan_sha256']==plan_hash
            assert load(HERE/'DEPLOYMENT_RECHECK.json')['status']=='passed'
        refs=submit('references','pilot.slurm',['--array=0-31%1'],['references'])
        dependencies=refs
        if record.get('reference_recovery_job'):dependencies+=':'+record['reference_recovery_job']
        pilot=submit('pilot','pilot.slurm',['--array=0-31%1','--dependency=afterok:'+dependencies],['pilot'])
        collection=submit('collection','collect.slurm',['--dependency=afterany:'+pilot],[])
        submit('replay','replay.slurm',['--dependency=afterok:'+collection],[])
        record.update(status='resource_pilot_submitted',reference_MIP_assignments=32,
            exact_reference_LP_attempts_at_most=32,pilot_MIP_assignments=256,
            global_comparative_concurrency=1)
    save(target,record)


if __name__=='__main__':main()
