#!/usr/bin/env python3
"""Direct spectral audit of the exported synthetic matrices.

The propositions are stated in terms of the spectral condition number
kappa_2(A) = sigma_max / sigma_min, but the synthetic suite as previously
reported measured only the coefficient-and-right-hand-side magnitude-range
proxy.  On the synthetic instances the matrices are small enough to form
densely and decompose exactly, so this script closes that gap: it parses the
exported LP of every variant, builds the constraint matrix, and reports

    kappa_2  = sigma_max / sigma_min           (spectral condition number)
    rank-deficiency-safe kappa_2^+             (using the smallest positive
                                                singular value)
    range    = max|a_ij| / min^+|a_ij|         (the proxy used so far)

so the proxy can be compared against the quantity the propositions describe.

Usage:
    python3 scripts/spectral_audit.py --lp-dir <dir> --out <csv>
"""
import argparse
import csv
import glob
import os
import re
import sys

import numpy as np

# LP-format term:  [+-] coefficient varname
TERM = re.compile(r'([+-]?\s*\d*\.?\d+(?:[eE][+-]?\d+)?)?\s*([A-Za-z_][A-Za-z0-9_()\[\].]*)')
SECTION = re.compile(r'^\s*(subject to|st|s\.t\.|bounds|binaries|binary|generals|general|'
                     r'integers|end|maximize|minimize)\b', re.I)


def parse_lp_matrix(path):
    """Return the constraint matrix of an LP file as a dense numpy array.

    Only the constraint section is read; bounds, integrality and the objective
    are ignored, which is exactly the matrix the propositions talk about.
    """
    rows, colindex = [], {}
    in_constraints = False
    current = None

    def flush():
        nonlocal current
        if current:
            rows.append(current)
        current = None

    with open(path) as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith('\\'):
                continue
            m = SECTION.match(line)
            if m:
                kind = m.group(1).lower()
                flush()
                in_constraints = kind in ('subject to', 'st', 's.t.')
                continue
            if not in_constraints:
                continue
            # a new constraint starts with "name:"
            if ':' in line and not line.lstrip().startswith(('<', '>', '=')):
                flush()
                current = {}
                line = line.split(':', 1)[1]
            if current is None:
                continue
            # stop at the relational operator; the RHS is not part of A
            body = re.split(r'[<>=]=?', line)[0]
            for coef, name in TERM.findall(body):
                if name in ('e', 'E'):
                    continue
                text = (coef or '+1').replace(' ', '')
                if text in ('+', '-'):
                    text += '1'
                try:
                    value = float(text)
                except ValueError:
                    continue
                if name not in colindex:
                    colindex[name] = len(colindex)
                current[colindex[name]] = current.get(colindex[name], 0.0) + value
        flush()

    if not rows or not colindex:
        return None
    A = np.zeros((len(rows), len(colindex)))
    for i, r in enumerate(rows):
        for j, v in r.items():
            A[i, j] = v
    return A


def spectrum(A, tol_factor=1e-12):
    sv = np.linalg.svd(A, compute_uv=False)
    smax = float(sv[0]) if sv.size else float('nan')
    smin = float(sv[-1]) if sv.size else float('nan')
    tol = smax * tol_factor
    positive = sv[sv > tol]
    smin_pos = float(positive[-1]) if positive.size else float('nan')
    nz = np.abs(A[A != 0.0])
    rng = float(nz.max() / nz.min()) if nz.size else float('nan')
    return {
        'rows': A.shape[0], 'cols': A.shape[1],
        'sigma_max': smax, 'sigma_min': smin, 'sigma_min_pos': smin_pos,
        'kappa2': smax / smin if smin > 0 else float('inf'),
        'kappa2_pos': smax / smin_pos if smin_pos > 0 else float('inf'),
        'range_proxy': rng,
        'rank_deficient': int(smin <= tol),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--lp-dir', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    rows = []
    for path in sorted(glob.glob(os.path.join(args.lp_dir, '*.lp'))):
        base = os.path.basename(path)[:-3]
        variant = base.rsplit('_', 1)[-1]
        instance = base.rsplit('_', 1)[0]
        A = parse_lp_matrix(path)
        if A is None:
            print(f'  skipped (no constraints parsed): {base}', file=sys.stderr)
            continue
        info = spectrum(A)
        info.update(instance=instance, variant=variant)
        rows.append(info)
        print('  %-28s %-12s rows=%d cols=%d kappa2+=%.4e range=%.4e'
              % (instance, variant, info['rows'], info['cols'],
                 info['kappa2_pos'], info['range_proxy']), file=sys.stderr)

    if not rows:
        sys.exit('no matrices parsed')
    fields = ['instance', 'variant', 'rows', 'cols', 'sigma_max', 'sigma_min',
              'sigma_min_pos', 'kappa2', 'kappa2_pos', 'range_proxy', 'rank_deficient']
    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    with open(args.out, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in fields})
    print(f'wrote {len(rows)} rows to {args.out}', file=sys.stderr)


if __name__ == '__main__':
    main()
