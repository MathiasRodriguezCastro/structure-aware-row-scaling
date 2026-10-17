"""Row-level reanalysis of fixed, existing exports and terminal results; no solves."""
import csv
from fractions import Fraction
import math
from pathlib import Path
import statistics
from common import HERE,ROOT,FRONT,F,INSTANCES,load,dump,sha,module,choose

def gm(xs):return math.exp(statistics.mean(math.log(x) for x in xs))
def write(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows)

def main():
    import activation_study as a
    out=HERE/'mechanism';out.mkdir(exist_ok=True)
    design=load(FRONT/'design.json')
    native=list(csv.DictReader((FRONT/'verified-runs.csv').open()))
    reference=module(FRONT/'study.py','archived_frontier_for_comparison')
    summary=[];row_records=[];checked=0;all_nonactivation_unchanged=True
    for instance in INSTANCES:
        folder=FRONT/'models'/instance
        parsed,physical=a.original_rows(folder/'Base.lp');_,lp,_=a.campaign.afb.read_lp(folder/'Base.lp')
        l2,_,_=choose(parsed,lp,None)
        assert l2==reference.choose(parsed,lp,None)[0]
        for budget in [10,30,100,300,1000,3000,10000]:
            factors,info,records=choose(parsed,lp,budget,details=True)
            archived=design['models'][instance+'/B'+str(budget)]
            assert info['incompatible_count']==archived['incompatible_count']
            assert factors==reference.choose(parsed,lp,budget)[0]
            changed=[n for n,v in factors.items() if v!=l2[n]]
            nonact=[n for n in changed if not a.ACT.fullmatch(n)]
            assert not nonact,(instance,budget,nonact)
            rr=[r for r in native if r['instance']==instance and r['presolve']=='-1' and r['policy']=='Budget-L2' and r['evaluated_volume_budget']==str(budget)]
            controls={r['seed']:r for r in native if r['instance']==instance and r['presolve']=='-1' and r['policy']=='L2-NF3' and r['evaluated_volume_budget']==str(budget)}
            actual={}
            if archived['model']:
                assert sha(ROOT/archived['model'])==archived['export_sha256']
                actual,_=a.parse(ROOT/archived['model'])
                for n,row in parsed.items():
                    assert actual[n]['sense']==row['sense']
                    assert float(actual[n]['rhs'])==factors[n]*float(row['rhs'])
                    assert {j:float(v) for j,v in actual[n]['terms'].items()}=={j:factors[n]*float(v) for j,v in row['terms'].items()}
                    checked+=len(row['terms'])+1
            actrecords=[]
            for r in records:
                if not r['activation']:continue
                n=r['row'];alpha=r['factor'];r={**r,'instance':instance,'volume_budget':budget,'l2_factor':l2[n],
                    'changed_from_L2':alpha is not None and alpha!=l2[n],
                    'L2_admissibility_threshold_m3':float(F(r['contract_reserve'])+F(1e-6)/F(l2[n]))}
                if alpha is not None:
                    coefficients=[abs(float(v)) for v in actual[n]['terms'].values()]
                    r.update(min_exported_coefficient=min(coefficients),max_exported_coefficient=max(coefficients),factor_ratio_to_L2=alpha/l2[n])
                    # The -1 storage coefficient carries the selected binary64 factor exactly.
                    storage=a.activation_spec(n,parsed[n])[1]
                    assert -float(actual[n]['terms'][storage])==alpha
                    if alpha!=l2[n]:
                        lower=F(1e-6)/(F(r['delta'])-F(r['contract_reserve']))
                        assert F(alpha)>=lower
                        assert F(math.nextafter(alpha,0.))<lower
                row_records.append(r);actrecords.append(r)
            valid=[r for r in actrecords if r['factor'] is not None]
            summary.append({'instance':instance,'volume_budget':budget,'changed_factors':len(changed),
                'changed_nonactivation_factors':len(nonact),'incompatible_rows':info['incompatible_count'],
                'precision_lower_bound_active_rows':sum(r['changed_from_L2'] for r in valid),
                'factor_min':min((r['factor'] for r in valid),default=None),'factor_max':max((r['factor'] for r in valid),default=None),
                'activation_small_coefficient_min':min((r['min_exported_coefficient'] for r in valid),default=None),
                'activation_large_coefficient_max':max((r['max_exported_coefficient'] for r in valid),default=None),
                'L2_admissibility_threshold_min_m3':min(r['L2_admissibility_threshold_m3'] for r in actrecords),
                'L2_admissibility_threshold_max_m3':max(r['L2_admissibility_threshold_m3'] for r in actrecords),
                'integer_reserve_max_m3':max(r['integer_reserve'] for r in actrecords),
                'calls':len(rr),'primal_budget_passes':sum(r['budget_pass']=='True' for r in rr),
                'bound_flags':sum(r['bound_contradiction']=='True' for r in rr),
                'completion_flags':sum(r['gap_contradiction']=='True' for r in rr),
                'max_observed_exported_violation':max((float(r['observed_exported_max_violation']) for r in rr),default=None),
                'exported_epsilon_violations':sum(int(r['exported_physical_rows_exceeding_epsilon']) for r in rr),
                'work_ratio_to_NF3':gm([float(r['work'])/float(controls[r['seed']]['work']) for r in rr]) if rr else None})
        print('Checked mechanism',instance,flush=True)
    write(out/'row-factors.csv',row_records);write(out/'model-budgets.csv',summary)
    aggregated=[]
    for budget in [10,30,100,300,1000,3000,10000]:
        rs=[r for r in summary if r['volume_budget']==budget]
        aggregated.append({'budget':budget,'changed_factors':sum(r['changed_factors'] for r in rs),
            'compatible_models':sum(not r['incompatible_rows'] for r in rs),'calls':sum(r['calls'] for r in rs),
            'primal_passes':sum(r['primal_budget_passes'] for r in rs),'bound_flags':sum(r['bound_flags'] for r in rs),
            'completion_flags':sum(r['completion_flags'] for r in rs),'exported_epsilon_violations':sum(r['exported_epsilon_violations'] for r in rs),
            'work_ratio_to_NF3':gm([r['work_ratio_to_NF3'] for r in rs if r['calls']])})
    write(out/'budget-summary.csv',aggregated)
    dump(out/'VALIDATION.json',{'research_solver_calls':0,'archived_export_data_values_checked':checked,
        'all_changed_rows_are_activation_rows':True,'precision_floor_inward_rounding_verified':True,
        'summary':aggregated,'not_a_causal_identification_of_solver_internal_operations':True,
        'dependencies':{str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),HERE/'common.py',HERE/'PROTOCOL.md',FRONT/'design.json',FRONT/'verified-runs.csv']}})
    print(aggregated,flush=True)

if __name__=='__main__':main()
