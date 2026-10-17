#!/usr/bin/env python3
"""Independent arithmetic replay of the crossover, no experimental-code imports."""
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
from pathlib import Path

from independent_check import load,dump,sha,point,write_csv,ROOT,PREVIOUS

HERE=Path(__file__).resolve().parent
F=Fraction.from_float


def main():
    manifest=load(PREVIOUS/'MANIFEST.json')
    expected=next(x['sha256'] for x in manifest['files'] if x['path'].endswith('/independent_check.py'))
    assert sha(PREVIOUS/'independent_check.py')==expected
    spec=importlib.util.spec_from_file_location('prior_arithmetic',PREVIOUS/'independent_check.py')
    arithmetic=importlib.util.module_from_spec(spec);spec.loader.exec_module(arithmetic)
    out=HERE/'ablation';design=load(out/'design.json')
    assert len(design['queue'])==design['assigned_treatments']==14
    for path,digest in design['source_hashes'].items():assert sha(ROOT/path)==digest,path
    assert sha(out/'source-snapshot.py')==sha(HERE/'ablation.py')
    model=load(out/'model/original-model.json');assert sha(out/'model/original-model.json')==design['model']['model_sha256']
    source=arithmetic.check_original_mps(model)
    assert sha(out/'model/prior-witness.json')==design['prior_witness_sha256']
    prior=load(out/'model/prior-witness.json')
    assert prior['model_digest']==hashlib.sha256(json.dumps(model,sort_keys=True).encode()).hexdigest()
    exact=arithmetic.rational_check(model,[Fraction(x) for x in prior['point']]);assert exact['exact_feasible']
    upper=Fraction(exact['objective_exact'])
    factors=load(out/'model/factors.json')
    for representation,digest in design['model']['exports'].items():assert sha(out/'model'/(representation+'.lp'))==digest
    rows=[];flags=[];gap_flags=[];internal=[];source_count=candidate_count=exact_count=repair_count=phase_count=0
    all_witnesses=[(upper,'available before ablation','model/prior-witness.json')]
    phase_records=[]
    for task in design['queue']:
        folder=out/'runs'/f"{task['arm']}-s{task['seed']}";r=load(folder/'run.json')
        assert all(r[k]==v for k,v in task.items())
        candidates={};costs={}
        for label in r['candidate_labels']:
            p=point(folder/(label+'.npz'));check,raw,rounded=arithmetic.floating_check(model,p)
            assert check['primal_accepted'] and raw==rounded
            candidates[label]=p;costs[label]=arithmetic.objective(model,raw);candidate_count+=1
        initial,final=design['arms'][task['arm']];expected_representations=[initial,final] if initial else [final]
        assert len(r['phases'])==len(expected_representations)
        for j,p in enumerate(r['phases']):
            final_source_budget_met=False
            phase_count+=1;pf=folder/f'phase-{j}';assert p==load(pf/'phase.json')
            representation=expected_representations[j]
            assert p['representation']==representation and p['import_preserved_original_exactly']
            assert sha(pf/'imported.lp')==p['lp_sha256']==design['model']['exports'][representation]
            params=p['parameters'];assert params['Threads']==4 and params['Seed']==task['seed']
            assert params['MIPGap']==.01 and params['Presolve']==-1 and params['ScaleFlag']==-1
            assert params['FeasibilityTol']==1e-6 and params['IntFeasTol']==1e-5
            assert params.get('IntegralityFocus',0)==(0 if initial and j==0 else 1)
            assert 0<params['TimeLimit']<=((1. if j==0 else 14.) if initial else 15.)
            if p['start_supplied']:
                assert initial and j==1
                assert point(pf/'start.npz')==candidates[p['start_candidate_label']]
            log=(pf/'solver.log').read_text()
            assert p['log_reports_loaded_mip_start']==('Loaded user MIP start with objective' in log)
            screen={'optimality_status':'unverified','bound_contradicted':False,'eligible_exact_witness':False}
            if p['bound'] is not None:
                guard=max(F(1e-6),8*F(math.ulp(float(p['bound']))))
                screen.update(eligible_exact_witness=True,exact_feasible_objective=str(upper),witness=prior['label'],
                              guard_exact=str(guard),bound_contradicted=F(float(p['bound']))>upper+guard)
                if screen['bound_contradicted']:flags.append({**task,'phase':j,'reported_bound':p['bound'],'exact_feasible_objective':float(upper)})
            assert screen==p['prior_witness_screen']
            source_point=None
            if p['has_point']:
                source_count+=1;source_point=point(pf/'source-point.npz')
                check,raw,rounded=arithmetic.floating_check(model,source_point,strict=False)
                assert p['raw_original_objective']==float(arithmetic.objective(model,raw))
                check,_,_=arithmetic.floating_check(model,[float(x) for x in rounded])
                final_source_budget_met=check['primal_accepted']
                label=f'phase-{j}-checked'
                if check['primal_accepted']:assert candidates[label]==[float(x) for x in rounded]
                for a in [x for x in r['repairs'] if x['source_label']==label]:
                    rf=folder/a['folder'];stored=load(rf/'repair.json');assert all(a[k]==v for k,v in stored.items())
                    objective,certificates,has_point=arithmetic.check_repair(model,rf,source_point);repair_count+=has_point
                    if a['delivered']:assert candidates[a['folder']]==point(rf/'delivered.npz')
            phase_records.append({**task,'phase':j,'bound':p['bound'],'completion':p['reported_completion'],'cost':p.get('raw_original_objective')})
        assert sum(p['parameters']['TimeLimit'] for p in r['phases'])<=15.
        if r.get('final_exact_audit'):
            label=r['final_audit_source_label'];before={k:v for k,v in costs.items() if k!='final-exact-audit'}
            assert costs[label]==min(before.values())
            assert r['final_exact_audit']==load(folder/'final-exact-audit/repair.json')
            objective,certificates,has_point=arithmetic.check_repair(model,folder/'final-exact-audit',candidates[label]);repair_count+=has_point
            if r['final_exact_audit']['delivered']:assert candidates['final-exact-audit']==point(folder/'final-exact-audit/delivered.npz')
        for relative in r['new_exact_witnesses']:
            check=arithmetic.rational_check(model,[Fraction(x) for x in load(folder/relative)])
            assert check['exact_feasible'];exact_count+=1
            all_witnesses.append((Fraction(check['objective_exact']),'post-ablation pool',str((folder/relative).relative_to(out))))
        assert bool(candidates)==r['delivered']
        if candidates:
            selected=r['selected_candidate'];assert costs[selected]==min(costs.values())
            assert point(folder/'delivered-point.npz')==candidates[selected]
            assert str(costs[selected])==r['delivered_objective_exact'] and float(costs[selected])==r['delivered_objective']
        assert r['online_bound_contradictions']==sum(p['prior_witness_screen']['bound_contradicted'] for p in r['phases'])
        assert r['optimality_status']=='unverified'
        rows.append({**task,'initial_representation':initial,'final_representation':final,'delivered':r['delivered'],
                     'objective':r.get('delivered_objective'),'total_seconds':r['total_seconds'],
                     'online_bound_contradictions':r['online_bound_contradictions'],'starts_loaded':sum(p['log_reports_loaded_mip_start'] for p in r['phases']),
                     'reported_final_completion':r['phases'][-1]['reported_completion'],'execution_error':r.get('execution_error')})
        rows[-1]['final_source_budget_met']=final_source_budget_met
    start_pairs=[]
    for seed in (59,71):
        for initial in ('L2','Budget'):
            paths=[out/'runs'/f'Warm-{initial}-to-{target}-s{seed}' for target in ('L2','Budget')]
            a,b=[point(p/'phase-1/start.npz') for p in paths]
            assert a==b
            first=[load(p/'phase-0/phase.json') for p in paths]
            assert first[0]['parameters']==first[1]['parameters'] and first[0]['lp_sha256']==first[1]['lp_sha256']
            digest=hashlib.sha256(json.dumps([float(x).hex() for x in a]).encode()).hexdigest()
            start_pairs.append({'seed':seed,'initial_representation':initial,'same_original_binary64_values':True,
                                'start_values_sha256':digest,'same_first_phase_parameters_and_export':True})
    dump(out/'crossover-start-comparisons.json',start_pairs)
    best=min(all_witnesses,key=lambda x:x[0]);pooled=[]
    for p in phase_records:
        if p['bound'] is not None:
            b=F(float(p['bound']));guard=max(F(1e-6),8*F(math.ulp(float(b))))
            if b>best[0]+guard:pooled.append({**p,'exact_feasible_objective':float(best[0]),'witness':best[2],'availability':best[1]})
        if p['completion'] and p['cost'] is not None:
            c=F(float(p['cost']))
            if best[0]<c-F(.01)*abs(c):gap_flags.append({**p,'exact_feasible_objective':float(best[0])})
            if p['bound'] is not None:
                b=F(float(p['bound']));guard=max(F(1e-6),8*F(math.ulp(float(b))),8*F(math.ulp(float(c))))
                if abs(c-b)>max(F(.01)*abs(c),F(1e-10))+guard:internal.append(p)
    write_csv(out/'outcomes.csv',rows);dump(out/'online-bound-discrepancies.json',flags)
    dump(out/'pooled-bound-discrepancies.json',pooled);dump(out/'pooled-gap-discrepancies.json',gap_flags)
    dump(out/'inconsistent-gap-reports.json',internal)
    result={'assigned_treatments':14,'native_mip_calls':phase_count,'source_points_checked':source_count,
            'candidate_points_checked':candidate_count,'delivered_points_checked':sum(r['delivered'] for r in rows),
            'new_exact_witnesses_checked':exact_count,'rational_repair_points_checked':repair_count,
            'online_bound_contradictions':len(flags),'pooled_bound_contradictions':len(pooled),
            'pooled_gap_contradictions':len(gap_flags),'internally_inconsistent_completion_reports':len(internal),
            'original_mps_check':source,'execution_errors':sum(r['execution_error'] is not None for r in rows),
            'wall_reference_overruns':sum(r['total_seconds']>20 for r in rows),
            'best_candidate_retention_checked':True,'requested_mip_limits_within_15_seconds':True,
            'crossover_start_pairs_identical':len(start_pairs),
            'solver_calls_during_replay':0,'scope':'mechanism study selected after observed result; not independent generalization'}
    dump(out/'independent-verification.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':main()
