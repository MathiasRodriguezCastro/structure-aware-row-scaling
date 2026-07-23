#!/usr/bin/env python3
"""Minimum-detectable-effect analysis (reviewer R3).

The manuscript reports p-values, q-values under four multiplicity schemes,
rank-biserial correlations and bootstrap intervals, but never the one quantity
a reader needs to interpret a null: the smallest effect the design could have
detected.  Without it, "no robust gain appears under CPLEX" is uninterpretable
-- an informative null and an underpowered one look the same.

This script answers that by simulation from the OBSERVED paired differences, so
the noise model is the data's own dispersion rather than an assumed one.  For a
given class, endpoint and kernel-matched contrast it takes the observed per-pair
log-ratios d_i = log(T_A,i / T_B,i), centres them to build a null residual pool,
and for a grid of candidate median shifts delta measures the power of the
paired Wilcoxon signed-rank test at alpha = 0.05.  The MDE is the smallest delta
reaching 80% power; exp(MDE) is the detectable median ratio.

Resampling is at the operational-family level (whole casoXX / instance pairs
drawn with replacement), so the clustering the paper is careful about elsewhere
is respected here too: the naive per-instance n would overstate power exactly
where the paper warns it overstates independence.

Usage:
    python3 scripts/mde_analysis.py
    python3 scripts/mde_analysis.py --power 0.8 --alpha 0.05 --reps 2000
"""
import argparse
import math
import os
import sys

import numpy as np
from scipy.stats import wilcoxon

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flat_control_tests as fct  # noqa: E402

# Gurobi direct-control batches available locally, per class and tolerance.
BATCHES = [
    ('0.1%', [('Simple', 'simple-gurobi-01pct'),
              ('SG-Ter-Mer', 'sgtm-gurobi-01pct'),
              ('Full', 'full-gurobi-01pct')]),
    ('1%', [('Simple', 'simple-gurobi-1pct'),
            ('SG-Ter-Mer', 'sgtm-gurobi-1pct'),
            ('Full', 'full-gurobi-1pct')]),
]

# endpoint -> which per-family log-difference dict analyze() exposes
ENDPOINTS = {
    'solver': '_cluster_logs',        # capped solver time  (d = log(SA/Flat))
    'total': '_cluster_total_logs',   # preprocessing+solver time
}


def family_pairs(rows, kernel, endpoint_key):
    """Return {family: [d_i,...]} for the requested kernel and endpoint."""
    for r in rows:
        if r['kernel'] == kernel:
            return r[endpoint_key]
    return None


def power_at(delta, fam_values, families, rng, alpha, reps):
    """Monte-Carlo power of the paired signed-rank test for a median shift delta.

    Null residuals are the family values with the overall median removed; each
    replicate resamples whole families with replacement and adds delta.
    """
    allvals = np.concatenate([fam_values[f] for f in families])
    resid = allvals - np.median(allvals)          # centre: null is "no effect"
    by_family = {f: fam_values[f] - np.median(allvals) for f in families}
    fam_list = list(families)
    rejects = 0
    for _ in range(reps):
        drawn = rng.choice(len(fam_list), size=len(fam_list), replace=True)
        sample = np.concatenate([by_family[fam_list[k]] for k in drawn])
        shifted = sample + delta
        # signed-rank needs a non-degenerate spread; guard tiny samples
        if np.allclose(shifted, shifted[0]):
            continue
        try:
            _, p = wilcoxon(shifted, zero_method='wilcox',
                            correction=False, mode='auto')
        except ValueError:
            continue
        if p < alpha:
            rejects += 1
    return rejects / reps


def mde(fam_values, alpha, power_target, reps, rng):
    """Smallest positive median log-shift reaching power_target, by bisection."""
    families = list(fam_values)
    n_inst = sum(len(fam_values[f]) for f in families)
    if n_inst < 3:
        return None, n_inst, len(families)
    # bracket: grow until power target met or an upper cap is hit
    lo, hi = 0.0, 0.01
    while power_at(hi, fam_values, families, rng, alpha, reps) < power_target:
        hi *= 2
        if hi > 2.0:                              # exp(2) ~ 7.4x ratio; give up
            return float('inf'), n_inst, len(families)
    for _ in range(22):                           # ~1e-6 resolution on log scale
        mid = 0.5 * (lo + hi)
        if power_at(mid, fam_values, families, rng, alpha, reps) < power_target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi), n_inst, len(families)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--alpha', type=float, default=0.05)
    ap.add_argument('--power', type=float, default=0.80)
    ap.add_argument('--reps', type=int, default=2000)
    ap.add_argument('--seed', type=int, default=20260723)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)

    print(f'Minimum detectable median ratio at {args.power:.0%} power, '
          f'alpha={args.alpha}, {args.reps} family-bootstrap replicates.\n'
          f'MDE is reported as the detectable ratio exp(delta); a class whose '
          f'MDE is 1.05 cannot resolve effects below ~5%.\n')
    header = ('gap', 'class', 'kernel', 'endpoint', 'n_inst', 'n_fam',
              'MDE ratio', 'MDE %')
    print('%-5s %-11s %-4s %-7s %6s %6s %10s %8s' % header)
    for gap, batches in BATCHES:
        for class_name, folder in batches:
            path = os.path.join(fct.ROOT, 'results-revision', 'plano-control',
                                folder, 'resumen.csv')
            if not os.path.exists(path):
                print(f'  [skip] {gap} {class_name}: {folder} absent')
                continue
            rows = fct.analyze(folder, class_name, 1.0)
            for kernel in ('Augmented', 'Matrix-only'):
                for ep, key in ENDPOINTS.items():
                    fam = family_pairs(rows, kernel, key)
                    if not fam:
                        continue
                    delta, n_inst, n_fam = mde(fam, args.alpha, args.power,
                                               args.reps, rng)
                    if delta is None:
                        cell = 'n<3'
                        pct = '-'
                    elif math.isinf(delta):
                        cell = '>7.4x'
                        pct = '>640'
                    else:
                        cell = '%.4f' % math.exp(delta)
                        pct = '%.2f' % (100 * (math.exp(delta) - 1))
                    print('%-5s %-11s %-4s %-7s %6d %6d %10s %8s' % (
                        gap, class_name, kernel[:3], ep, n_inst, n_fam,
                        cell, pct))
    print('\nContrast is SA versus kernel-matched Flat (the coverage question, '
          'SC-4).\nResampling is at the operational-family level, so n_fam '
          '(not n_inst) sets the power.')


if __name__ == '__main__':
    main()
