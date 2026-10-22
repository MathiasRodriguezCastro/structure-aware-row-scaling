#!/usr/bin/env python3
"""Close the verified campaign and describe its scope without changing the paper."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from fractions import Fraction as Q
import json
from pathlib import Path
import subprocess
import sys

from seal_confirmation import digest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(path):
    return json.loads(path.read_text())


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main(check_raw):
    plan = load(HERE / 'CONFIRMATION_PLAN.json')
    validation = load(HERE / 'CONFIRMATION_ANALYSIS_VALIDATION_PLAN.json')
    proof = load(HERE / 'CONFIRMATION_ANALYSIS_REPLAY.json')
    analysis = load(HERE / 'CONFIRMATION_ANALYSIS.json')
    execution = load(HERE / 'CONFIRMATION_EXECUTION_REPORT.json')
    raw = load(HERE / 'CONFIRMATION_RAW_MANIFEST.json')
    assert execution['status'] == 'complete_verified' and execution['replayed_assignments'] == 3840
    assert not execution['missing_jobs'] and not execution['failed_jobs']
    assert proof['status'] == 'passed' and proof['comparisons_reproduced'] == 48
    assert proof['bootstrap_intervals_reproduced'] == 80
    assert analysis['status'] == 'analyzed'
    for filename, expected in plan['dependencies'].items():
        assert digest(ROOT / filename) == expected, filename
    for filename, expected in validation['sources'].items():
        assert digest(ROOT / filename) == expected, filename
    for filename, expected in proof['input_sha256'].items():
        assert digest(HERE / filename) == expected, filename
    post_manifest = load(HERE / 'CONFIRMATION_ANALYSIS_VALIDATION_MANIFEST.json')
    for item in post_manifest['files']:
        path = ROOT / item['path']
        assert path.stat().st_size == item['bytes'] and digest(path) == item['sha256'], item['path']
    assert post_manifest['original_raw_manifest_sha256'] == digest(HERE / 'CONFIRMATION_RAW_MANIFEST.json')
    sealed = {r['path']: r for r in raw['files']}
    groups = defaultdict(Counter)
    bounds = defaultdict(list)
    for i in range(480):
        path = HERE / 'confirmation-replay' / f'{i:03d}.json'
        item = sealed[path.relative_to(ROOT).as_posix()]
        assert digest(path) == item['sha256'] and path.stat().st_size == item['bytes']
        report = load(path)
        assert report['status'] == 'passed' and report['confirmation_plan_sha256'] == digest(HERE / 'CONFIRMATION_PLAN.json')
        for row in report['rows']:
            if row['diagnostic']:
                continue
            final = row.get('final')
            assert final is not None
            key = row['job']['solver'], row['job']['policy']
            count = groups[key]
            count['final_candidates'] += 1
            for flag in ['physical_pass', 'domain_pass', 'other_rows_pass', 'primal_pass', 'quality_pass']:
                count[flag] += bool(final.get(flag))
            if not final['domain_pass']:
                count['failed_domain'] += 1
                violation = Q(final['max_bound_violation'])
                if violation > 0:
                    count['positive_bound_violation'] += 1
                    bounds[key].append(violation)
                count['integrality_above_1e-9'] += Q(final['max_integrality']) > Q.from_float(1e-9)
    diagnostics = []
    official = {(r['solver'], r['policy']): r for r in analysis['policy_counts']}
    for key, count in sorted(groups.items()):
        assert count['final_candidates'] == 477
        assert count['primal_pass'] == official[key]['final_primal_pass']
        if key[0] == 'cplex':
            assert count['failed_domain'] == count['positive_bound_violation']
            assert count['integrality_above_1e-9'] == 0
        violation = bounds[key]
        diagnostics.append(dict(solver=key[0], policy=key[1], counts=dict(count),
            positive_bound_violation_range_exact=[str(min(violation)), str(max(violation))] if violation else None,
            positive_bound_violation_range_float=[float(min(violation)), float(max(violation))] if violation else None,
            bound_comparisons=official[key]['bound_comparisons'],
            detected_bound_contradictions=official[key]['detected_bound_contradictions']))
    cplex_bounds = [value for key, values in bounds.items() if key[0] == 'cplex' for value in values]
    assert sum(r['counts']['physical_pass'] for r in diagnostics) == 3816
    save(HERE / 'CONFIRMATION_FINAL_DIAGNOSTICS.json', dict(
        status='derived_from_complete_verified_campaign', posthoc_descriptive_diagnostic=True,
        primary_endpoint_modified=False, rows=diagnostics, final_candidates=3816,
        interpretation='Final vectors only; target success may instead use an earlier saved incumbent.',
        explicit_written_bounds_remain_exact=True, acceptance_tolerances_modified=False,
        optimizer_calls=0, source_sha256=digest(Path(__file__).resolve()),
        execution_report_sha256=digest(HERE / 'CONFIRMATION_EXECUTION_REPORT.json'),
        analysis_sha256=digest(HERE / 'CONFIRMATION_ANALYSIS.json')))
    local = None
    previous_local_check = HERE / 'CONFIRMATION_LOCAL_RAW_CHECK.json'
    if previous_local_check.exists():
        local = load(previous_local_check)
        assert local['status'] == 'passed'
        assert local['raw_manifest_sha256'] == digest(HERE / 'CONFIRMATION_RAW_MANIFEST.json')
        assert local['verifier_sha256'] == digest(HERE / 'seal_confirmation.py')
    if check_raw:
        process = subprocess.run([sys.executable, str(HERE / 'seal_confirmation.py'), '--check'],
            cwd=ROOT, text=True, capture_output=True, check=True)
        local = dict(status='passed', captured_utc=datetime.now(timezone.utc).isoformat(),
            file_count=raw['file_count'], total_bytes=raw['total_bytes'],
            raw_manifest_sha256=digest(HERE / 'CONFIRMATION_RAW_MANIFEST.json'),
            verifier_sha256=digest(HERE / 'seal_confirmation.py'),
            returncode=process.returncode, stdout=process.stdout, optimizer_calls=0)
        save(HERE / 'CONFIRMATION_LOCAL_RAW_CHECK.json', local)
        print(process.stdout.strip(), flush=True)
    comparisons = {(r['solver'], r['stratum'], r['denominator']): r for r in analysis['comparisons']}
    def ratio(item):
        result = f"{item['geometric_mean_paired_ratio']:.4f}"
        if 'interval_95' in item:
            result += f" [{item['interval_95'][0]:.4f}, {item['interval_95'][1]:.4f}]"
        return result
    lines = ['# Cierre e interpretación de la campaña confirmatoria ORF', '',
        '22 de octubre de 2026. Las 3.840 ejecuciones y sus 480 reproducciones '
        'independientes terminaron sin fallas de ejecución. Se conservaron 3.816 '
        'ejecuciones con calidad evaluable y 24 diagnósticas del modelo infactible.', '',
        'La campaña **no confirma una aceleración general de Budget-L2 frente a L2** '
        'en la métrica primaria registrada. Los intervalos de ambos solvers contienen '
        'uno; esto no demuestra equivalencia.', '',
        '## Comparación primaria completa', '',
        '| Solver | Pares | Objetivos alcanzados Budget/L2 | PAR2 Budget/L2 [IC 95%] | Tiempo completo [IC 95%] | Trabajo [IC 95%] |',
        '| --- | ---: | ---: | --- | --- | --- |']
    for solver in ['gurobi', 'cplex']:
        r = comparisons[solver, 'all', 'L2']; metrics = r['metrics']
        lines.append(f"| {solver} | {r['paired_assignments']} | {r['numerator_successes']}/{r['denominator_successes']} | "
            f"{ratio(metrics['par2_seconds'])} | {ratio(metrics['complete_process_seconds'])} | {ratio(metrics['solver_work'])} |")
    lines += ['', 'PAR2 mide la disponibilidad verificada después del solver: '
        'usa el tiempo medido en los éxitos y dos veces el límite más preparación '
        'si no se alcanza el objetivo. Los cocientes son medias geométricas '
        'emparejadas; los intervalos marginales proceden de 100.000 remuestreos '
        'de los 40 padres completos, conservando horizontes, semillas y máscara '
        'diagnóstica. El costo de referencia es factible y verificado, no un '
        'óptimo MILP certificado.', '',
        'Con Gurobi, el tiempo completo de Budget-L2 es aproximadamente un 7,9 % '
        'mayor que el de L2. Los nueve éxitos adicionales no establecen una ventaja '
        'general: el intervalo de la diferencia de tasas incluye cero. En CPLEX '
        'hay tres éxitos menos y la diferencia también incluye cero. La pequeña '
        'reducción de trabajo de CPLEX es secundaria, conserva censura y no '
        'constituye una mejora del objetivo primario.', '',
        '## Precisión física y dominio', '',
        'Los 3.816 candidatos finales evaluables satisfacen los presupuestos '
        'físicos congelados de las filas mapeadas (0,01 MW y 100 m³), bajo las '
        'cuatro políticas de cada solver. En esta muestra no se observa recuperación '
        'adicional de esos presupuestos por usar el contrato. Son objetivos '
        'numéricos del estudio, no tolerancias operativas atribuidas al operador.', '',
        'El diagnóstico descriptivo posterior distingue esos presupuestos de '
        'las cotas exactas del dominio y del objetivo de calidad. En CPLEX, todas '
        'las fallas del dominio final se explican por residuos positivos de cotas '
        f"escritas. El rango global es [{float(min(cplex_bounds)):.4g}, {float(max(cplex_bounds)):.4g}], "
        'en las unidades algebraicas respectivas de cada variable. '
        'No se modificó el criterio registrado de cotas exactas ni se recalculó '
        'el éxito con otra tolerancia. El diagnóstico usa el vector final; un '
        'éxito del objetivo puede corresponder a un incumbente anterior guardado. '
        f"En CPLEX fallaron las cotas exactas en {groups['cplex', 'Budget-L2']['failed_domain']}/477 "
        f"finales Budget-L2 y {groups['cplex', 'L2']['failed_domain']}/477 finales L2; "
        'este criterio domina la baja tasa de aceptación combinada de ese solver.', '',
        '## Controles fuertes y cotas', '',
        'Gurobi L2-NF3 alcanza 454 objetivos frente a 432 de Budget-L2; '
        'CPLEX L2-NumEmphasis alcanza 106 frente a 99. Las reducciones de trabajo '
        'frente a esos controles se interpretan junto con estas diferencias '
        'de éxito y los límites finitos. Las comparaciones secundarias con Base '
        'están en el JSON completo: no sustituyen la comparación primaria.', '',
        'Las políticas escaladas tienen **cero comparaciones de cotas aplicables** '
        'en este detector, porque el testigo Base no se certificó factible para '
        'el export redondeado. Sus cero contradicciones detectadas no constituyen '
        'evidencia de cotas correctas. Base tiene 477 comparaciones aplicables '
        'por solver, con 13 contradicciones detectadas en CPLEX y dos en Gurobi.', '',
        '## Alcance y uso editorial', '',
        'Simple produce los mismos exports con L2 y Budget-L2. Los padres '
        'proceden de recombinaciones históricas con exposición previa documentada; '
        'el remuestreo no los convierte en nuevas observaciones operativas '
        'independientes. Las tres formulaciones siguen perteneciendo al despacho '
        'hidroeléctrico.', '',
        'Esta campaña aporta una validación reproducible de alcance y límites. '
        'La afirmación defendible conserva el foco en especificación explícita '
        'de precisión, selección contractual y verificación. La evidencia nueva '
        'no justifica ampliar una afirmación de superioridad computacional general.', '',
        'Si se incorpora al artículo, presentar un resumen breve de la comparación '
        'primaria con los éxitos y los intervalos, y desarrollar los estratos y '
        'diagnósticos en el suplemento. Incluir también los resultados nulos y '
        'desfavorables. El manuscrito y la versión de envío permanecen congelados '
        'durante este cierre separado.', '',
        '## Evidencia de cierre', '',
        f"La verificación estadística independiente reprodujo {proof['comparisons_reproduced']} comparaciones y "
        f"{proof['bootstrap_intervals_reproduced']} intervalos. Las auditorías de ejecución abarcan "
        f"{execution['replay_counts']['candidate_vectors']:,} vectores, "
        f"{execution['replay_counts']['full_candidate_audits']:,} auditorías completas y "
        f"{execution['replay_counts']['exact_reference_checks']} verificaciones de referencia. "
        f"El archivo sellado inventaría {raw['file_count']:,} archivos y {raw['total_bytes']:,} bytes.", '',
        'Los hashes de las fuentes, datos tabulados, 480 informes y prueba '
        'estadística se comprobaron en la copia local. '
        + ('La copia local de todos los archivos del manifiesto también pasó el verificador completo.' if local else
           'La comprobación local de todos los registros voluminosos se conserva separada del control estadístico realizado en el clúster.'), '',
        'Fuentes: `CONFIRMATION_ANALYSIS.json`, `CONFIRMATION_EXECUTION_REPORT.json`, '
        '`CONFIRMATION_ANALYSIS_REPLAY.json`, `CONFIRMATION_RAW_MANIFEST.json` y '
        '`CONFIRMATION_FINAL_DIAGNOSTICS.json`. No se ejecutaron nuevos optimizadores.', '']
    (HERE / 'INFORME_CIERRE_CONFIRMATORIO.md').write_text('\n'.join(lines))
    save(HERE / 'CONFIRMATION_CLOSURE.json', dict(status='closed_verified',
        captured_utc=datetime.now(timezone.utc).isoformat(), assignments=3840,
        quality_evaluable=3816, diagnostic=24, comparisons_reproduced=48,
        bootstrap_intervals_reproduced=80, local_complete_raw_seal_verified=local is not None,
        optimizer_calls=0, general_speedup_confirmed=False, manuscript_modified=False,
        source_sha256=digest(Path(__file__).resolve()),
        hashes={n: digest(HERE / n) for n in ['CONFIRMATION_PLAN.json', 'CONFIRMATION_EXECUTION_REPORT.json',
            'CONFIRMATION_ANALYSIS.json', 'CONFIRMATION_ANALYSIS_REPLAY.json',
            'CONFIRMATION_RAW_MANIFEST.json', 'CONFIRMATION_ANALYSIS_VALIDATION_MANIFEST.json',
            'CONFIRMATION_FINAL_DIAGNOSTICS.json', 'INFORME_CIERRE_CONFIRMATORIO.md']}))
    print('Confirmation closure recorded; no scientific sources or manuscript changed.', flush=True)


if __name__ == '__main__':
    if sys.flags.optimize:
        raise RuntimeError('Run without -O; integrity assertions are required.')
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify-local-raw', action='store_true')
    main(parser.parse_args().verify_local_raw)
