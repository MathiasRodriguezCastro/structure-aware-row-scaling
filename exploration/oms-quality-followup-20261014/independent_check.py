#!/usr/bin/env python3
"""Replay warm-start retention, primal budgets and exact bound contradictions.

Imports only the previous independent arithmetic checker, never experimental
runner/controller/repair modules or solver libraries. Its prior manifest pins
the arithmetic dependency. No optimization calls occur during this replay.
"""
import csv
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREVIOUS = ROOT / 'exploration/oms-decision-study-20261014'
F = Fraction.from_float


def load(path):
    return json.loads(Path(path).read_text())


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def point(path):
    with np.load(path, allow_pickle=False) as z:
        return list(z['x'])


def write_csv(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def main():
    prior_manifest = load(PREVIOUS / 'MANIFEST.json')
    dependency = next(v for v in prior_manifest['files'] if v['path'] == 'exploration/oms-decision-study-20261014/independent_check.py')
    assert sha(PREVIOUS / 'independent_check.py') == dependency['sha256']
    spec = importlib.util.spec_from_file_location('previous_independent_arithmetic', PREVIOUS / 'independent_check.py')
    arithmetic = importlib.util.module_from_spec(spec); spec.loader.exec_module(arithmetic)
    out = HERE / 'confirmation'; design = load(out / 'design.json')
    assert len(design['queue']) == design['assigned_treatments'] == 48
    for path, digest in design['source_hashes'].items():
        assert sha(ROOT / path) == digest, path
    assert sha(out / 'source-snapshot.py') == sha(HERE / 'study.py')
    assert sha(out / 'controller-source-snapshot.py') == sha(HERE / 'controller.py')
    models = {}; factors = {}; witnesses = {}; priors = {}; mps_checks = []
    factor_count = incompatible = 0
    for item in design['models']:
        folder = out / 'models' / item['name']
        assert sha(folder / 'original-model.json') == item['model_sha256']
        assert sha(folder / 'prior-witness.json') == item['witness_sha256']
        model = load(folder / 'original-model.json'); models[item['name']] = model
        mps_checks.append(arithmetic.check_original_mps(model))
        factors[item['name']] = load(folder / 'factors.json')
        for policy, alphas in factors[item['name']].items():
            for r, a in zip(model['rows'], alphas):
                magnitudes = [abs(F(float(c))) for c in r['terms'].values() if c]
                lower, upper = F(1e-9) / min(magnitudes), F(1e9) / max(magnitudes)
                if policy.startswith('Budget'):
                    lower = max(lower, F(1e-6) / F(float(r['budget'])))
                if a is None:
                    assert lower > upper; incompatible += 1
                else:
                    q = F(float(a)); assert q > 0
                    assert all(F(float(float(a) * float(c))) == q * F(float(c)) for c in (*r['terms'].values(), r['rhs']))
                    if policy != 'Base':
                        assert lower <= q <= upper
                    factor_count += 1
        for policy, digest in item['exports'].items():
            assert sha(folder / (policy + '.lp')) == digest
        prior = load(folder / 'prior-witness.json'); priors[item['name']] = prior
        assert prior['model_digest'] == hashlib.sha256(json.dumps(model, sort_keys=True).encode()).hexdigest()
        reconstructed = (json.dumps(prior['point'], indent=2) + '\n').encode()
        assert hashlib.sha256(reconstructed).hexdigest() == prior['source_sha256']
        exact = arithmetic.rational_check(model, [Fraction(x) for x in prior['point']])
        assert exact == load(folder / 'prior-witness-exact-check.json') and exact['exact_feasible']
        converted = point(folder / 'prior-witness-delivery.npz')
        assert converted == [float(Fraction(x)) for x in prior['point']]
        assert arithmetic.floating_check(model, converted)[0]['primal_accepted']
        witnesses[item['name']] = [{'objective': Fraction(exact['objective_exact']), 'path': str((folder / 'prior-witness.json').relative_to(HERE)), 'available': 'before all new solves'}]
    records = []; phases = []; source_count = candidate_count = repair_points = exact_count = delivered_count = 0
    online_flags = []; loaded = supplied = 0
    for task in design['queue']:
        folder = out / 'runs' / task['model'] / f"{task['arm']}-s{task['seed']}"
        record = load(folder / 'run.json'); assert all(record[k] == v for k, v in task.items())
        model = models[task['model']]; candidate_costs = {}; candidates = {}
        for label in record['candidate_labels']:
            values = point(folder / (label + '.npz'))
            check, raw, rounded = arithmetic.floating_check(model, values)
            assert check['primal_accepted'] and raw == rounded
            candidates[label] = values; candidate_costs[label] = arithmetic.objective(model, raw)
            candidate_count += 1
        warm = '-warm-' in task['arm'] and not task['arm'].startswith('Witness')
        assert len(record['phases']) <= (2 if warm else 1)
        prior = priors[task['model']]
        prior_cost = Fraction(load(out / 'models' / task['model'] / 'prior-witness-exact-check.json')['objective_exact'])
        if task['arm'].startswith('Witness'):
            assert candidates['prior-witness'] == point(out / 'models' / task['model'] / 'prior-witness-delivery.npz')
        for j, phase in enumerate(record['phases']):
            pf = folder / f'phase-{j}'
            assert phase == load(pf / 'phase.json')
            assert phase['import_preserved_original_exactly']
            item = next(v for v in design['models'] if v['name'] == task['model'])
            assert sha(pf / 'imported.lp') == phase['lp_sha256'] == item['exports'][record['representation']]
            parameters = phase['parameters']; assert parameters['Seed'] == task['seed']
            allocation = (1. if j == 0 else 14.) if warm else 15.
            assert 0 < parameters['TimeLimit'] <= allocation
            assert parameters['Threads'] == 4 and parameters['MIPGap'] == .01 and parameters['ScaleFlag'] == -1
            assert parameters['Presolve'] == (0 if task['arm'] == 'Cold-tight-presolve-off' else -1)
            robust = 'ordinary' if warm and j == 0 else 'IF1' if task['arm'].endswith('IF1') else 'tight'
            assert parameters['FeasibilityTol'] == (1e-9 if robust == 'tight' else 1e-6)
            assert parameters['IntFeasTol'] == (1e-9 if robust == 'tight' else 1e-5)
            assert parameters.get('IntegralityFocus', 0) == (1 if robust == 'IF1' else 0)
            if phase['start_supplied']:
                supplied += 1
                assert warm and j == 1 or task['arm'].startswith('Witness')
                start = point(pf / 'start.npz'); label = phase['start_candidate_label']
                assert start == candidates[label] and arithmetic.floating_check(model, start)[0]['primal_accepted']
            log = (pf / 'solver.log').read_text()
            assert phase['log_reports_loaded_mip_start'] == ('Loaded user MIP start with objective' in log)
            assert phase['log_reports_rejected_mip_start'] == ('User MIP start did not produce a new incumbent solution' in log)
            loaded += phase['log_reports_loaded_mip_start']
            bound = phase['bound']; status = {'optimality_status': 'unverified', 'bound_contradicted': False, 'eligible_exact_witness': False}
            if bound is not None:
                guard = max(F(1e-6), 8 * F(math.ulp(float(bound))))
                status.update(eligible_exact_witness=True, exact_feasible_objective=str(prior_cost), witness=prior['label'],
                              guard_exact=str(guard), bound_contradicted=F(float(bound)) > prior_cost + guard)
            assert status == phase['prior_witness_screen']
            if status['bound_contradicted']:
                online_flags.append({**task, 'phase': j, 'reported_bound': bound, 'exact_feasible_objective': float(prior_cost), 'witness': prior['label']})
            phase_row = {**task, 'phase': j, 'status': phase['status'], 'reported_completion': phase['reported_completion'],
                         'bound': bound, 'mip_seconds': phase['mip_seconds'], 'source_delivery_passed': False,
                         'source_maximum_ratio': None, 'start_supplied': phase['start_supplied'],
                         'raw_original_objective': None,
                         'start_loaded_log': phase['log_reports_loaded_mip_start'], 'online_bound_contradicted': status['bound_contradicted']}
            if phase['has_point']:
                source = point(pf / 'source-point.npz'); source_count += 1
                check, raw, rounded = arithmetic.floating_check(model, source, strict=False)
                assert float(arithmetic.objective(model, raw)) == phase['raw_original_objective']
                checked, _, _ = arithmetic.floating_check(model, [float(x) for x in rounded])
                phase_row.update(source_delivery_passed=checked['primal_accepted'], source_maximum_ratio=checked['integer_rounded']['maximum_row_budget_ratio'],
                                 raw_original_objective=phase['raw_original_objective'])
                label = f'phase-{j}-checked'
                if checked['primal_accepted']:
                    assert candidates[label] == [float(x) for x in rounded]
                for attempt in [v for v in record['repairs'] if v['source_label'] == label]:
                    rf = folder / attempt['folder']; stored = load(rf / 'repair.json')
                    assert all(attempt[k] == v for k, v in stored.items())
                    witness_cost, certificates, has_point = arithmetic.check_repair(model, rf, source)
                    repair_points += has_point
                    if attempt['delivered']:
                        assert candidates[attempt['folder']] == point(rf / 'delivered.npz')
            phases.append(phase_row)
        assert sum(p['parameters']['TimeLimit'] for p in record['phases']) <= 15.
        if record['outcome'] == 'contract_abstention':
            assert not candidates and not record['phases'] and not record['delivered']
            assert record['incompatible_rows'] == sum(a is None for a in factors[task['model']][record['representation']])
        if record.get('final_exact_audit'):
            label = record['final_audit_source_label']; source = candidates[label]
            before_audit = {k: v for k, v in candidate_costs.items() if k != 'final-exact-audit'}
            assert candidate_costs[label] == min(before_audit.values())
            assert record['final_exact_audit'] == load(folder / 'final-exact-audit/repair.json')
            witness_cost, certificates, has_point = arithmetic.check_repair(model, folder / 'final-exact-audit', source)
            repair_points += has_point
            if record['final_exact_audit']['delivered']:
                assert candidates['final-exact-audit'] == point(folder / 'final-exact-audit/delivered.npz')
        if (folder / 'best-pre-audit-exact-check.json').exists():
            before_audit = {k: v for k, v in candidate_costs.items() if k != 'final-exact-audit'}
            selected = min(before_audit, key=before_audit.get)
            q = [F(float(x)) for x in candidates[selected]]
            check = arithmetic.rational_check(model, q)
            assert check == load(folder / 'best-pre-audit-exact-check.json')
            if check['exact_feasible']:
                assert q == [Fraction(x) for x in load(folder / 'best-pre-audit-exact-point.json')]
        # Every exact witness is checked anew, including all bounds and integrality.
        for relative in record['new_exact_witnesses']:
            q = [Fraction(x) for x in load(folder / relative)]
            exact = arithmetic.rational_check(model, q); assert exact['exact_feasible']
            witnesses[task['model']].append({'objective': Fraction(exact['objective_exact']), 'path': str((folder / relative).relative_to(HERE)),
                                            'available': 'post-resolution pool; not an online oracle'})
            exact_count += 1
        if candidates:
            assert record['delivered'] and record['selected_candidate'] in candidates
            chosen = record['selected_candidate']; delivered = point(folder / 'delivered-point.npz')
            assert delivered == candidates[chosen]
            assert candidate_costs[chosen] == min(candidate_costs.values())
            check, raw, rounded = arithmetic.floating_check(model, delivered)
            assert check == record['delivery_check'] and check['primal_accepted']
            assert str(candidate_costs[chosen]) == record['delivered_objective_exact']
            assert float(candidate_costs[chosen]) == record['delivered_objective']
            delivered_count += 1
        else:
            assert not record['delivered'] and not (folder / 'delivered-point.npz').exists()
        assert record.get('optimality_status') == 'unverified'
        if record['phases']:
            assert record['online_bound_contradictions'] == sum(p['prior_witness_screen']['bound_contradicted'] for p in record['phases'])
        records.append(record)
    pooled_flags = []; pooled_gap_flags = []
    inconsistent_reports = []
    for p in phases:
        best_witness = min(witnesses[p['model']], key=lambda x: x['objective']); u = best_witness['objective']
        if p['bound'] is not None:
            guard = max(F(1e-6), 8 * F(math.ulp(float(p['bound']))))
            if F(float(p['bound'])) > u + guard:
                pooled_flags.append({**{k: p[k] for k in ('model', 'arm', 'seed', 'phase')}, 'reported_bound': p['bound'],
                                     'exact_feasible_objective': float(u), 'witness': best_witness['path'], 'availability': best_witness['available']})
        if p['reported_completion'] and p['raw_original_objective'] is not None:
            c = F(float(p['raw_original_objective']))
            if p['bound'] is not None:
                b=F(float(p['bound'])); guard=max(F(1e-6),8*F(math.ulp(float(c))),8*F(math.ulp(float(b))))
                if abs(c-b)>max(F(.01)*abs(c),F(1e-10))+guard:
                    inconsistent_reports.append({**{k:p[k] for k in ('model','arm','seed','phase')},
                                                 'recomputed_source_objective':float(c),'reported_bound':float(b),
                                                 'scope':'completion label conflicts with gap of recomputed saved-point objective; no global optimality certificate'})
            if u < c - F(.01) * abs(c):
                pooled_gap_flags.append({**{k: p[k] for k in ('model', 'arm', 'seed', 'phase')}, 'source_objective': float(c),
                                         'exact_feasible_objective': float(u), 'witness': best_witness['path']})
    comparisons = []
    for warm_arm, cold_arm in [('Base-warm-tight', 'Cold-tight'), ('Base-warm-IF1', 'Cold-IF1'), ('L2-warm-IF1', 'Cold-IF1'),
                              ('Budget-warm-IF1', 'Cold-IF1'), ('Witness-warm-tight', 'Cold-tight')]:
        for name in models:
            for seed in design['seeds']:
                warm = next(r for r in records if r['model'] == name and r['seed'] == seed and r['arm'] == warm_arm)
                cold = next(r for r in records if r['model'] == name and r['seed'] == seed and r['arm'] == cold_arm)
                status = 'not_both_delivered'; difference = None
                if warm['delivered'] and cold['delivered']:
                    w, c = Fraction(warm['delivered_objective_exact']), Fraction(cold['delivered_objective_exact'])
                    difference = float(w - c); guard = max(F(1e-6), 8 * F(math.ulp(float(c))))
                    status = 'better' if w < c - guard else 'worse' if w > c + guard else 'equal_with_guard'
                comparisons.append({'model': name, 'seed': seed, 'warm_arm': warm_arm, 'cold_arm': cold_arm,
                                    'objective_comparison': status, 'warm_minus_cold_objective': difference,
                                    'better_by_one_percent': bool(difference is not None and w < c - F(.01) * abs(c) - guard),
                                    'worse_by_one_percent': bool(difference is not None and w > c + F(.01) * abs(c) + guard),
                                    'warm_seconds': warm['total_seconds'], 'cold_seconds': cold['total_seconds'],
                                    'information_assisted_diagnostic': warm_arm == 'Witness-warm-tight'})
    flat = [{**{k: r[k] for k in ('model', 'seed', 'arm', 'outcome', 'delivered', 'total_seconds')},
             'delivered_objective': r.get('delivered_objective'), 'selected_candidate': r.get('selected_candidate'),
             'native_phases': len(r['phases']), 'repairs': len(r['repairs']), 'exact_witnesses': len(r['new_exact_witnesses']),
             'online_vetoes': r.get('online_bound_contradictions', 0), 'execution_error': r.get('execution_error')} for r in records]
    write_csv(out / 'outcomes.csv', flat); write_csv(out / 'phases.csv', phases); write_csv(out / 'paired-comparisons.csv', comparisons)
    dump(out / 'online-bound-discrepancies.json', online_flags); dump(out / 'pooled-bound-discrepancies.json', pooled_flags)
    dump(out / 'pooled-gap-discrepancies.json', pooled_gap_flags)
    dump(out / 'inconsistent-gap-reports.json', inconsistent_reports)
    dump(out / 'best-exact-witnesses.json', {name: {**min(v, key=lambda x: x['objective']), 'objective': str(min(v, key=lambda x: x['objective'])['objective'])} for name, v in witnesses.items()})
    result = {'assigned_treatments': len(records), 'native_mip_calls': len(phases), 'source_points_checked': source_count,
              'candidate_points_checked': candidate_count, 'delivered_points_checked': delivered_count,
              'rational_repair_points_checked': repair_points, 'new_exact_witnesses_checked': exact_count,
              'prior_exact_witnesses_checked': len(models), 'factor_records_checked': factor_count,
              'incompatible_intervals_checked': incompatible, 'original_mps_checks': mps_checks,
              'mip_starts_supplied': supplied, 'mip_starts_loaded_in_logs': loaded,
              'online_bound_contradictions': len(online_flags), 'pooled_bound_contradictions': len(pooled_flags),
              'pooled_gap_contradictions': len(pooled_gap_flags),
              'internally_inconsistent_completion_reports':len(inconsistent_reports),
              'execution_errors': sum('execution_error' in r for r in records),
              'wall_reference_overruns': sum(r['total_seconds'] > 20 for r in records),
              'requested_mip_limits_within_15_seconds': True, 'best_candidate_retention_checked': True,
              'native_solver_calls_during_replay': 0, 'optimality_status': 'unverified'}
    dump(out / 'independent-verification.json', result); print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
