#!/usr/bin/env python3
"""Basis-fixed conditioning diagnostic.

The conditioning readout reported elsewhere in this paper is taken along each
variant's OWN solve path: every variant fixes integers to its OWN incumbent and
factorizes its OWN final basis.  Two things therefore differ between the numbers
being compared -- the linear program and the basis -- so the comparison cannot
separate the quality of the representation from the accident of which incumbent
and which vertex that particular solve happened to reach.

This script removes both confounds.  Because positive row scaling preserves the
mixed-integer program exactly, one integer assignment is feasible under every
variant, and the exported matrices differ only by a positive row scaling
D: A_variant = D A_base with the same rows, columns and sparsity pattern.  So:

  1. solve the BASE model once and fix its integer variables,
  2. solve the resulting LP once to obtain ONE reference basis B,
  3. rebuild that SAME basis, column for column, from each variant's exported
     matrix, and report its condition number.

Everything except the row scaling is then held fixed by construction, and the
differences that remain are attributable to the transformation alone.

Two details are handled explicitly rather than assumed away.

Slack columns.  A basis normally contains slacks.  Solvers carry slacks with
unit coefficients, so scaling row r by d_r does NOT scale the slack column of
row r: the basis is [ (DA)_{:,J} | e_r ], not D[ A_{:,J} | e_r ].  The basis is
therefore assembled the way the solver holds it, which is also the numerics the
solver actually faces.

Conditioning measure.  These bases are square and large (of order 10^4), so a
dense SVD is neither affordable nor necessary.  We report the 1-norm condition
number kappa_1(B) = ||B||_1 ||B^{-1}||_1, estimated via a sparse LU and Higham's
1-norm estimator.  This is the same quantity Gurobi's Kappa attribute reports,
so the numbers stay commensurable with the rest of the paper.

Usage:
    python3 scripts/fixed_basis_diagnostic.py --instancias data/entradas/entrada-modelo-simple/*.txt \
        --out results-revision/fixed-basis/simple.csv
"""
import argparse
import csv
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validar_preprocesamiento import clean_instance_text  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# (tag, preprocessing flags).  'base' only snapshots; it does not scale.
VARIANTS = [
    ('Base', '--solodiagnostico'),
    ('SA-Aug', '--local-estructurado'),
    ('Flat-Aug', '--local-estructurado --plano'),
    ('SA-Mat', '--local-matricial'),
    ('Flat-Mat', '--local-matricial --plano'),
    ('Ruiz', '--local-ruiz --ruiz-iters 4'),
]


def export_lp(exe, instance_text, flags, target, mipgap, timeout_s=600.0):
    script = (
        f"{instance_text}\n\n"
        f"configurarSolver --Gurobi --timeout 3600 --mipgap {mipgap:g}\n"
        f"preprocesar {flags}\n"
        f"grabar {target}\n"
        "salir\n"
    )
    with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as fh:
        fh.write(script)
        path = fh.name
    try:
        with open(path) as stdin:
            subprocess.run([str(exe)], stdin=stdin, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, cwd=str(ROOT / 'code'),
                           timeout=timeout_s)
        return os.path.exists(target) and os.path.getsize(target) > 0
    except subprocess.TimeoutExpired:
        return False
    finally:
        os.unlink(path)


def reference_basis(base_lp, mipgap, timelimit):
    """Solve the base model, fix integers, solve the LP, return the basis.

    Returns (row_names, basic_var_names, basic_slack_rows, info) or None.
    """
    import gurobipy as gp

    m = gp.read(str(base_lp))
    m.Params.OutputFlag = 0
    m.Params.MIPGap = mipgap
    m.Params.TimeLimit = timelimit
    m.Params.Seed = 1
    m.optimize()
    if m.SolCount == 0:
        return None

    fixed = m.fixed()          # integers pinned at the incumbent
    fixed.Params.OutputFlag = 0
    fixed.Params.Method = 1    # dual simplex: we need a basis, not an interior point
    fixed.optimize()
    if fixed.Status != gp.GRB.OPTIMAL:
        return None

    basic_vars = [v.VarName for v in fixed.getVars() if v.VBasis == 0]
    basic_rows = [c.ConstrName for c in fixed.getConstrs() if c.CBasis == 0]
    row_names = [c.ConstrName for c in fixed.getConstrs()]
    info = {
        'mip_obj': m.ObjVal,
        'mip_gap': m.MIPGap,
        'rows': fixed.NumConstrs,
        'cols': fixed.NumVars,
        'basic_structural': len(basic_vars),
        'basic_slack': len(basic_rows),
    }
    return row_names, basic_vars, basic_rows, info


def basis_matrix(lp_path, row_names, basic_vars, basic_rows):
    """Assemble the reference basis from this variant's exported matrix.

    Structural basic columns are taken from the variant's (scaled) matrix;
    basic slack columns enter as unit vectors, which is how a solver holds them.
    """
    import gurobipy as gp

    m = gp.read(str(lp_path))
    m.Params.OutputFlag = 0
    ridx = {n: i for i, n in enumerate(row_names)}
    if {c.ConstrName for c in m.getConstrs()} != set(ridx):
        raise ValueError(f'row set differs in {lp_path}')

    byname = {v.VarName: v for v in m.getVars()}
    rows, cols, vals = [], [], []
    ncol = 0
    for name in basic_vars:
        v = byname.get(name)
        if v is None:
            raise ValueError(f'basic variable {name} missing in {lp_path}')
        col = m.getCol(v)
        for k in range(col.size()):
            rows.append(ridx[col.getConstr(k).ConstrName])
            cols.append(ncol)
            vals.append(col.getCoeff(k))
        ncol += 1
    for name in basic_rows:                      # unit slack columns
        rows.append(ridx[name])
        cols.append(ncol)
        vals.append(1.0)
        ncol += 1

    n = len(row_names)
    B = sp.csc_matrix((vals, (rows, cols)), shape=(n, ncol))
    return B


def kappa1(B):
    """kappa_1(B) = ||B||_1 ||B^{-1}||_1, with ||B^{-1}||_1 estimated from a sparse LU."""
    n, k = B.shape
    if n != k:
        return {'kappa1': float('nan'), 'singular': 1, 'note': f'non-square {n}x{k}'}
    norm_B = float(abs(B).sum(axis=0).max())
    try:
        lu = spla.splu(B.tocsc())
    except (RuntimeError, ValueError) as exc:
        return {'kappa1': float('inf'), 'singular': 1, 'note': str(exc)[:60]}
    op = spla.LinearOperator(
        (n, n),
        matvec=lambda x: lu.solve(x),
        rmatvec=lambda x: lu.solve(x, 'T'),
        dtype=np.float64,
    )
    norm_inv = float(spla.onenormest(op))
    return {'kappa1': norm_B * norm_inv, 'singular': 0, 'note': ''}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--instancias', nargs='+', required=True)
    ap.add_argument('--exe', default=str(ROOT / 'code' / 'build_release' / 'SistemaElectrico'))
    ap.add_argument('--mipgap', type=float, default=1e-3)
    ap.add_argument('--timelimit', type=float, default=3600.0)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = ['instance', 'variant', 'kappa1', 'rows', 'basic_structural',
              'basic_slack', 'singular', 'mip_obj', 'mip_gap', 'note']
    rows_out = []

    for spec in args.instancias:
        inst = Path(spec)
        text = clean_instance_text(inst)
        work = Path(tempfile.mkdtemp(prefix='fixbasis_'))
        try:
            lps = {}
            for tag, flags in VARIANTS:
                target = work / f'{tag}.lp'
                if not export_lp(args.exe, text, flags, str(target), args.mipgap):
                    print(f'  {inst.name}: export failed for {tag}', file=sys.stderr)
                    break
                lps[tag] = target
            if len(lps) != len(VARIANTS):
                continue

            ref = reference_basis(lps['Base'], args.mipgap, args.timelimit)
            if ref is None:
                print(f'  {inst.name}: no reference basis', file=sys.stderr)
                continue
            row_names, basic_vars, basic_rows, info = ref

            for tag, _ in VARIANTS:
                try:
                    B = basis_matrix(lps[tag], row_names, basic_vars, basic_rows)
                    res = kappa1(B)
                except ValueError as exc:
                    res = {'kappa1': float('nan'), 'singular': 1, 'note': str(exc)[:60]}
                rows_out.append({
                    'instance': inst.name, 'variant': tag,
                    'kappa1': res['kappa1'], 'rows': info['rows'],
                    'basic_structural': info['basic_structural'],
                    'basic_slack': info['basic_slack'],
                    'singular': res['singular'], 'mip_obj': info['mip_obj'],
                    'mip_gap': info['mip_gap'], 'note': res['note'],
                })
                print('  %-14s %-9s kappa1=%.4e' % (inst.name, tag, res['kappa1']),
                      file=sys.stderr, flush=True)
        finally:
            for f in work.glob('*'):
                f.unlink()
            work.rmdir()

    with open(out, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows_out)
    print(f'wrote {len(rows_out)} rows to {out}', file=sys.stderr)


if __name__ == '__main__':
    main()
