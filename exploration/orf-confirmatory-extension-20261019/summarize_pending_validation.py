#!/usr/bin/env python3
"""Read completed prerequisite evidence and optionally freeze caps and reference eligibility."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name):
    return json.loads((HERE / name).read_text())


def digest(name):
    return hashlib.sha256((HERE / name).read_bytes()).hexdigest()


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main(freeze):
    plan = load('PENDING_VALIDATION_PLAN.json')
    calibration = load('BASE_CALIBRATION_REPORT.json')
    references = load('CONFIRMATION_REFERENCE_REPORT.json')
    replay = load('CONFIRMATION_REFERENCE_REPLAY.json')
    stdlib = load('STDLIB_REFERENCE_REPLAY.json')
    assert calibration['plan_sha256'] == references['plan_sha256'] == replay['plan_sha256'] == digest('PENDING_VALIDATION_PLAN.json')
    assert calibration['status'] == 'completed' and references['status'] == 'completed'
    assert replay['status'] == 'passed' and replay['optimizer_calls'] == 0
    names = set(plan['confirmation_instances'])
    records = references['records']
    assert {r['instance'] for r in records} == names and len(records) == 160
    assert {r['instance'] for r in replay['records']} == names and len(replay['records']) == 160
    statuses = {r['instance']: r['status'] for r in records}
    assert all(statuses[r['instance']] == r['status'] for r in replay['records'])
    counts = dict(Counter(statuses.values()))
    assert counts == references['counts']
    admitted = sorted(n for n, status in statuses.items() if status == 'verified_feasible')
    diagnostics = sorted(n for n, status in statuses.items() if status == 'certified_infeasible_diagnostic')
    unknowns = sorted(n for n, status in statuses.items() if status == 'unknown')
    assert diagnostics == plan['certified_infeasible_confirmation_models']
    assert len(admitted) == replay['verified_feasible']
    assert stdlib['status'] == 'passed' and stdlib['models_classified'] == 160
    assert stdlib['optimizer_calls'] == stdlib['third_party_packages'] == 0
    assert stdlib['verified_feasible'] == len(admitted) and stdlib['unknown'] == len(unknowns)
    assert stdlib['certified_infeasible'] == len(diagnostics)
    assert stdlib['verifier_sha256'] == digest('verify_reference_witnesses_stdlib.py')
    caps = []
    assessment = load('BASE_RESOURCE_ASSESSMENT.json')
    for stratum in assessment['strata']:
        key = f"{stratum['family']}-h{stratum['horizon']}-{stratum['solver']}"
        recommendation = calibration['recommended_caps'].get(key)
        cap = recommendation['cap_seconds'] if recommendation else 60
        met = recommendation['operational_target_met'] if recommendation else not stratum['additional_Base_calibration_required']
        caps.append(dict(family=stratum['family'], horizon=stratum['horizon'], solver=stratum['solver'],
            cap_seconds=cap, operational_native_gap_target_met=met,
            all_four_policies_share_cap=True, right_censoring_retained=True))
    assert len(caps) == 24
    proof_records = {r['instance']: r for r in replay['records'] if r['status'] == 'verified_feasible'}
    readiness = (len(admitted) + len(unknowns) == 159 and len(diagnostics) == 1)
    assert readiness, 'All 160 models must be classified before freezing.'
    if freeze:
        assert references['recorded_models'] == 160 and not references['missing_models']
    result = dict(status='prerequisites_complete' if not unknowns else 'prerequisites_processed_with_unknown_references',
        counts=counts, eligibility=dict(verified_feasible=admitted, diagnostic=diagnostics, unknown=unknowns),
        caps=caps, threads=4, memory_GiB=8, simultaneous_MIP_processes=1,
        requested_gap=.001, quality_relative_target=.001, confirmation_solver_seeds=[401,457,503],
        registered_assignments=3840, quality_eligible_assignments=len(admitted)*24,
        diagnostic_assignments=len(diagnostics)*24, unknown_quality_assignments=len(unknowns)*24,
        common_references={n: dict(base_sha256=proof_records[n]['base_sha256'],
            witness_sha256=proof_records[n]['witness_sha256']) for n in admitted},
        calibration_operational_target_unmet_strata=[r for r in caps if not r['operational_native_gap_target_met']],
        actual_calibration_MIP_calls=calibration['actual_MIP_calls'],
        actual_reference_MIP_calls=references['actual_MIP_calls'],
        actual_reference_exact_LP_calls=references['actual_exact_LP_calls'],
        caps_and_reference_mask_frozen=freeze, confirmation_comparative_assignments_submitted=0,
        policy_outcomes_used=False, optimality_certified=False,
        unknown_quality_is_not_scored_as_target_failure=True,
        standard_library_replay_passed=True, explicit_written_finite_bounds_checked=True,
        hashes={n: digest(n) for n in ['PENDING_VALIDATION_PLAN.json','BASE_CALIBRATION_REPORT.json',
            'CONFIRMATION_REFERENCE_REPORT.json','CONFIRMATION_REFERENCE_REPLAY.json',
            'STDLIB_REFERENCE_REPLAY.json','STDLIB_READER_CHECK.json']})
    if freeze:
        path = HERE / 'CONFIRMATION_PREREQUISITES_FROZEN.json'
        if path.exists():
            assert json.loads(path.read_text()) == result, 'An immutable freeze already exists.'
        else:
            save(path.name, result)
    save('PENDING_VALIDATION_SUMMARY.json', result)
    lines = ['# Referencias comunes y calibración de recursos ORF', '',
        'Continuación del piloto cerrado; artículo y generador original sin cambios.', '',
        '## Referencias de confirmación', '',
        f"De los 160 modelos registrados: **{len(admitted)} con referencia factible racional verificada**, "
        f"{len(diagnostics)} certificado inviable y {len(unknowns)} desconocidos.", '',
        'La referencia común no es un óptimo MILP certificado. Todos los intentos Base y sus '
        'costos permanecen separados de las políticas. La reproducción independiente revisó '
        'filas, cotas, integralidad, objetivos y hashes sin llamar a optimizadores.', '',
        'Un segundo verificador lee el formato LP del generador usando solo Python estándar. '
        'Conserva y comprueba las cotas finitas escritas, incluso las que el lector nativo '
        'interpreta como infinitas, y reproduce el certificado de inviabilidad del caso diagnóstico.', '',
        f"Adquisición: {references['actual_MIP_calls']} intentos MIP y "
        f"{references['actual_exact_LP_calls']} LP racionales. Calibración separada: "
        f"{calibration['actual_MIP_calls']} MIP Base.", '',
        '## Límites de resolución', '',
        '| Familia | Horizonte | Solver | Límite (s) | Criterio operativo Base alcanzado |',
        '| --- | ---: | --- | ---: | --- |']
    for row in caps:
        lines.append(f"| {row['family']} | {row['horizon']} | {row['solver']} | {row['cap_seconds']} | "
                     f"{'sí' if row['operational_native_gap_target_met'] else 'no; censura explícita'} |")
    lines += ['', 'Se mantienen cuatro hilos, 8 GiB y una resolución simultánea. Cada límite '
        'se aplica por igual a las cuatro políticas del estrato. El criterio del 80% es '
        'operativo y no certifica optimalidad. Los estratos que no lo alcanzan al límite '
        'registrado de 300 s se conservan como censurados; no se presentan como superados.', '',
        '## Estado de la campaña', '',
        f"{'Se congelaron' if freeze else 'Todavía no se congelaron'} los límites y la máscara común de referencias. "
        'Las **3.840 asignaciones comparativas siguen sin lanzar**. '
        f"La calidad es evaluable en {len(admitted)*24} asignaciones; "
        f"{len(diagnostics)*24} permanecen diagnósticas y {len(unknowns)*24} tienen calidad desconocida.", '',
        'No se seleccionó ninguna política ganadora. Estas comprobaciones no demuestran '
        'una ventaja computacional de Budget-L2 ni amplían la procedencia de los datos.', '',
        'Los bancos siguen siendo recombinaciones históricas con exposición previa documentada. '
        'La inferencia posterior debe remuestrear padres completos, conservando horizontes, '
        'semillas y la máscara común de elegibilidad.', '']
    (HERE / 'INFORME_REFERENCIAS_Y_RECURSOS.md').write_text('\n'.join(lines))
    print(result['status'], counts, 'frozen:', freeze)


if __name__ == '__main__':
    import sys
    if sys.flags.optimize:
        raise RuntimeError('Run without -O; integrity assertions are required.')
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', action='store_true')
    main(parser.parse_args().freeze)
