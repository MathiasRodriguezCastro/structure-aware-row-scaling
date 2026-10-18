"""Replay the compact diagnostic using only Python standard-library rationals."""
from fractions import Fraction
import json
from pathlib import Path

F=Fraction.from_float
data=json.loads((Path(__file__).parent/'NONMONOTONICITY_CASE.json').read_text())
ratios=[]
for case in data['cases']:
    row=case['row'];values=case['rounded_sparse_values']
    assert len(case['integer_indices'])==1
    for j,v in case['raw_sparse_values'].items():
        assert values[j]==(round(v) if j in case['integer_indices'] else v)
    assert values[case['integer_indices'][0]] in (0,1)
    residual=sum((F(float(c))*F(float(values[j])) for j,c in row['terms'].items()),Fraction(0))-F(float(row['rhs']))
    error=max(Fraction(0),residual if row['sense']=='<' else -residual)
    assert error==Fraction(case['rounded_violation_exact'])
    assert F(case['h'])*F(case['radius'])==F(case['contracted_M'])
    assert F(case['epsilon'])/F(case['alpha'])+F(case['h'])*max(F(case['gamma_SOS']),F(case['tau']))==Fraction(case['exported_link_budget_bound_exact'])
    assert Fraction(case['exported_link_budget_bound_exact'])<=F(float(row['budget']))
    support=min(abs(F(case['complement_w'])),abs(F(case['auxiliary_y'])))
    assert support==Fraction(case['SOS_support_violation_exact'])
    assert (support<=F(case['gamma_SOS']))==case['SOS_hypothesis_met']
    ratios.append(error/F(float(row['budget'])))
assert ratios[0]<=1 and ratios[1]>1 and ratios[2]<=1
print(json.dumps({'compact_cases_checked':3,'middle_budget_violation_ratio':float(ratios[1]),
                  'middle_SOS_hypothesis_met':data['cases'][1]['SOS_hypothesis_met'],
                  'new_optimizer_calls':0,'certificate_of_optimality':False}))
