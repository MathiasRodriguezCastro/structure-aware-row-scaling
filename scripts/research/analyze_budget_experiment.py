#!/usr/bin/env python3
"""Regenerate descriptive tables and figures from the frozen stress experiment."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd

from budget_scaling import select_factor


PAIRS = [('Budget-GM','GM'), ('Budget-dyadic','Dyadic-GM'), ('Budget-only','GM'),
         ('GM','Base'), ('Budget-only','Base'), ('Budget-GM','Base'), ('Budget-dyadic','Base'),
         ('GM-tight','GM'), ('Budget-only','GM-tight'), ('Budget-only','Budget-GM')]


SOLVER_LABELS = {'highs': 'HiGHS 1.15.1', 'gurobi': 'Gurobi 13.0.2', 'cplex': 'CPLEX 22.1.2'}


def paired_table(d, solvers, tables):
    """Discordant verified outcomes on identical model/presolve/solver keys."""
    key = ['model_id','presolve','solver']
    wide = d.pivot_table(index=key, columns='method', values='rounded_optimal', aggfunc='first')
    head = ' & '.join(r'\multicolumn{2}{c}{%s}' % SOLVER_LABELS[s].split()[0] for s in solvers)
    lines = [r'\begin{tabular}{l' + 'rr'*len(solvers) + '}', r'\toprule', '& ' + head + r' \\',
             r'Comparison $A$ vs $B$ & ' + ' & '.join([r'$A$ only & $B$ only']*len(solvers)) + r' \\',
             r'\midrule']
    counts = {}
    for a, b in PAIRS:
        vals = []
        for solver in solvers:
            w = wide.xs(solver, level='solver')
            only_a, only_b = int((w[a] & ~w[b]).sum()), int((~w[a] & w[b]).sum())
            counts[f'{a} vs {b} ({solver})'] = [only_a, only_b]
            vals += [str(only_a), str(only_b)]
        lines.append(f'{a} vs {b} & ' + ' & '.join(vals) + r' \\')
    lines += [r'\bottomrule', r'\end{tabular}']
    (tables/'budget-paired.tex').write_text('\n'.join(lines)+'\n')
    return counts


def paired_record(d, root, solvers):
    """Per data root: discordance counts and Budget-only/Budget-GM factor distances in ulps."""
    key = ['model_id','presolve','solver']
    wide = d.pivot_table(index=key, columns='method', values='rounded_optimal', aggfunc='first')
    counts = {}
    for a, b in PAIRS:
        for solver in solvers:
            w = wide.xs(solver, level='solver')
            counts[f'{a} vs {b} ({solver})'] = [int((w[a] & ~w[b]).sum()), int((~w[a] & w[b]).sum())]
    fac = d.set_index(key+['method']).factors
    exps = d.drop_duplicates('model_id').set_index('model_id').exponent
    ulp = lambda k: int(np.max(np.rint(np.abs(np.array(json.loads(fac[k+('Budget-GM',)]))
                                             - np.array(json.loads(fac[k+('Budget-only',)])))
                                      / np.spacing(np.array(json.loads(fac[k+('Budget-only',)]))))))
    dist, distinct_exp = [], set()
    for k, row in wide.iterrows():
        if row['Budget-only'] != row['Budget-GM']:
            dist.append(ulp(k)); distinct_exp.add(int(exps[k[0]]))
    binding = [ulp(k) for k in wide.index if exps[k[0]] >= 6]
    out = dict(discordant_counts=counts,
               budget_only_vs_budget_gm=dict(discordant_configurations=len(dist),
                   max_factor_ulp_distance_on_discordant=max(dist) if dist else None,
                   exponents_with_discordant_outcomes=sorted(distinct_exp),
                   max_factor_ulp_distance_for_exponent_6_and_9=max(binding)))
    (root/'paired-discordance.json').write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps(out, indent=2))


def load(root):
    d = pd.read_csv(root/'runs.csv')
    d['abstained'] = d.status.eq('ABSTAIN')
    d['submitted'] = ~d.abstained
    d['failed_output'] = (~d.rounded_optimal) & d.submitted
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, default=Path('results-revision/research-audit/budget-final'))
    ap.add_argument('--figures', type=Path, default=Path('paper/figs/research'))
    ap.add_argument('--tables', type=Path, default=Path('paper/tables'))
    ap.add_argument('--classical-root', type=Path, default=Path('results-revision/research-audit/exploration-lattice'))
    ap.add_argument('--extra-root', type=Path, action='append', default=[],
                    help='additional solver arm on the same stored models (e.g. CPLEX)')
    ap.add_argument('--extra-classical-root', type=Path, action='append', default=[])
    args = ap.parse_args()
    args.figures.mkdir(parents=True, exist_ok=True)
    args.tables.mkdir(parents=True, exist_ok=True)
    d = load(args.root)
    summary = d.groupby(['solver','method'],sort=False).agg(n=('status','size'),
                 attempted=('submitted','sum'), abstained=('abstained','sum'),
                 exact_optimal=('rounded_optimal','sum'), failed=('failed_output','sum'))
    summary.to_csv(args.root/'summary.csv')
    paired_record(d, args.root, sorted(set(d.solver), key=list(SOLVER_LABELS).index))
    parts = [d]
    for extra in args.extra_root:
        e = load(extra)
        e.groupby(['solver','method'],sort=False).agg(n=('status','size'), attempted=('submitted','sum'),
            abstained=('abstained','sum'), exact_optimal=('rounded_optimal','sum'),
            failed=('failed_output','sum')).to_csv(extra/'summary.csv')
        paired_record(e, extra, sorted(set(e.solver), key=list(SOLVER_LABELS).index))
        parts.append(e)
    d = pd.concat(parts, ignore_index=True)
    solvers = [s for s in SOLVER_LABELS if s in set(d.solver)]
    paired_table(d, solvers, args.tables)
    methods = ['Base','GM','L2','GM-tight','Dyadic-GM','Budget-only','Budget-GM','Budget-dyadic','Budget-round']
    # A later integer-aware control must remain visible beside the scaling arms.
    # Keep frozen nine-policy data/summary intact; combine only for presentation.
    classical = pd.concat([pd.read_csv(r/'runs.csv') for r in [args.classical_root] + args.extra_classical_root],
                          ignore_index=True)
    classical = classical[classical.method.eq('GCD-floor')].copy()
    assert len(classical) == 192*len(solvers), len(classical)
    classical['abstained']=False;classical['submitted']=True
    classical['failed_output'] = ~classical.rounded_optimal
    d=pd.concat([d,classical],ignore_index=True)
    summary=d.groupby(['solver','method'],sort=False).agg(n=('status','size'),
                 attempted=('submitted','sum'),abstained=('abstained','sum'),
                 exact_optimal=('rounded_optimal','sum'),failed=('failed_output','sum'))
    methods.append('GCD-floor')
    lines = [r'\begin{tabular}{l' + 'rrr'*len(solvers) + '}', r'\toprule',
             '& ' + ' & '.join(r'\multicolumn{3}{c}{%s}' % SOLVER_LABELS[s] for s in solvers) + r' \\',
             'Method & ' + ' & '.join(['Verified & Other & Abstain']*len(solvers)) + r' \\', r'\midrule']
    for method in methods:
        if method=='GCD-floor':lines.append(r'\midrule')
        vals = []
        for solver in solvers:
            r = summary.loc[(solver,method)]
            vals += [str(int(r.exact_optimal)), str(int(r.failed)), str(int(r.abstained))]
        lines.append(method+' & '+' & '.join(vals)+r' \\')
    lines += [r'\bottomrule',r'\end{tabular}']
    (args.tables/'budget-results.tex').write_text('\n'.join(lines)+'\n')
    plt.rcParams.update({'font.size':11, 'pdf.fonttype':42, 'ps.fonttype':42})
    fig, axes = plt.subplots(1,len(solvers),figsize=(4.5*len(solvers),5.5),sharey=True,layout='constrained')
    for ax, solver in zip(np.atleast_1d(axes),solvers):
        a = d[d.solver.eq(solver)]
        grid = np.empty((len(methods),4))
        for i, method in enumerate(methods):
            for j, e in enumerate([0,3,6,9]):
                s = a[a.method.eq(method)&a.exponent.eq(e)]
                grid[i,j] = 100*s.rounded_optimal.mean()
        ax.imshow(grid,cmap='Blues',vmin=0,vmax=100,aspect='auto')
        for i,method in enumerate(methods):
            for j,e in enumerate([0,3,6,9]):
                s = a[a.method.eq(method)&a.exponent.eq(e)]
                if s.abstained.all():
                    ax.add_patch(Rectangle((j-.5,i-.5),1,1,facecolor='#eeeeee',edgecolor='#aaaaaa',hatch='//'))
                    label, color = 'abstain', 'black'
                else:
                    label = f'{int(s.rounded_optimal.sum())}/{len(s)}'
                    color = 'white' if grid[i,j]>65 else 'black'
                ax.text(j,i,label,ha='center',va='center',fontsize=11,color=color)
        ax.set_xticks(range(4),[r'$10^0$',r'$10^3$',r'$10^6$',r'$10^9$'])
        ax.set_yticks(range(len(methods)),methods)
        ax.axhline(len(methods)-1.5,color='black',linewidth=1.2)
        ax.set_xlabel('Coefficient multiplier')
        ax.set_title(f'({"abc"[solvers.index(solver)]}) {SOLVER_LABELS[solver]}')
    fig.savefig(args.figures/'budget-verification.pdf',bbox_inches='tight')
    fig.savefig(args.figures/'budget-verification.png',dpi=180,bbox_inches='tight')
    plt.close(fig)

    # Phase diagram of contract compatibility, with exact analytic boundaries.
    logs_M = np.linspace(-3,12,151)
    logs_delta = np.linspace(-14,2,161)
    regimes = np.zeros((len(logs_delta),len(logs_M)))
    for i,ld in enumerate(logs_delta):
        for j,lM in enumerate(logs_M):
            row = [10.**(lM-4),10.**lM]
            decision = select_factor(row,10.**ld,coefficient_floor=1e-6,coefficient_ceiling=1e6)
            regimes[i,j] = 0 if decision.factor is None else (1 if decision.reason=='projected' else 2)
    from matplotlib.colors import ListedColormap
    fig,ax = plt.subplots(figsize=(6.5,4.2),layout='constrained')
    ax.imshow(regimes,origin='lower',extent=[-3,12,-14,2],aspect='auto',interpolation='nearest',
              cmap=ListedColormap(['#bdbdbd','#e9c46a','#2a9d8f']),vmin=0,vmax=2)
    ax.plot(logs_M,logs_M-12,'k-',lw=1.2,label=r'Feasibility: $\delta=\epsilon M/U$')
    ax.plot(logs_M,logs_M-8,'k--',lw=1.2,label=r'Unconstrained GM becomes admissible')
    ax.set(xlabel=r'$\log_{10} M$',ylabel=r'$\log_{10}\delta$',ylim=(-14,2))
    ax.text(4,-10.5,'Incompatible specifications',ha='center',fontsize=9)
    ax.text(6.5,-3.5,'Projected factor',ha='center',fontsize=9)
    ax.text(1,0,'Unconstrained GM',ha='center',fontsize=9)
    ax.legend(loc='lower right',fontsize=8,framealpha=.9)
    ax.set_title(r'$M/m=10^4$, $[\ell,U]=[10^{-6},10^6]$, $\epsilon=10^{-6}$')
    fig.savefig(args.figures/'budget-compatibility.pdf',bbox_inches='tight')
    fig.savefig(args.figures/'budget-compatibility.png',dpi=180,bbox_inches='tight')
    plt.close(fig)
    print(summary.to_string())


if __name__=='__main__':
    main()
