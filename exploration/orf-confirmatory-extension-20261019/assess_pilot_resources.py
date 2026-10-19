#!/usr/bin/env python3
"""Base-only cap assessment, separating exactly certified infeasible models."""
from collections import defaultdict
from runner import HERE,load,save,sha


def main():
    plan=load(HERE/'PILOT_PLAN.json');data=load(HERE/'MODEL_PREPARATION.json')['models']
    audit=load(HERE/'STRUCTURAL_FEASIBILITY_AUDIT.json')
    assert load(HERE/'STRUCTURAL_CERTIFICATE_REPLAY.json')['status']=='passed'
    infeasible=set(audit['certified_infeasible_instances']);groups=defaultdict(list)
    missing=[];diagnostic=[];failures=[];recorded=0;peak=0
    for block in plan['blocks']:
        name=block['instance'];m=data[name]
        for job in block['jobs']:
            path=HERE/'pilot-runs'/job['id']/'result.json'
            if not path.exists():missing.append(job['id']);continue
            r=load(path);recorded+=1;peak=max(peak,r.get('maximum_RSS_KiB',0))
            if r['status'] not in ['completed','abstained']:
                failures.append(dict(job=job['id'],status=r['status'],error=r.get('error')))
            if job['policy']!='Base':continue
            row=dict(job=job['id'],instance=name,status=r['status'],native=r.get('outcome'),
                requested_seconds=job['time_limit'],reference_available=r.get('quality_reference_available',False))
            if name in infeasible:diagnostic.append(row)
            else:groups[m['family'],m['horizon'],job['solver']].append(row)
    strata=[];proposed=[]
    for (family,horizon,solver),rows in sorted(groups.items()):
        completed=sum(r['native'] is not None and r['native']['completed'] for r in rows)
        unknown_refs=[r['instance'] for r in rows if not r['reference_available']]
        need=len(rows)>0 and completed/len(rows)<.8
        strata.append(dict(family=family,horizon=horizon,solver=solver,Base_recorded=len(rows),
            native_gap_stops=completed,native_gap_stop_fraction=completed/len(rows),
            additional_Base_calibration_required=need,unknown_references=unknown_refs,rows=rows))
        if need:
            for row in rows:
                proposed.append(dict(instance=row['instance'],solver=solver,policy='Base',seed=401,
                    time_limit=120.,reason='Entire feasible stratum repeated at the next cap; no policy ranking.'))
    complete=recorded==256 and not missing and not failures
    save(HERE/'BASE_RESOURCE_ASSESSMENT.json',dict(status='complete' if complete else 'incomplete',
        registered_assignments=256,recorded_assignments=recorded,missing_jobs=missing,failures=failures,
        structural_audit_sha256=sha(HERE/'STRUCTURAL_FEASIBILITY_AUDIT.json'),
        structural_certificate_replay_sha256=sha(HERE/'STRUCTURAL_CERTIFICATE_REPLAY.json'),
        diagnostic_Base_records=diagnostic,strata=strata,maximum_worker_RSS_KiB=peak,
        proposed_120_second_Base_only_jobs=proposed,proposed_jobs_launched=False,
        policy_ranking_used=False,confirmation_launched=False,
        interpretation='Native gap stopping calibrates resources; it is not an independent MILP optimality certificate.'))
    print('Base-only resource assessment:',recorded,'of 256 assignments;',len(proposed),'proposed calibration jobs.')


if __name__=='__main__':main()
