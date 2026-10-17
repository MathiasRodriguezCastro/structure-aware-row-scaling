#!/usr/bin/env python3
"""License-free, solver-free replay of the activation study and exact witnesses."""
import csv
from fractions import Fraction
import json
import math
from pathlib import Path
import statistics

import numpy as np

import activation_study as study
import exact_dispatch_witness as certificate

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
F=Fraction.from_float
PHASES={'confirmation-bank':72,'confirmation-mechanism':27,
        'presolve-off-followup':6,'presolve-off-global-tight':3,
        'sensitivity-reference':3,'sensitivity-permissive':3}


def native_source(policy):
    if policy in ('Base','GM','Ruiz-R4','Budget-L2','L2-dyadic','Budget-dyadic'):return policy
    return 'L2-window' if policy.startswith('L2-') else 'GM'


def main():
    witnesses={}
    index=json.loads((HERE/'exact-witnesses/index.json').read_text())
    for item in index:
        folder=(ROOT/item['certificate']).parent
        certificate.check(folder)
        data=json.loads((folder/'independent-certificate.json').read_text())
        witnesses[item['model_sha256']]=Fraction(data['objective_exact_fraction'])
    if (HERE/'exact-witness-reference/independent-certificate.json').exists():
        folder=HERE/'exact-witness-reference';certificate.check(folder)
        data=json.loads((folder/'independent-certificate.json').read_text())
        witnesses[data['original_model_sha256']]=Fraction(data['objective_exact_fraction'])
    all_runs=[];factor_rows=0;changed_rows=0;hypothesis_failures=0
    for phase,assigned in PHASES.items():
        out=HERE/phase;design=json.loads((out/'design.json').read_text())
        assert study.sha(out/'source-snapshot.py')==design['source_sha256']
        runs=list(csv.DictReader((out/'runs.csv').open()))
        assert len(runs)==assigned
        assert len({(r['instance'],r['policy'],r['seed']) for r in runs})==assigned
        saved=list(csv.DictReader((out/'physical.csv').open()))
        stored={(r['instance'],r['policy'],r['seed'],r['group']):r for r in saved}
        for item in design['prepared']:
            instance=item['instance'];folder=out/'models'/instance
            for source,expected in item['exports'].items():assert study.sha(folder/(source+'.lp'))==expected
            parsed,rows=study.original_rows(folder/'Base.lp')
            _,lp,_=study.campaign.afb.read_lp(folder/'Base.lp')
            integers={n for n,k in zip(lp.col_names_,lp.integrality_) if str(k)!='HighsVarType.kContinuous'}
            boxes={n:max(abs(float(lo)),abs(float(hi))) for n,lo,hi in zip(lp.col_names_,lp.col_lower_,lp.col_upper_)}
            decisions=list(csv.DictReader((folder/'decisions.csv').open()))
            exported,_=study.parse(folder/'Budget-L2.lp')
            _,base_other=study.parse(folder/'Base.lp')
            for source in ('L2-window','Budget-L2','GM','Ruiz-R4','L2-dyadic','Budget-dyadic'):
                _,other=study.parse(folder/(source+'.lp'));assert other==base_other
            changed=0
            for d in decisions:
                name=d['row'];alpha=F(float(d['budget_factor']));row=parsed[name]
                assert alpha>0
                for n,a in row['terms'].items():
                    if a:
                        assert F(1e-9)<=alpha*abs(F(float(a)))<=F(1e9)
                    assert F(float(exported[name]['terms'][n]))==F(float(alpha)*float(a))
                assert F(float(exported[name]['rhs']))==F(float(alpha)*float(row['rhs']))
                modified=float(d['budget_factor'])!=float(d['l2_window_factor'])
                assert modified==(d['changed_by_budget'] in ('True','true','1'))
                if modified:assert study.ACT.fullmatch(name)
                changed+=modified;factor_rows+=1
                if study.ACT.fullmatch(name):
                    e=F(item['guided_gamma'])*sum((abs(F(float(v))) for n,v in row['terms'].items() if n in integers),Fraction(0))
                    drift=sum((abs(F(float(exported[name]['terms'][n]))/alpha-F(float(a)))*F(boxes[n]) for n,a in row['terms'].items()),Fraction(0))+abs(F(float(exported[name]['rhs']))/alpha-F(float(row['rhs'])))
                    declared=F(2.**-52)*(sum((abs(F(float(a)))*F(boxes[n]) for n,a in row['terms'].items()),Fraction(0))+abs(F(float(row['rhs']))))
                    assert drift<=declared
                    assert F(1e-6)/alpha+e+drift<=F(design['budgets']['m3'])
            assert changed==item['budget_changed_rows'];changed_rows+=changed
            for run in (r for r in runs if r['instance']==instance):
                policy=run['policy'];seed=run['seed'];run_dir=out/'runs'/instance/(policy+'-s'+seed)
                params=json.loads((run_dir/'parameters.json').read_text())
                assert params['Seed']==int(seed) and params['TimeLimit']==120 and params['Threads']==4
                assert 'Gurobi Optimizer version 13.0.2' in (run_dir/'solver.log').read_text()
                with np.load(run_dir/'solution.npz',allow_pickle=False) as sol:
                    values=dict(zip(sol['names'].tolist(),sol['x'].tolist()))
                assert set(values)==set(lp.col_names_)
                audited=study.audit_values(rows,values,integers)
                for r in audited:
                    s=stored[instance,policy,seed,r['group']]
                    assert math.isclose(float(s['raw_max']),r['raw_max'],rel_tol=1e-13,abs_tol=1e-15)
                    assert math.isclose(float(s['rounded_max']),r['rounded_max'],rel_tol=1e-13,abs_tol=1e-15)
                a=next(r for r in audited if r['group']=='Volume-dependent activation')
                assert float(run['raw_activation_m3'])==a['raw_max'] and float(run['rounded_activation_m3'])==a['rounded_max']
                actual_objective=sum((F(float(cost))*F(values[n]) for n,cost in zip(lp.col_names_,lp.col_cost_)),F(float(lp.offset_)))
                assert math.isclose(float(actual_objective),float(run['objective']),rel_tol=1e-12,abs_tol=1e-6)
                source=native_source(policy);source_path=folder/(source+'.lp')
                source_hash=study.sha(source_path)
                w=witnesses.get(source_hash)
                # Both dyadic controls are exactly proportional to Base, so its
                # exact witness applies, not merely a numerically screened point.
                if policy in ('L2-dyadic','Budget-dyadic'):
                    transformed,_=study.parse(source_path)
                    for name,row in parsed.items():
                        pivot=next(n for n,a in row['terms'].items() if a)
                        scalar=F(float(transformed[name]['terms'][pivot]))/F(float(row['terms'][pivot]))
                        assert scalar>0
                        assert all(F(float(transformed[name]['terms'][n]))==scalar*F(float(a)) for n,a in row['terms'].items())
                        assert F(float(transformed[name]['rhs']))==scalar*F(float(row['rhs']))
                    w=witnesses[study.sha(folder/'Base.lp')]
                if policy in ('GM-tight-M','GM-indicators'):w=None
                bound=F(float(run['bound']));obj=F(float(run['objective']))
                allowance=F(max(1e-6,8*math.ulp(float(run['bound']))))
                excess=max(Fraction(0),bound-w) if w is not None else None
                contradiction=(excess>allowance) if w is not None else None
                completion_contradiction=(obj-w>F(.01)*abs(obj)) if w is not None else None
                exact_known_gap=float(max(Fraction(0),obj-w)/max(F(1.),abs(obj))) if w is not None else None
                actual_hyp=0
                if policy not in ('GM-tight-M','GM-indicators'):
                    sr,_=study.parse(source_path)
                    for name in parsed:
                        if study.ACT.fullmatch(name):
                            violation=study.campaign.exact_violation(sr[name]['terms'],sr[name]['rhs'],values,sr[name]['sense'])
                            actual_hyp+=violation>F(params['FeasibilityTol'])
                hypothesis_failures+=actual_hyp
                all_runs.append({**run,'phase':phase,'source_sha256':source_hash,
                    'activation_observed_exported_hypothesis_failures':actual_hyp,
                    'exact_witness_objective':float(w) if w is not None else None,
                    'bound_excess_over_exact_witness':float(excess) if excess is not None else None,
                    'bound_contradiction':contradiction,'completion_contradiction':completion_contradiction,
                    'gap_to_exact_feasible_witness':exact_known_gap,
                    'rounded_budget_met':float(run['rounded_physical_max_ratio'])<=1})
        print('Independent replay passed',phase,assigned,flush=True)
    assert len(all_runs)==114
    cost_runs=list(csv.DictReader((HERE/'factor-cost-runs.csv').open()))
    cost_summary=list(csv.DictReader((HERE/'factor-cost-summary.csv').open()))
    assert len(cost_runs)==36 and len(cost_summary)==12
    bank=json.loads((HERE/'confirmation-bank/design.json').read_text())
    for r in cost_runs:
        item=next(i for i in bank['prepared'] if i['instance']==r['instance'])
        assert r['export_sha256']==item['exports'][r['policy']]
    for r in cost_summary:
        measured=[float(v['selection_export_seconds']) for v in cost_runs
                  if v['instance']==r['instance'] and v['policy']==r['policy']]
        assert len(measured)==3
        assert float(r['median_selection_export_seconds'])==statistics.median(measured)
    # Recompute the fixed-continuous-point binary-choice certificate.
    base_rows,_=study.parse(HERE/'confirmation-bank/models/instance046/Base.lp')
    path=ROOT/'results-revision/research-audit/oms-close-20261013/runs/sgtm/instance046/Base-solution.npz'
    with np.load(path,allow_pickle=False) as saved:
        point=dict(zip(saved['names'].tolist(),saved['x'].tolist()))
    gate=json.loads((HERE/'gate-rounding-certificate.json').read_text())
    binary=gate['binary']
    assert F(float(base_rows['a1_g4h_def(18)']['terms']['g1(18)']))==1
    assert F(float(base_rows['a1_g4h_def(18)']['terms']['a1_theta42(18)']))==-1
    for row in gate['checks']:
        values={**point,binary:float(row['binary_choice'])}
        power=study.campaign.exact_violation(base_rows['a1_cota_altura_3(18)']['terms'],0,values,'<=')
        activation=base_rows['a1_activacion_1(18)']
        water=study.campaign.exact_violation(activation['terms'],activation['rhs'],values,'<=')
        assert power==Fraction(row['power_exact_fraction']) and water==Fraction(row['volume_exact_fraction'])
        assert not (power<=F(.1) and water<=F(1000.))
    study.csvwrite(HERE/'verified-runs.csv',all_runs)
    summary=[]
    for phase in PHASES:
        selected=[r for r in all_runs if r['phase']==phase]
        for policy in sorted({r['policy'] for r in selected}):
            r=[v for v in selected if v['policy']==policy]
            gm=lambda key:math.exp(sum(math.log(float(v[key])) for v in r)/len(r))
            summary.append({'phase':phase,'policy':policy,'runs':len(r),
                'reported_completions':sum(v['completed']=='1' for v in r),
                'rounded_budget_met':sum(v['rounded_budget_met'] for v in r),
                'exact_witness_available':sum(v['exact_witness_objective'] is not None for v in r),
                'bound_contradictions':sum(v['bound_contradiction'] is True for v in r),
                'completion_contradictions':sum(v['completion_contradiction'] is True for v in r),
                'geomean_work':gm('work'),'geomean_load_optimize_seconds':gm('total_seconds'),
                'maximum_rounded_activation_m3':max(float(v['rounded_activation_m3']) for v in r),
                'maximum_gap_to_exact_feasible_witness':max((v['gap_to_exact_feasible_witness'] for v in r if v['gap_to_exact_feasible_witness'] is not None),default=None)})
    study.csvwrite(HERE/'verified-summary.csv',summary)
    study.dump(HERE/'independent-study-verification.json',{'nonpilot_calls_replayed':len(all_runs),
        'exact_native_export_witnesses':len(witnesses),'factor_records_checked':factor_rows,
        'contract_modified_factor_records':changed_rows,
        'actual_activation_exported_hypothesis_failures':hypothesis_failures,
        'optimizer_calls_during_verification':0,'original_costs_recomputed':True,
        'factor_cost_measurements_checked':len(cost_runs),'binary_choice_certificate_recomputed':True,
        'comparison_uses_certificate_for_same_native_export_or_exact_dyadic_equivalence':True,
        'scope':'exact feasible witnesses and original-unit point residuals; no global MILP optimality certificates'})
    print('Activation study replay and summaries passed',len(all_runs),flush=True)


if __name__=='__main__':main()
