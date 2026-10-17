#!/usr/bin/env python3
"""Replay stored original-model arithmetic, without importing experimental code.

Uses rational arithmetic on the canonical binary64 model, not solver residuals.
No commercial solver, HiGHS, SoPlex or Pyomo is imported or called.
"""
import csv
from fractions import Fraction
import gzip
import hashlib
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
F = Fraction.from_float


def load(path):
    return json.loads(Path(path).read_text())


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_original_mps(model):
    """Independent adapter for the exact subset of MPS features in these sources.

    Follows documented Gurobi MPS defaults; unsupported features are rejected.
    Decimal literals are interpreted as binary64, as in the canonical model.
    """
    sources = ROOT / 'exploration/oms-generalization-20261014/sources/miplib-models'
    source = next(r for r in load(sources / 'provenance.json') if r['name'] == model['name'])
    path = sources / (model['name'] + '.mps.gz'); assert sha(path) == source['sha256']
    rows = {}; columns = {}; rhs = {}; integer_names = set(); bound_lines = []
    section = ''; active_integer = False; objective_name = None
    for line in gzip.decompress(path.read_bytes()).decode('latin1').splitlines():
        if not line.strip() or line.startswith('*'):
            continue
        tokens = line.split()
        if not line[0].isspace():
            section = tokens[0]
            assert section in ('NAME', 'ROWS', 'COLUMNS', 'RHS', 'BOUNDS', 'ENDATA'), section
            continue
        if section == 'ROWS':
            sense, name = tokens; assert sense in ('N', 'E', 'L', 'G')
            if sense == 'N':
                assert objective_name is None; objective_name = name
            else:
                rows[name] = {'sense': {'E': '=', 'L': '<', 'G': '>'}[sense], 'terms': {}}
        elif section == 'COLUMNS':
            if "'MARKER'" in tokens:
                assert tokens[2] in ("'INTORG'", "'INTEND'")
                active_integer = tokens[2] == "'INTORG'"; continue
            assert len(tokens) in (3, 5)
            name = tokens[0]; columns.setdefault(name, {})
            if active_integer:
                integer_names.add(name)
            for j in range(1, len(tokens), 2):
                row, value = tokens[j], F(float(tokens[j + 1].replace('D', 'E')))
                assert row not in columns[name], 'duplicate MPS coefficients require another adapter'
                columns[name][row] = value
        elif section == 'RHS':
            assert len(tokens) in (3, 5)
            for j in range(1, len(tokens), 2):
                assert tokens[j] not in rhs
                rhs[tokens[j]] = F(float(tokens[j + 1].replace('D', 'E')))
        elif section == 'BOUNDS':
            bound_lines.append(tokens)
    assert objective_name is not None and not rhs.get(objective_name, 0), 'objective offsets are unsupported'
    bounds = {name: [Fraction(0), Fraction(1) if name in integer_names else None] for name in columns}
    explicit_upper = set()
    for t in bound_lines:
        kind, _, name = t[:3]; assert name in bounds and kind in ('FR', 'UP', 'LI'), kind
        if kind == 'FR':
            bounds[name] = [None, None]; explicit_upper.add(name)
        elif kind == 'UP':
            bounds[name][1] = F(float(t[3])); explicit_upper.add(name)
        else:
            integer_names.add(name); bounds[name][0] = F(float(t[3]))
            if name not in explicit_upper:
                bounds[name][1] = None
    index = {v['name']: i for i, v in enumerate(model['variables'])}
    assert set(index) == set(columns) and set(rows) == {r['name'] for r in model['rows']}
    for name, terms in columns.items():
        variable = model['variables'][index[name]]
        assert F(float(variable['cost'])) == terms.get(objective_name, Fraction(0))
        assert variable['integer'] == (name in integer_names)
        assert [F(float(variable[k])) if variable[k] is not None else None for k in ('lower', 'upper')] == bounds[name]
        for row, value in terms.items():
            if row != objective_name and value:
                rows[row]['terms'][str(index[name])] = value
    for row in model['rows']:
        expected = rows[row['name']]
        assert expected['sense'] == row['sense']
        assert expected['terms'] == {i: F(float(c)) for i, c in row['terms'].items() if c}
        assert rhs.get(row['name'], Fraction(0)) == F(float(row['rhs']))
    return {'name': model['name'], 'source_sha256': sha(path), 'rows': len(rows), 'variables': len(columns),
            'coefficients': sum(len(r['terms']) for r in rows.values()),
            'objective_bounds_and_domains_checked': True,
            'literal_interpretation': 'original MPS literals converted to binary64; not ideal decimal rationals'}


def violation(row, values):
    signed = sum((F(float(c)) * values[int(i)] for i, c in row['terms'].items()), Fraction(0)) - F(float(row['rhs']))
    assert row['sense'] in ('<', '>', '=')
    return abs(signed) if row['sense'] == '=' else max(Fraction(0), signed if row['sense'] == '<' else -signed)


def objective(model, values):
    return sum((F(float(v['cost'])) * x for v, x in zip(model['variables'], values)), Fraction(0))


def integer_failures(model, values):
    return [i for i, (v, x) in enumerate(zip(model['variables'], values)) if v['integer'] and
            (x.denominator != 1 or v['lower'] is not None and x < F(float(v['lower'])) or
             v['upper'] is not None and x > F(float(v['upper'])))]


def numerical(model, values):
    assert len(values) == len(model['variables'])
    errors = [violation(r, values) for r in model['rows']]
    ratios = [e / F(float(r['budget'])) for e, r in zip(errors, model['rows'])]
    failures = [i for i, q in enumerate(ratios) if q > 1]
    bounds = 0
    for v, x in zip(model['variables'], values):
        allowance = F(float(v['bound_budget']))
        if v['lower'] is not None and F(float(v['lower'])) - x > allowance:
            bounds += 1
        elif v['upper'] is not None and x - F(float(v['upper'])) > allowance:
            bounds += 1
    return {'maximum_row_budget_ratio': float(max(ratios, default=Fraction(0))),
            'failed_rows': failures, 'bound_failures': bounds,
            'max_mass_violation_kg': float(max((e for e, r in zip(errors, model['rows']) if r['unit'] == 'kg'), default=Fraction(0))),
            'all_row_and_bound_budgets_met': not failures and not bounds}


def floating_check(model, point, strict=True):
    assert len(point) == len(model['variables']) and all(math.isfinite(float(x)) for x in point)
    values = [F(float(x)) for x in point]
    rounded = [Fraction(round(float(x))) if v['integer'] else x for v, x in zip(model['variables'], values)]
    result = {'raw': numerical(model, values), 'integer_rounded': numerical(model, rounded),
              'original_objective': float(objective(model, values)),
              'maximum_raw_integer_distance': max((float(abs(x - round(float(x)))) for v, x in zip(model['variables'], values) if v['integer']), default=0.),
              'primal_accepted': numerical(model, rounded)['all_row_and_bound_budgets_met'],
              'optimality_status': 'unverified'}
    if strict:
        result['exact_integer_domain_failures'] = integer_failures(model, values)
        result['primal_accepted'] = result['primal_accepted'] and not result['exact_integer_domain_failures']
    return result, values, rounded


def rational_check(model, values):
    rows = [(i, str(violation(r, values))) for i, r in enumerate(model['rows']) if violation(r, values)]
    bounds = []
    for i, (v, x) in enumerate(zip(model['variables'], values)):
        if v['lower'] is not None and x < F(float(v['lower'])):
            bounds.append(i)
        if v['upper'] is not None and x > F(float(v['upper'])):
            bounds.append(i)
    domains = [i for i, (v, x) in enumerate(zip(model['variables'], values)) if v['integer'] and x.denominator != 1]
    return {'exact_feasible': not rows and not bounds and not domains,
            'row_violations': [list(v) for v in rows], 'bound_violations': bounds, 'integer_domain_violations': domains,
            'rows_checked': len(model['rows']), 'variables_checked': len(values),
            'objective_exact': str(objective(model, values)), 'objective_for_display': float(objective(model, values)),
            'scope': 'exact feasible point of original binary64 model; no MILP optimality certificate'}


def check_obstructions(model, folder):
    count = 0
    path = folder / 'fixed-assignment-obstruction.json'
    if path.exists():
        c = load(path); z = c['integers']
        if c['failure'] == 'fixed_integer_outside_exact_domain':
            v = model['variables'][int(c['variable'])]; x = Fraction(c['value'])
            assert v['integer'] and (v['lower'] is not None and x < F(float(v['lower'])) or v['upper'] is not None and x > F(float(v['upper'])))
        else:
            assert c['failure'] == 'fixed_integer_contradicts_constant_row'
            r = model['rows'][c['row']]
            assert all(i in z or not a for i, a in r['terms'].items())
            b = F(float(r['rhs'])) - sum((F(float(a)) * z[i] for i, a in r['terms'].items() if i in z), Fraction(0))
            assert str(b) == c['rhs_exact']
            assert not (b == 0 if r['sense'] == '=' else b >= 0 if r['sense'] == '<' else b <= 0)
        count += 1
    path = folder / 'binary64-delivery-obstructions.json'
    if path.exists():
        fixed = load(folder / 'mapping.json')['integers']
        for c in load(path):
            r = model['rows'][c['row']]; j = c['continuous_variable']
            assert r['sense'] == '=' and not model['variables'][int(j)]['integer']
            terms = {i: F(float(a)) for i, a in r['terms'].items() if i not in fixed and a}
            assert list(terms) == [j]
            a = terms[j]; b = F(float(r['rhs'])) - sum((F(float(v)) * fixed[i] for i, v in r['terms'].items() if i in fixed), Fraction(0))
            below, above = float.fromhex(c['lower_neighbor_hex']), float.fromhex(c['upper_neighbor_hex'])
            assert math.nextafter(below, math.inf) == above and F(below) < b / a < F(above)
            minimum = min(abs(a * F(below) - b), abs(a * F(above) - b))
            assert str(a) == c['coefficient_exact'] and str(b) == c['fixed_rhs_exact']
            assert str(b / a) == c['required_rational_value'] and str(minimum) == c['minimum_binary64_residual']
            assert str(F(float(r['budget']))) == c['budget_exact'] and minimum > F(float(r['budget']))
            count += 1
    return count


def check_repair(model, folder, source_point):
    result = load(folder / 'repair.json')
    expected_integers = {str(i): round(float(x)) for i, (v, x) in enumerate(zip(model['variables'], source_point)) if v['integer']}
    if (folder / 'mapping.json').exists():
        mapping = load(folder / 'mapping.json')
        assert mapping['integers'] == expected_integers
        assert mapping['continuous'] == [i for i, v in enumerate(model['variables']) if not v['integer']]
        assert mapping['original_model_digest'] == hashlib.sha256(json.dumps(model, sort_keys=True).encode()).hexdigest()
        expected_omitted = [i for i, r in enumerate(model['rows']) if all(j in expected_integers or not a for j, a in r['terms'].items())]
        assert mapping['omitted_rows'] == expected_omitted
    else:
        assert load(folder / 'fixed-assignment-obstruction.json')['integers'] == expected_integers
    certificates = check_obstructions(model, folder)
    if 'lp_sha256' in result:
        assert sha(folder / 'fixed.lp') == result['lp_sha256']
    path = folder / 'rational-point.json'
    if not path.exists():
        assert not result['exact_feasible'] and not result['delivered']
        return None, certificates, False
    values = [Fraction(x) for x in load(path)]
    assert all(values[int(i)] == z for i, z in expected_integers.items())
    exact = rational_check(model, values)
    assert exact == load(folder / 'exact-check.json')
    assert exact['exact_feasible'] == result['exact_feasible']
    check, _, _ = floating_check(model, [float(x) for x in values])
    assert check == load(folder / 'delivery-check.json') and check['primal_accepted'] == result['delivered']
    if result['delivered']:
        with np.load(folder / 'delivered.npz', allow_pickle=False) as stored:
            assert list(stored['x']) == [float(x) for x in values]
    return objective(model, values) if exact['exact_feasible'] else None, certificates, True


def write_csv(path, records):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)


def main():
    out = HERE / 'confirmation'; design = load(out / 'design.json')
    for path, digest in design['source_hashes'].items():
        assert sha(ROOT / path) == digest, path
    assert sha(out / 'source-snapshot.py') == sha(HERE / 'prospective.py')
    assert sha(out / 'repair-source-snapshot.py') == sha(HERE / 'repair.py')
    assert len(design['queue']) == design['assigned_arms'] == 80
    records = []; factor_count = incompatible = source_points = delivered_points = rational_points = proofs = 0
    exact_witnesses = {}; diagnostics = []; mps_checks = []
    for item in design['models']:
        folder = out / 'models' / item['name']; model = load(folder / 'original-model.json')
        assert sha(folder / 'original-model.json') == item['model_sha256']
        if model['name'] in ('control30-3-2-3', 'neos-3421095-cinca', 'ta1-UUM'):
            mps_checks.append(check_original_mps(model))
        factors = load(folder / 'factors.json')
        gamma = model['guided_gamma'] or 1e-5
        def nominal(policy):
            alphas = factors[policy]
            if any(a is None for a in alphas):
                return None
            return float(max((F(1e-6) / F(float(a)) + F(float(gamma)) *
                       sum((abs(F(float(c))) for i, c in r['terms'].items() if model['variables'][int(i)]['integer']), Fraction(0))) /
                       F(float(r['budget'])) for r, a in zip(model['rows'], alphas)))
        mi = max((abs(c) for r in model['rows'] for i, c in r['terms'].items() if model['variables'][int(i)]['integer']), default=0.)
        mc = max((abs(c) for r in model['rows'] for i, c in r['terms'].items() if not model['variables'][int(i)]['integer']), default=0.)
        dominance = mi / mc if mc else None
        ml, mb = nominal('Dyadic-L2'), nominal('Budget-dyadic-L2')
        if ml is not None and ml <= 1:
            route, reason = 'Dyadic-L2', 'conventional_nominal_rounding_bound_met'
        elif dominance is not None and dominance >= 1e6:
            route, reason = 'Base', 'large_coefficients_removed_by_integer_fixing'
        elif mb is not None and mb <= 1:
            route, reason = 'Budget-dyadic-L2', 'contract_nominal_rounding_bound_met'
        else:
            route, reason = 'Base', 'posterior_verification_required_no_prior_rounding_bound'
        diagnostic = {'maximum_integer_coefficient': mi, 'maximum_continuous_coefficient': mc,
                      'integer_coefficient_dominance': dominance, 'mu_l2': ml, 'mu_budget': mb,
                      'diagnostic_route': route, 'diagnostic_reason': reason,
                      'incompatible_rows': {p: sum(a is None for a in v) for p, v in factors.items()}}
        assert diagnostic == item['diagnostic'] == load(folder / 'diagnostic.json')
        for policy, alphas in factors.items():
            assert len(alphas) == len(model['rows'])
            for r, alpha in zip(model['rows'], alphas):
                magnitudes = [abs(F(float(a))) for a in r['terms'].values() if a]
                lower, upper = F(1e-9) / min(magnitudes), F(1e9) / max(magnitudes)
                reserve = F(float(item['guided_gamma'])) * sum((abs(F(float(a))) for i, a in r['terms'].items() if model['variables'][int(i)]['integer']), Fraction(0)) if policy.startswith('Budget') and item['guided_gamma'] else Fraction(0)
                if policy.startswith('Budget') and reserve < F(float(r['budget'])):
                    lower = max(lower, F(1e-6) / (F(float(r['budget'])) - reserve))
                if alpha is None:
                    assert reserve >= F(float(r['budget'])) or lower > upper
                    incompatible += 1
                else:
                    q = F(float(alpha)); assert q > 0
                    assert all(F(float(float(alpha) * float(a))) == q * F(float(a)) for a in (*r['terms'].values(), r['rhs']))
                    if policy != 'Base':
                        assert lower <= q <= upper
                    factor_count += 1
        for policy, digest in item['exports'].items():
            assert sha(folder / (policy + '.lp')) == digest
        exact_witnesses[item['name']] = []
    for task in design['queue']:
        folder = out / 'runs' / task['model'] / f"{task['arm']}-s{task['seed']}"
        record = load(folder / 'run.json')
        assert all(record[k] == v for k, v in task.items())
        model = load(out / 'models' / task['model'] / 'original-model.json')
        if 'lp_sha256' in record:
            assert sha(folder / 'imported.lp') == record['lp_sha256']
            item = next(v for v in design['models'] if v['name'] == task['model'])
            assert record['lp_sha256'] == item['exports'][record['selected_representation']]
            assert record['import_preserved_original_exactly']
        if record.get('has_source_point'):
            source_points += 1
            with np.load(folder / 'source-point.npz', allow_pickle=False) as stored:
                raw_check, raw, rounded = floating_check(model, stored['x'], strict=False)
                check, _, _ = floating_check(model, [float(x) for x in rounded])
            assert raw_check == load(folder / 'raw-source-check.json')
            assert check == load(folder / 'source-check.json')
            assert record['source_point_budget_met'] == check['primal_accepted']
            assert record['source_raw_budget_met'] == raw_check['raw']['all_row_and_bound_budgets_met']
            assert record['original_source_objective'] == float(objective(model, raw))
            alphas = load(out / 'models' / task['model'] / 'factors.json')[record['selected_representation']]
            eps, gamma = F(float(record['parameters']['FeasibilityTol'])), F(float(record['parameters']['IntFeasTol']))
            mu = [eps / F(float(a)) / F(float(r['budget'])) + gamma * sum((abs(F(float(c))) for i, c in r['terms'].items() if model['variables'][int(i)]['integer']), Fraction(0)) / F(float(r['budget'])) for r, a in zip(model['rows'], alphas)]
            failed_exported = sum(F(float(a)) * violation(r, raw) > eps for r, a in zip(model['rows'], alphas))
            integer_hypothesis = max((abs(x - round(float(x))) for v, x in zip(model['variables'], raw) if v['integer']), default=Fraction(0)) <= gamma
            if max(mu) <= 1 and not failed_exported and integer_hypothesis:
                assert not check['integer_rounded']['failed_rows']
            diagnostics.append({**task, 'nominal_maximum_mu': float(max(mu)), 'exported_hypothesis_failed_rows': failed_exported,
                                'integer_hypothesis_met': integer_hypothesis, 'source_delivery_met': check['primal_accepted']})
        if record['delivered']:
            delivered_points += 1
            with np.load(folder / 'delivered-point.npz', allow_pickle=False) as stored:
                check, values, _ = floating_check(model, stored['x'])
            assert check == load(folder / 'delivered-check.json') and check['primal_accepted']
            assert record['delivered_objective'] == float(objective(model, values))
        else:
            assert not (folder / 'delivered-point.npz').exists()
        for attempt in record['repair_attempts']:
            repair_folder = folder / ('repair-' + attempt['mode'])
            assert attempt == load(repair_folder / 'repair.json')
            witness, certificates, has_point = check_repair(model, repair_folder, raw)
            proofs += certificates; rational_points += has_point
            if witness is not None:
                exact_witnesses[task['model']].append({'objective': witness, 'source': str(repair_folder.relative_to(HERE))})
        records.append(record)
    # Development is audited but never enters confirmation denominators.
    development_model = load(out / 'models' / 'control30-3-2-3' / 'original-model.json')
    for name in ('development-repair-initial', 'development-repair'):
        assert sha(HERE / 'development-source-point.npz') == load(HERE / name / 'summary.json')['source_point_sha256']
    development = []
    with np.load(HERE / 'development-source-point.npz', allow_pickle=False) as stored:
        development_source = list(stored['x'])
    for name in ('development-repair-initial', 'development-repair'):
        for mode in ('floating', 'exact'):
            folder = HERE / name / mode
            witness, certificates, has_point = check_repair(development_model, folder, development_source)
            development.append({'folder': str(folder.relative_to(HERE)), 'exact_feasible': witness is not None,
                                'delivered': load(folder / 'repair.json')['delivered']})
    gaps = []; bounds = []
    for r in records:
        if not exact_witnesses[r['model']]:
            continue
        best = min(exact_witnesses[r['model']], key=lambda x: x['objective'])
        u = best['objective']
        if r.get('bound') is not None:
            b = F(float(r['bound'])); margin = max(F(1e-6), 8 * F(math.ulp(float(r['bound']))))
            if b > u + margin:
                bounds.append({**{k: r[k] for k in ('model', 'seed', 'arm')}, 'reported_bound': r['bound'],
                               'exact_feasible_upper_bound': float(u), 'witness': best['source']})
        if r.get('reported_completion') and 'original_source_objective' in r:
            c = F(float(r['original_source_objective']))
            if u < c - F(.01) * abs(c):
                gaps.append({**{k: r[k] for k in ('model', 'seed', 'arm')}, 'source_objective': float(c),
                             'exact_feasible_upper_bound': float(u), 'witness': best['source'],
                             'scope': 'exact witness is better by more than 1% of displayed source objective; not a global optimality certificate'})
    flat = []
    for r in records:
        flat.append({**{k: r[k] for k in ('model', 'seed', 'arm', 'outcome', 'delivered', 'source_point_budget_met', 'total_seconds')},
                     'source_objective': r.get('original_source_objective'), 'delivered_objective': r.get('delivered_objective'),
                     'repair_attempts': len(r['repair_attempts']), 'exact_witness_available': r['exact_witness_available'],
                     'source_maximum_delivery_ratio': r.get('source_maximum_delivery_ratio'),
                     'delivered_maximum_ratio': r.get('delivered_maximum_ratio'),
                     'reported_completion': r['reported_completion'], 'outer_persistence_seconds': r.get('outer_persistence_seconds', 0.)})
    write_csv(out / 'outcomes.csv', flat); write_csv(out / 'prior-indicators.csv', diagnostics)
    dump(out / 'bound-discrepancies.json', bounds); dump(out / 'gap-discrepancies.json', gaps)
    summary = {'assigned_treatments': len(records), 'native_calls': sum('status' in r for r in records),
               'source_points_independently_checked': source_points, 'delivered_points_independently_checked': delivered_points,
               'rational_points_independently_checked': rational_points,
               'exact_feasible_confirmation_witnesses': sum(len(v) for v in exact_witnesses.values()),
               'fixed_assignment_or_delivery_obstructions_checked': proofs, 'dyadic_factor_records_checked': factor_count,
               'incompatible_factor_intervals_checked': incompatible, 'bound_discrepancies': len(bounds),
               'gap_discrepancies': len(gaps), 'development_excluded': development,
               'execution_failures': sum(r['outcome'] == 'execution_failure' for r in records),
               'wall_reference_overruns': sum(r['total_seconds'] > 20 for r in records),
               'original_mps_independent_checks': mps_checks,
               'prior_diagnostic_routes_independently_checked': len(design['models']),
               'source_points_with_nominal_mu_at_most_one': sum(r['nominal_maximum_mu'] <= 1 for r in diagnostics),
               'accepted_sources_with_nominal_mu_above_one': sum(r['nominal_maximum_mu'] > 1 and r['source_delivery_met'] for r in diagnostics),
               'source_points_with_exported_hypothesis_failure': sum(r['exported_hypothesis_failed_rows'] > 0 for r in diagnostics),
               'solver_calls_during_replay': 0, 'strict_integer_domains_checked': True,
               'scope': 'exact canonical binary64 model arithmetic; numerical delivery budgets; global MILP optimality unverified'}
    dump(out / 'independent-verification.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
