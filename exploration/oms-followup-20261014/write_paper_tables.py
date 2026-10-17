#!/usr/bin/env python3
"""Compact main-text and supplementary tables from independently replayed data."""
import csv
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def main():
    rows=list(csv.DictReader((HERE/'verified-summary.csv').open()))
    lookup={(r['phase'],r['policy']):r for r in rows}
    labels={'GM':'GM','L2-matched-int':'L2, matched $\\gamma$',
        'Budget-L2':'Budget-L2','L2-global-tight':'L2, global tight',
        'L2-PresolveOff':'L2, presolve off','L2-NumericFocus3':'L2, NumericFocus 3',
        'L2-dyadic':'L2, dyadic','Budget-dyadic':'Budget-L2, dyadic',
        'GM-IntFocus':'GM, IntegralityFocus','GM-tight-M':'GM, tight $M$',
        'GM-indicators':'GM, indicators','Base':'Base','Ruiz-R4':'Ruiz-R4'}

    def table(selected):
        lines=[r'\begin{tabular}{lrrrrr}',r'\toprule',
            r'Policy & Calls & Budgets & $B>U$ & Gap flags & Work\\',r'\midrule']
        for phase,policy in selected:
            row=lookup[phase,policy]
            bounds=row['bound_contradictions'] if int(row['exact_witness_available']) else '--'
            gaps=row['completion_contradictions'] if int(row['exact_witness_available']) else '--'
            lines.append(f"{labels[policy]} & {row['runs']} & {row['rounded_budget_met']} & {bounds} & {gaps} & {float(row['geomean_work']):.3f}\\\\")
        lines.extend([r'\bottomrule',r'\end{tabular}'])
        return '\n'.join(lines)+'\n'
    folder=ROOT/'paper/tables'
    (folder/'activation-bank.tex').write_text(table([('confirmation-bank',p) for p in ('GM','L2-matched-int','Budget-L2','L2-global-tight')]))
    (folder/'activation-controls.tex').write_text(table([('confirmation-mechanism',p) for p in
        ('Base','Ruiz-R4','L2-PresolveOff','L2-NumericFocus3','L2-dyadic','Budget-dyadic','GM-IntFocus','GM-tight-M','GM-indicators')]))
    (folder/'activation-fresh-seeds.tex').write_text(table([
        ('presolve-off-followup','L2-matched-int'),('presolve-off-followup','Budget-L2'),
        ('presolve-off-global-tight','L2-global-tight')]))
    lines=[r'\begin{tabular}{lrrrrr}',r'\toprule',
        r'Policy & Calls & Max. $v_V$ (m$^3$) & $B>U$ & Gap flags & Work\\',r'\midrule']

    def residual(value):
        value=float(value)
        if value==0:
            return '0'
        if value>=1:
            return f'{value:,.3f}'
        mantissa,exponent=f'{value:.3e}'.split('e')
        return f'${mantissa}\\times10^{{{int(exponent)}}}$'

    panels=[
        ('Six models; seeds 1, 7, 42; automatic presolve',
         [('confirmation-bank',p) for p in ('GM','L2-matched-int','Budget-L2','L2-global-tight')]),
        ('instance046; fresh seeds 11, 23, 47; presolve off',
         [('presolve-off-followup','L2-matched-int'),('presolve-off-followup','Budget-L2'),
          ('presolve-off-global-tight','L2-global-tight')]),
        ('instance046; seeds 1, 7, 42; automatic presolve',
         [('confirmation-mechanism','L2-NumericFocus3')])]
    for panel,selected in panels:
        lines.append(r'\multicolumn{6}{l}{\emph{'+panel+r'}}\\')
        for phase,policy in selected:
            row=lookup[phase,policy]
            assert int(row['exact_witness_available'])==int(row['runs'])
            lines.append(f"{labels[policy]} & {row['runs']} & {residual(row['maximum_rounded_activation_m3'])} & "
                f"{row['bound_contradictions']} & {row['completion_contradictions']} & {float(row['geomean_work']):.3f}\\\\")
        lines.append(r'\midrule')
    lines[-1]=r'\bottomrule'
    lines.append(r'\end{tabular}')
    (folder/'activation-summary.tex').write_text('\n'.join(lines)+'\n')
    lines=[r'\begin{tabular}{lrrrrr}',r'\toprule',
        r'Scenario & $\delta_V$ (m$^3$) & $\gamma$ & Changed rows & Budgets & Gap flags\\',r'\midrule']
    for tag,water,path,phase in (('Demanding',100,'confirmation-bank','confirmation-bank'),
        ('Reference',1000,'sensitivity-reference','sensitivity-reference'),
        ('Permissive',10000,'sensitivity-permissive','sensitivity-permissive')):
        design=json.loads((HERE/path/'design.json').read_text())
        item=next(i for i in design['prepared'] if i['instance']=='instance046')
        if tag=='Demanding':
            data=[r for r in csv.DictReader((HERE/'verified-runs.csv').open())
                  if r['phase']==phase and r['instance']=='instance046' and r['policy']=='Budget-L2']
            passed=sum(r['rounded_budget_met']=='True' for r in data)
            flags=sum(r['completion_contradiction']=='True' for r in data)
        else:
            r=lookup[phase,'Budget-L2'];passed=int(r['rounded_budget_met']);flags=int(r['completion_contradictions'])
        exponent=round(__import__('math').log2(item['guided_gamma']))
        lines.append(f"{tag} & {water:,} & $2^{{{exponent}}}$ & {item['budget_changed_rows']:,} & {passed}/3 & {flags}/3\\\\")
    lines.extend([r'\bottomrule',r'\end{tabular}'])
    (folder/'activation-sensitivity.tex').write_text('\n'.join(lines)+'\n')
    print('Five compact activation tables written from verified records')


if __name__=='__main__':main()
