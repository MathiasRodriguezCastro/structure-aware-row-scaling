#!/usr/bin/env python3
"""Recompute recorded pilot endpoints from saved vectors, with zero solver calls."""
from fractions import Fraction as Q
import math
import numpy as np
from runner import HERE,ROOT,load,save,sha,library


def row_violation(row,point):
    value=sum((a*point[n] for n,a in row['terms'].items()),Q(0))-row['rhs']
    if row['sense']=='=':return abs(value)
    return max(Q(0),value if row['sense']=='<=' else -value)


def exact_feasible(model,point):
    rows,bounds,_,integers,_,_=model
    assert set(point)==set(bounds)
    return (all(row_violation(row,point)==0 for row in rows.values()) and
        all((lo is None or point[n]>=lo) and (hi is None or point[n]<=hi)
            for n,(lo,hi) in bounds.items()) and
        all(point[n].denominator==1 for n in integers))


def candidate_cost(model,point):
    rounded={n:Q(round(v)) if n in model[3] else v for n,v in point.items()}
    return model[5]+sum((c*rounded[n] for n,c in model[2].items()),Q(0)),rounded


def candidate_audit(model,point,rounded):
    rows,bounds,costs,integers,scope,offset=model
    maxima=dict(power=Q(0),activation=Q(0),water=Q(0));other=Q(0)
    for n,row in rows.items():
        violation=max(row_violation(row,point),row_violation(row,rounded))
        if n in scope:
            group,unit,conversion=scope[n]
            category='power' if unit=='MW' else 'activation' if group=='Volume-dependent activation' else 'water'
            maxima[category]=max(maxima[category],violation/conversion)
        else:
            magnitude=max(Q(1),abs(row['rhs']),sum((abs(c*rounded[j]) for j,c in row['terms'].items()),Q(0)))
            other=max(other,violation/magnitude)
    integer_distance=max((abs(point[n]-round(point[n])) for n in integers),default=Q(0))
    bound_violation=max([Q(0)]+[lo-rounded[n] for n,(lo,hi) in bounds.items() if lo is not None]+
        [rounded[n]-hi for n,(lo,hi) in bounds.items() if hi is not None])
    budgets=dict(power=.01,activation=100.,water=100.)
    return dict(physical_pass=all(maxima[k]<=Q.from_float(budgets[k]) for k in budgets),
        domain_pass=bound_violation==0 and integer_distance<=Q.from_float(1e-9),
        other_rows_pass=other<=Q.from_float(1e-6),
        maximum_physical_violation={k:str(v) for k,v in maxima.items()},
        max_integrality=str(integer_distance),max_bound_violation=str(bound_violation),
        max_other_backward_error=str(other),
        objective_exact=str(offset+sum((c*rounded[n] for n,c in costs.items()),Q(0))))


def main():
    plan=load(HERE/'PILOT_PLAN.json');data=load(HERE/'MODEL_PREPARATION.json')['models']
    for name,digest in plan['dependencies'].items():assert sha(ROOT/name)==digest,name
    checker=library(ROOT/'exploration/orf-confirmatory-20261018/check.py','independent_pilot_model_reader')
    counts=dict(recorded_assignments=0,candidate_vectors=0,full_candidate_audits=0,
        exact_reference_checks=0,unknown_quality_assignments=0,abstentions=0)
    missing=[];failed=[];verified=[]
    for block in plan['blocks']:
        name=block['instance'];base=HERE/'models'/name/'Base.lp'
        assert sha(base)==data[name]['base_sha256'];model=checker.canonical(base)
        reference=None;witness=None
        ref=HERE/'references'/name
        acquisition=HERE/'reference-acquisition'/name/'result.json'
        if acquisition.exists() and load(acquisition)['status']=='verified_feasible':
            certificate=load(ref/'independent-certificate.json')
            assert certificate['original_model_sha256']==sha(base)
            witness={n:Q(v) for n,v in load(ref/'exact-witness.json').items()}
            assert exact_feasible(model,witness),name
            reference,_=candidate_cost(model,witness)
            assert reference==Q(certificate['objective_exact_fraction'])
            counts['exact_reference_checks']+=1
        for job in block['jobs']:
            folder=HERE/'pilot-runs'/job['id'];result=folder/'result.json'
            if not result.exists():missing.append(job['id']);continue
            r=load(result);counts['recorded_assignments']+=1
            assert r['job']==job
            if r['status']=='abstained':counts['abstentions']+=1;continue
            if r['status']!='completed':failed.append(dict(job=job['id'],status=r['status']));continue
            assert r['base_sha256']==sha(folder/'Base.lp')==sha(base)
            rep='Base' if job['policy']=='Base' else 'Budget-L2' if job['policy']=='Budget-L2' else 'L2'
            export=folder/('Base.lp' if rep=='Base' else 'scaled.lp')
            expected=data[name]['base_sha256'] if rep=='Base' else data[name]['policies'][rep]['export_sha256']
            assert sha(export)==r['export_sha256']==expected
            assert r['quality_reference_available']==(reference is not None)
            assert r['reference_exact']==(str(reference) if reference is not None else None)
            if reference is None:counts['unknown_quality_assignments']+=1
            with np.load(folder/'candidates.npz',allow_pickle=False) as arrays:
                names=arrays['names'].tolist();vectors=arrays['x']
                assert len(names)==len(set(names)) and set(names)==set(model[1])
                assert vectors.shape==(len(r['events']),len(names)) and np.isfinite(vectors).all()
                first=None
                for i,(event,vector) in enumerate(zip(r['events'],vectors)):
                    point={n:Q.from_float(float(x)) for n,x in zip(names,vector)}
                    cost,rounded=candidate_cost(model,point)
                    quality=None if reference is None else cost<=reference+Q.from_float(.001)*max(Q(1),abs(reference))
                    assert event['quality_pass']==quality
                    assert Q(event['audit']['objective_exact'])==cost
                    if quality or event['kind']=='final':
                        audit=candidate_audit(model,point,rounded)
                        assert audit==event['audit'],(job['id'],i)
                        counts['full_candidate_audits']+=1
                        if quality and all(audit[k] for k in ['physical_pass','domain_pass','other_rows_pass']) and first is None:first=i
                counts['candidate_vectors']+=len(vectors)
            assert (None if r['first_qualified'] is None else r['first_qualified']['index'])==first
            native_witness=False;contradiction=None
            if witness is not None:
                native_witness=exact_feasible(checker.canonical(export),witness)
                bound=r['outcome']['reported_bound']
                if native_witness and bound is not None:
                    contradiction=Q.from_float(bound)>reference+Q.from_float(max(1e-6,8*math.ulp(bound)))
            assert r['exact_reference_feasible_for_imported_export']==native_witness
            assert r['bound_contradiction']==contradiction
            timing=load(HERE/'pilot-execution-logs'/(job['id']+'.json'))
            assert timing['returncode']==0 and timing['complete_process_seconds']>=r['worker_total_seconds']
            verified.append(job['id'])
    status='passed' if counts['recorded_assignments']==256 and not missing and not failed else 'incomplete_retained_outcomes'
    save(HERE/'PILOT_REPLAY.json',dict(status=status,counts=counts,verified_jobs=verified,
        missing_jobs=missing,failed_jobs=failed,optimizer_calls=0,policy_selection=False,
        check_scope='All saved costs and quality decisions; complete physical/domain audits for eligible and final candidates; exact reference feasibility and bound flags.'))
    print('Pilot replay:',status,counts,flush=True)


if __name__=='__main__':main()
