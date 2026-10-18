"""Quality-first summary, exact counterfactual row transfers, and inclusion decision."""
import csv
from fractions import Fraction as F
import json

from fetch import HERE,dump


def read(stage):return list(csv.DictReader((HERE/f'stage-{stage}-results.csv').open()))


def main():
    all_rows=read('b')+read('c')+read('b2')
    assert len(all_rows)==57
    counts=dict(calls=57,stored_points=sum(r['point_available']=='True' for r in all_rows),
        within_budget=sum(r.get('rounded_pass')=='True' for r in all_rows),
        observed_failures=sum(r.get('rounded_pass')=='False' for r in all_rows),
        unknown_no_point=sum(r['point_available']=='False' for r in all_rows))
    assert counts==dict(calls=57,stored_points=40,within_budget=36,observed_failures=4,unknown_no_point=17)
    cases=[];rejection=[]
    for name in ('neos-619167','neos-3762025-ognon'):
        methods={r['policy']:r for r in all_rows if r['instance']==name}
        budget=methods['Budget-L2'];tight=methods['Dyadic-L2-tight'];base=methods['Base']
        assert all(r['rounded_pass']=='True' for r in (budget,tight,base))
        cases.append(dict(instance=name,budget=float(budget['budget']),
            L2_original_max=float(methods['Dyadic-L2']['rounded_max']),
            NF3_original_max=float(methods['Dyadic-L2-NumericFocus3']['rounded_max']),
            Budget_original_max=float(budget['rounded_max']),
            budget_over_tight_work=float(budget['work'])/float(tight['work']),
            budget_over_base_work=float(budget['work'])/float(base['work']),
            budget_over_tight_measured_cycle=float(budget['measured_cycle_seconds'])/float(tight['measured_cycle_seconds']),
            budget_over_base_measured_cycle=float(budget['measured_cycle_seconds'])/float(base['measured_cycle_seconds']),
            Base_and_tight_already_meet_budget=True,independent_confirmation_gate_passed=False))
        validation=json.loads((HERE/'stage-b'/name/'Dyadic-L2'/'verification.json').read_text())
        worst=max(validation['failed_original_rows'],key=lambda r:r['ratio'])
        i=worst['row'];violation=F(worst['raw_violation_exact'])
        a=F(json.loads((HERE/'exports'/name/'Dyadic-L2-factors.json').read_text())[i])
        b=F(json.loads((HERE/'exports'/name/'Budget-L2-factors.json').read_text())[i])
        assert b*violation>F(1e-6)
        rejection.append(dict(instance=name,row=worst['name'],original_violation_exact=str(violation),
            L2_factor_exact=str(a),Budget_factor_exact=str(b),
            L2_exported_violation_exact=str(a*violation),
            same_point_Budget_exported_violation_exact=str(b*violation),
            L2_point_satisfies_exported_hypothesis=a*violation<=F(1e-6),
            same_point_Budget_violates_exported_hypothesis=True,
            interpretation='counterfactual exact row rejection under the residual hypothesis, not a causal identification of proprietary solver internals'))
    exact=json.loads((HERE/'verification-exact.json').read_text())
    out=dict(screened_models=12,numerically_eligible=9,counts=counts,remedy_cases=cases,
        counterfactual_rows=rejection,exact_unique_patterns=exact['unique_patterns'],
        exact_feasible_patterns=exact['exact_feasible_patterns'],
        exact_infeasible_patterns=len({r['pattern_key'] for r in exact['records'] if r.get('fixed_pattern_infeasibility_certified')}),
        native_exact_LP_calls=10,
        decision='retain outside OMS: two recoveries versus L2/NF3, but Base and strict L2 already succeed and Budget does not beat those strong controls',
        unresolved_scope='four of five controls have no incumbent for lot sizing even at WorkLimit16; do not infer accuracy safety or failure for those calls',
        speed_scope='exploratory timings; preparation starts from loaded native model data and excludes initial data parsing, interpreter/license startup, and independent verification',
        global_optimality_claim=False)
    dump(HERE/'summary.json',out)
    print(json.dumps(out,indent=2))


if __name__=='__main__':main()
