#!/usr/bin/env python3
"""Three-arm coverage-versus-selectivity analysis (reviewer R1).

The R1 campaign (run_coverage_policy.slurm) runs six variants per cell so the
coverage question becomes a three-arm comparison on matched pairs, per kernel:

    selective         estructurado          / estructurado_matricial
    metadata-routed   estructurado_full     / matricial_full        (SA-*-Full)
    role-blind Flat   estructurado_plano    / matricial_plano

The paper's original comparison was selective-versus-Flat only, i.e. "leave the
worst rows unscaled" versus "scale everything."  The new SA-*-Full arm keeps the
role metadata but routes the residual-global rows through the kernel too, so it
is metadata-driven full coverage.  The decisive question is whether SA-*-Full
matches Flat: if it does, the coverage gap -- not the use of metadata -- was the
defect, which sharpens the paper's conclusion.

This reports, per class-tolerance cell and per kernel, the paired capped-
solver-time comparison (the build-invariant endpoint) for the two contrasts that
answer that question:

    SA-Full vs Flat        (does metadata-routed coverage reach role-blind coverage?)
    SA-Full vs selective   (does covering R_other help over leaving it unscaled?)

Ratio is T_a/T_b on matched instances; Wilcoxon signed-rank with BH within the
cell.  Runs on whatever cells are present, so it works incrementally while the
campaign fills in.

Usage:
    python3 scripts/coverage_policy_analysis.py
"""
import argparse
import csv
import math
import os
import statistics
import sys

from scipy.stats import wilcoxon

ROOT = os.path.join(os.path.dirname(__file__), '..')
BASE = os.path.join(ROOT, 'results-revision', 'coverage-policy')

CELLS = [
    ('Simple', '1%', 'simple-1pct'),
    ('Simple', '0.1%', 'simple-01pct'),
    ('SG-Ter-Mer', '1%', 'sgtm-1pct'),
    ('SG-Ter-Mer', '0.1%', 'sgtm-01pct'),
    ('Full', '1%', 'full-1pct'),
    ('Full', '0.1%', 'full-01pct'),
]

# per kernel: (selective, metadata-routed full, role-blind flat)
KERNELS = {
    'Augmented': ('estructurado', 'estructurado_full', 'estructurado_plano'),
    'Matrix-only': ('estructurado_matricial', 'matricial_full', 'matricial_plano'),
}


def read_cell(folder):
    path = os.path.join(BASE, folder, 'resumen.csv')
    if not os.path.exists(path):
        return None
    by_inst = {}
    for row in csv.DictReader(open(path)):
        if row.get('status') != 'OK':
            continue
        t = row.get('tiempo_solver_s')
        try:
            t = float(t)
        except (TypeError, ValueError):
            continue
        by_inst.setdefault(row['instancia'], {})[row['variante']] = t
    return by_inst


def paired(by_inst, va, vb):
    """log(T_va / T_vb) over instances solved by both; returns (diffs, ratios)."""
    diffs, ratios = [], []
    for cells in by_inst.values():
        if va in cells and vb in cells and cells[va] > 0 and cells[vb] > 0:
            ratios.append(cells[va] / cells[vb])
            diffs.append(math.log(cells[va] / cells[vb]))
    return diffs, ratios


def bh(pvals):
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    q = [0.0] * m
    prev = 1.0
    for rank, i in enumerate(reversed(order), start=1):
        k = m - rank + 1
        prev = min(prev, pvals[i] * m / k)
        q[i] = prev
    return q


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()

    print('Three-arm coverage vs selectivity, capped solver time. '
          'Ratio = T_a/T_b on matched pairs.\n'
          'SA-Full ~ Flat (ratio ~1, ns) => the coverage gap, not metadata, was the defect.\n')
    header = ('cell', 'kernel', 'contrast', 'n', 'med ratio', 'p', 'q')
    for cls, tol, folder in CELLS:
        by_inst = read_cell(folder)
        if not by_inst:
            print(f'[pending] {cls} {tol} ({folder})')
            continue
        rows = []
        for kernel, (sel, full, flat) in KERNELS.items():
            for label, (va, vb) in (('SA-Full/Flat', (full, flat)),
                                    ('SA-Full/selective', (full, sel))):
                diffs, ratios = paired(by_inst, va, vb)
                if len(diffs) < 3:
                    rows.append((kernel, label, len(diffs), float('nan'), float('nan')))
                    continue
                try:
                    _, p = wilcoxon(diffs, zero_method='wilcox', correction=False)
                except ValueError:
                    p = float('nan')
                rows.append((kernel, label, len(diffs), statistics.median(ratios), p))
        qs = bh([r[4] for r in rows if not math.isnan(r[4])])
        qi = iter(qs)
        print(f'\n=== {cls} {tol} ({len(by_inst)} instances) ===')
        print('  %-11s %-18s %4s %10s %9s %9s' % header[1:])
        for kernel, label, n, mr, p in rows:
            q = next(qi) if not math.isnan(p) else float('nan')
            mrs = '%.4f' % mr if not math.isnan(mr) else '-'
            ps = '%.4f' % p if not math.isnan(p) else '-'
            qsr = '%.4f' % q if not math.isnan(q) else '-'
            print('  %-11s %-18s %4d %10s %9s %9s' % (kernel, label, n, mrs, ps, qsr))


if __name__ == '__main__':
    main()
