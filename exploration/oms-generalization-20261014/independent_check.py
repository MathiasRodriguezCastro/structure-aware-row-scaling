#!/usr/bin/env python3
"""Separate arithmetic replay and pre-solve indicators; no runner or solver import."""
import csv
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

import numpy as np

HERE=Path(__file__).resolve().parent
F=Fraction.from_float


def row_violation(row, values):
    activity=sum((F(float(c))*values[int(i)] for i,c in row['terms'].items()),Fraction(0))
    difference=activity-F(float(row['rhs']))
    if row['sense']=='=':return abs(difference)
    return max(Fraction(0),difference if row['sense']=='<' else -difference)


def check_point(model, point):
    assert len(point)==len(model['variables']) and all(math.isfinite(float(v)) for v in point)
    raw=[F(float(v)) for v in point]
    rounded=[Fraction(round(float(x))) if v['integer'] else x for x,v in zip(raw,model['variables'])]
    metrics={}
    for name,values in (('raw',raw),('integer_rounded',rounded)):
        violations=[row_violation(r,values) for r in model['rows']]
        ratios=[v/F(float(r['budget'])) for v,r in zip(violations,model['rows'])]
        failures=[i for i,v in enumerate(ratios) if v>1]
        bfail=0
        for x,v in zip(values,model['variables']):
            tolerance=F(float(v['bound_budget']))
            if v['lower'] is not None and F(float(v['lower']))-x>tolerance:bfail+=1
            elif v['upper'] is not None and x-F(float(v['upper']))>tolerance:bfail+=1
        metrics[name]={'maximum_row_budget_ratio':float(max(ratios,default=Fraction(0))),
            'failed_rows':failures,'bound_failures':bfail,
            'max_mass_violation_kg':float(max((v for v,r in zip(violations,model['rows']) if r['unit']=='kg'),default=Fraction(0))),
            'all_row_and_bound_budgets_met':not failures and not bfail}
    metrics['original_objective']=float(sum((F(float(v['cost']))*x for x,v in zip(raw,model['variables'])),Fraction(0)))
    metrics['maximum_raw_integer_distance']=max((float(abs(x-round(float(x)))) for x,v in zip(raw,model['variables']) if v['integer']),default=0.)
    metrics['primal_accepted']=metrics['integer_rounded']['all_row_and_bound_budgets_met']
    metrics['optimality_status']='unverified'
    return metrics,raw,rounded


def csvwrite(path, rows):
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def main():
    design=json.loads((HERE/'pilot/design.json').read_text())
    assert hashlib.sha256((HERE/'generalization_study.py').read_bytes()).hexdigest()==design['source_sha256']
    factor_count=0;incompatible_count=0;checked=0;diagnostics=[];certificates=[]
    for item in design['models']:
        folder=HERE/'pilot/models'/item['name'];model=json.loads((folder/'original-model.json').read_text())
        factors=json.loads((folder/'factors.json').read_text())
        for policy,alphas in factors.items():
            for alpha,row in zip(alphas,model['rows']):
                values=[F(float(v)) for v in row['terms'].values() if v]
                reserve=F(float(item['guided_gamma']))*sum((abs(F(float(v))) for i,v in row['terms'].items()
                    if model['variables'][int(i)]['integer']),Fraction(0)) if policy.startswith('Budget') and item['guided_gamma'] else Fraction(0)
                lower=F(1e-9)/min(abs(v) for v in values);upper=F(1e9)/max(abs(v) for v in values)
                if policy.startswith('Budget') and reserve<F(float(row['budget'])):
                    lower=max(lower,F(1e-6)/(F(float(row['budget']))-reserve))
                if alpha is None:
                    assert reserve>=F(float(row['budget'])) or lower>upper
                    certificates.append({'model':item['name'],'policy':policy,'original_row':row['name'],
                        'coefficient_minimum':str(min(abs(v) for v in values)),
                        'coefficient_maximum':str(max(abs(v) for v in values)),
                        'epsilon':str(F(1e-6)),'original_row_budget':str(F(float(row['budget']))),
                        'rounding_reserve':str(reserve),'exact_lower_endpoint':str(lower),
                        'exact_upper_endpoint':str(upper),
                        'lower_strictly_above_upper':lower>upper,
                        'scope':'conditional factor specification; not MILP infeasibility or a prediction of an inaccurate returned point'})
                    incompatible_count+=1;continue
                q=F(float(alpha))
                assert q>0 and all(F(float(alpha*float(c)))==q*F(float(c)) for c in (*row['terms'].values(),row['rhs']))
                if policy!='Base':assert lower<=q<=upper
                factor_count+=1
        for path in sorted((HERE/'pilot/runs'/item['name']).glob('*/run.json')):
            record=json.loads(path.read_text())
            if not record['has_point']:continue
            with np.load(path.parent/'solution.npz',allow_pickle=False) as saved:metrics,raw,rounded=check_point(model,saved['x'])
            assert metrics==json.loads((path.parent/'verification.json').read_text())
            assert record['primal_accepted']==metrics['primal_accepted'];checked+=1
            if metrics['primal_accepted']:
                for x,v in zip(rounded,model['variables']):
                    if v['integer']:
                        assert x.denominator==1
                        assert v['lower'] is None or x>=F(float(v['lower']))
                        assert v['upper'] is None or x<=F(float(v['upper']))
            source='Dyadic-L2' if record['policy'].startswith('Dyadic-L2-') else record['policy']
            alpha=factors[source];parameters=record['parameters']
            gamma=float(parameters['IntFeasTol' if record['solver']=='gurobi' else 'mip_feasibility_tolerance'])
            epsilon=float(parameters['FeasibilityTol' if record['solver']=='gurobi' else 'mip_feasibility_tolerance'])
            mu=[];mu_round=[];failed_hypotheses=0
            for r,a in zip(model['rows'],alpha):
                delta=F(float(r['budget']));raw_ratio=F(epsilon)/F(float(a))/delta
                integer_sum=sum((abs(F(float(c))) for i,c in r['terms'].items() if model['variables'][int(i)]['integer']),Fraction(0))
                mu.append(raw_ratio);mu_round.append(raw_ratio+F(gamma)*integer_sum/delta)
                failed_hypotheses+=F(float(a))*row_violation(r,raw)>F(epsilon)
            integer_hyp=max((abs(v-round(float(v))) for v,d in zip(raw,model['variables']) if d['integer']),default=Fraction(0))<=F(gamma)
            if max(mu_round)<=1 and not failed_hypotheses and integer_hyp:
                assert not metrics['integer_rounded']['failed_rows']
            diagnostics.append({'model':item['name'],'solver':record['solver'],'policy':record['policy'],
                'mu_nominal_raw':float(max(mu)), 'mu_nominal_rounded':float(max(mu_round)),
                'observed_exported_hypothesis_failures':failed_hypotheses,'integer_hypothesis_met':integer_hyp,
                'raw_budget_met':metrics['raw']['all_row_and_bound_budgets_met'],
                'rounded_budget_met':metrics['primal_accepted'],
                'max_raw_budget_ratio':metrics['raw']['maximum_row_budget_ratio'],
                'max_rounded_budget_ratio':metrics['integer_rounded']['maximum_row_budget_ratio'],
                'max_mass_kg':metrics['integer_rounded']['max_mass_violation_kg']})
    assert checked==52
    csvwrite(HERE/'pilot/pre-solve-indicators.csv',diagnostics)
    (HERE/'pilot/incompatibility-certificates.json').write_text(json.dumps(certificates,indent=2)+'\n')
    result={'saved_points_independently_rechecked':checked,'exact_factor_records_checked':factor_count,
        'continuous_interval_incompatibilities_rechecked':incompatible_count,
        'unsupported_rounding_guarantee_but_observed_budget_met':sum(float(r['mu_nominal_rounded'])>1 and r['rounded_budget_met'] for r in diagnostics),
        'accepted_primal_points':sum(r['rounded_budget_met'] for r in diagnostics),
        'raw_budget_compliant_points':sum(r['raw_budget_met'] for r in diagnostics),
        'accepted_integer_domains_checked_exactly':True,
        'solver_calls':0,'scope':'original binary64 primal numerical budgets; no global optimality or bound certificate'}
    (HERE/'pilot/independent-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
