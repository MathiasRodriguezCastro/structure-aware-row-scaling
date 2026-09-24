#!/usr/bin/env python3
"""Analyze frozen guard controls and independently verify the lattice baseline."""
import argparse
from fractions import Fraction as F
import hashlib
from itertools import product
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--control', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    d = pd.read_csv(args.root/'verified-runs.csv')
    control = pd.read_csv(args.control/'runs.csv')
    checked = {}
    states = np.array(list(product([0,1], repeat=6)), dtype=np.int64)
    local_checks = 0
    for p in sorted(args.control.glob('M*_s*.npz')):
        raw = np.load(args.root/p.name)
        q = np.load(p)
        for key in ['A', 'b']:
            assert np.array_equal(raw[key], q[key+'_original'])
        assert np.array_equal(raw['c'], q['c'])
        A, b, B, rhs = raw['A'], raw['b'], q['A_exported'], q['b_exported']
        assert np.array_equal(B, B.astype(np.int64))
        assert np.array_equal(rhs, rhs.astype(np.int64))
        assert float(np.max(abs(A))) * A.shape[1] < 2**62
        for k in range(A.shape[1]//6):
            sl = slice(6*k,6*k+6)
            good = np.all(states @ A[2*k:2*k+2, sl].astype(np.int64).T <= np.floor(b[2*k:2*k+2]), axis=1)
            new = np.all(states @ B[4*k:4*k+4, sl].astype(np.int64).T <= rhs[4*k:4*k+4], axis=1)
            assert np.array_equal(good, new)
            local_checks += 1
        assert np.array_equal(A[-1], B[-1]) and b[-1]==rhs[-1]
        # Integer lattice gap proves a conditional rounding certificate for
        # every exported control row, including the resource coupling.
        assert all(F(1e-6)*(1+int(sum(abs(row))))<1 for row in B.astype(np.int64))
        checked[p.stem] = (A.astype(np.int64), np.floor(b).astype(np.int64),
                           raw['c'].astype(np.int64), int(raw['optimum']))
    for i, row in control.iterrows():
        A, b, c, opt = checked[f'M{row.M}_s{row.seed}']
        values = json.loads(row.x)
        feasible = optimal = False
        if values is not None:
            z = np.rint(values).astype(np.int64)
            feasible = bool(np.all((z>=0)&(z<=1)) and np.all(A@z<=b))
            optimal = bool(feasible and c@z==opt)
        assert feasible==row.rounded_feasible and optimal==row.rounded_optimal
        control.loc[i, 'independent_rounded_feasible'] = feasible
        control.loc[i, 'independent_rounded_optimal'] = optimal
    control['independent_rounded_feasible'] = control.independent_rounded_feasible.astype(bool)
    control['independent_rounded_optimal'] = control.independent_rounded_optimal.astype(bool)
    combined = pd.concat([d, control], ignore_index=True)
    combined['total_seconds'] = combined.prep_seconds + combined.solver_seconds
    combined['abstain'] = combined.status=='ABSTAIN'
    summary = combined.groupby(['solver','method']).agg(
        configurations=('status','size'), feasible=('independent_rounded_feasible','sum'),
        optimal=('independent_rounded_optimal','sum'), abstain=('abstain','sum'),
        median_prep_seconds=('prep_seconds','median'), median_solver_seconds=('solver_seconds','median'),
        median_total_seconds=('total_seconds','median'), median_rows=('exported_rows','median'))
    summary.to_csv(args.out/'summary.csv')
    combined.to_csv(args.out/'all-verified-runs.csv', index=False)
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in
              [args.root/'runs.csv', args.control/'runs.csv', Path(__file__)]}
    (args.out/'verification.json').write_text(json.dumps(dict(
        lattice_models_checked=len(checked), local_equivalence_checks=local_checks,
        lattice_solver_outputs_checked=len(control), full_design_configurations=len(combined),
        original_optima_source='independent DP in verify_guard_experiment.py; byte-identical source models checked',
        sha256=hashes), indent=2)+'\n')
    order = ['Base','GCD-floor','Dyadic-GM','Pair-sum','All-elimination','Selected-guards',
             'Unsafe-clauses','All-clauses','Lattice-decomposition']
    labels = ['Original','GCD / RHS flooring','Dyadic GM','Pair aggregation','All elimination rows',
              'Selected LP-valid guards','Targeted integer clauses','Full clause cover','Lattice decomposition']
    plt.rcParams.update({'font.size':9,'pdf.fonttype':42,'ps.fonttype':42})
    fig, axs = plt.subplots(1,2,figsize=(8.0,4.6),sharey=True)
    for ax, solver in zip(axs, ['gurobi','highs']):
        sub = summary.loc[solver].loc[order]
        y = np.arange(len(order))
        ax.barh(y, sub.feasible, color='#93c5dd', height=.66, label='Exactly feasible after rounding')
        ax.barh(y, sub.optimal, color='#174f70', height=.66, label='Also exactly optimal')
        for j, row in enumerate(sub.itertuples()):
            label = '24 abstentions' if row.abstain==24 else f'{row.optimal}/{row.feasible}'
            ax.text(max(row.feasible,.2)+.35,j,label,va='center',fontsize=8)
        ax.set(title={'gurobi':'Gurobi','highs':'HiGHS'}[solver],xlim=(0,29.5),xticks=[0,6,12,18,24],
               xlabel='Configurations (24 per method)', yticks=y, yticklabels=labels)
        ax.grid(axis='x',alpha=.16)
        ax.set_axisbelow(True)
        ax.spines[['top','right']].set_visible(False)
    axs[0].invert_yaxis()
    handles, legend = axs[0].get_legend_handles_labels()
    fig.legend(handles,legend,loc='lower center',bbox_to_anchor=(.59,0),ncol=1,frameon=False,fontsize=8)
    fig.tight_layout(rect=(0,.095,1,1))
    fig.savefig(args.out/'feasibility-and-optimality.pdf',bbox_inches='tight')
    fig.savefig(args.out/'feasibility-and-optimality.png',dpi=180,bbox_inches='tight')
    print(summary.to_string())


if __name__=='__main__':
    main()
