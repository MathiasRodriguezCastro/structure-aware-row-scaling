"""Exhaustive integer-radius oracle and coherent-unit checks; no optimizer."""
from fractions import Fraction
import copy
import json
from pathlib import Path
import random
import method

F=Fraction.from_float
rng=random.Random(1710197)
checked=0;covariant=0;clipped=0
for trial in range(200):
    group=[{'row':i,'M':float(2**rng.randint(2,25)),
            'g':{'0':float(2.**rng.randint(-8,8)),'1':float(2.**rng.randint(-8,8))},
            'delta':1e-6} for i in range(rng.randint(1,5))]
    low=rng.randint(-20,10);high=rng.randint(low,40)
    q=[F(g['M'])**2/sum((F(c)**2 for c in g['g'].values()),Fraction(0)) for g in group]
    def score(r):return max(max(q)/Fraction(2)**(2*r),Fraction(2)**(2*r)/min(q)),r
    chosen,_=method.center(group,low,high)
    assert chosen==min(range(low,high+1),key=score);checked+=1
    free,_=method.center(group)
    clipped+=chosen!=free
    transformed=copy.deepcopy(group)
    for g in transformed:
        k=rng.randint(-20,20);g['M']*=2.**k;g['delta']*=2.**k
        g['g']={j:c*2.**k for j,c in g['g'].items()}
    assert method.center(transformed,low,high)==method.center(group,low,high);covariant+=1
    if trial<50:
        selected=method.radius(group,'Centered-shared',1e-6,1e-5)
        assert selected['compatible']
        for g,d in zip(group,selected['decisions']):
            assert F(d['h'])*F(selected['radius'])==F(g['M'])
            assert Fraction(d['bound'])<=F(g['delta'])
result={'exhaustive_interval_minimizations':checked,'mixed_row_unit_covariance_checks':covariant,
        'center_clipped_cases':clipped,'complete_contract_decisions_checked':50,
        'optimizer_calls':0}
(Path(__file__).parent/'TESTS.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
