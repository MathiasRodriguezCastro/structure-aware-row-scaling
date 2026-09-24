#!/usr/bin/env python3
"""Fixed-basis conditioning analysis (reviewer objection 3 / DA-C1).

The objection: the paper's conditioning readouts are taken along each variant's
own solve path, so a variant's better condition number could reflect the vertex
its solve happened to reach rather than the representation itself.  The
fixed_basis_diagnostic holds the basis fixed -- one reference basis (the shared
LP-relaxation optimum, which every variant reaches at the same objective) rebuilt
from each variant's own scaled matrix -- so any remaining spread in kappa_1 is due
to the representation alone.

This reads that diagnostic's CSV and reports, on matched instances (the basis is
per-instance, so every contrast is paired), two things:

  1. Does scaling improve conditioning on the FIXED basis?  If SA still beats Base
     with the vertex held constant, the improvement is representational, not a
     vertex artifact -- which is the answer to the objection.
  2. Does the metadata change conditioning?  SA vs Flat within each kernel isolates
     the role metadata with coverage and basis both held fixed.

Ratios are kappa_1(a)/kappa_1(b); we report the median and the median of log10, so
"orders of magnitude" is legible.  Wilcoxon signed-rank on the log ratios.

Usage:
    python3 scripts/fixed_basis_analysis.py results-revision/fixed-basis/simple_highs.csv
"""
import argparse
import csv
import math
import statistics
import sys

from scipy.stats import wilcoxon

CONTRASTS = [
    ('SA-Aug / Base', 'SA-Aug', 'Base'),
    ('SA-Mat / Base', 'SA-Mat', 'Base'),
    ('Ruiz / Base', 'Ruiz', 'Base'),
    ('SA-Aug / Flat-Aug', 'SA-Aug', 'Flat-Aug'),
    ('SA-Mat / Flat-Mat', 'SA-Mat', 'Flat-Mat'),
]
VARIANTS = ['Base', 'SA-Aug', 'Flat-Aug', 'SA-Mat', 'Flat-Mat', 'Ruiz']


def read(path):
    by_inst = {}
    for row in csv.DictReader(open(path)):
        try:
            k = float(row['kappa1'])
        except (TypeError, ValueError):
            continue
        if not math.isfinite(k) or k <= 0 or int(row.get('singular', 0)) == 1:
            continue
        by_inst.setdefault(row['instance'], {})[row['variant']] = k
    return by_inst


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('csv')
    args = ap.parse_args()

    by_inst = read(args.csv)
    n = len(by_inst)
    if n == 0:
        print('no usable rows', file=sys.stderr)
        return

    print(f'Fixed-basis kappa_1 on {n} instances (basis held fixed per instance).\n')
    print('Per-variant kappa_1 (geometric mean over instances):')
    for v in VARIANTS:
        ks = [cells[v] for cells in by_inst.values() if v in cells]
        if ks:
            gm = math.exp(statistics.fmean(math.log(k) for k in ks))
            print(f'  {v:10s} n={len(ks):4d}  geomean={gm:.3e}')
    print()

    print('Paired contrasts (kappa_1 ratio a/b on matched instances):')
    print('  %-20s %5s %12s %12s %10s' % ('contrast', 'n', 'med ratio', 'med log10', 'p'))
    for label, a, b in CONTRASTS:
        logs, ratios = [], []
        for cells in by_inst.values():
            if a in cells and b in cells:
                ratios.append(cells[a] / cells[b])
                logs.append(math.log10(cells[a] / cells[b]))
        if len(logs) < 3:
            print('  %-20s %5d  (too few)' % (label, len(logs)))
            continue
        try:
            _, p = wilcoxon(logs, zero_method='wilcox', correction=False)
        except ValueError:
            p = float('nan')
        ps = '%.2e' % p if math.isfinite(p) else '-'
        print('  %-20s %5d %12.4g %12.3f %10s' % (
            label, len(logs), statistics.median(ratios), statistics.median(logs), ps))

    print('\nReading: SA-*/Base << 1 (many orders) => scaling improves conditioning with the\n'
          'vertex held fixed, so the improvement is representational, not a vertex artifact.\n'
          'SA-Mat/Flat-Mat ~ 1 => the matrix-only kernel is metadata-neutral on a fixed basis.')


if __name__ == '__main__':
    main()
