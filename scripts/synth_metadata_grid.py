#!/usr/bin/env python3
"""Kernel-matched metadata grid (reviewer follow-up to the spectral audit).

The existence proof in subsec:spectral-audit runs SA-Mat against a same-kernel
role-blind control (Flat-Mat) at one block-scale range and one severity.  This
sweeps the block-scale heterogeneity and the disturbance severity so the reader
can see where the metadata advantage appears, whether it grows with heterogeneity,
whether it is specific to the coupling patterns, and where it vanishes.

For each cell (block-scale range R, severity S, pattern) we generate the
block-heterogeneous family with exponents spread over [-R, R] (env
SYNTH_BLOCK_RANGE), export every variant's matrix, and read kappa2+ from the
exported LPs with spectral_audit.py.  The reported quantity is the paired
SA-Mat / Flat-Mat ratio (both coefficient-only, so the gap is the block metadata
alone): median, win fraction, and a Wilcoxon signed-rank p on the log ratios.

Usage:
    python3 scripts/synth_metadata_grid.py [--seeds 30] [--exe <path>]
"""
import argparse
import csv
import math
import os
import statistics
import subprocess
import sys
import tempfile

from scipy.stats import wilcoxon

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RANGES = [1.0, 2.0, 3.0]
SEVERITIES = [3, 6]
PATTERNS = ['coupling', 'coupling_uniform', 'mixed']
VARIANTS = 'Base,SA-Mat,Flat-Mat'


def run_cell(exe, R, S, pattern, seeds, workdir):
    lpdir = os.path.join(workdir, f'lp_R{R:g}_S{S}_{pattern}')
    os.makedirs(lpdir, exist_ok=True)
    csv_out = os.path.join(workdir, f'run_R{R:g}_S{S}_{pattern}.csv')
    script = (
        f'benchmarkSintetico --coef-family block_heterogeneous --volcar-lp {lpdir}\n'
        f'DummyLp\n20250803\n{seeds}\n4\n6 2\n8 3\n{pattern}\n{S}\n{VARIANTS}\n{csv_out}\n'
    )
    env = dict(os.environ, SYNTH_BLOCK_RANGE=f'{R:g}')
    subprocess.run([exe], input=script, text=True, cwd=os.path.join(ROOT, 'code'),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    spec = os.path.join(workdir, f'spec_R{R:g}_S{S}_{pattern}.csv')
    subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'spectral_audit.py'),
                    '--lp-dir', lpdir, '--out', spec],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    by_inst = {}
    for r in csv.DictReader(open(spec)):
        by_inst.setdefault(r['instance'], {})[r['variant']] = float(r['kappa2_pos'])
    ratios = [c['SAMat'] / c['FlatMat'] for c in by_inst.values()
              if 'SAMat' in c and 'FlatMat' in c and c['FlatMat'] > 0]
    if len(ratios) < 3:
        return None
    logs = [math.log(x) for x in ratios]
    try:
        _, p = wilcoxon(logs)
    except ValueError:
        p = float('nan')
    return {
        'n': len(ratios),
        'med_ratio': statistics.median(ratios),
        'wins': sum(1 for x in ratios if x < 1),
        'p': p,
        'med_kappa_samat': statistics.median(c['SAMat'] for c in by_inst.values() if 'SAMat' in c),
        'med_kappa_flatmat': statistics.median(c['FlatMat'] for c in by_inst.values() if 'FlatMat' in c),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--seeds', type=int, default=30)
    ap.add_argument('--exe', default=os.path.join(ROOT, 'code', 'build', 'SistemaElectrico'))
    ap.add_argument('--out', default=os.path.join(
        ROOT, 'results-revision', 'spectral-heterogeneous', 'metadata_grid.csv'))
    args = ap.parse_args()

    rows = []
    work = tempfile.mkdtemp(prefix='synthgrid_')
    print('SA-Mat / Flat-Mat on kappa2+ (both coefficient-only; gap = block metadata).\n'
          'ratio < 1 favours the structure-aware rule.\n')
    print('%-6s %3s %-16s %4s %11s %8s %10s' %
          ('range', 'S', 'pattern', 'n', 'med ratio', 'wins', 'p'))
    for R in RANGES:
        for S in SEVERITIES:
            for pat in PATTERNS:
                res = run_cell(args.exe, R, S, pat, args.seeds, work)
                if res is None:
                    print('%-6s %3d %-16s   (failed)' % (f'[-{R:g},{R:g}]', S, pat))
                    continue
                print('%-6s %3d %-16s %4d %11.4g %5d/%-2d %10.2e' % (
                    f'[-{R:g},{R:g}]', S, pat, res['n'], res['med_ratio'],
                    res['wins'], res['n'], res['p']))
                rows.append({'block_range': f'[-{R:g},{R:g}]', 'severity_S': S,
                             'pattern': pat, **res})
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['block_range', 'severity_S', 'pattern', 'n',
                                           'med_ratio', 'wins', 'p', 'med_kappa_samat',
                                           'med_kappa_flatmat'])
        w.writeheader()
        w.writerows(rows)
    print(f'\nwrote {len(rows)} cells to {args.out}')


if __name__ == '__main__':
    main()
