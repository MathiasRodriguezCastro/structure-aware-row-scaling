#!/usr/bin/env python3
"""Rebuild operational paired solver-time tests under the capped-time rule.

``T_max`` is read from each scenario manifest and must equal the operational
protocol value of 3600 s.  A one-sided timeout is right-censored at ``T_max``.
By default, a one-sided algorithmic/pipeline abort is also assigned ``T_max``
as an operational-failure convention; ``--abort-penalty par10`` provides the
pre-specified sensitivity in which it receives ``10*T_max`` instead.  Pairs are
excluded only when both sides fail to complete, when the required solver time
is missing, or when every campaign variant has a non-zero return code on the
instance.  The last category is called ``uniformly unavailable`` and is a data
criterion, not a causal claim.

Wilcoxon is two-sided on ``T_variant-T_base`` with the ``wilcox`` zero method
and no continuity correction.  The exact null distribution is used for at
most 50 nonzero differences when there are no tied absolute ranks; otherwise
the normal approximation with tie correction is used.  Benjamini--Hochberg is
applied separately in each solver-by-gap scenario to its twelve tests (four
variants against Base in each of three classes).  Output reports the manifest
full class pool, the scenario-specific common pool, effective pairs, excluded
categories, test method, and optional instance identifiers.
"""

import argparse
import collections
import csv
import json
import math
import os

from scipy.stats import rankdata, wilcoxon


ROOT = os.path.join(os.path.dirname(__file__), '..')
OPERATIONAL_TMAX = 3600.0
VARIANTS = ['estructurado', 'estructurado_matricial', 'ruiz', 'ruiz_columnas']
LABEL = {
    'estructurado': 'SA-Aug',
    'estructurado_matricial': 'SA-Mat',
    'ruiz': 'Ruiz',
    'ruiz_columnas': 'Ruiz+Cols',
}
SCENARIOS = [
    ('Gurobi', '1%', 0.01, [
        ('Simple', 'validacion-preproc-simple'),
        ('SG-Ter-Mer', 'validacion-preproc-sg-ter-mer'),
        ('Full', 'validacion-preproc-completo'),
    ]),
    ('Gurobi', '0.1%', 0.001, [
        ('Simple', 'validacion-preproc-simple-gap0001'),
        ('SG-Ter-Mer', 'validacion-preproc-sg-ter-mer-gap0001'),
        ('Full', 'validacion-preproc-completo-gap0001'),
    ]),
    ('CPLEX', '1%', 0.01, [
        ('Simple', 'validacion-preproc-simple-cplex-ute'),
        ('SG-Ter-Mer', 'validacion-preproc-sg-ter-mer-cplex-ute'),
        ('Full', 'validacion-preproc-completo-cplex-ute'),
    ]),
    ('CPLEX', '0.1%', 0.001, [
        ('Simple', 'validacion-preproc-simple-cplex-ute-gap0001'),
        ('SG-Ter-Mer', 'validacion-preproc-sg-ter-mer-cplex-ute-gap0001'),
        ('Full', 'validacion-preproc-completo-cplex-ute-gap0001'),
    ]),
]


def classify(row):
    if not row:
        return 'abort'
    # An explicit solver timeout remains a timeout even if a surrounding
    # pipeline step later returned non-zero.
    if row.get('status_solver') == 'TIME_LIMIT':
        return 'timeout'
    if (row.get('rc') == '0' and row.get('status') != 'ERROR'
            and row.get('status_solver') == 'OPTIMAL'):
        return 'ok'
    return 'abort'


def solver_time(row):
    try:
        value = float(row['tiempo_solver_s'])
    except (KeyError, TypeError, ValueError):
        return None
    return value if math.isfinite(value) and value >= 0.0 else None


def bh_adjust(pvalues):
    n = len(pvalues)
    order = sorted(range(n), key=lambda i: pvalues[i])
    adjusted = [math.nan] * n
    running = 1.0
    for rank, index in reversed(list(enumerate(order, 1))):
        running = min(running, pvalues[index] * n / rank)
        adjusted[index] = running
    return adjusted


def rank_biserial(differences):
    # Match scipy.stats.wilcoxon(zero_method='wilcox'): only exact zero
    # differences are removed.
    nonzero = [d for d in differences if d != 0.0]
    if not nonzero:
        return math.nan, len(differences)
    ranks = rankdata([abs(d) for d in nonzero])
    positive = sum(r for r, d in zip(ranks, nonzero) if d > 0)
    negative = sum(r for r, d in zip(ranks, nonzero) if d < 0)
    value = (positive - negative) / (positive + negative)
    return float(value), len(differences) - len(nonzero)


def wilcoxon_method(differences):
    """Choose the test calculation explicitly (SciPy 1.15 ``auto`` rule).

    This keeps the published calculation independent of future changes to
    SciPy's ``method='auto'`` heuristic.  Exact signed-rank probabilities are
    valid only without zero differences or tied absolute ranks.
    """
    nonzero = [d for d in differences if d != 0.0]
    absolute = [abs(d) for d in nonzero]
    has_zeros = len(nonzero) != len(differences)
    has_ties = len(set(absolute)) != len(absolute)
    return ('exact' if len(nonzero) <= 50 and not has_zeros and not has_ties
            else 'asymptotic')


def analyze_class(folder, class_name, expected_solver, expected_gap,
                  abort_penalty):
    directory = os.path.join(ROOT, 'results', folder)
    with open(os.path.join(directory, 'manifest.json')) as fh:
        manifest = json.load(fh)
    tmax = float(manifest['time_limit_seconds'])
    if tmax != OPERATIONAL_TMAX:
        raise ValueError(
            f'{directory}/manifest.json: operational time limit is {tmax:g} s, '
            f'expected {OPERATIONAL_TMAX:g} s')
    if manifest.get('solver') != expected_solver:
        raise ValueError(
            f'{directory}/manifest.json: solver is {manifest.get("solver")!r}, '
            f'expected {expected_solver!r}')
    if manifest.get('instance_class') != class_name:
        raise ValueError(
            f'{directory}/manifest.json: class is {manifest.get("instance_class")!r}, '
            f'expected {class_name!r}')
    if not math.isclose(float(manifest['mipgap']), expected_gap,
                        rel_tol=0.0, abs_tol=1e-12):
        raise ValueError(
            f'{directory}/manifest.json: MIPGap is {manifest["mipgap"]}, '
            f'expected {expected_gap}')
    all_variants = ['base'] + VARIANTS
    if manifest.get('variants') != all_variants:
        raise ValueError(
            f'{directory}/manifest.json: expected variants {all_variants}, '
            f'found {manifest.get("variants")}')
    full_n = int(manifest['num_instances'])
    with open(os.path.join(directory, 'resumen.csv')) as fh:
        rows = list(csv.DictReader(fh))
    by_instance = collections.defaultdict(dict)
    for row in rows:
        key = (row['instancia'], row['variante'])
        if row['variante'] in by_instance[row['instancia']]:
            raise ValueError(f'{directory}/resumen.csv: duplicate row for {key}')
        by_instance[row['instancia']][row['variante']] = row
    if len(by_instance) != full_n:
        raise ValueError(
            f'{directory}/resumen.csv: observed {len(by_instance)} instances, '
            f'manifest declares {full_n}')

    uniform_missing = {
        instance for instance, cells in by_instance.items()
        if all(cells.get(v, {}).get('rc') not in (None, '0') for v in all_variants)
    }
    common_n = full_n - len(uniform_missing)
    output = []
    for variant in VARIANTS:
        reasons = collections.Counter()
        reason_ids = collections.defaultdict(list)
        pairs = []
        for instance, cells in by_instance.items():
            if instance in uniform_missing:
                reasons['uniform_missing'] += 1
                reason_ids['uniform_missing'].append(instance)
                continue
            var_row = cells.get(variant)
            base_row = cells.get('base')
            var_status = classify(var_row)
            base_status = classify(base_row)
            if var_status != 'ok' and base_status != 'ok':
                if var_status == base_status == 'timeout':
                    reason = 'double_timeout'
                elif var_status == base_status == 'abort':
                    reason = 'double_abort'
                else:
                    reason = 'other_double_noncompletion'
                reasons[reason] += 1
                reason_ids[reason].append(instance)
                continue

            def paired_time(row, status):
                if status == 'timeout':
                    return tmax
                if status == 'abort':
                    return abort_penalty * tmax
                return solver_time(row)

            var_time = paired_time(var_row, var_status)
            base_time = paired_time(base_row, base_status)
            if var_time is None or base_time is None:
                reasons['missing_time'] += 1
                reason_ids['missing_time'].append(instance)
                continue
            if var_status != 'ok' or base_status != 'ok':
                reasons['one_sided_capped'] += 1
                reason_ids['one_sided_capped'].append(instance)
                side = 'variant' if var_status != 'ok' else 'base'
                status = var_status if var_status != 'ok' else base_status
                reasons[f'{side}_{status}_capped'] += 1
            pairs.append((var_time, base_time))

        excluded_common = sum(reasons[key] for key in (
            'double_timeout', 'double_abort', 'other_double_noncompletion',
            'missing_time'))
        if len(pairs) + excluded_common != common_n:
            raise AssertionError(
                f'{folder}/{variant}: pair accounting does not match common pool')
        differences = [a - b for a, b in pairs]
        method = wilcoxon_method(differences)
        result = wilcoxon(
            differences, zero_method='wilcox', alternative='two-sided',
            correction=False, method=method)
        r_rb, zeros = rank_biserial(differences)
        output.append({
            'class': class_name,
            'variant': variant,
            'n_full': full_n,
            'n_common': common_n,
            'n_pairs': len(pairs),
            'zeros': zeros,
            'W': float(result.statistic),
            'p': float(result.pvalue),
            'r_rb': r_rb,
            'method': method,
            'reason_ids': {key: sorted(value) for key, value in reason_ids.items()},
            **reasons,
        })
    metadata = {
        'class': class_name,
        'folder': folder,
        'solver': expected_solver,
        'mipgap': expected_gap,
        'time_limit': tmax,
        'n_full': full_n,
        'n_common': common_n,
        'uniform_missing_ids': sorted(uniform_missing),
    }
    return metadata, output


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        '--solver', choices=('gurobi', 'cplex', 'all'), default='all',
        help='solver scenarios to print (default: all)')
    parser.add_argument(
        '--show-ids', action='store_true',
        help='print instance identifiers for every non-empty exclusion/capping category')
    parser.add_argument(
        '--abort-penalty', choices=('tmax', 'par10'), default='tmax',
        help=('one-sided abort cost: T_max for the primary operational convention '
              'or 10*T_max for the sensitivity analysis (default: tmax)'))
    args = parser.parse_args()
    abort_penalty = 1.0 if args.abort_penalty == 'tmax' else 10.0

    for solver, gap_label, expected_gap, groups in SCENARIOS:
        if args.solver != 'all' and args.solver != solver.lower():
            continue
        rows = []
        pools = []
        for class_name, folder in groups:
            pool, class_rows = analyze_class(
                folder, class_name, solver, expected_gap, abort_penalty)
            pools.append(pool)
            rows.extend(class_rows)
        if len(rows) != 12:
            raise AssertionError(
                f'{solver}, {gap_label}: BH family has {len(rows)} tests, expected 12')
        for row, qvalue in zip(rows, bh_adjust([row['p'] for row in rows])):
            row['q_bh'] = qvalue

        print(
            f'=== {solver}, {gap_label}; one-sided abort cost='
            f'{abort_penalty:g}*T_max ===')
        for pool in pools:
            print(
                f"  pool {pool['class']:11s}: common n={pool['n_common']}; "
                f"full N={pool['n_full']}; T_max={pool['time_limit']:g} s; "
                f"uniformly unavailable={len(pool['uniform_missing_ids'])}"
                + (f" {pool['uniform_missing_ids']}" if args.show_ids else ''))
        for row in rows:
            reasons = ', '.join(
                f'{key}={row.get(key, 0)}' for key in (
                    'uniform_missing', 'double_timeout', 'double_abort',
                    'other_double_noncompletion', 'one_sided_capped',
                    'missing_time', 'zeros'))
            print(
                f"{row['class']:11s} {LABEL[row['variant']]:9s} "
                f"n={row['n_pairs']:3d} W={row['W']:7.1f} "
                f"p={row['p']:.8g} q={row['q_bh']:.8g} "
                f"r_rb={row['r_rb']:+.3f} method={row['method']} | {reasons}")
            if args.show_ids:
                for key in (
                        'double_timeout', 'double_abort',
                        'other_double_noncompletion', 'one_sided_capped',
                        'missing_time'):
                    ids = row['reason_ids'].get(key, [])
                    if ids:
                        print(f'    {key}: {ids}')
        print()


if __name__ == '__main__':
    main()
