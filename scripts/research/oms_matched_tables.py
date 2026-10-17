#!/usr/bin/env python3
"""Regenerate the definitive main comparison and supplementary diagnostic panels."""
import csv
from pathlib import Path
import runpy
import shutil

ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'exploration/oms-matched-accuracy-20261016'
runpy.run_path(str(HERE/'write_report.py'),run_name='__main__')
for name in ('matched-accuracy.tex','matched-cases.tex'):
    shutil.copyfile(HERE/name,ROOT/'paper/tables'/name)
summary=list(csv.DictReader((HERE/'verified-summary.csv').open()))
lines=[r'\begin{tabular}{llrrrrr}',r'\toprule',
    r'Presolve & Policy & Budgets & $B>U$ & Gap flags & Work & Total (s)\\',r'\midrule']
# Seven columns; all policies have 18 terminal comparisons per presolve setting.
for i,s in enumerate(summary):
    if i==4:lines.append(r'\midrule')
    lines.append(' & '.join(['Auto' if int(s['presolve'])==-1 else 'Off',s['policy'],
        s['budgets_pass']+'/18',s['bound_contradictions'],s['completion_contradictions'],
        f"{float(s['geometric_mean_work']):.3f}",f"{float(s['median_total_seconds']):.3f}"])+r'\\')
lines.extend([r'\bottomrule',r'\end{tabular}'])
(ROOT/'paper/tables/matched-main.tex').write_text('\n'.join(lines)+'\n')
