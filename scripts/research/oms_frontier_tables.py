#!/usr/bin/env python3
"""Small final tables from independently replayed, fixed sensitivity results."""
import csv
import json
import math
from pathlib import Path
import statistics

ROOT=Path(__file__).resolve().parents[2]
FRONT=ROOT/'exploration/oms-frontier-20261016'
def gm(values):return math.exp(statistics.mean(math.log(x) for x in values))
def table(name,header,rows,columns):
    lines=[r'\begin{tabular}{'+columns+'}',r'\toprule',header+r'\\',r'\midrule',*[' & '.join(row)+r'\\' for row in rows],r'\bottomrule',r'\end{tabular}']
    (ROOT/'paper/tables'/name).write_text('\n'.join(lines)+'\n')

def main():
    summary=list(csv.DictReader((FRONT/'verified-summary.csv').open()))
    runs=list(csv.DictReader((FRONT/'verified-runs.csv').open()))
    rows=[];pairs=[];main_rows=[]
    for p in [-1,0]:
        for b in [10,30,100,300,1000,3000,10000]:
            budget=next(r for r in summary if r['presolve']==str(p) and r['budget']==str(b) and r['policy']=='Budget-L2')
            base=next(r for r in summary if r['presolve']==str(p) and r['budget']==str(b) and r['policy']=='L2')
            nf=next(r for r in summary if r['presolve']==str(p) and r['budget']==str(b) and r['policy']=='L2-NF3')
            rr=[r for r in runs if r['presolve']==str(p) and r['evaluated_volume_budget']==str(b) and r['policy']=='Budget-L2']
            controls={(r['instance'],r['seed']):r for r in runs if r['presolve']==str(p) and r['evaluated_volume_budget']==str(b) and r['policy']=='L2-NF3'}
            work=gm([float(r['work'])/float(controls[r['instance'],r['seed']]['work']) for r in rr])
            seconds=gm([float(r['total_seconds'])/float(controls[r['instance'],r['seed']]['total_seconds']) for r in rr])
            pairs.append({'presolve':p,'budget':b,'pairs':len(rr),'work_ratio':work,'full_time_ratio':seconds})
            rows.append(['Auto' if p==-1 else 'Off',str(b),budget['calls']+'/18',budget['budgets_passed']+'/'+budget['calls'],
                budget['bound_flags']+'/'+budget['gap_flags'],base['bound_flags']+'/'+base['gap_flags'],
                f'{work:.3f}',f'{seconds:.3f}'])
            if p==-1:
                main_rows.append([str(b),budget['calls']+'/18',budget['budgets_passed']+'/'+budget['calls'],
                    budget['bound_flags']+'/'+budget['gap_flags'],f'{work:.3f}',f'{seconds:.3f}'])
    table('precision-frontier.tex',r'Presolve & $\delta_V$ & Calls & Budgets & B/G & L2 B/G & $W/W_{\rm NF3}$ & $T/T_{\rm NF3}$',rows,'lrrrrrrr')
    table('precision-frontier-main.tex',r'$\delta_V$ (m$^3$) & Calls & Budgets & B/G & $W/W_{\rm NF3}$ & $T/T_{\rm NF3}$',main_rows,'rrrrrr')
    native=json.loads((ROOT/'exploration/oms-native-selector-20261016/VALIDATION.json').read_text())
    rows=[]
    for r in native['summary']:
        if r['policy']=='Budget-L2':rows.append([r['instance'].replace('instance',''),f"{r['median_python_seconds']:.3f}",f"{r['median_cpp_seconds']:.3f}",f"{r['preparation_speedup']:.2f}"])
    table('native-selection-cost.tex',r'Model & Python (s) & C++ (s) & Preparation speedup',rows,'lrrr')
    intervals=list(csv.DictReader((ROOT/'exploration/oms-global-lp-20261016/verified-intervals.csv').open()))
    rows=[]
    for r in intervals:
        rows.append([r['instance'].replace('instance',''),f"{float(r['LB_display']):.3f}",f"{float(r['U_display']):.3f}",
            f"{float(r['relative_interval_width_percent']):.3f}",'Exact optimum' if r['MILP_optimum_certified']=='True' else ('Within 1\%' if r['MILP_one_percent_certified']=='True' else 'Interval only')])
    table('global-lp-certificates.tex',r'Model & Global LP $L$ & Integer witness $U$ & Width (\%) & Verified conclusion',rows,'lrrrl')
    with (FRONT/'paired-costs.csv').open('w',newline='') as out:
        w=csv.DictWriter(out,fieldnames=list(pairs[0]));w.writeheader();w.writerows(pairs)

if __name__=='__main__':main()
