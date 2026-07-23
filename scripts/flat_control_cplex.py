#!/usr/bin/env python3
"""Coverage-versus-selectivity audit for the CPLEX direct-control batches.

The direct Flat-versus-SA comparison was originally run under Gurobi only, so
the ordering it reports could not be told apart from a property of one solver's
pipeline.  This script applies the SAME analysis to the CPLEX batches, reusing
the machinery of flat_control_tests rather than reimplementing it, so the two
solvers' numbers are produced by identical code and remain comparable.

Two differences from the Gurobi driver are deliberate.

The Gurobi driver asserts six comparisons per MIPGap family (three classes x
two kernels) and applies Benjamini-Hochberg within that family and jointly over
twelve tests.  The CPLEX batches are being filled in one class-tolerance cell at
a time, so this script adjusts within whatever cells are actually present and
says so in the output.  A BH family over two tests is reported as such; it is
not the six- or twelve-test family of the main analysis and must not be quoted
as if it were.

Nothing here is confirmatory.  The endpoint hierarchy was chosen after looking
at the Gurobi data, and this analysis inherits that choice, so its role is to
test whether the Gurobi ordering PERSISTS under a second solver -- not to
establish a new effect.

Usage:
    python3 scripts/flat_control_cplex.py
    python3 scripts/flat_control_cplex.py --abort-penalty par10
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import flat_control_tests as fct  # noqa: E402

# The CPLEX batches live in their own tree; everything else is shared.
fct.BATCH_ROOT = 'plano-control-cplex'

# (MIPGap label, [(class, batch folder)]).  Extend as cluster cells land.
CPLEX_SCENARIOS = [
    ('1%', [('Simple', 'simple-cplex-1pct')]),
]


def available(scenarios):
    """Drop cells whose resumen.csv is not on disk yet, reporting what is used."""
    out = []
    for gap, batches in scenarios:
        present = []
        for class_name, folder in batches:
            path = os.path.join(fct.ROOT, 'results-revision', fct.BATCH_ROOT,
                                folder, 'resumen.csv')
            if os.path.exists(path):
                present.append((class_name, folder))
            else:
                print(f'  [skip] {gap} {class_name}: {folder} not present yet',
                      file=sys.stderr)
        if present:
            out.append((gap, present))
    return out


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--abort-penalty', choices=('tmax', 'par10'), default='tmax')
    args = ap.parse_args()
    multiplier = 1.0 if args.abort_penalty == 'tmax' else 10.0

    scenarios = available(CPLEX_SCENARIOS)
    if not scenarios:
        sys.exit('no CPLEX control batches found')

    all_rows = []
    for gap, batches in scenarios:
        rows = []
        for class_name, folder in batches:
            rows.extend(fct.analyze(folder, class_name, multiplier))
        # BH within the cell, per endpoint.  The primary endpoint is
        # preprocessing-plus-solver time, whose p-value is total_p; adjusting the
        # solver-time p and printing it beside the total-time effect would report
        # a q that belongs to a different test.
        for row, q in zip(rows, fct.bh_adjust([r['total_p'] for r in rows])):
            row['q_total'] = q
        for row, q in zip(rows, fct.bh_adjust([r['p'] for r in rows])):
            row['q_solver'] = q
        for row in rows:
            row['gap'] = gap
        all_rows.extend(rows)

        print(f'\n=== CPLEX, MIPGap {gap} '
              f'({len(rows)} kernel-matched contrasts; BH within these {len(rows)}) ===')
        print('  primary endpoint: preprocessing-plus-solver time')
        print('  %-12s %-20s %4s %5s %11s %11s %9s %9s %9s' % (
            'class', 'contrast', 'n', 'fam', 'med T_S/T_F', 'HL', 'p', 'p(block)', 'q(cell)'))
        for r in rows:
            print('  %-12s %-20s %4d %5d %11.4f %11.4f %9.4f %9.4f %9.4f' % (
                r['class'], f"{r['flat']} vs {r['sa']}", r['n_total'], r['n_total_families'],
                r['median_total_ratio'], r['hl_total'], r['total_p'],
                r['total_p_block'], r['q_total']))
        print('  secondary endpoint: capped solver time')
        for r in rows:
            print('  %-12s %-20s %4d %5d %11.4f %11.4f %9.4f %9.4f %9.4f' % (
                r['class'], f"{r['flat']} vs {r['sa']}", r['n'], r['n_families'],
                r['median_ratio'], r['hl_solver'], r['p'], r['p_block'], r['q_solver']))
        print('  preprocessing cost (median s):')
        for r in rows:
            print('  %-12s %-20s SA=%.4f  Flat=%.4f  diff=%.4f' % (
                r['class'], f"{r['flat']} vs {r['sa']}",
                r['preproc_median_sa'], r['preproc_median_flat'], r['preproc_median_diff']))

    print('\nRatio is T_SA/T_Flat, matching the convention of the Gurobi tables: '
          'values above 1 mean the selective rule is slower and so favour full '
          'coverage (Flat); below 1 favour selectivity (SA).')
    print('Exploratory: the endpoint hierarchy was fixed on the Gurobi data. '
          'This tests persistence across solvers, not a new effect.')
    print(f'Abort convention: {args.abort_penalty}.')


if __name__ == '__main__':
    main()
