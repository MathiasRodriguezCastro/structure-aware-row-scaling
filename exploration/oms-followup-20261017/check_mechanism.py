"""Derive the activation-factor path directly from original and written rows."""
import csv
from fractions import Fraction
import json
import math
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'scripts/research')]
from audit_identifiability_grid import parse
from audit_fixed_basis import read_lp
F=Fraction.from_float
FRONT=ROOT/'exploration/oms-frontier-20261016'
ACT=re.compile(r'a\d+_activacion_[1-4]\(\d+\)')

def up(q):
    v=float(q)
    return math.nextafter(v,math.inf) if F(v)<q else v
def numbers(row):return row['sense'],float(row['rhs']),{n:float(v) for n,v in row['terms'].items()}

def main():
    design=json.loads((FRONT/'design.json').read_text());count=changed=unchanged=blocked=0;thresholds=[]
    for instance in design['instances']:
        folder=FRONT/'models'/instance
        base,_=parse(folder/'Base.lp');l2,_=parse(folder/'L2.lp');_,lp,_=read_lp(folder/'Base.lp')
        boxes={n:max(abs(float(l)),abs(float(u))) for n,l,u in zip(lp.col_names_,lp.col_lower_,lp.col_upper_)}
        integers={n for n,k in zip(lp.col_names_,lp.integrality_) if str(k)!='HighsVarType.kContinuous'}
        for budget in design['volume_budgets']:
            entry=design['models'][instance+'/B'+str(budget)]
            actual=parse(ROOT/entry['model'])[0] if entry['model'] else None
            bad=0
            for n,r in base.items():
                if not ACT.fullmatch(n):
                    if actual is not None:assert numbers(actual[n])==numbers(l2[n]);unchanged+=1
                    continue
                assert len(r['terms'])==2
                storage=next(j for j,v in r['terms'].items() if float(v)==-1)
                binary=next(j for j in r['terms'] if j!=storage);assert binary in integers and storage not in integers
                E=F(1e-9)*F(float(r['terms'][binary]))
                rho=F(2.**-52)*(sum((abs(F(float(v)))*F(boxes[j]) for j,v in r['terms'].items()),Fraction(0))+abs(F(float(r['rhs']))))
                reserve=F(up(E+rho));alpha0=-float(l2[n]['terms'][storage]);assert alpha0==1e-9
                if budget==100:thresholds.append(float(reserve+F(1e-6)/F(alpha0)))
                if F(float(budget))<=reserve:bad+=1;blocked+=1;continue
                if actual is None:continue
                expected=up(max(F(alpha0),F(1e-6)/(F(float(budget))-reserve)))
                alpha=-float(actual[n]['terms'][storage]);assert alpha==expected
                assert {j:float(v) for j,v in actual[n]['terms'].items()}=={j:alpha*float(v) for j,v in r['terms'].items()}
                assert float(actual[n]['rhs'])==alpha*float(r['rhs'])
                assert F(1e-6)/F(alpha)+reserve<=F(float(budget))
                count+=1;changed+=alpha!=alpha0
            assert bad==entry['incompatible_count']
    result={'activation_factors_directly_verified':count,'changed_activation_factors':changed,
        'incompatible_activation_intervals':blocked,'unchanged_nonactivation_rows_checked':unchanged,
        'independent_formula':'ceil_binary64(max(alpha_L2, epsilon/(delta-ceil_binary64(E+rho))))',
        'L2_budget_switch_threshold_range_m3':[min(thresholds),max(thresholds)],
        'optimizer_calls':0,'driver_or_selector_imported':False,'internal_solver_cause_identified':False}
    (HERE/'mechanism/INDEPENDENT_VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
