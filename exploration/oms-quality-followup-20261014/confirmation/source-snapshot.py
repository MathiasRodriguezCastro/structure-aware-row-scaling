#!/usr/bin/env python3
"""Frozen comparison of checked warm starts, objective retention and bound vetoes."""
import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import shutil
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PILOT = ROOT / 'exploration/oms-generalization-20261014'
PREVIOUS = ROOT / 'exploration/oms-decision-study-20261014'
sys.path.insert(0, str(PILOT)); sys.path.insert(0, str(PREVIOUS))
import generalization_study as original
from repair import repair, exact_check, delivery_check, dump, sha
from controller import accept, best, cost, model_digest, screen_bound

F = Fraction.from_float
ARMS = ('Cold-tight', 'Cold-IF1', 'Base-warm-tight', 'Base-warm-IF1',
        'L2-warm-IF1', 'Budget-warm-IF1', 'Cold-tight-presolve-off', 'Witness-warm-tight')
SEEDS = (31, 47)
NAMES = ('control30-3-2-3', 'neos-3421095-cinca', 'ta1-UUM')


def save_point(path, point):
    with Path(path).open('wb') as stream:
        np.savez_compressed(stream, x=np.array(point))


def prepare():
    started = time.perf_counter(); out = HERE / 'confirmation'
    if (out / 'design.json').exists():
        raise SystemExit('An existing design must remain unchanged')
    prepared = []
    witness_sources = {
        'control30-3-2-3': PREVIOUS / 'development-repair/exact/rational-point.json',
        'neos-3421095-cinca': HERE / 'development-known-witness/cinca/rational-point.json',
        'ta1-UUM': PREVIOUS / 'confirmation/runs/ta1-UUM/Base-check-repair-s23/repair-floating/rational-point.json'}
    for name in NAMES:
        folder = out / 'models' / name; folder.mkdir(parents=True, exist_ok=True)
        source = PREVIOUS / 'confirmation/models' / name
        for file in ('original-model.json', 'factors.json'):
            shutil.copy2(source / file, folder / file)
        model = json.loads((folder / 'original-model.json').read_text())
        factors = json.loads((folder / 'factors.json').read_text())
        for policy, alphas in factors.items():
            if all(a is not None for a in alphas):
                original.write_lp(folder / (policy + '.lp'), model, alphas)
        q = json.loads(witness_sources[name].read_text())
        exact = exact_check(model, q); assert exact['exact_feasible']
        delivery, converted = delivery_check(model, q); assert delivery['primal_accepted']
        witness = {'model_digest': model_digest(model), 'point': q, 'label': name + '-preexisting-exact-witness',
                   'source_path': str(witness_sources[name].relative_to(ROOT)), 'source_sha256': sha(witness_sources[name])}
        dump(folder / 'prior-witness.json', witness); dump(folder / 'prior-witness-exact-check.json', exact)
        save_point(folder / 'prior-witness-delivery.npz', converted)
        prepared.append({'name': name, 'model_sha256': sha(folder / 'original-model.json'),
                         'witness_sha256': sha(folder / 'prior-witness.json'),
                         'exports': {p: sha(folder / (p + '.lp')) for p in factors if (folder / (p + '.lp')).exists()}})
    queue = [{'model': name, 'seed': seed, 'arm': arm} for name in NAMES for seed in SEEDS for arm in ARMS]
    rng = np.random.default_rng(20261016); queue = [queue[i] for i in rng.permutation(len(queue))]
    design = {'assigned_treatments': len(queue), 'models': prepared, 'seeds': SEEDS, 'arms': ARMS, 'queue': queue,
              'mip_limits': {'cold_or_witness': 15., 'warm_initial': 1., 'warm_final': 14.},
              'wall_reference_seconds': 20., 'initial_shared_preparation_seconds': time.perf_counter() - started,
              'parameters': {'Threads': 4, 'MIPGap': .01, 'Presolve': -1, 'ScaleFlag': -1,
                             'FeasibilityTol': 1e-6, 'IntFeasTol': 1e-5},
              'prior_witness_scope': 'available before solving; information-assisted diagnostic, acquisition excluded and declared',
              'model_selection': 'all 3 previously selected mixed MIPLIB groups; new seeds, no new families',
              'source_hashes': {str(p.relative_to(ROOT)): sha(p) for p in
                  (Path(__file__), HERE / 'controller.py', HERE / 'PROTOCOL.md', PREVIOUS / 'repair.py',
                   PILOT / 'generalization_study.py', ROOT / 'scripts/research/budget_scaling.py')},
              'optimality_status': 'unverified; bound veto is one-sided'}
    dump(out / 'design.json', design)
    shutil.copy2(Path(__file__), out / 'source-snapshot.py')
    shutil.copy2(HERE / 'controller.py', out / 'controller-source-snapshot.py')
    print('Frozen 48 treatment assignments before any new MILP call', flush=True)


def phase(model, alphas, representation, item, folder, env, seed, limit, robust, presolve, start):
    import gurobipy as gp
    folder.mkdir(parents=True, exist_ok=True); began = time.perf_counter()
    lp = folder / 'imported.lp'; original.write_lp(lp, model, alphas)
    assert sha(lp) == item['exports'][representation]
    export_seconds = time.perf_counter() - began
    before_import = time.perf_counter(); m = gp.read(str(lp), env=env)
    params = {'Threads': 4, 'MIPGap': .01, 'Presolve': presolve, 'ScaleFlag': -1,
              'FeasibilityTol': 1e-6, 'IntFeasTol': 1e-5, 'Seed': seed, 'TimeLimit': limit}
    if robust == 'tight':
        params.update(FeasibilityTol=1e-9, IntFeasTol=1e-9)
    elif robust == 'IF1':
        params['IntegralityFocus'] = 1
    m.Params.LogToConsole = 0; m.Params.OutputFlag = 1; m.Params.LogFile = str(folder / 'solver.log')
    for key, value in params.items():
        m.setParam(key, value)
    variables = m.getVars(); names = [v.VarName for v in variables]; rows = []
    for c in m.getConstrs():
        e = m.getRow(c)
        rows.append((c.ConstrName, {e.getVar(j).VarName: float(e.getCoeff(j)) for j in range(e.size())}, c.Sense, float(c.RHS)))
    data = [(v.VarName, float(v.LB) if abs(v.LB) < 1e100 else None,
             float(v.UB) if abs(v.UB) < 1e100 else None, v.VType != 'C', float(v.Obj)) for v in variables]
    original.check_import(model, alphas, names, rows, data)
    if start is not None:
        assert accept(model, start) == list(start)
        for i, x in enumerate(start):
            m.getVarByName(f'x{i:05d}').Start = float(x)
        save_point(folder / 'start.npz', start)
    import_seconds = time.perf_counter() - before_import
    before_mip = time.perf_counter(); m.optimize(); mip_seconds = time.perf_counter() - before_mip
    point = [m.getVarByName(f'x{i:05d}').X for i in range(len(model['variables']))] if m.SolCount else None
    record = {'parameters': params, 'status': m.Status, 'reported_completion': m.Status == gp.GRB.OPTIMAL,
              'bound': float(m.ObjBound) if math.isfinite(m.ObjBound) else None,
              'has_point': point is not None, 'work': float(m.Work), 'start_supplied': start is not None,
              'import_preserved_original_exactly': True, 'lp_sha256': sha(lp),
              'export_seconds': export_seconds, 'import_seconds': import_seconds, 'mip_seconds': mip_seconds,
              'solver_version': gp.gurobi.version(), 'representation': representation}
    m.dispose()
    if point is not None:
        save_point(folder / 'source-point.npz', point)
        record['raw_original_objective'] = float(cost(model, point))
    log = (folder / 'solver.log').read_text()
    record['log_reports_loaded_mip_start'] = 'Loaded user MIP start with objective' in log
    record['log_reports_rejected_mip_start'] = 'User MIP start did not produce a new incumbent solution' in log
    return record, point


def solve():
    import gurobipy as gp
    out = HERE / 'confirmation'; design = json.loads((out / 'design.json').read_text())
    for name, digest in design['source_hashes'].items():
        assert sha(ROOT / name) == digest, name
    env = gp.Env(params={'OutputFlag': 0})
    for task in design['queue']:
        folder = out / 'runs' / task['model'] / f"{task['arm']}-s{task['seed']}"
        if (folder / 'run.json').exists():
            continue
        folder.mkdir(parents=True, exist_ok=True)
        item = next(v for v in design['models'] if v['name'] == task['model'])
        inputs = out / 'models' / task['model']; assert sha(inputs / 'original-model.json') == item['model_sha256']
        assert sha(inputs / 'prior-witness.json') == item['witness_sha256']
        model = json.loads((inputs / 'original-model.json').read_text())
        prior = json.loads((inputs / 'prior-witness.json').read_text())
        began = time.perf_counter(); deadline = began + 20.
        record = {**task, 'phases': [], 'repairs': [], 'candidate_labels': [], 'delivered': False,
                  'new_exact_witnesses': [], 'optimality_status': 'unverified'}
        candidates = []
        arm = task['arm']; representation = 'Budget-dyadic-L2' if arm.startswith('Budget') else 'Dyadic-L2' if arm.startswith('L2') else 'Base'
        if representation == 'Base':
            alphas = [1.] * len(model['rows'])
        else:
            alphas = [original.factor(r, model, representation.startswith('Budget'), 'l2')[0] for r in model['rows']]
        record['selection_seconds'] = time.perf_counter() - began
        record['representation'] = representation
        if any(a is None for a in alphas):
            record.update(outcome='contract_abstention', incompatible_rows=sum(a is None for a in alphas), total_seconds=time.perf_counter()-began)
            dump(folder / 'run.json', record); print(task['model'], task['seed'], arm, 'contract_abstention', flush=True); continue
        def consider(point, label):
            if point is None:
                return
            checked = accept(model, point)
            if checked is not None:
                candidates.append((label, checked)); save_point(folder / (label + '.npz'), checked)
                return
            for mode, cap in (('floating', .5), ('exact', 1.)):
                remaining = deadline - time.perf_counter() - .25
                if remaining <= 0:
                    break
                target = folder / (label + '-repair-' + mode)
                result, candidate = repair(model, point, target, mode, min(cap, remaining))
                record['repairs'].append({'folder': target.name, 'source_label': label, **result})
                if result['exact_feasible']:
                    record['new_exact_witnesses'].append(str((target / 'rational-point.json').relative_to(folder)))
                if candidate is not None:
                    candidates.append((target.name, candidate)); save_point(folder / (target.name + '.npz'), candidate); break
        try:
            warm = '-warm-' in arm and not arm.startswith('Witness')
            if arm.startswith('Witness'):
                check, point = delivery_check(model, prior['point']); assert check['primal_accepted']
                candidates.append(('prior-witness', point)); save_point(folder / 'prior-witness.npz', point)
            specs = [(1., 'ordinary', -1), (14., 'tight' if arm.endswith('tight') else 'IF1', -1)] if warm else [
                (15., 'IF1' if arm == 'Cold-IF1' else 'tight', 0 if arm == 'Cold-tight-presolve-off' else -1)]
            for j, (allocation, robust, presolve) in enumerate(specs):
                remaining = deadline - time.perf_counter() - 1.5
                if remaining <= .01:
                    break
                label, start = best(model, candidates)
                before_phase = time.perf_counter()
                result, point = phase(model, alphas, representation, item, folder / f'phase-{j}', env,
                                      task['seed'], min(allocation, remaining), robust, presolve,
                                      start if (warm and j == 1 or arm.startswith('Witness')) else None)
                result['start_candidate_label'] = label if result['start_supplied'] else None
                check_started = time.perf_counter(); consider(point, f'phase-{j}-checked')
                result['check_and_repair_seconds'] = time.perf_counter() - check_started
                screen_started = time.perf_counter(); result['prior_witness_screen'] = screen_bound(model, result['bound'], prior)
                result['bound_screen_seconds'] = time.perf_counter() - screen_started
                result['total_phase_seconds'] = time.perf_counter() - before_phase
                record['phases'].append(result); dump(folder / f'phase-{j}' / 'phase.json', result)
            label, point = best(model, candidates)
            if point is not None:
                audit_started = time.perf_counter(); exact = exact_check(model, [F(float(x)) for x in point])
                dump(folder / 'best-pre-audit-exact-check.json', exact)
                if exact['exact_feasible']:
                    target = folder / 'best-pre-audit-exact-point.json'
                    dump(target, [str(F(float(x))) for x in point]); record['new_exact_witnesses'].append(target.name)
                elif deadline - time.perf_counter() > .25:
                    result, converted = repair(model, point, folder / 'final-exact-audit', 'exact', min(1., deadline-time.perf_counter()-.25))
                    record['final_exact_audit'] = result; record['final_audit_source_label'] = label
                    if result['exact_feasible']:
                        record['new_exact_witnesses'].append('final-exact-audit/rational-point.json')
                    if converted is not None:
                        candidates.append(('final-exact-audit', converted)); save_point(folder / 'final-exact-audit.npz', converted)
                record['exact_audit_seconds'] = time.perf_counter() - audit_started
        except Exception as error:
            record.update(execution_error_type=type(error).__name__, execution_error=str(error))
        label, point = best(model, candidates)
        record.update(candidate_labels=[s for s, p in candidates], selected_candidate=label,
                      delivered=point is not None, online_bound_contradictions=sum(p['prior_witness_screen']['bound_contradicted'] for p in record['phases']))
        if point is not None:
            check, _ = delivery_check(model, point); assert check['primal_accepted']
            record['delivered_objective_exact'] = str(cost(model, point)); record['delivered_objective'] = float(cost(model, point))
            record['delivery_check'] = check
        record['outcome'] = 'verified_delivery' if point is not None else 'no_verified_delivery'
        if 'execution_error' in record:
            record['outcome'] += '_with_execution_error'
        record['total_seconds'] = time.perf_counter() - began
        record['wall_reference_exceeded'] = record['total_seconds'] > 20.
        save_started = time.perf_counter()
        if point is not None:
            save_point(folder / 'delivered-point.npz', point)
        record['outer_persistence_seconds'] = time.perf_counter() - save_started
        dump(folder / 'run.json', record)
        print(task['model'], task['seed'], arm, record['outcome'], 'cost', record.get('delivered_objective'),
              'seconds', round(record['total_seconds'], 3), 'vetoes', record['online_bound_contradictions'], flush=True)
    env.dispose()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('stage', choices=('prepare', 'solve'))
    globals()[parser.parse_args().stage]()
