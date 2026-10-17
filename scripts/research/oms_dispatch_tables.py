#!/usr/bin/env python3
"""Render the compact OMS tables from verified dispatch summaries."""
import csv
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from oms_dispatch_validation import OUT, ROOT, POLICIES, SCENARIOS

def write(name,text):
    (ROOT/'paper/tables'/name).write_text(text+'\n')

def main():
    summary=json.loads((OUT/'summary.json').read_text())
    physical=list(csv.DictReader((OUT/'physical-verification.csv').open()))
    rows=[]
    for r in summary['comparison']:
        points={}
        for v in physical:
            if v['class']==r['class'] and v['policy']==r['policy']:
                limit=.01 if v['unit']=='MW' else 100.
                points.setdefault(v['instance'],[]).append(float(v['max_original_physical_residual'])<=limit)
        passed=sum(all(v) for v in points.values())
        cls='Simple' if r['class']=='simple' else 'SG-Ter-Mer'
        rows.append(f"{cls} & {r['policy']} & {r['completed']}/15 & {r['geomean_work_ratio']:.3f} & {r['geomean_total_time_ratio']:.3f} & {r['mean_par10_seconds']:.1f} & {r['median_kappa_ratio']:.2g} & {r['median_equilibrated_kappa_ratio']:.2g} & {passed}/15 \\\\")
    common={r['class']:r['common_completed'] for r in summary['comparison']}
    text=r'''\begin{table}[tb]
\centering\scriptsize\setlength{\tabcolsep}{3pt}
\caption{Controlled local comparison. Work and total-time geometric-mean ratios to Base
use the common-completed subset ('''+str(common['simple'])+' Simple and '+str(common['sgtm'])+r''' SG-Ter-Mer).
PAR10 and completion counts use all 15 per class with a 120-second limit.
Condition ratios are medians of paired ratios over all 15 before and after ten
equilibration passes. ``Phys.'' counts saved incumbents meeting the demanding physical
budgets on all declared rows, including incumbents from unfinished runs; it does not
certify MILP optimality. All other original-row, bound and integrality diagnostics
are preserved with the runs.}\label{tab:oms-comparison}
\begin{tabular}{llrrrrrrr}
\toprule
Class & Policy & Done & Work & Time & PAR10 (s) & $\kappa_1$ & Equil. & Phys.\\
\midrule
'''+ '\n'.join(rows)+r'''
\bottomrule\end{tabular}
\end{table}'''
    write('oms-comparison.tex',text)
    rows=[]
    for r in summary['ablation']:
        cls='Simple' if r['class']=='simple' else 'SG-Ter-Mer'
        rows.append(f"{cls} & {r['policy']} & {r['completed']}/3 & {r['common_completed']} & {r['geomean_work_ratio']:.3f} & {r['geomean_total_time_ratio']:.3f} & {r['mean_par10_seconds']:.1f} \\\\")
    write('oms-ablation.tex',r'''\begin{table}[tb]
\centering\small
\caption{Final Role-Hybrid stage ablation on six prospectively selected models.
Work and total-time ratios use the common-completed subset in each class;
completion counts and PAR10 retain all three. Rows are scaled with the final C++
kernels and guards. Base and full-policy calls are shared with
Table~\ref{tab:oms-comparison}.}\label{tab:oms-ablation}
\begin{tabular}{llrrrrr}\toprule
Class & Policy & Done & Paired $n$ & Work & Time & PAR10 (s)\\\midrule
'''+ '\n'.join(rows)+r'''
\bottomrule\end{tabular}\end{table}''')
    rows=[]
    for scenario,(power,water) in SCENARIOS.items():
        members=[r for r in summary['budgets'] if r['scenario']==scenario]
        n=sum(r['rows'] for r in members); admitted=sum(r['admissible'] for r in members)
        changed=sum(r['modified'] for r in members); incompatible=sum(r['incompatible'] for r in members)
        ratio=max(r['max_observed_budget_ratio'] for r in members)
        rows.append(f"{scenario} & {power:g} & {water:,.0f} & {100*admitted/n:.0f}\\% & {changed} & {incompatible} & {ratio:.2g} \\\\")
    write('oms-application-budgets.tex',r'''\begin{table}[tb]
\centering\small\setlength{\tabcolsep}{4pt}
\caption{Application-level precision sensitivity. Each scenario audits 129,600
physical rows per policy (518,400 decisions over the four policies).
``Admiss.'' is the fraction of proposed factors inside the conditional interval;
``Changed'' and ``Incompat.'' count projections and empty intervals.
$\max v/\delta$ is the largest independently observed physical residual-to-budget
ratio over all declared rows and saved incumbents. Budgets are study objectives,
not operator standards.}\label{tab:application-budget}
\begin{tabular}{lrrrrrr}\toprule
Scenario & MW & m\textsuperscript{3} & Admiss. & Changed & Incompat. & $\max v/\delta$\\\midrule
'''+ '\n'.join(rows)+r'''
\bottomrule\end{tabular}\end{table}''')
    print('Regenerated three OMS dispatch tables')

if __name__=='__main__':main()
