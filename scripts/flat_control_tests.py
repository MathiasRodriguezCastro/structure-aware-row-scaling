#!/usr/bin/env python3
"""Direct coverage-versus-selectivity audit for the Gurobi control batches.

Every contrast is reconstructed inside one dedicated class-by-tolerance
plano-control batch. Those batches reran both methods and are independent of
the main Base-versus-SA campaign. Two kernel-matched contrasts are used:

* Flat-Aug versus SA-Aug (coefficient-and-right-hand-side kernel), and
* Flat-Mat versus SA-Mat (coefficient-only kernel).

The primary operational endpoint is total pipeline time
T_total = T_preproc + T_solver, because it includes the cost of the
intervention itself; capped solver time is the secondary endpoint that
isolates the subsequent solver response. For both endpoints the primary
paired variable is the log time ratio d_i = log(T_Flat,i / T_SA,i), so the
magnitude, the interval, and the test all live on the same relative scale;
negative values favor full coverage (Flat). A one-sided timeout is
right-censored at T_max=3600 s. A one-sided pipeline/algorithmic abort receives
T_max as an operational-failure convention; use --abort-penalty par10 for the
10*T_max sensitivity. Double non-completions and required missing times are
excluded. The Wilcoxon implementation matches the main analysis.

The script additionally reports:

* BH adjustment within each six-test MIPGap family and jointly over all twelve
  coverage-versus-selectivity tests, separately per endpoint (total time is
  the primary family; solver time and Work are secondary families and add no
  confirmatory claims);
* an exact scenario-family sign-flip sensitivity. The six Simple instances
  casoXX[a-f] form one family, and SG-Ter-Mer instanceXXX and
  instance(XXX+48) form one family; Full has one record per family;
* a 2000-resample scenario-family bootstrap interval for the median log time
  ratio in the two central 0.1%-MIPGap augmented contrasts;
* total time including external preprocessing, deterministic Gurobi Work, and
  the own-incumbent path-specific diagnostic;
* common-pool ITT, strict, and mixed PAR10 for SA and Flat. These use a
  10*T_max failure cost and the verifier thresholds in the manuscript.

Time endpoints use the paired log ratio d_i = log(T_Flat/T_SA); Work (a
deterministic count that can be zero) keeps the paired difference Flat-SA.
Under both conventions negative rank-biserial values favor full coverage
(Flat).
"""

import argparse
import collections
import csv
import math
import os
import random
import re
import statistics

from scipy.stats import rankdata, wilcoxon


ROOT = os.path.join(os.path.dirname(__file__), '..')
TMAX = 3600.0
PAR10_PENALTY = 10.0 * TMAX
STRICT_ROW = 1e-4
STRICT_INT = 1e-5
MIXED_REL = 1e-6
NOMINAL_N = {'Simple': 204, 'SG-Ter-Mer': 68, 'Full': 34}
CONTRASTS = [
    ('Augmented', 'estructurado', 'estructurado_plano', 'SA-Aug', 'Flat-Aug'),
    ('Matrix-only', 'estructurado_matricial', 'matricial_plano',
     'SA-Mat', 'Flat-Mat'),
]
SCENARIOS = [
    ('1%', [
        ('Simple', 'simple-gurobi-1pct'),
        ('SG-Ter-Mer', 'sgtm-gurobi-1pct'),
        ('Full', 'full-gurobi-1pct'),
    ]),
    ('0.1%', [
        ('Simple', 'simple-gurobi-01pct'),
        ('SG-Ter-Mer', 'sgtm-gurobi-01pct'),
        ('Full', 'full-gurobi-01pct'),
    ]),
]


def finite_number(row, key):
    try:
        value = float(row[key])
    except (KeyError, TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def classify(row):
    if not row:
        return 'abort'
    if row.get('status_solver') == 'TIME_LIMIT':
        return 'timeout'
    if (row.get('rc') == '0' and row.get('status') != 'ERROR'
            and row.get('status_solver') == 'OPTIMAL'
            and finite_number(row, 'tiempo_solver_s') is not None):
        return 'ok'
    return 'abort'


def solver_time(row):
    value = finite_number(row, 'tiempo_solver_s')
    return value if value is not None and value >= 0.0 else None


def cost(row, status, abort_multiplier):
    if status == 'timeout':
        return TMAX
    if status == 'abort':
        return abort_multiplier * TMAX
    return solver_time(row)


def total_time(row, status, abort_multiplier):
    """Total-time counterpart of the capped solver-time convention."""
    preprocessing = finite_number(row or {}, 'tiempo_preprocesamiento_s')
    preprocessing = preprocessing if preprocessing is not None else 0.0
    if status == 'timeout':
        return TMAX + preprocessing
    if status == 'abort':
        return abort_multiplier * TMAX + preprocessing
    value = finite_number(row, 'tiempo_total_s')
    if value is not None and value >= 0.0:
        return value
    value = solver_time(row)
    return None if value is None else value + preprocessing


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
    nonzero = [d for d in differences if d != 0.0]
    if not nonzero:
        return 0.0, len(differences)
    ranks = rankdata([abs(d) for d in nonzero])
    positive = sum(rank for rank, diff in zip(ranks, nonzero) if diff > 0)
    negative = sum(rank for rank, diff in zip(ranks, nonzero) if diff < 0)
    return float((positive - negative) / (positive + negative)), (
        len(differences) - len(nonzero))


def test_method(differences):
    nonzero = [d for d in differences if d != 0.0]
    absolute = [abs(d) for d in nonzero]
    has_zeros = len(nonzero) != len(differences)
    has_ties = len(set(absolute)) != len(absolute)
    return ('exact' if len(nonzero) <= 50 and not has_zeros and not has_ties
            else 'asymptotic')


def wilcoxon_summary(differences):
    if not any(d != 0.0 for d in differences):
        return 0.0, 1.0, 0.0, len(differences), 'all-zero'
    method = test_method(differences)
    result = wilcoxon(
        differences, zero_method='wilcox', alternative='two-sided',
        correction=False, method=method)
    effect, zeros = rank_biserial(differences)
    return float(result.statistic), float(result.pvalue), effect, zeros, method


def scenario_family(class_name, instance):
    """Operational family encoded by the released instance identifiers."""
    if class_name == 'Simple':
        match = re.fullmatch(r'caso(\d+)[a-f]\.txt', instance)
        if not match:
            raise ValueError(f'unrecognized Simple identifier: {instance}')
        return f'caso{match.group(1)}'
    if class_name == 'SG-Ter-Mer':
        match = re.fullmatch(r'instance(\d+)\.txt', instance)
        if not match:
            raise ValueError(f'unrecognized SG-Ter-Mer identifier: {instance}')
        number = int(match.group(1))
        return f'instance{number - 48 if number > 48 else number:03d}'
    return instance


def exact_block_sign_p(differences, families):
    """Two-sided exact sign flip with one sign per operational family."""
    nonzero = [
        (difference, family)
        for difference, family in zip(differences, families)
        if difference != 0.0
    ]
    if not nonzero:
        return 1.0, 0
    ranks = rankdata([abs(difference) for difference, _ in nonzero])
    contributions = collections.defaultdict(float)
    for (difference, family), rank in zip(nonzero, ranks):
        contributions[family] += rank if difference > 0.0 else -rank
    integer_contributions = [
        int(round(2.0 * value)) for value in contributions.values()
    ]
    observed = abs(sum(integer_contributions))
    distribution = {0: 1}
    for contribution in integer_contributions:
        weight = abs(contribution)
        updated = collections.defaultdict(int)
        for total, count in distribution.items():
            updated[total + weight] += count
            updated[total - weight] += count
        distribution = updated
    extreme = sum(
        count for total, count in distribution.items()
        if abs(total) >= observed
    )
    return extreme / (2 ** len(integer_contributions)), len(contributions)


def percentile(sorted_values, probability):
    position = (len(sorted_values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = position - lower
    return (sorted_values[lower]
            + fraction * (sorted_values[upper] - sorted_values[lower]))


def cluster_bootstrap_ratio_ci(cluster_logs, repetitions, rng):
    keys = sorted(cluster_logs)
    if not keys:
        return math.nan, math.nan
    estimates = []
    for _ in range(repetitions):
        selected = [rng.choice(keys) for _ in keys]
        sample = [
            value
            for key in selected
            for value in cluster_logs[key]
        ]
        estimates.append(statistics.median(sample))
    estimates.sort()
    lower = percentile(estimates, 0.025)
    upper = percentile(estimates, 0.975)
    return math.exp(lower), math.exp(upper)


def verification_available(row):
    fields = (
        'verif_solver_max_le', 'verif_solver_max_ge',
        'verif_solver_max_eq', 'verif_solver_max_lb',
        'verif_solver_max_ub', 'verif_solver_max_int',
        'verif_solver_max_viol_rel',
    )
    return row is not None and all(
        finite_number(row, field) is not None for field in fields)


def max_row_violation(row):
    fields = (
        'verif_solver_max_le', 'verif_solver_max_ge',
        'verif_solver_max_eq', 'verif_solver_max_lb',
        'verif_solver_max_ub',
    )
    return max(finite_number(row, field) for field in fields)


def strict_fail(row):
    if not verification_available(row):
        return True
    return (max_row_violation(row) > STRICT_ROW
            or finite_number(row, 'verif_solver_max_int') > STRICT_INT)


def mixed_fail(row):
    if not verification_available(row):
        return True
    return (
        finite_number(row, 'verif_solver_max_int') > STRICT_INT
        or (
            max_row_violation(row) > STRICT_ROW
            and finite_number(row, 'verif_solver_max_viol_rel') > MIXED_REL
        )
    )


def reliability_readings(by_instance, pool, variant):
    counts = collections.Counter()
    totals = {'itt': 0.0, 'strict': 0.0, 'mixed': 0.0}
    for instance in pool:
        row = by_instance[instance].get(variant)
        status = classify(row)
        if status != 'ok':
            counts[status] += 1
            for reading in totals:
                totals[reading] += PAR10_PENALTY
            continue
        counts['ok'] += 1
        time = solver_time(row)
        fail_strict = strict_fail(row)
        fail_mixed = mixed_fail(row)
        counts['fail_strict'] += int(fail_strict)
        counts['fail_mixed'] += int(fail_mixed)
        totals['itt'] += time
        totals['strict'] += PAR10_PENALTY if fail_strict else time
        totals['mixed'] += PAR10_PENALTY if fail_mixed else time
    return {
        'n': len(pool),
        'n_ok': counts['ok'],
        'n_timeout': counts['timeout'],
        'n_abort': counts['abort'],
        'n_fail_strict': counts['fail_strict'],
        'n_fail_mixed': counts['fail_mixed'],
        'par_itt': totals['itt'] / len(pool),
        'par_strict': totals['strict'] / len(pool),
        'par_mixed': totals['mixed'] / len(pool),
    }


def read_batch(folder):
    path = os.path.join(
        ROOT, 'results-revision', 'plano-control', folder, 'resumen.csv')
    with open(path, newline='') as handle:
        rows = list(csv.DictReader(handle))
    by_instance = collections.defaultdict(dict)
    for row in rows:
        instance = row['instancia']
        variant = row['variante']
        if variant in by_instance[instance]:
            raise ValueError(f'{path}: duplicate {instance}/{variant}')
        by_instance[instance][variant] = row
    return path, by_instance


def analyze(folder, class_name, abort_multiplier):
    path, by_instance = read_batch(folder)
    observed_n = len(by_instance)
    all_variants = sorted({
        variant for cells in by_instance.values() for variant in cells})
    uniformly_unavailable = {
        instance for instance, cells in by_instance.items()
        if all(cells.get(variant, {}).get('rc') not in (None, '0')
               for variant in all_variants)
    }
    pool = sorted(set(by_instance) - uniformly_unavailable)
    output = []
    for kernel, sa_key, flat_key, sa_label, flat_label in CONTRASTS:
        counts = collections.Counter()
        pairs = []
        families = []
        ratios = []
        total_ratios = []
        total_families = []
        cluster_total_logs = collections.defaultdict(list)
        work_sa = []
        work_flat = []
        work_families = []
        diagnostic_ratios = []
        cluster_logs = collections.defaultdict(list)
        for instance in pool:
            cells = by_instance[instance]
            sa_row = cells.get(sa_key)
            flat_row = cells.get(flat_key)
            sa_status = classify(sa_row)
            flat_status = classify(flat_row)
            if sa_status != 'ok' and flat_status != 'ok':
                counts['double_noncompletion'] += 1
                continue
            sa_time = cost(sa_row, sa_status, abort_multiplier)
            flat_time = cost(flat_row, flat_status, abort_multiplier)
            if sa_time is None or flat_time is None or flat_time <= 0:
                counts['missing_time'] += 1
                continue
            if sa_status == 'timeout' or flat_status == 'timeout':
                counts['one_sided_timeout'] += 1
            if sa_status == 'abort' or flat_status == 'abort':
                counts['one_sided_abort'] += 1

            family = scenario_family(class_name, instance)
            pairs.append((flat_time, sa_time))
            families.append(family)
            ratio = sa_time / flat_time
            ratios.append(ratio)
            cluster_logs[family].append(math.log(ratio))

            sa_total = total_time(sa_row, sa_status, abort_multiplier)
            flat_total = total_time(flat_row, flat_status, abort_multiplier)
            if (sa_total is not None and flat_total is not None
                    and sa_total > 0.0 and flat_total > 0.0):
                total_ratios.append(sa_total / flat_total)
                total_families.append(family)
                cluster_total_logs[family].append(
                    math.log(sa_total / flat_total))

            sa_work_value = finite_number(sa_row or {}, 'work_units')
            flat_work_value = finite_number(flat_row or {}, 'work_units')
            if (sa_work_value is not None and flat_work_value is not None
                    and sa_work_value >= 0.0 and flat_work_value >= 0.0):
                work_sa.append(sa_work_value)
                work_flat.append(flat_work_value)
                work_families.append(family)

            sa_diagnostic = finite_number(
                sa_row or {}, 'kappa_solver_ratio_vs_base')
            flat_diagnostic = finite_number(
                flat_row or {}, 'kappa_solver_ratio_vs_base')
            if (sa_diagnostic is not None and flat_diagnostic is not None
                    and flat_diagnostic > 0.0):
                diagnostic_ratios.append(sa_diagnostic / flat_diagnostic)

        # Primary paired variable on the relative scale: d_i = log(T_Flat/T_SA),
        # negative favors Flat. sign(d_i) = sign(T_Flat - T_SA), so orientation
        # matches the earlier absolute-difference convention; ranks differ.
        differences = [math.log(flat / sa) for flat, sa in pairs]
        statistic, pvalue, effect, zeros, method = wilcoxon_summary(differences)
        p_block, effective_blocks = exact_block_sign_p(differences, families)
        counts['zeros'] = zeros

        total_differences = [
            -math.log(ratio) for ratio in total_ratios]  # log(Flat/SA) totals
        (total_statistic, total_p, total_effect, total_zeros,
         total_method) = wilcoxon_summary(total_differences)
        total_p_block, total_effective_blocks = exact_block_sign_p(
            total_differences, total_families)

        work_differences = [
            flat - sa for flat, sa in zip(work_flat, work_sa)
        ]
        (work_statistic, work_p, work_effect, work_zeros,
         work_method) = wilcoxon_summary(work_differences)
        work_p_block, work_effective_blocks = exact_block_sign_p(
            work_differences, work_families)

        output.append({
            'class': class_name,
            'folder': folder,
            'path': path,
            'kernel': kernel,
            'sa': sa_label,
            'flat': flat_label,
            'nominal_n': NOMINAL_N[class_name],
            'observed_n': observed_n,
            'common_n': len(pool),
            'n': len(pairs),
            'n_families': len(set(families)),
            'effective_blocks': effective_blocks,
            'median_ratio': statistics.median(ratios),
            'n_total': len(total_ratios),
            'median_total_ratio': statistics.median(total_ratios),
            'n_total_families': len(set(total_families)),
            'total_W': total_statistic,
            'total_p': total_p,
            'total_r_rb': total_effect,
            'total_zeros': total_zeros,
            'total_method': total_method,
            'total_p_block': total_p_block,
            'total_effective_blocks': total_effective_blocks,
            'n_work': len(work_differences),
            'median_work_sa': statistics.median(work_sa),
            'median_work_flat': statistics.median(work_flat),
            'median_shifted_work_ratio': statistics.median(
                (1.0 + sa) / (1.0 + flat)
                for sa, flat in zip(work_sa, work_flat)),
            'work_W': work_statistic,
            'work_p': work_p,
            'work_r_rb': work_effect,
            'work_zeros': work_zeros,
            'work_method': work_method,
            'work_p_block': work_p_block,
            'work_effective_blocks': work_effective_blocks,
            'n_diagnostic': len(diagnostic_ratios),
            'median_diagnostic_ratio': statistics.median(diagnostic_ratios),
            'W': statistic,
            'p': pvalue,
            'p_block': p_block,
            'r_rb': effect,
            'method': method,
            'sa_reliability': reliability_readings(
                by_instance, pool, sa_key),
            'flat_reliability': reliability_readings(
                by_instance, pool, flat_key),
            '_cluster_logs': cluster_logs,
            '_cluster_total_logs': cluster_total_logs,
            **counts,
        })
    return output


def format_reliability(reading):
    return (
        f"TO={reading['n_timeout']} abort={reading['n_abort']} "
        f"fail_s/m={reading['n_fail_strict']}/{reading['n_fail_mixed']} "
        f"PAR10_ITT/s/m={reading['par_itt']:.1f}/"
        f"{reading['par_strict']:.1f}/{reading['par_mixed']:.1f}"
    )


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        '--abort-penalty', choices=('tmax', 'par10'), default='tmax',
        help='one-sided abort cost in paired tests (default: tmax)')
    parser.add_argument(
        '--bootstrap-reps', type=int, default=2000,
        help='scenario-family bootstrap replicates for the two central contrasts')
    parser.add_argument(
        '--bootstrap-seed', type=int, default=12345,
        help='fixed bootstrap RNG seed (default: 12345)')
    args = parser.parse_args()
    if args.bootstrap_reps <= 0:
        parser.error('--bootstrap-reps must be positive')
    abort_multiplier = 1.0 if args.abort_penalty == 'tmax' else 10.0

    rows_by_gap = {}
    all_rows = []
    for gap, batches in SCENARIOS:
        rows = []
        for class_name, folder in batches:
            rows.extend(analyze(folder, class_name, abort_multiplier))
        if len(rows) != 6:
            raise AssertionError(f'{gap}: expected six direct comparisons')
        for row, qvalue in zip(rows, bh_adjust([row['p'] for row in rows])):
            row['q_bh6'] = qvalue
        for row, qvalue in zip(
                rows, bh_adjust([row['p_block'] for row in rows])):
            row['q_block6'] = qvalue
        for row, qvalue in zip(
                rows, bh_adjust([row['total_p'] for row in rows])):
            row['total_q_bh6'] = qvalue
        for row, qvalue in zip(
                rows, bh_adjust([row['total_p_block'] for row in rows])):
            row['total_q_block6'] = qvalue
        for row, qvalue in zip(
                rows, bh_adjust([row['work_p'] for row in rows])):
            row['work_q_bh6'] = qvalue
        for row, qvalue in zip(
                rows, bh_adjust([row['work_p_block'] for row in rows])):
            row['work_q_block6'] = qvalue
        rows_by_gap[gap] = rows
        all_rows.extend(rows)

    for key, pkey in (
            ('q_bh12', 'p'),
            ('q_block12', 'p_block'),
            ('total_q_bh12', 'total_p'),
            ('total_q_block12', 'total_p_block'),
            ('work_q_bh12', 'work_p'),
            ('work_q_block12', 'work_p_block')):
        for row, qvalue in zip(
                all_rows, bh_adjust([row[pkey] for row in all_rows])):
            row[key] = qvalue

    central_order = [
        ('0.1%', 'Simple', 'Augmented'),
        ('0.1%', 'SG-Ter-Mer', 'Augmented'),
    ]
    bootstrap_rng = random.Random(args.bootstrap_seed)
    for gap, class_name, kernel in central_order:
        row = next(
            candidate for candidate in rows_by_gap[gap]
            if candidate['class'] == class_name
            and candidate['kernel'] == kernel)
        row['bootstrap_ratio_ci'] = cluster_bootstrap_ratio_ci(
            row['_cluster_logs'], args.bootstrap_reps, bootstrap_rng)
        row['bootstrap_total_ratio_ci'] = cluster_bootstrap_ratio_ci(
            row['_cluster_total_logs'], args.bootstrap_reps, bootstrap_rng)

    for gap, _ in SCENARIOS:
        print(
            f'=== Gurobi {gap}; direct Flat vs SA; one-sided abort cost='
            f'{abort_multiplier:g}*T_max ===')
        for row in rows_by_gap[gap]:
            print(
                f"{row['class']:11s} {row['kernel']:11s} "
                f"attempted={row['observed_n']:3d}/{row['nominal_n']:3d} "
                f"pool={row['common_n']:3d} n={row['n']:3d} "
                f"G={row['n_families']:2d} "
                f"dnc={row.get('double_noncompletion', 0)} "
                f"mt={row.get('missing_time', 0)} "
                f"zeros={row.get('zeros', 0)} "
                f"med(Tsolver_SA/Flat)={row['median_ratio']:.4f} "
                f"med(Ttotal_SA/Flat)={row['median_total_ratio']:.4f} | "
                f"TOTAL n={row['n_total']} p={row['total_p']:.8g} "
                f"q6={row['total_q_bh6']:.8g} q12={row['total_q_bh12']:.8g} "
                f"r_rb={row['total_r_rb']:+.3f} "
                f"p_block={row['total_p_block']:.8g} "
                f"q_block6={row['total_q_block6']:.8g} "
                f"q_block12={row['total_q_block12']:.8g} | "
                f"SOLVER p={row['p']:.8g} q6={row['q_bh6']:.8g} "
                f"q12={row['q_bh12']:.8g} "
                f"r_rb={row['r_rb']:+.3f} "
                f"p_block={row['p_block']:.8g} "
                f"q_block6={row['q_block6']:.8g} "
                f"q_block12={row['q_block12']:.8g} | "
                f"Work n={row['n_work']} zeros={row['work_zeros']} "
                f"med_shifted_ratio={row['median_shifted_work_ratio']:.4f} "
                f"p_block={row['work_p_block']:.8g} "
                f"q_block6={row['work_q_block6']:.8g} | "
                f"own_inc_rho={row['median_diagnostic_ratio']:.4f} "
                f"(n={row['n_diagnostic']})")
            print(f"  SA   {format_reliability(row['sa_reliability'])}")
            print(f"  Flat {format_reliability(row['flat_reliability'])}")

    print('=== Central 0.1%-MIPGap magnitude/dependence sensitivity ===')
    for gap, class_name, kernel in central_order:
        row = next(
            candidate for candidate in rows_by_gap[gap]
            if candidate['class'] == class_name
            and candidate['kernel'] == kernel)
        lower, upper = row['bootstrap_ratio_ci']
        total_lower, total_upper = row['bootstrap_total_ratio_ci']
        print(
            f"{class_name:11s} {kernel:11s} n={row['n']} "
            f"G={row['n_families']} median={row['median_ratio']:.8f} "
            f"cluster_bootstrap95=[{lower:.8f},{upper:.8f}] "
            f"total_median={row['median_total_ratio']:.8f} "
            f"total_bootstrap95=[{total_lower:.8f},{total_upper:.8f}] "
            f"total_p/q6/q12_block={row['total_p_block']:.8g}/"
            f"{row['total_q_block6']:.8g}/{row['total_q_block12']:.8g} "
            f"time_p/q6/q12_block={row['p_block']:.8g}/"
            f"{row['q_block6']:.8g}/{row['q_block12']:.8g} "
            f"Work_med_SA/Flat={row['median_work_sa']:.6g}/"
            f"{row['median_work_flat']:.6g} zeros={row['work_zeros']} "
            f"Work_r_rb={row['work_r_rb']:+.6f} "
            f"Work_p/q6/q12_block={row['work_p_block']:.8g}/"
            f"{row['work_q_block6']:.8g}/"
            f"{row['work_q_block12']:.8g}")


if __name__ == '__main__':
    main()
