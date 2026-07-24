#!/usr/bin/env python3
"""Rebuild the operational three-reading PAR10 audit from aggregate results.

The time limit is read from each scenario's ``manifest.json`` and must equal the
operational protocol value ``T_max = 3600 s``.  Consequently, the PAR10 penalty
is ``10*T_max = 36000 s`` for every operational class, including Simple.

Per-run cost, for reading k in {ITT, strict, mixed}:

    c_ITT    = t_iv                       if the run terminates normally (solver OPTIMAL)
             = 10 * T_max                 if it times out or aborts
    c_strict = c_ITT                      if it passes the strict absolute check
             = 10 * T_max                 if it completes but fails the strict check
    c_mixed  = c_ITT                      if it passes the mixed absolute-relative check
             = 10 * T_max                 if it completes but fails the mixed check

    PAR10^(k)_v = (1/n) * sum_i c_iv^(k)    over the common operational pool.

Strict absolute check: max original-scale row violation <= 1e-4 and max
integrality violation <= 1e-5.  Under the mixed check, an absolute row failure
is genuine only when its RHS-normalized residual v_r/(1+|b_r|) also exceeds
1e-6; integrality retains its absolute 1e-5 threshold.

The scenario-specific common pool excludes only instances with a non-zero
pipeline return code under every attempted variant.  The script calls these
instances ``uniformly unavailable``: that is a reproducible data criterion, not
by itself a causal claim about infrastructure.  Per-variant aborts on all other
instances remain in the pool and are penalized.  With
``--full-pool-sensitivity``, uniformly unavailable cells are also penalized on
the original class pool declared by the manifest.
"""
import argparse
import collections
import csv
import json
import math
import os
import sys

OPERATIONAL_TMAX = 3600.0
VARIANTS = ['base', 'estructurado', 'estructurado_matricial', 'ruiz', 'ruiz_columnas']
LABEL = {'base': 'Base', 'estructurado': 'SA-Aug', 'estructurado_matricial': 'SA-Mat',
         'ruiz': 'Ruiz', 'ruiz_columnas': 'Ruiz+Cols'}
STRICT_ROW = 1e-4
STRICT_INT = 1e-5
MIXED_REL = 1e-6

ROOT = os.path.join(os.path.dirname(__file__), '..')
SCENARIOS = [
    ('Simple, $1\\%$', 'validacion-preproc-simple'),
    ('SG-Ter-Mer, $1\\%$', 'validacion-preproc-sg-ter-mer'),
    ('Full, $1\\%$', 'validacion-preproc-completo'),
    ('Simple, $0.1\\%$', 'validacion-preproc-simple-gap0001'),
    ('SG-Ter-Mer, $0.1\\%$', 'validacion-preproc-sg-ter-mer-gap0001'),
    ('Full, $0.1\\%$', 'validacion-preproc-completo-gap0001'),
]

CPLEX_SCENARIOS = [
    ('Simple, $1\\%$', 'validacion-preproc-simple-cplex-ute'),
    ('SG-Ter-Mer, $1\\%$', 'validacion-preproc-sg-ter-mer-cplex-ute'),
    ('Full, $1\\%$', 'validacion-preproc-completo-cplex-ute'),
    ('Simple, $0.1\\%$', 'validacion-preproc-simple-cplex-ute-gap0001'),
    ('SG-Ter-Mer, $0.1\\%$', 'validacion-preproc-sg-ter-mer-cplex-ute-gap0001'),
    ('Full, $0.1\\%$', 'validacion-preproc-completo-cplex-ute-gap0001'),
]


def f(x):
    try:
        value = float(x)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def max_row_viol(r):
    vals = [f(r.get(k)) for k in ('verif_solver_max_le', 'verif_solver_max_ge',
            'verif_solver_max_eq', 'verif_solver_max_lb', 'verif_solver_max_ub')]
    return max([x for x in vals if x is not None], default=0.0)


def int_viol(r):
    return f(r.get('verif_solver_max_int')) or 0.0


def rel_viol(r):
    # R5: the mixed reading normalizes the row residual by the row ACTIVITY,
    # max{1,|b_r|,Sum_j|a_rj x_j|}, reported by the binary as
    # verif_solver_max_viol_relact.  This replaces the RHS-only form (1+|b_r|),
    # which under-normalizes rows whose activity is large while the right-hand side
    # is small -- exactly the zero-RHS balance rows on which the failures concentrate.
    # Fall back to the RHS-only column for CSVs produced before the activity
    # denominator existed.
    v = f(r.get('verif_solver_max_viol_relact'))
    if v is None:
        v = f(r.get('verif_solver_max_viol_rel'))
    return v or 0.0


def classify(r):
    """Return one of: 'ok', 'timeout', 'abort'. 'ok' = solver terminated normally."""
    if not r:
        return 'abort'
    ss = r.get('status_solver', '')
    # Preserve an explicit solver timeout even if a surrounding pipeline later
    # returned non-zero; both receive the same PAR10 cost, but the audit counts
    # should distinguish solver censoring from an abort.
    if ss == 'TIME_LIMIT':
        return 'timeout'
    if (r.get('rc') == '0' and r.get('status') != 'ERROR'
            and ss == 'OPTIMAL' and f(r.get('tiempo_solver_s')) is not None):
        return 'ok'
    # anything else (empty, INFEASIBLE, ...) is a non-normal termination -> abort
    return 'abort'


def strict_fail(r):
    if not verification_available(r):
        return True
    return max_row_viol(r) > STRICT_ROW or int_viol(r) > STRICT_INT


def mixed_fail(r):
    if not verification_available(r):
        return True
    # The relative rescue applies only to row feasibility.  Integrality keeps
    # its absolute threshold under both reliability-adjusted readings.
    return (int_viol(r) > STRICT_INT
            or (max_row_viol(r) > STRICT_ROW and rel_viol(r) > MIXED_REL))


def verification_available(r):
    fields = (
        'verif_solver_max_le', 'verif_solver_max_ge', 'verif_solver_max_eq',
        'verif_solver_max_lb', 'verif_solver_max_ub', 'verif_solver_max_int',
        'verif_solver_max_viol_rel',
    )
    return all(f(r.get(field)) is not None for field in fields)


def analyze(csv_path, manifest_path=None):
    if manifest_path is None:
        manifest_path = os.path.join(os.path.dirname(csv_path), 'manifest.json')
    with open(manifest_path) as fh:
        manifest = json.load(fh)
    tmax = float(manifest['time_limit_seconds'])
    if tmax != OPERATIONAL_TMAX:
        raise ValueError(
            f'{manifest_path}: operational time limit is {tmax:g} s, expected '
            f'{OPERATIONAL_TMAX:g} s')
    penalty = 10.0 * tmax
    full_n = int(manifest['num_instances'])
    with open(csv_path) as fh:
        rows = list(csv.DictReader(fh))
    manifest_variants = manifest.get('variants', [])
    variants = [v for v in VARIANTS if v in manifest_variants]
    if variants != VARIANTS:
        raise ValueError(
            f'{manifest_path}: expected variants {VARIANTS}, found {manifest_variants}')
    byinst = collections.defaultdict(dict)
    for r in rows:
        key = (r['instancia'], r['variante'])
        if r['variante'] in byinst[r['instancia']]:
            raise ValueError(f'{csv_path}: duplicate row for {key}')
        byinst[r['instancia']][r['variante']] = r
    if len(byinst) != full_n:
        raise ValueError(
            f'{csv_path}: observed {len(byinst)} instances, manifest declares {full_n}')
    # Uniformly unavailable according to the campaign records: every variant has a
    # non-zero pipeline return code.  This is a reproducible exclusion criterion,
    # not by itself proof that the underlying cause was external infrastructure.
    uniform_missing = sorted(
        i for i, d in byinst.items()
        if all(d.get(v, {}).get('rc') not in (None, '0') for v in variants))
    pool = [i for i in byinst if i not in uniform_missing]
    n = len(pool)
    if n == 0:
        raise ValueError(f'{csv_path}: common operational pool is empty')
    out = {
        'n': n,
        'full_n': full_n,
        'uniform_missing': uniform_missing,
        'time_limit': tmax,
        'penalty': penalty,
        'manifest': manifest,
        'variants': {},
    }
    for v in variants:
        cITT = cS = cM = 0.0
        nTO = nAB = nOK = nFS = nFM = 0
        for i in pool:
            r = byinst[i].get(v)
            if r is None:
                # missing cell on a pooled instance: treat as abort (penalized)
                cITT += penalty; cS += penalty; cM += penalty; nAB += 1
                continue
            cls = classify(r)
            if cls == 'timeout':
                cITT += penalty; cS += penalty; cM += penalty; nTO += 1
            elif cls == 'abort':
                cITT += penalty; cS += penalty; cM += penalty; nAB += 1
            else:  # ok
                nOK += 1
                t = f(r.get('tiempo_solver_s'))
                assert t is not None  # guaranteed by classify()
                cITT += t
                sf = strict_fail(r)
                mf = mixed_fail(r)
                cS += penalty if sf else t
                cM += penalty if mf else t
                if sf:
                    nFS += 1
                if mf:
                    nFM += 1
        out['variants'][v] = dict(
            par_itt=cITT / n, par_strict=cS / n, par_mixed=cM / n,
            n_attempted=n, n_completed=nOK, nTO=nTO, nAB=nAB,
            nFS=nFS, nFM=nFM, nPS=nOK - nFS, nPM=nOK - nFM)
    return out


def full_pool_sensitivity(result, variant):
    """Penalize every uniformly unavailable cell on the original class pool."""
    s = result['variants'][variant]
    missing = result['full_n'] - result['n']
    return {
        key: (result['n'] * s[key] + missing * result['penalty']) / result['full_n']
        for key in ('par_itt', 'par_strict', 'par_mixed')
    }


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        '--all-solvers', action='store_true',
        help='also print the six CPLEX operational scenarios used in Supporting Information')
    parser.add_argument(
        '--full-pool-sensitivity', action='store_true',
        help='also penalize uniformly unavailable cells on the original class pool')
    args = parser.parse_args()

    scenarios = SCENARIOS + (CPLEX_SCENARIOS if args.all_solvers else [])
    for label, folder in scenarios:
        path = os.path.join(ROOT, 'results', folder, 'resumen.csv')
        if not os.path.exists(path):
            print(f'# MISSING {path}', file=sys.stderr)
            continue
        res = analyze(path)
        solver = res['manifest']['solver']
        missing = res['uniform_missing']
        print(f'=== {solver}: {label}  (folder {folder}) ===')
        print(f'  common pool n={res["n"]}; full class pool N={res["full_n"]}; '
              f'uniformly unavailable({len(missing)}): {missing}')
        print(f'  T_max={res["time_limit"]:g} s; PAR10 penalty={res["penalty"]:g} s')
        for v in VARIANTS:
            if v not in res['variants']:
                continue
            s = res['variants'][v]
            print('  %-9s ITT=%7.0f strict=%7.0f mixed=%7.0f | '
                  'attempted=%d completed=%d nTO=%d nAb=%d '
                  'pass_strict=%d pass_mixed=%d fail_strict=%d fail_mixed=%d'
                  % (LABEL[v], s['par_itt'], s['par_strict'], s['par_mixed'],
                     s['n_attempted'], s['n_completed'], s['nTO'], s['nAB'],
                     s['nPS'], s['nPM'], s['nFS'], s['nFM']))
            if args.full_pool_sensitivity and missing:
                fs = full_pool_sensitivity(res, v)
                print('             full-pool sensitivity: '
                      'ITT=%7.0f strict=%7.0f mixed=%7.0f'
                      % (fs['par_itt'], fs['par_strict'], fs['par_mixed']))
        print()


if __name__ == '__main__':
    main()
