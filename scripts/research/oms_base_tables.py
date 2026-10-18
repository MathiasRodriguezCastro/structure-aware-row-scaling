#!/usr/bin/env python3
"""Tables for the directed unscaled-control audit; all numbers from saved replay."""
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'exploration/oms-base-control-20261018'


def table(name,columns,header,rows):
    (ROOT/'paper/tables'/name).write_text('\n'.join([
        r'\begin{tabular}{'+columns+'}',r'\toprule',header+r'\\',r'\midrule',
        *[' & '.join(r)+r'\\' for r in rows],r'\bottomrule',r'\end{tabular}'])+'\n')


def main():
    d=json.loads((HERE/'VALIDATION.json').read_text())
    old=list(csv.DictReader((ROOT/'exploration/oms-frontier-20261016/verified-summary.csv').open()))
    base={r['policy']:r for r in d['results'] if r['budget']==100}
    rows=[]
    for p in ['Base','Base-tight','L2','L2-tight','L2-NF3','Budget-L2']:
        budgets=[30,100] if p=='Budget-L2' else [100]
        for b in budgets:
            if p in ['Base','Base-tight','Budget-L2']:
                r=next(v for v in d['results'] if v['budget']==b and v['policy']==p)
                calls=r['calls'];passed=r['budgets_passed'];bf=r['bound_flags'];gf=r['completion_flags'];work=r['gm_work']
            else:
                r=next(v for v in old if v['budget']==str(b) and v['presolve']=='-1' and v['policy']==p)
                calls=int(r['calls']);passed=int(r['budgets_passed']);bf=int(r['bound_flags']);gf=int(r['gap_flags']);work=float(r['geometric_work'])
                r30=next(v for v in old if v['budget']=='30' and v['presolve']=='-1' and v['policy']==p)
                assert r30['budgets_passed']==r['budgets_passed']
            rows.append([p,str(b) if p=='Budget-L2' else '30, 100',f'{passed}/{calls}',f'{bf}/{gf}',
                f'{work:.3f}',f"{work/base['Base']['gm_work']:.3f}",f"{work/base['Base-tight']['gm_work']:.3f}"])
    table('base-controls-main.tex','lrrrrrr',
        r'Policy & $\delta_V$ & Budgets & B/G & Work & $W/W_{\rm Base}$ & $W/W_{\rm Base\text{-}tight}$',rows)
    rows=[]
    for r in d['paired_comparisons']:
        rows.append(['Initial',str(r['budget']),r['control'],f"{r['both_budgets_pass']}/18",
            f"{r['gm_work_ratio']:.3f}",'---',f"{r['max_cost_deterioration_percent']:.4f}"])
    conf=HERE/'confirmation/VALIDATION.json'
    if conf.exists():
        c=json.loads(conf.read_text())
        paired=list(csv.DictReader((HERE/'confirmation/pairs.csv').open()))
        for r in c['paired']:
            both=sum(p['both_budgets_pass']=='True' for p in paired if p['control']==r['control'])
            rows.append(['Interleaved','100',r['control'],f"{both}/18",
                f"{r['paired_work_ratio']:.3f}",f"{r['paired_full_time_ratio']:.3f}",f"{r['max_cost_deterioration_percent']:.4f}"])
    table('base-controls-supplement.tex','llrrrrr',
        r'Stage & $\delta_V$ & Control & Both pass & $W_{\rm B}/W_{\rm C}$ & $T_{\rm B}/T_{\rm C}$ & Max cost (\%)',rows)


if __name__=='__main__':
    main()
