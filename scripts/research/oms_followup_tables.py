"""Compact OMS tables from the independently replayed 17 October follow-up."""
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'exploration/oms-followup-20261017'
def table(name,header,rows,columns):
    lines=[r'\begin{tabular}{'+columns+'}',r'\toprule',header+r'\\',r'\midrule',*[' & '.join(row)+r'\\' for row in rows],r'\bottomrule',r'\end{tabular}']
    (ROOT/'paper/tables'/name).write_text('\n'.join(lines)+'\n')

def main():
    d=json.loads((HERE/'external/VALIDATION.json').read_text());rows=[]
    totals={p:0 for p in ['L2','Budget-L2','L2-tight','L2-NF3']}
    for r in d['summary']:
        line=[r['instance'].replace('Kondili-H',''),str(r['changed_factors'])]
        for p in totals:
            n=r[p+'_primal_passes'];totals[p]+=n;line.append(str(n)+'/3')
        rows.append(line)
    rows.append(['All',str(d['contract_changed_factors']),*[str(totals[p])+'/24' for p in totals]])
    table('external-transfer.tex',r'Horizon & Changed rows & L2 & Budget-L2 & L2-tight & L2-NF3',rows,'lrrrrr')
    d=json.loads((HERE/'tolerance/VALIDATION.json').read_text());rows=[]
    for r in d['summary']:
        n=r['calls'];rows.append([r'$10^{-9}$' if r['gamma']==1e-9 else r'$2^{-28}$',str(r['budget']),str(n)+'/18',str(r['abstentions']),
            str(r['primal_passes'])+'/'+str(n) if n else '--',str(r['bound_flags'])+'/'+str(r['gap_flags']) if n else '--',
            f"{r['work_ratio_to_NF3']:.3f}" if n else '--'])
    table('integer-tolerance.tex',r'IntFeasTol & $\delta_V$ & Calls & Abstentions & Budgets & B/G & $W/W_{\rm NF3}$',rows,'rrrrrrr')
    d=json.loads((HERE/'native-cycle/VALIDATION.json').read_text());rows=[]
    for r in d['summary']:
        rows.append([r['instance'].replace('instance',''),f"{r['python_geometric_seconds']:.3f}",f"{r['cpp_geometric_seconds']:.3f}",f"{r['cpp_to_python_full_time_ratio']:.3f}"])
    rows.append(['All 18 pairs','--','--',f"{d['cpp_to_python_full_time_ratio']:.3f}"])
    table('native-cycle-cost.tex',r'Model & Python (s) & C++ (s) & C++/Python time',rows,'lrrr')

if __name__=='__main__':main()
