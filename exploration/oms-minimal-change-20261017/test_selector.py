"""Positive-radius and bound-budget obstruction checks by direct enumeration."""
from fractions import Fraction
import json
from pathlib import Path

import selector

F=Fraction.from_float
HERE=Path(__file__).resolve().parent


def main():
    model={'rows':{'r':{'terms':{'z':2.**40,'x':-2.**-30},'rhs':0.,'sense':'<='}},
           'columns':['z','x'],'integers':{'z'},'costs':{'z':0.,'x':0.},
           'bounds':{'z':(0.,1.),'x':(0.,2.**30)},'delta':{'r':Fraction(2)**30},
           'E':{'r':F(1e-9)*Fraction(2)**40}}
    pairs=[]
    for v in range(-20,21):
        for u in range(-60,61):
            terms=[Fraction(2)**(40+u),Fraction(2)**(-30+u+v)]
            if min(terms)<F(1e-9) or max(terms)>F(1e9):continue
            if F(1e-6)/(Fraction(2)**u)+model['E']['r']>model['delta']['r']:continue
            pairs.append((abs(v),u,v))
    minimum=min(p[0] for p in pairs)
    got=selector.select(model)
    assert minimum==12 and got['compatible'] and got['radius']==minimum
    assert (got['radius'],got['u']['r'],got['v']['x']) in pairs
    blocked=selector.select(model,{'x':1e-6*2.**11})
    assert not blocked['compatible']
    cert=blocked['certificate'];edges=[cert['edges'][i] for i in cert['result']['negative_cycle']]
    assert sum(e[2] for e in edges)<0
    assert not any(p[2]<=11 for p in pairs)
    result={'constructed_positive_radius':minimum,'independently_enumerated_pairs':len(pairs),
            'bound_budget_obstruction_checked':True,'optimizer_calls':0,
            'phase_note':'constructed tests completed after the saved real-case opportunity diagnosis'}
    (HERE/'STATIC_TESTS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
