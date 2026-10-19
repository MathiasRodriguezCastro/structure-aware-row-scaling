#!/usr/bin/env python3
"""Resource report only; do not choose a scaling policy from pilot outcomes."""
from collections import defaultdict
import statistics
from runner import HERE,load,save


def main():
    plan=load(HERE/'PILOT_PLAN.json');metadata=load(HERE/'MODEL_PREPARATION.json')['models']
    groups=defaultdict(list);missing=[];failed=[];results=[]
    references=[]
    for b in plan['blocks']:
        name=b['instance'];m=metadata[name]
        reference=HERE/'reference-acquisition'/name/'result.json'
        references.append(load(reference) if reference.exists() else dict(instance=name,status='not_attempted'))
        for j in b['jobs']:
            p=HERE/'pilot-runs'/j['id']/'result.json'
            if not p.exists():missing.append(j['id']);continue
            r=load(p);results.append(r)
            if r['status'] not in ['completed','abstained']:failed.append(dict(job=j['id'],status=r['status'],error=r.get('error')))
            groups[m['family'],m['horizon'],j['solver']].append(r)
    strata=[]
    for (family,horizon,solver),rr in sorted(groups.items()):
        base=[r for r in rr if r['job']['policy']=='Base']
        seconds=[r['worker_total_seconds'] for r in rr if r['status']=='completed']
        complete_seconds=[]
        for r in rr:
            timing=HERE/'pilot-execution-logs'/(r['job']['id']+'.json')
            if timing.exists():complete_seconds.append(load(timing)['complete_process_seconds'])
        row=dict(family=family,horizon=horizon,solver=solver,attempts=len(rr),
            Base_completed=sum(r.get('outcome',{}).get('completed',False) for r in base),Base_attempted=len(base),
            maximum_worker_RSS_KiB=max(r.get('maximum_RSS_KiB',0) for r in rr),
            median_worker_seconds=statistics.median(seconds) if seconds else None,
            maximum_worker_seconds=max(seconds) if seconds else None,
            median_complete_process_seconds=statistics.median(complete_seconds) if complete_seconds else None,
            maximum_complete_process_seconds=max(complete_seconds) if complete_seconds else None,
            outer_process_timings_recorded=len(complete_seconds),
            quality_references_available=sum(r.get('quality_reference_available',False) for r in rr),
            policies_not_ranked=True)
        row['longer_Base_calibration_required']=not base or row['Base_completed']/len(base)<.8
        strata.append(row)
    complete=len(results)==256 and not missing and not failed
    status='resource_pilot_complete' if complete else 'resource_pilot_incomplete'
    save(HERE/'PILOT_RESOURCE_REPORT.json',dict(status=status,registered_assignments=256,
        recorded_assignments=len(results),missing_jobs=missing,failed_jobs=failed,
        independently_feasible_references=sum(r['status']=='verified_feasible' for r in references),
        unknown_references=[r for r in references if r['status']!='verified_feasible'],
        strata=strata,policy_ranking_used=False,confirmatory_results=False,
        confirmation_may_be_frozen=complete and all(not s['longer_Base_calibration_required'] for s in strata),
        required_next_step='Review Base censoring, measured memory and failed references; freeze confirmation settings before any of the 3840 main assignments.'))
    print('Pilot resource report:',status,'recorded',len(results),'of 256; no policy ranking or confirmation launched.')


if __name__=='__main__':main()
