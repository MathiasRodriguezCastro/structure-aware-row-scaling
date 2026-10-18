"""Small exhaustive mathematics and exact unit-conversion tests, without solvers."""
from fractions import Fraction
import copy
import importlib.util
import json
from pathlib import Path
import random

import activity as a

HERE=Path(__file__).resolve().parent
F=Fraction.from_float


def brute_row(g,r):
    R=Fraction(2)**r;h=F(float(g['M']))/R
    try:hh=float(h)
    except OverflowError:return False
    if F(hh)!=h or R>F(1e19):return False
    values=[abs(F(float(v))) for v in g['g'].values()]+[h]
    for u in range(-100,101):
        alpha=Fraction(2)**u
        if min(values)*alpha<F(1e-9) or max(values)*alpha>F(1e9):continue
        if F(1e-6)/alpha+h*F(1e-5)>F(float(g['delta'])):continue
        if all(F(float(v*alpha))==v*alpha for v in values):return True
    return False


def main():
    cases=[]
    for M in (2.**8,2.**24):
        for delta in (1e-4,1e-8):
            cases.append([{'row':0,'z':0,'M':M,'delta':delta,'g':{'1':1.,'2':-2.**-4}},
                          {'row':1,'z':0,'M':2*M,'delta':2*delta,'g':{'1':2.,'2':-2.**-3}}])
    exhaustive=0
    for group in cases:
        result=a.select_shared(group)
        feasible=[r for r in range(-10,46) if all(brute_row(g,r) for g in group)]
        assert bool(feasible)==result['compatible']
        if feasible:assert result['r']==min(feasible)
        exhaustive+=1
    spec=importlib.util.spec_from_file_location('prior_enumerative_activity',HERE/'activity-before-closed-form.py')
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    randomizer=random.Random(1700181);random_cases=0;covariance=0
    for i in range(200):
        group=[]
        for j in range(randomizer.randint(1,4)):
            group.append({'row':j,'z':0,'M':2.**randomizer.randint(-10,40),
                          'delta':2.**randomizer.randint(-35,10),
                          'g':{'1':2.**randomizer.randint(-20,20),'2':-2.**randomizer.randint(-20,20)}})
        new=a.select_shared(group);ref=old.select_shared(group)
        assert new['compatible']==ref['compatible']
        if new['compatible']:
            assert new['radius']==ref['radius'] and new['decisions']==ref['decisions']
            converted=copy.deepcopy(group);exponents=[]
            for g in converted:
                k=randomizer.choice((-20,-10,0,10,20));exponents.append(k)
                g['M']*=2.**k;g['delta']*=2.**k;g['g']={v:c*2.**k for v,c in g['g'].items()}
            changed=a.select_shared(converted)
            assert changed['compatible'] and changed['radius']==new['radius']
            for g,h,k in zip(new['decisions'],changed['decisions'],exponents):
                assert h['h']==g['h']*2.**k and h['alpha']==g['alpha']*2.**(-k)
                assert F(h['h'])*F(h['alpha'])==F(g['h'])*F(g['alpha'])
            covariance+=1
        random_cases+=1
    projections=0
    for z in (0,1):
        for R in (Fraction(1,8),Fraction(8),Fraction(1024)):
            for g1 in (-32,-1,0,1,8,16,32):
                for g2 in (-64,-1,0,1,16,32,64):
                    y=max(Fraction(0),Fraction(g1)*R/16,Fraction(g2)*R/32)
                    old=g1<=16*z and g2<=32*z
                    lifted=0<=y<=R and (z==1 or y==0)
                    assert old==lifted;projections+=1
    result={'exhaustive_group_cases':exhaustive,'random_comparisons_with_enumerative_selector':random_cases,
            'independent_row_unit_covariance_cases':covariance,'shared_projection_checks':projections,'optimizer_calls':0}
    (HERE/'STATIC_TESTS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
