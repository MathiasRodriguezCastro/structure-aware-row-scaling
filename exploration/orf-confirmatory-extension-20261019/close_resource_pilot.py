#!/usr/bin/env python3
"""Close the registered resource pilot from retained evidence, without policy ranking."""
import csv
import hashlib
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(path):
    return json.loads(path.read_text())


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def elapsed_seconds(value):
    days, clock = value.split('-') if '-' in value else ('0', value)
    h, m, s = map(float, clock.split(':'))
    return int(days) * 86400 + 3600 * h + 60 * m + s


def main():
    plan = load(HERE / 'PILOT_PLAN.json')
    data = load(HERE / 'MODEL_PREPARATION.json')['models']
    reports = {name: load(HERE / name) for name in [
        'PILOT_RESOURCE_REPORT.json', 'PILOT_REPLAY.json', 'BASE_RESOURCE_ASSESSMENT.json',
        'STRUCTURAL_FEASIBILITY_AUDIT.json', 'STRUCTURAL_CERTIFICATE_REPLAY.json',
        'FACTOR_PORTABILITY-Haswell.json', 'FACTOR_PORTABILITY-Haswell-all.json',
        'PILOT_RAW_MANIFEST.json', 'LOCAL_PILOT_REPLAY.json', 'SLURM_SUBMISSION.json']}
    for name, expected in plan['dependencies'].items():
        assert sha(ROOT / name) == expected, 'Frozen dependency changed: ' + name
    manifest = reports['PILOT_RAW_MANIFEST.json']
    assert manifest['status'] == 'sealed'
    assert manifest['pilot_plan_sha256'] == sha(HERE / 'PILOT_PLAN.json')
    assert manifest['file_count'] == len({r['path'] for r in manifest['files']}) == len(manifest['files'])
    assert manifest['total_bytes'] == sum(r['bytes'] for r in manifest['files'])
    for item in manifest['files']:
        path = (HERE / item['path']).resolve()
        assert path.is_relative_to(HERE)
        assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256'], item['path']
    replay = reports['PILOT_REPLAY.json']
    assert replay['status'] == 'passed' and replay['optimizer_calls'] == 0
    local_replay = reports['LOCAL_PILOT_REPLAY.json']
    assert local_replay['status'] == 'passed' and local_replay['local_replay_optimizer_calls'] == 0
    assert local_replay['replay_sha256'] == sha(HERE / 'PILOT_REPLAY.json')
    assert (HERE / 'PILOT_REPLAY.json').read_bytes() == (HERE / 'setup-evidence/pilot-6069328/PILOT_REPLAY.json').read_bytes()
    collection = reports['PILOT_RESOURCE_REPORT.json']
    assert collection['status'] == 'resource_pilot_complete'
    assert collection['recorded_assignments'] == 256 and not collection['missing_jobs'] and not collection['failed_jobs']
    assert reports['STRUCTURAL_CERTIFICATE_REPLAY.json']['status'] == 'passed'
    certified = set(reports['STRUCTURAL_FEASIBILITY_AUDIT.json']['certified_infeasible_instances'])
    assessment = reports['BASE_RESOURCE_ASSESSMENT.json']
    assert assessment['status'] == 'complete'
    assert not assessment['policy_ranking_used'] and not assessment['confirmation_launched']
    for filename, count in [('FACTOR_PORTABILITY-Haswell.json', 64),
                            ('FACTOR_PORTABILITY-Haswell-all.json', 384)]:
        gate = reports[filename]
        assert gate['status'] == 'passed'
        assert gate['exports_checked'] == gate['byte_identical_exports'] == count
        assert len(gate['records']) == count
        assert all(r['actual_sha256'] == r['expected_sha256'] for r in gate['records'])

    rows = []
    native_counts = defaultdict(Counter)
    base_counts = Counter()
    simple_pairs = set()
    for block in plan['blocks']:
        name = block['instance']
        for job in block['jobs']:
            folder = HERE / 'pilot-runs' / job['id']
            result = load(folder / 'result.json')
            timing = load(HERE / 'pilot-execution-logs' / (job['id'] + '.json'))
            assert result['job'] == timing['job'] == job
            assert result['status'] == 'completed' and timing['returncode'] == 0
            assert not result['callback_errors']
            assert result['native_import']['matrix_rhs_objective_bounds_integer_domains_equal']
            assert result['base_sha256'] == data[name]['base_sha256'] == sha(folder / 'Base.lp')
            representation = 'Base' if job['policy'] == 'Base' else 'Budget-L2' if job['policy'] == 'Budget-L2' else 'L2'
            export = folder / ('Base.lp' if representation == 'Base' else 'scaled.lp')
            expected = data[name]['base_sha256'] if representation == 'Base' else data[name]['policies'][representation]['export_sha256']
            assert result['export_sha256'] == sha(export) == expected
            native = result['outcome']
            if name in certified:
                classification = 'certified_infeasible_diagnostic'
                assert not result['quality_reference_available'] and not native['completed']
            elif native['completed']:
                classification = 'native_gap_stop'
            else:
                # Codes are retained verbatim; these are the only non-diagnostic
                # non-gap terminations observed in this completed pilot.
                assert (job['solver'], native['status']) in [('gurobi', 9), ('cplex', 107)]
                classification = 'native_time_limit_with_incumbent'
                assert native['solutions'] > 0
                assert native['runtime'] >= job['time_limit'] * .95
            if name not in certified:
                assert result['quality_reference_available']
            assert timing['complete_process_seconds'] >= result['worker_total_seconds']
            native_counts[job['solver']][str(native['status'])] += 1
            if job['policy'] == 'Base':
                base_counts[classification] += 1
            if data[name]['family'] == 'simple':
                assert data[name]['policies']['L2']['export_sha256'] == data[name]['policies']['Budget-L2']['export_sha256']
                simple_pairs.add((name, job['solver']))
            rows.append(dict(job_id=job['id'], instance=name, family=data[name]['family'],
                horizon=data[name]['horizon'], solver=job['solver'], policy=job['policy'],
                seed=job['seed'], worker_status=result['status'], native_status=native['status'],
                classification=classification, reference_available=result['quality_reference_available'],
                solve_limit_seconds=job['time_limit'], native_runtime_seconds=native['runtime'],
                preparation_seconds=result['preparation_time'],
                postsolve_verification_seconds=result['verification_seconds'],
                complete_process_seconds=timing['complete_process_seconds'],
                maximum_worker_RSS_KiB=result['maximum_RSS_KiB'], hostname=result['hostname'],
                base_sha256=result['base_sha256'], export_sha256=result['export_sha256']))
    assert len(rows) == len({r['job_id'] for r in rows}) == 256
    assert set(replay['verified_jobs']) == {r['job_id'] for r in rows}
    assert replay['counts']['recorded_assignments'] == 256
    feasible_reference_names = {r['instance'] for r in rows if r['reference_available']}
    assert len(feasible_reference_names) == replay['counts']['exact_reference_checks'] == collection['independently_feasible_references']

    accounting = HERE / 'setup-evidence/pilot-6069328/accounting.psv'
    scheduler_rows = [line.split('|') for line in accounting.read_text().splitlines() if line.strip()]
    blocks = [r for r in scheduler_rows if re.fullmatch(r'6069328_\d+', r[0])]
    assert {int(r[0].split('_')[1]) for r in blocks} == set(range(32))
    assert all(r[3] == 'COMPLETED' and r[4] == '0:0' and r[5] == '4' for r in blocks)
    assert all(r[6] == '2097152Kc' for r in blocks)
    classification_counts = dict(Counter(r['classification'] for r in rows))
    totals = [r['complete_process_seconds'] for r in rows]
    peak = max(r['maximum_worker_RSS_KiB'] for r in rows)
    proposed = assessment['proposed_120_second_Base_only_jobs']
    assert not assessment['proposed_jobs_launched']
    assert reports['SLURM_SUBMISSION.json']['confirmation_assignments_submitted'] == 0
    summary = dict(status='resource_pilot_closed', registered_assignments=256,
        processed_assignments=len(rows), failed_assignments=0, missing_assignments=0,
        classifications=classification_counts, native_status_counts=dict(native_counts),
        Base_classifications=dict(base_counts), verified_feasible_references=len(feasible_reference_names),
        certified_infeasible_pilot_models=sorted({r['instance'] for r in rows if r['instance'] in certified}),
        unknown_noncertified_pilot_references=[], replay_counts=replay['counts'],
        identical_Simple_L2_Budget_solver_pairs=len(simple_pairs),
        maximum_worker_RSS_KiB=peak, maximum_worker_RSS_GiB=peak / 1048576,
        maximum_scheduler_sampled_RSS_KiB=max(float(r[9].removesuffix('K')) for r in scheduler_rows if r[9]),
        median_complete_process_seconds=statistics.median(totals),
        maximum_complete_process_seconds=max(totals), sum_complete_process_seconds=sum(totals),
        sum_block_elapsed_seconds=sum(elapsed_seconds(r[7]) for r in blocks),
        maximum_block_elapsed_seconds=max(elapsed_seconds(r[7]) for r in blocks),
        nodes=sorted({r['hostname'] for r in rows}),
        resource_proposal=dict(threads=4, memory_GiB=8, simultaneous_MIP_processes=1,
            registered_block_wall_limit_minutes=45,
            current_solver_limit_seconds=60,
            next_Base_only_candidate_limit_seconds=120,
            next_candidate_jobs=len(proposed), candidate_jobs_launched=False,
            candidate_not_validated=True, confirmation_resources_frozen=False,
            rationale='Retain tested threads, memory reservation and serial concurrency; only Base censoring identifies strata requiring a larger-cap calibration.'),
        policy_ranking_used=False, optimizer_calls_during_closure=0,
        confirmation_launched=False, manuscript_modified=False, generator_modified=False,
        raw_evidence=dict(manifest_sha256=sha(HERE / 'PILOT_RAW_MANIFEST.json'),
            files=manifest['file_count'], bytes=manifest['total_bytes']),
        source_hashes={name: sha(HERE / name) for name in reports},
        pilot_plan_sha256=sha(HERE / 'PILOT_PLAN.json'), accounting_sha256=sha(accounting))
    (HERE / 'PILOT_CLOSURE.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    with (HERE / 'PILOT_ASSIGNMENTS.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    render(summary, assessment)
    print('Resource pilot closed: 256/256; no missing/failed assignments; no policy ranking.')


def render(summary, assessment):
    counts = summary['classifications']
    text = f'''# Cierre del piloto de recursos ORF

Investigación separada de `v1.5.0-orf-submission`. Se completó exclusivamente
el piloto registrado: **256/256 asignaciones, cero fallos de infraestructura
y cero asignaciones faltantes**. El artículo, el generador original y las
instancias registradas permanecen intactos. No se seleccionaron políticas
ganadoras ni se lanzaron las 3.840 asignaciones confirmatorias.

## Qué se completó

Los mismos ocho padres, 32 modelos, dos solvers y cuatro políticas se repitieron
íntegramente con semilla 401 y cuatro hilos. El array `6069328` terminó sus
32 bloques con código 0; consolidación `6069330`, reproducción independiente
`6069331` y evaluación Base `6069367` terminaron correctamente.

| Clasificación de las 256 asignaciones | Cantidad |
| --- | ---: |
| Terminación nativa por el criterio de gap solicitado | {counts['native_gap_stop']} |
| Límite de tiempo nativo, con incumbente guardado | {counts['native_time_limit_with_incumbent']} |
| Modelo certificado inviable, conservado como diagnóstico | {counts['certified_infeasible_diagnostic']} |
| Fallo de infraestructura o asignación faltante | 0 |

La terminación por gap es una declaración del optimizador, no una prueba
independiente de optimalidad. El estado `completed` del ejecutor significa que
el proceso y su persistencia terminaron correctamente; no implica éxito primal
ni optimalidad. Los estados numéricos originales se conservan por asignación.

`simple-v1_simple_000127-h168` permanece con sus ocho combinaciones. Su
inviabilidad está probada exactamente; su calidad primal es **no aplicable**.
No cuenta como timeout y no se propone aumentar su límite. La salida original
del colector conserva la etiqueta histórica de referencia desconocida; este
informe la interpreta junto al certificado, sin sobrescribir aquella evidencia.
Los otros 31 modelos disponen de referencias factibles verificadas, sin afirmar
que sean óptimos MILP certificados. Esto no completa las referencias de los
160 modelos previstos para confirmación.

## Reproducibilidad y verificaciones

- `OPENBLAS_CORETYPE=Haswell`, `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`
  y `PYTHONINTMAXSTRDIGITS=0`; los solvers conservan sus cuatro hilos registrados.
- Los 64 exports escalados del piloto coinciden byte por byte con los fijados.
  La puerta ampliada verificó 192 Base y reprodujo 384 exports escalados.
  Cada worker volvió a comprobar sus fuentes, Base, representación e importación.
- La reproducción independiente verificó {summary['replay_counts']['candidate_vectors']:,} vectores guardados,
  {summary['replay_counts']['full_candidate_audits']} auditorías completas de candidatos elegibles o finales y
  {summary['replay_counts']['exact_reference_checks']} referencias exactas, sin resolver otro problema.
- Los {summary['identical_Simple_L2_Budget_solver_pairs']} pares L2/Budget-L2 de la familia Simple tienen exports idénticos.
  Son controles de estabilidad; no prueban un beneficio del contrato.
- El inventario `PILOT_RAW_MANIFEST.json` identifica {summary['raw_evidence']['files']:,} archivos y
  {summary['raw_evidence']['bytes']:,} bytes. Se verifica íntegramente contra la copia local.
  Los intentos anteriores siguen conservados en `infrastructure-attempts/`:
  no se sustituyeron por estos resultados ni se mezclaron en el piloto válido.

## Recursos medidos y propuesta

El máximo RSS informado por un worker fue **{summary['maximum_worker_RSS_KiB']:,} KiB
({summary['maximum_worker_RSS_GiB']:.3f} GiB)**. Slurm muestrea memoria y registró un máximo
de {summary['maximum_scheduler_sampled_RSS_KiB']:,.0f} KiB; se conservan ambas medidas.
No representan una garantía de memoria para todos los modelos confirmatorios.
El proceso completo más largo duró {summary['maximum_complete_process_seconds']:.2f} s,
incluida preparación, resolución, verificación y persistencia. La mediana fue
{summary['median_complete_process_seconds']:.2f} s. El bloque más largo duró
{summary['maximum_block_elapsed_seconds']:.0f} s. Estos tiempos excluyen cola, instalación
del entorno y adquisición separada de referencias. Se registraron los nodos
{', '.join(summary['nodes'])}; los inventarios del scheduler se adjuntan.

Propongo conservar **4 hilos, 8 GiB por trabajo, una resolución simultánea y
45 minutos de pared por bloque**. Son los recursos efectivamente ensayados;
no se infiere capacidad adicional de licencias ni concurrencia a partir del RSS.

Para decidir límites de resolución se usó exclusivamente Base. Entre los 62
casos Base con referencia factible, 58 llegaron al criterio nativo de gap y
cuatro alcanzaron 60 s. Tras separar el diagnóstico inviable, solo tres estratos
quedan por debajo del 80% operativo registrado:

| Familia | Horizonte | Solver | Base con parada nativa por gap / modelos factibles |
| --- | ---: | --- | ---: |
'''
    for row in assessment['strata']:
        if row['additional_Base_calibration_required']:
            text += f"| {row['family']} | {row['horizon']} | {row['solver']} | {row['native_gap_stops']}/{row['Base_recorded']} |\n"
    text += '''
El siguiente candidato es **120 s**, mediante siete calibraciones exclusivamente
Base que cubran todos los casos factibles de esos estratos, también los que
terminaron a 60 s. Es una propuesta, **todavía no una calibración validada ni un
límite confirmatorio congelado**. No se lanzan esas siete resoluciones dentro
del cierre de las 256 asignaciones solicitadas. Los restantes estratos cumplen
el criterio a 60 s dentro de este piloto pequeño; eso no garantiza ausencia de
timeouts en la confirmación. Cualquier comparación futura usará el mismo límite
para todas las políticas de un estrato.

El colector original devuelve `confirmation_may_be_frozen=false`, y se conserva
ese resultado. Completar el piloto no equivale a habilitar la confirmación:
faltan validar los límites superiores y adquirir/clasificar las referencias
comunes de los modelos confirmatorios. Los padres y horizontes no se sustituyen.

## Cómo reproducir este cierre

Desde la raíz del repositorio, con los artefactos inventariados presentes:

```sh
PYTHONINTMAXSTRDIGITS=0 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 exploration/orf-confirmatory-extension-20261019/replay_pilot.py
python3 exploration/orf-confirmatory-extension-20261019/close_resource_pilot.py
```

La primera orden usa NumPy y los lectores científicos del repositorio; no llama
a optimizadores. La segunda usa solo la biblioteca estándar, verifica todos
los hashes, identidades y estados y genera `PILOT_CLOSURE.json`, la tabla de
256 asignaciones `PILOT_ASSIGNMENTS.csv` y este informe. No regenera ni
sobrescribe el inventario remoto al verificar la transferencia.

El archivo original del repositorio y este informe por sí solos no sustituyen
los vectores/exports identificados en el inventario. Esos archivos están
preservados en la copia local y en la copia aislada del clúster; los materiales
comerciales y las credenciales no forman parte de los archivos de distribución.

El piloto responde una pregunta de recursos y reproducibilidad. No estima una
ventaja de Budget-L2, no añade resultados al manuscrito y no habilita una
afirmación de validación externa sobre nuevos datos operativos independientes.
'''
    (HERE / 'INFORME_PILOTO.md').write_text(text)


if __name__ == '__main__':
    if sys.flags.optimize:
        raise RuntimeError('Run without -O: integrity assertions are required for this report.')
    main()
