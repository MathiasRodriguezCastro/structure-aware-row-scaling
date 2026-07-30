#!/usr/bin/env python3
"""Seed-replication noise floor (reviewer R2 / objection 6).

The retained runtime effects are of order 1%.  The reviewer asks whether they
exceed the solver's own run-to-run variability, which a single run per cell
cannot measure.  This reads the seed-replication campaign (the same instances
solved under Seed in {1..5}) and reports, per class and variant, the within-
instance across-seed dispersion of capped solver time: the noise floor the
~1% effects have to clear.

For each (instance, variant) we take the five per-seed solver times, compute the
relative spread (IQR / median, and max-min / median), and report the median of
that over instances.  A retained effect below this floor is inside the noise.

Usage:
    python3 scripts/seed_noise_floor.py
"""
import csv
import glob
import os
import statistics

ROOT = os.path.join(os.path.dirname(__file__), '..')
BASE = os.path.join(ROOT, 'results-revision', 'seed-replication')

CLASSES = [('Simple', 'simple-01pct'), ('SG-Ter-Mer', 'sgtm-01pct')]
SEEDS = [1, 2, 3, 4, 5]
VARIANTS = ['base', 'estructurado', 'estructurado_plano',
            'estructurado_matricial', 'matricial_plano']


def read_seed(tag, seed):
    path = os.path.join(BASE, f'{tag}-seed{seed}', 'resumen.csv')
    if not os.path.exists(path):
        return {}
    out = {}
    for row in csv.DictReader(open(path)):
        if row.get('status') != 'OK':
            continue
        try:
            t = float(row['tiempo_solver_s'])
        except (TypeError, ValueError, KeyError):
            continue
        out[(row['instancia'], row['variante'])] = t
    return out


def iqr(xs):
    xs = sorted(xs)
    n = len(xs)
    if n < 2:
        return 0.0
    # simple linear-interpolation quartiles
    def q(p):
        i = p * (n - 1)
        lo = int(i)
        return xs[lo] if lo + 1 >= n else xs[lo] + (i - lo) * (xs[lo + 1] - xs[lo])
    return q(0.75) - q(0.25)


def main():
    print('Within-instance across-seed dispersion of capped solver time '
          '(seeds 1..5).\nThe noise floor the ~1% retained effects must clear.\n')
    print('%-11s %-22s %6s %12s %12s' % (
        'class', 'variant', 'n', 'med relIQR', 'med rel range'))
    for cls, tag in CLASSES:
        per_seed = {s: read_seed(tag, s) for s in SEEDS}
        keys = set.intersection(*[set(per_seed[s]) for s in SEEDS]) \
            if all(per_seed.values()) else set()
        by_var = {}
        for (inst, var) in keys:
            ts = [per_seed[s][(inst, var)] for s in SEEDS]
            med = statistics.median(ts)
            if med <= 0:
                continue
            by_var.setdefault(var, []).append((iqr(ts) / med, (max(ts) - min(ts)) / med))
        for var in VARIANTS:
            xs = by_var.get(var, [])
            if not xs:
                print('%-11s %-22s %6d %12s %12s' % (cls, var, 0, '-', '-'))
                continue
            riqr = statistics.median(x[0] for x in xs)
            rrng = statistics.median(x[1] for x in xs)
            print('%-11s %-22s %6d %11.2f%% %11.2f%%' % (
                cls, var, len(xs), 100 * riqr, 100 * rrng))
    print('\nRead against the retained runtime effects (~0.9% on the Simple augmented '
          'contrast): if the\nabsolute across-seed dispersion is of the same order, a '
          'single-seed absolute time is noisy.')

    # The published comparison is PAIRED within a seed, so the absolute noise above is
    # partly cancelled.  The decisive R2 question is whether the paired contrast itself
    # replicates across seeds: we recompute the SA-Aug-vs-Flat paired median ratio
    # (estructurado / estructurado_plano) and SA-Aug-vs-Base separately under each seed.
    # A ratio that holds its value across the five seeds is a real (if small) effect; one
    # that swings across 1.0 is inside the noise.
    print('\n\nPaired contrast under each seed (median T_a/T_b on that seed\'s matched pairs).')
    print('Stable across seeds => the ~1% effect is real; swinging across 1.0 => noise.\n')
    contrasts = [('SA-Aug/Flat', 'estructurado', 'estructurado_plano'),
                 ('SA-Aug/Base', 'estructurado', 'base')]
    for cls, tag in CLASSES:
        per_seed = {s: read_seed(tag, s) for s in SEEDS}
        print(f'=== {cls} ===')
        print('  %-14s %s' % ('contrast', ' '.join('seed%d' % s for s in SEEDS)))
        for label, va, vb in contrasts:
            cells = []
            for s in SEEDS:
                by = {}
                for (inst, var), t in per_seed[s].items():
                    by.setdefault(inst, {})[var] = t
                rs = [c[va] / c[vb] for c in by.values()
                      if va in c and vb in c and c[va] > 0 and c[vb] > 0]
                cells.append('%.4f' % statistics.median(rs) if rs else '  -  ')
            print('  %-14s %s' % (label, ' '.join('%7s' % c for c in cells)))
        print()


if __name__ == '__main__':
    main()
