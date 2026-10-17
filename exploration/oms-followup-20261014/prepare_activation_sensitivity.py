#!/usr/bin/env python3
"""Existing reference/permissive precision scenarios; no outcome-tuned budgets."""
import csv
from fractions import Fraction
import json
import math
from pathlib import Path
import shutil

import activation_study as study

HERE=Path(__file__).resolve().parent
BANK=HERE/'confirmation-bank'
F=Fraction.from_float


def main():
    for tag,power,water in (('Reference',.1,1000.),('Permissive',1.,10000.)):
        out=HERE/('sensitivity-'+tag.lower())
        assert not out.exists();out.mkdir()
        design=json.loads((BANK/'design.json').read_text())
        design.update(phase='post-hoc preset precision sensitivity',policies=['Budget-L2'],
            instances=[i for i in design['instances'] if i['instance']=='instance046'],
            prepared=[i for i in design['prepared'] if i['instance']=='instance046'],
            budgets={'MW':power,'m3':water},budget_scenario=tag,
            trigger='Sensitivity on the same independently predeclared precision scenarios; compare accuracy and reported quality, retaining negative outcomes.')
        folder=out/'models/instance046';shutil.copytree(BANK/'models/instance046',folder)
        parsed,physical=study.original_rows(folder/'Base.lp')
        original=study.campaign.afb.read_lp(folder/'Base.lp');_,lp,_=original
        integers={n for n,k in zip(lp.col_names_,lp.integrality_) if str(k)!='HighsVarType.kContinuous'}
        boxes={n:max(abs(float(lo)),abs(float(hi))) for n,lo,hi in zip(lp.col_names_,lp.col_lower_,lp.col_upper_)}
        maximum=max(study.activation_spec(n,r)[2] for n,r in parsed.items() if study.ACT.fullmatch(n))
        gamma=min(1e-5,math.ldexp(1.,math.floor(math.log2(water/(2*maximum)))))
        decisions=list(csv.DictReader((folder/'decisions.csv').open()));factors={r['row']:float(r['l2_window_factor']) for r in decisions}
        for record in decisions:
            name=record['row']
            record['budget_factor']=factors[name];record['changed_by_budget']=False
            if name not in physical:continue
            row=physical[name];delta=design['budgets'][row['unit']]*row['conversion']
            e=F(gamma)*sum((F(abs(float(v))) for n,v in row['terms'].items() if n in integers),Fraction(0))
            d=Fraction(0)
            if study.ACT.fullmatch(name):d=F(2.**-52)*(sum((F(abs(float(v)))*F(boxes[n]) for n,v in row['terms'].items()),Fraction(0))+F(abs(float(row['rhs']))))
            reserve=float(e+d)
            if F(reserve)<e+d:reserve=math.nextafter(reserve,math.inf)
            selected=study.select_factor(list(row['terms'].values()),delta,kernel='l2',rounding_allowance=reserve)
            assert selected.factor is not None
            record.update(budget_factor=selected.factor,rounding_reserve=float(e),finite_export_reserve=float(d),changed_by_budget=selected.factor!=factors[name])
            factors[name]=selected.factor
        study.csvwrite(folder/'decisions.csv',decisions)
        study.export_scaled(folder/'Base.lp',folder/'Budget-L2.lp',factors)
        study.campaign.afb.check_scaling(original,study.campaign.afb.read_lp(folder/'Budget-L2.lp'),folder/'Budget-L2-factors.csv')
        prepared=design['prepared'][0];prepared.update(guided_gamma=gamma,budget_changed_rows=sum(r['changed_by_budget'] for r in decisions))
        prepared['exports']['Budget-L2']=study.sha(folder/'Budget-L2.lp')
        study.dump(out/'design.json',design);shutil.copy2(BANK/'source-snapshot.py',out/'source-snapshot.py')
        print(tag,'gamma',gamma,'changed factors',prepared['budget_changed_rows'],flush=True)


if __name__=='__main__':main()
