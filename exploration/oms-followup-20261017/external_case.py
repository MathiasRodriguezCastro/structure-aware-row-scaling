"""Exact original-unit explanation of the retained STN control failure."""
import json
from fractions import Fraction
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
F=Fraction.from_float
def load(p):return json.loads(p.read_text())
def main():
    out=HERE/'external';name='Kondili-H40';model=load(out/'models'/name/'original-model.json')
    factors=load(out/'models'/name/'factors.json');folder=out/'runs'/f'{name}-L2-NF3-149'
    r=load(folder/'result.json');assert not r['verification']['primal_accepted']
    bad=r['verification']['integer_rounded']['failed_rows'];assert len(bad)==1
    j=bad[0];row=model['rows'][j]
    with np.load(folder/'solution.npz',allow_pickle=False) as p:x=[F(float(v)) for v in p['x']]
    signed=sum((F(float(c))*x[int(i)] for i,c in row['terms'].items()),Fraction(0))-F(float(row['rhs']))
    assert row['sense']=='<' and signed>0 and row['unit']=='kg'
    alpha=factors['L2'][j];budget_alpha=factors['Budget-L2'][j]
    E=F(1e-9)*sum((abs(F(float(c))) for i,c in row['terms'].items() if model['variables'][int(i)]['integer']),Fraction(0))
    assert F(alpha)*signed<=F(1e-6)
    assert F(1e-6)/F(budget_alpha)+E<=F(row['budget'])
    assert r['verification']['maximum_raw_integer_distance']==0
    result={'model':name,'seed':149,'policy':'dyadic L2-NF3','source_row_index':j,'source_row_name':row['name'],
        'terms':[{'source_variable':model['variables'][int(i)]['name'],'coefficient':float(c),'point_coordinate_exact':str(x[int(i)])} for i,c in row['terms'].items()],
        'budget_kg':row['budget'],'original_violation_exact':str(signed),'original_violation_kg':float(signed),
        'original_violation_mg':float(signed*1000000),'budget_mg':row['budget']*1000000,
        'observed_exported_violation_exact':str(F(alpha)*signed),'observed_exported_violation':float(F(alpha)*signed),
        'exported_epsilon':1e-6,'integer_distance':0.,'L2_factor':alpha,'Budget_L2_factor':budget_alpha,
        'contract_bound_kg':float(F(1e-6)/F(budget_alpha)+E),'matched_L2_also_meets_all_24_primal_checks':True,
        'not_a_unique_primal_recovery_over_matched_L2':True,'other_7_reference_bound_checks_unknown':True}
    (out/'EXPLANATORY_CASE.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
