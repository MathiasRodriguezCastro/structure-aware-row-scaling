#!/usr/bin/env python3
"""Prespecified paired analysis; resample entire parents, never individual seeds."""
from collections import defaultdict
import hashlib
import math
import numpy as np
from runner import HERE, load, save, sha
from collect_confirmation import read_blocks


def cluster_interval(values, parents, seed, logarithmic, all_parents=None):
    keys = sorted(set(parents if all_parents is None else all_parents))
    totals, counts = [], []
    for parent in keys:
        selected = [v for v, p in zip(values, parents) if p == parent]
        totals.append(sum(selected)); counts.append(len(selected))
    totals, counts = np.asarray(totals), np.asarray(counts)
    rng = np.random.default_rng(seed)
    statistics = []
    for _ in range(10):
        indices = rng.integers(0, len(keys), size=(10000, len(keys)))
        denominators = counts[indices].sum(axis=1)
        numerators = totals[indices].sum(axis=1)
        statistics.append(numerators[denominators > 0] / denominators[denominators > 0])
    samples = np.concatenate(statistics)
    assert len(samples), 'No defined bootstrap replicate.'
    lo, hi = np.percentile(samples, [2.5, 97.5])
    if logarithmic:
        lo, hi = math.exp(lo), math.exp(hi)
    return dict(interval_95=[float(lo), float(hi)], resamples=100000,
                defined_resamples=len(samples), parent_blocks=len(keys),
                interval_type='marginal percentile; whole-parent blocks with nested horizons/seeds and fixed eligibility')


def summarize_pairs(pairs, solver, stratum, comparator, bootstrap_seed):
    result = dict(solver=solver, stratum=stratum, numerator='Budget-L2', denominator=comparator,
        paired_assignments=len(pairs), parents=len({a['job']['parent_id'] for a, b in pairs}),
        numerator_successes=sum(a['success'] for a, b in pairs),
        denominator_successes=sum(b['success'] for a, b in pairs), metrics={})
    if not pairs:
        return result
    differences = [float(a['success']) - float(b['success']) for a, b in pairs]
    parents = [a['job']['parent_id'] for a, b in pairs]
    delta = dict(value=sum(differences) / len(differences))
    if comparator == 'L2':
        delta.update(cluster_interval(differences, parents, bootstrap_seed, False))
    result['success_rate_difference'] = delta
    for metric in ['par2_seconds', 'complete_process_seconds', 'solver_work', 'verified_available_seconds']:
        usable = [(a, b) for a, b in pairs if a.get(metric) is not None and b.get(metric) is not None
                  and a[metric] > 0 and b[metric] > 0]
        item = dict(paired_assignments=len(usable), unavailable_pairs=len(pairs) - len(usable),
                    conditional_on_common_success=metric == 'verified_available_seconds')
        if usable:
            logs = [math.log(a[metric] / b[metric]) for a, b in usable]
            item.update(geometric_mean_paired_ratio=math.exp(sum(logs) / len(logs)),
                        numerator_lower_count=sum(a[metric] < b[metric] for a, b in usable))
            if comparator == 'L2':
                item.update(cluster_interval(logs, [a['job']['parent_id'] for a, b in usable],
                    bootstrap_seed, True, all_parents=parents))
        result['metrics'][metric] = item
    return result


def main():
    execution = load(HERE / 'CONFIRMATION_EXECUTION_REPORT.json')
    if execution['status'] != 'complete_verified':
        save(HERE / 'CONFIRMATION_ANALYSIS.json', dict(status='not_analyzed_incomplete_execution',
            execution_report_sha256=sha(HERE / 'CONFIRMATION_EXECUTION_REPORT.json'),
            optimizer_calls=0, no_outcomes_imputed=True))
        raise RuntimeError('Full independently verified execution is required for policy comparisons.')
    plan, rows, reports, missing = read_blocks()
    assert not missing and len(rows) == 3840 and all(r['status'] == 'passed' for r in reports)
    eligible = [r for r in rows if r['quality_evaluable'] and not r['diagnostic']]
    assert len(eligible) == 3816
    indexed = {(r['job']['instance'], r['job']['seed'], r['job']['solver'], r['job']['policy']): r for r in eligible}
    comparisons = []
    for solver in ['gurobi', 'cplex']:
        numeric = 'L2-NF3' if solver == 'gurobi' else 'L2-NumEmphasis'
        for comparator in ['L2', 'Base', numeric]:
            pairs = []
            for row in eligible:
                j = row['job']
                if j['solver'] == solver and j['policy'] == 'Budget-L2':
                    pairs.append((row, indexed[j['instance'], j['seed'], solver, comparator]))
            for stratum in ['all', 'simple', 'sgtm', 'completo', 'h24', 'h72', 'h168', 'h360']:
                subset = [(a, b) for a, b in pairs if stratum == 'all' or stratum == a['job']['family']
                          or stratum == 'h' + str(a['job']['horizon'])]
                seed = plan['analysis']['bootstrap_seed'] + int.from_bytes(hashlib.sha256((solver + '/' + stratum).encode()).digest()[:4], 'big')
                comparisons.append(summarize_pairs(subset, solver, stratum, comparator, seed))
    policy_counts = []
    groups = defaultdict(list)
    for row in eligible:
        groups[row['job']['solver'], row['job']['policy']].append(row)
    for (solver, policy), group in sorted(groups.items()):
        policy_counts.append(dict(solver=solver, policy=policy, assignments=len(group),
            verified_target_successes=sum(r['success'] for r in group),
            final_primal_pass=sum(bool(r.get('final', {}).get('primal_pass')) for r in group if r.get('final')),
            final_candidates=sum(r.get('final') is not None for r in group),
            native_gap_stops=sum(r.get('native_gap_stop', False) for r in group),
            bound_comparisons=sum(r.get('bound_comparison_available', False) for r in group),
            detected_bound_contradictions=sum(r.get('bound_contradiction') is True for r in group)))
    report = dict(status='analyzed', primary_comparison='Budget-L2 / L2, separately by solver',
        primary_endpoint='postsolve verified availability PAR2; not online stopping',
        comparisons=comparisons, policy_counts=policy_counts, optimizer_calls=0,
        confirmation_plan_sha256=sha(HERE / 'CONFIRMATION_PLAN.json'),
        execution_report_sha256=sha(HERE / 'CONFIRMATION_EXECUTION_REPORT.json'),
        simple_representations_identical=True, certified_MILP_optimality_claimed=False,
        observed_operational_independence=False, work_is_censored_and_not_equal_quality_certification=True,
        marginal_intervals_not_simultaneous=True, interval_containing_one_is_not_equivalence=True)
    save(HERE / 'CONFIRMATION_ANALYSIS.json', report)
    lines = ['# Campaña confirmatoria ORF', '',
        '3.840 ejecuciones registradas: 3.816 con calidad evaluable y 24 diagnósticas. '
        'Todos los bloques pasaron su reproducción independiente.', '',
        '## Comparación primaria Budget-L2/L2', '',
        '| Solver | Estrato | Pares | Éxitos Budget/L2 | PAR2 (IC 95%) | Trabajo | Tiempo completo |',
        '| --- | --- | ---: | --- | --- | ---: | ---: |']
    def number(item):
        value = item.get('geometric_mean_paired_ratio')
        return 'NA' if value is None else f'{value:.3f}'
    for item in comparisons:
        if item['denominator'] != 'L2':
            continue
        metrics = item['metrics']; primary = metrics.get('par2_seconds', {})
        interval = primary.get('interval_95')
        text = number(primary) + (f" [{interval[0]:.3f}, {interval[1]:.3f}]" if interval else '')
        lines.append(f"| {item['solver']} | {item['stratum']} | {item['paired_assignments']} | "
            f"{item['numerator_successes']}/{item['denominator_successes']} | {text} | "
            f"{number(metrics.get('solver_work', {}))} | {number(metrics.get('complete_process_seconds', {}))} |")
    lines += ['', 'Las razones son medias geométricas emparejadas. El bootstrap remuestrea '
        '100.000 veces los padres completos, conservando horizontes, semillas y elegibilidad. '
        'Los intervalos son marginales. Un intervalo que contiene uno no demuestra equivalencia.', '',
        'Simple produce representaciones L2 y Budget-L2 idénticas: sus diferencias de tiempo '
        'o trabajo no prueban un beneficio de modificar factores. Los bancos son recombinaciones '
        'históricas con exposición previa documentada, no observaciones operativas nuevas independientes.', '',
        'La referencia es una solución factible verificada, no un óptimo MILP. La ausencia '
        'de contradicciones detectadas no certifica cotas ni optimalidad. El trabajo a un límite '
        'finito conserva censura y no equivale a una comparación a calidad certificada igual.', '',
        'El PAR2 usa la disponibilidad verificada después del solver en los éxitos y '
        'dos veces el límite más preparación en los objetivos no alcanzados. Los tiempos '
        'en éxitos comunes son condicionales y se reportan separados. El alcance físico '
        'conserva el mapa congelado: las otras filas se controlan por error relativo hacia atrás.', '',
        'El manuscrito y su generador original permanecen sin cambios. Estos resultados '
        'requieren valoración científica antes de incorporarlos al artículo.', '']
    (HERE / 'INFORME_CONFIRMACION.md').write_text('\n'.join(lines))
    print('Paired confirmation analysis complete; no paper changes.', flush=True)


if __name__ == '__main__':
    import sys
    if sys.flags.optimize:
        raise RuntimeError('Run without -O; integrity assertions are required.')
    main()
