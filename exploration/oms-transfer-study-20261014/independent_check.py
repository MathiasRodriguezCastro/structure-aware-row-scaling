#!/usr/bin/env python3
"""Replay the held-out study independently of experimental/solver modules."""
import csv
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
from mps_check import check as mps_check

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PREVIOUS=ROOT/'exploration/oms-decision-study-20261014'
F=Fraction.from_float


def load(p):return json.loads(Path(p).read_text())
def dump(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def point(p):
    with np.load(p,allow_pickle=False) as z:return list(z['x'])
def csvwrite(path,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)


def main():
    prior=load(PREVIOUS/'MANIFEST.json');expected=next(v['sha256'] for v in prior['files'] if v['path'].endswith('/independent_check.py'))
    assert sha(PREVIOUS/'independent_check.py')==expected
    spec=importlib.util.spec_from_file_location('prior_independent_arithmetic',PREVIOUS/'independent_check.py')
    a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    out=HERE/'confirmation';d=load(out/'design.json');assert len(d['queue'])==d['assigned_treatments']==80
    assert sha(HERE/'SELECTION.json')==d['selection_sha256']
    for path,digest in d['source_hashes'].items():assert sha(ROOT/path)==digest,path
    assert sha(out/'source-snapshot.py')==sha(HERE/'transfer.py')
    selection=load(HERE/'SELECTION.json');old=load(ROOT/'exploration/oms-generalization-20261014/MIPLIB_SELECTION.json')
    used={r['group'] for r in old['selected']};selected=[]
    for row in old['all_eligible']:
        if row['group'] in ('–','-',None,'') or row['group'] in used:continue
        selected.append(row);used.add(row['group'])
        if len(selected)==4:break
    assert selected==selection['selected']
    models={};witnesses={};source_checks=[];factors_count=0;incompatible=0
    for item in d['models']:
        if not item['prepared']:continue
        folder=out/'models'/item['name'];model=load(folder/'original-model.json');models[item['name']]=model
        assert sha(folder/'original-model.json')==item['model_sha256']
        source_checks.append(mps_check(model,HERE/'sources/miplib-models'))
        assert all(F(float(r['budget']))==F(1e-4*max(1.,abs(float(r['rhs'])))) for r in model['rows'])
        factors=load(folder/'factors.json')
        for policy,alphas in factors.items():
            for row,alpha in zip(model['rows'],alphas):
                magnitudes=[abs(F(float(c))) for c in row['terms'].values() if c]
                lower,upper=F(1e-9)/min(magnitudes),F(1e9)/max(magnitudes)
                if policy.startswith('Budget'):lower=max(lower,F(1e-6)/F(float(row['budget'])))
                if alpha is None:assert lower>upper;incompatible+=1;continue
                q=F(float(alpha));assert q>0
                assert all(F(float(float(alpha)*float(c)))==q*F(float(c)) for c in (*row['terms'].values(),row['rhs']))
                if policy!='Base':assert lower<=q<=upper
                factors_count+=1
        for policy,digest in item['exports'].items():assert sha(folder/(policy+'.lp'))==digest
        witnesses[item['name']]=[]
        if item['known_reference']:
            assert sha(folder/'prior-witness.json')==item['prior_witness_sha256']
            prior=load(folder/'prior-witness.json');q=[Fraction(v) for v in prior['point']]
            assert prior['model_digest']==hashlib.sha256(json.dumps(model,sort_keys=True).encode()).hexdigest()
            exact=a.rational_check(model,q);assert exact['exact_feasible']
            witnesses[item['name']].append({'objective':Fraction(exact['objective_exact']),'path':str((folder/'prior-witness.json').relative_to(HERE)),
                                          'availability':'before study; known reference only'})
    records=[];flat=[];diagnostics=[];per_run_witnesses={};native_count=source_count=candidate_count=delivered_count=exact_count=repair_count=0
    internal=[];online=[]
    for task in d['queue']:
        folder=out/'runs'/task['model']/f"{task['arm']}-s{task['seed']}";r=load(folder/'run.json')
        assert all(r[k]==v for k,v in task.items())
        item=next(v for v in d['models'] if v['name']==task['model']);candidates={};costs={};model=models.get(task['model'])
        if model is not None:
            for label in r['candidate_labels']:
                p=point(folder/(label+'.npz'));check,raw,rounded=a.floating_check(model,p)
                assert check['primal_accepted'] and raw==rounded
                candidates[label]=p;costs[label]=a.objective(model,raw);candidate_count+=1
        if 'native' in r:
            native_count+=1;n=r['native'];assert n['import_preserved_original_exactly']
            assert sha(folder/'imported.lp')==n['export_sha256']==item['exports'][r['representation']]
            p=n['parameters'];tight=task['arm'].endswith('tight');solver=task['arm'].split('-')[0]
            if solver=='gurobi':
                assert p['Threads']==4 and p['MIPGap']==.01 and p['Seed']==task['seed']
                assert p['Presolve']==p['ScaleFlag']==-1 and 0<p['TimeLimit']<=15
                assert p['FeasibilityTol']==(1e-9 if tight else 1e-6) and p['IntFeasTol']==(1e-9 if tight else 1e-5)
                assert p.get('IntegralityFocus',0)==(0 if tight else 1)
                eps,gamma=F(float(p['FeasibilityTol'])),F(float(p['IntFeasTol']))
            else:
                assert p['threads']==4 and p['mip_rel_gap']==.01 and p['random_seed']==task['seed'] and p['presolve']=='on'
                assert 0<p['time_limit']<=15 and p['primal_feasibility_tolerance']==p['mip_feasibility_tolerance']==(1e-9 if tight else 1e-6)
                eps,gamma=F(float(p['primal_feasibility_tolerance'])),F(float(p['mip_feasibility_tolerance']))
            if n['reported_completion'] and n['objective_api'] is not None and n['bound'] is not None:
                c,b=F(float(n['objective_api'])),F(float(n['bound']))
                guard=max(F(1e-6),8*F(math.ulp(float(c))),8*F(math.ulp(float(b))))
                if abs(c-b)>max(F(.01)*abs(c),F(float(n['absolute_gap_target'])))+guard:
                    internal.append({**task,'objective_api':float(c),'bound':float(b),'mip_gap_api':n['mip_gap_api']})
            if item['known_reference'] and 'prior_witness_screen' in r:
                u=witnesses[item['name']][0]['objective'];prior=load(out/'models'/item['name']/'prior-witness.json')
                screen={'optimality_status':'unverified','bound_contradicted':False,'eligible_exact_witness':False}
                if n['bound'] is not None:
                    guard=max(F(1e-6),8*F(math.ulp(float(n['bound']))))
                    screen.update(eligible_exact_witness=True,exact_feasible_objective=str(u),witness=prior['label'],guard_exact=str(guard),
                                  bound_contradicted=F(float(n['bound']))>u+guard)
                assert screen==r['prior_witness_screen']
                if screen['bound_contradicted']:online.append({**task,'bound':n['bound'],'exact_upper_bound':float(u)})
        if r['has_source_point']:
            source_count+=1;source=point(folder/'source-point.npz');raw_check,raw,rounded=a.floating_check(model,source,strict=False)
            assert raw_check==load(folder/'raw-source-check.json')
            rounded_check,_,_=a.floating_check(model,[float(v) for v in rounded])
            assert rounded_check['primal_accepted']==r['source_budget_met']
            assert raw_check['raw']['all_row_and_bound_budgets_met']==r['raw_source_budget_met']
            assert float(a.objective(model,raw))==r['source_objective']
            if r['source_budget_met']:assert candidates['source-checked']==[float(v) for v in rounded]
            alphas=load(out/'models'/task['model']/'factors.json')[r['representation']]
            mu=[];failed=0
            for row,alpha in zip(model['rows'],alphas):
                reserve=gamma*sum((abs(F(float(c))) for i,c in row['terms'].items() if model['variables'][int(i)]['integer']),Fraction(0))
                mu.append((eps/F(float(alpha))+reserve)/F(float(row['budget'])))
                failed+=F(float(alpha))*a.violation(row,raw)>eps
            ih=max((abs(v-round(float(v))) for v,x in zip(raw,model['variables']) if x['integer']),default=Fraction(0))<=gamma
            if max(mu)<=1 and failed==0 and ih:assert not rounded_check['integer_rounded']['failed_rows']
            diagnostics.append({**task,'nominal_maximum_mu':float(max(mu)),'exported_hypothesis_failed_rows':failed,
                                'integer_hypothesis_met':ih,'source_accepted':r['source_budget_met'],
                                'raw_maximum_ratio':raw_check['raw']['maximum_row_budget_ratio'],
                                'rounded_maximum_ratio':rounded_check['integer_rounded']['maximum_row_budget_ratio']})
            for attempt in r['repairs']:
                rf=folder/attempt['folder'];stored=load(rf/'repair.json');assert all(attempt[k]==v for k,v in stored.items())
                objective,certs,has_point=a.check_repair(model,rf,source);repair_count+=has_point
                if attempt['delivered']:assert candidates[attempt['folder']]==point(rf/'delivered.npz')
        if 'final_exact_audit' in r:
            label=r['final_audit_source_label'];before={k:v for k,v in costs.items() if k!='final-exact-audit'}
            assert costs[label]==min(before.values()) and r['final_exact_audit']==load(folder/'final-exact-audit/repair.json')
            objective,certs,has_point=a.check_repair(model,folder/'final-exact-audit',candidates[label]);repair_count+=has_point
            if r['final_exact_audit']['delivered']:assert candidates['final-exact-audit']==point(folder/'final-exact-audit/delivered.npz')
        if (folder/'best-pre-audit-exact-check.json').exists():
            before={k:v for k,v in costs.items() if k!='final-exact-audit'};chosen=min(before,key=before.get)
            q=[F(float(v)) for v in candidates[chosen]];check=a.rational_check(model,q)
            assert check==load(folder/'best-pre-audit-exact-check.json')
            if check['exact_feasible']:assert q==[Fraction(v) for v in load(folder/'best-pre-audit-exact-point.json')]
        per_run_witnesses[(task['model'],task['arm'],task['seed'])]=[]
        for relative in r['new_exact_witnesses']:
            q=[Fraction(v) for v in load(folder/relative)];exact=a.rational_check(model,q);assert exact['exact_feasible'];exact_count+=1
            witnesses[task['model']].append({'objective':Fraction(exact['objective_exact']),'path':str((folder/relative).relative_to(HERE)),
                                          'availability':'post-resolution pool; held-out model' if not item['known_reference'] else 'post-resolution pool; reference'})
            per_run_witnesses[(task['model'],task['arm'],task['seed'])].append(Fraction(exact['objective_exact']))
        assert bool(candidates)==r['delivered']
        if candidates:
            chosen=r['selected_candidate'];assert costs[chosen]==min(costs.values())
            delivered=point(folder/'delivered-point.npz');assert delivered==candidates[chosen]
            check,raw,rounded=a.floating_check(model,delivered);assert check==r['delivery_check'] and check['primal_accepted']
            assert str(costs[chosen])==r['delivered_objective_exact'] and float(costs[chosen])==r['delivered_objective'];delivered_count+=1
        else:assert not (folder/'delivered-point.npz').exists()
        if r['outcome']=='factor_incompatibility_abstention':
            assert not r['has_source_point'] and r['incompatible_rows']==item['incompatible_rows'][r['representation']]
        assert r['optimality_status']=='unverified';records.append(r)
        run_witnesses=per_run_witnesses[(task['model'],task['arm'],task['seed'])]
        flat.append({**task,'known_reference':item['known_reference'],'outcome':r['outcome'],'source_budget_met':r['source_budget_met'],
                     'delivered':r['delivered'],'source_objective':r.get('source_objective'),'delivered_objective':r.get('delivered_objective'),
                     'best_exact_feasible_objective':float(min(run_witnesses)) if run_witnesses else None,
                     'total_seconds':r['total_seconds'],'solver_seconds':r.get('native',{}).get('solver_seconds'),
                     'repairs':len(r['repairs']),'new_exact_witnesses':len(r['new_exact_witnesses']),
                     'reported_completion':r.get('native',{}).get('reported_completion',False),'execution_error':r.get('execution_error')})
    bounds=[];gaps=[];infeasible=[]
    for r in records:
        n=r.get('native');pool=witnesses.get(r['model'])
        if not n or not pool:continue
        best=min(pool,key=lambda x:x['objective']);u=best['objective']
        if n['status'] in (3,'Infeasible'):
            infeasible.append({**{k:r[k] for k in ('model','seed','arm','known_reference')},'reported_status':n['status'],
                               'exact_feasible_objective':float(u),'witness':best['path'],'availability':best['availability']})
        if n['bound'] is not None:
            b=F(float(n['bound']));guard=max(F(1e-6),8*F(math.ulp(float(b))))
            if b>u+guard:bounds.append({**{k:r[k] for k in ('model','seed','arm','known_reference')},'bound':float(b),'exact_upper_bound':float(u),'witness':best['path'],'availability':best['availability']})
        if n['reported_completion'] and n['objective_api'] is not None:
            c=F(float(n['objective_api']))
            if u<c-F(.01)*abs(c):gaps.append({**{k:r[k] for k in ('model','seed','arm','known_reference')},'source_objective_api':float(c),'exact_upper_bound':float(u),'witness':best['path']})
    comparisons=[]
    for item in d['models']:
        for solver in ('gurobi','highs'):
            suffix='-IF1' if solver=='gurobi' else ''
            for seed in d['seeds']:
                budget=next(r for r in records if r['model']==item['name'] and r['seed']==seed and r['arm']==solver+'-Budget'+suffix)
                for label in ('L2','Base','Base-tight'):
                    arm=solver+'-'+label+(suffix if label!='Base-tight' else '')
                    control=next(r for r in records if r['model']==item['name'] and r['seed']==seed and r['arm']==arm)
                    status='not_both_delivered';difference=None;better=worse=False
                    if budget['delivered'] and control['delivered']:
                        b,c=Fraction(budget['delivered_objective_exact']),Fraction(control['delivered_objective_exact'])
                        guard=max(F(1e-6),8*F(math.ulp(float(c))))
                        status='better' if b<c-guard else 'worse' if b>c+guard else 'equal_with_guard'
                        difference=float(b-c);better=b<c-F(.01)*abs(c)-guard;worse=b>c+F(.01)*abs(c)+guard
                    bw=per_run_witnesses[(item['name'],budget['arm'],seed)];cw=per_run_witnesses[(item['name'],control['arm'],seed)]
                    exact_status='not_both_witnessed';exact_better=exact_worse=False
                    if bw and cw:
                        b,c=min(bw),min(cw);guard=max(F(1e-6),8*F(math.ulp(float(c))))
                        exact_status='better' if b<c-guard else 'worse' if b>c+guard else 'equal_with_guard'
                        exact_better=b<c-F(.01)*abs(c)-guard;exact_worse=b>c+F(.01)*abs(c)+guard
                    comparisons.append({'model':item['name'],'known_reference':item['known_reference'],'solver':solver,'seed':seed,
                                        'control':label,'budget_source_accepted':budget['source_budget_met'],'control_source_accepted':control['source_budget_met'],
                                        'budget_delivered':budget['delivered'],'control_delivered':control['delivered'],'comparison':status,
                                        'objective_difference':difference,'better_by_one_percent':better,'worse_by_one_percent':worse,
                                        'exact_witness_comparison':exact_status,'exact_witness_better_by_one_percent':exact_better,
                                        'exact_witness_worse_by_one_percent':exact_worse,
                                        'same_scaled_input':label=='L2' and item.get('exports',{}).get('Dyadic-L2')==item.get('exports',{}).get('Budget-dyadic-L2')})
    csvwrite(out/'outcomes.csv',flat);csvwrite(out/'diagnostics.csv',diagnostics);csvwrite(out/'paired-comparisons.csv',comparisons)
    dump(out/'bound-discrepancies.json',bounds);dump(out/'gap-discrepancies.json',gaps);dump(out/'inconsistent-gap-reports.json',internal);dump(out/'online-vetoes.json',online)
    dump(out/'infeasibility-discrepancies.json',infeasible)
    summary={'assigned_treatments':80,'held_out_group_treatments':64,'known_reference_treatments':16,'native_calls':native_count,
             'source_points_checked':source_count,'candidate_points_checked':candidate_count,'delivered_points_checked':delivered_count,
             'exact_witness_records_checked':exact_count,'rational_repair_points_checked':repair_count,
             'factor_records_checked':factors_count,'incompatible_intervals_checked':incompatible,'original_mps_checks':source_checks,
             'bound_discrepancies':len(bounds),'gap_discrepancies':len(gaps),'internally_inconsistent_reports':len(internal),'online_vetoes_reference_only':len(online),
             'infeasibility_discrepancies':len(infeasible),
             'execution_errors':sum('execution_error' in r for r in records),'wall_reference_overruns':sum(r['total_seconds']>20 for r in records),
             'accepted_sources_with_nominal_mu_above_one':sum(v['nominal_maximum_mu']>1 and v['source_accepted'] for v in diagnostics),
             'solver_calls_during_replay':0,'best_candidate_retention_checked':True,'global_optimality_status':'unverified'}
    dump(out/'independent-verification.json',summary);print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
