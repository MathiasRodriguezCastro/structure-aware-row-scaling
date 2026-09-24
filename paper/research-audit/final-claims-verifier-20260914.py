#!/usr/bin/env python3
"""Read-only numerical claim audit; no solver or experiment implementation imports."""
import csv
from collections import defaultdict
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import re
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / 'results-revision/research-audit'
OUT = Path(__file__).with_name('final-claims-evidence-20260914.json')


def rows(path):
    return list(csv.DictReader(path.open()))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


models = {}
for path in sorted((AUDIT/'budget-final/models').glob('*.npz')):
    with np.load(path) as data:
        A, b, c = data['A'], data['b'], data['c']
        assert np.all(A == np.rint(A)) and np.all(c == np.rint(c))
        assert sum(np.max(abs(A), axis=0)) < 2**62
        Z = ((np.arange(2**len(c))[:, None] >> np.arange(len(c))) & 1).astype(np.int64)
        ai, ci = A.astype(np.int64), c.astype(np.int64)
        floor = np.floor(b).astype(np.int64)
        feasible = np.all(Z@ai.T <= floor, axis=1)
        optimum = int(np.max(Z[feasible]@ci))
        assert optimum == int(data['optimum'])
        models[path.stem] = (ai, floor, ci, optimum, Z, feasible)

result = {'models_independently_enumerated': len(models), 'campaigns': {}, 'hashes': {}}
export_equivalence_rows = []
for name in ('budget-final', 'exploration-lattice'):
    path = AUDIT/name/'runs.csv'
    data = rows(path)
    keys = set()
    summary = defaultdict(lambda: {'n': 0, 'verified': 0, 'abstained': 0})
    seen_exports = set()
    exact_export_equivalence = defaultdict(lambda: {'models': 0, 'same_binary_set': 0,
                                                    'models_with_excluded_points': 0,
                                                    'models_with_added_points': 0})
    for r in data:
        key = (r['model_id'], r['method'], r['solver'], r['presolve'])
        assert key not in keys
        keys.add(key)
        ai, floor, ci, optimum, Z, original_feasible = models[r['model_id']]
        x = json.loads(r['x'])
        accepted = False
        if x is not None:
            x = np.asarray(x)
            z = np.rint(x).astype(np.int64)
            feasible = bool(np.all((z >= 0)&(z <= 1)) and np.all(ai@z <= floor))
            accepted = bool(feasible and np.max(abs(x-z)) <= 1e-9 and
                            np.all(x >= -1e-9) and np.all(x <= 1+1e-9) and int(ci@z) == optimum)
        assert accepted == (r['rounded_optimal'] == 'True'), key
        cell = summary[r['solver']+'/'+r['method']]
        cell['n'] += 1
        cell['verified'] += accepted
        cell['abstained'] += r['status'] == 'ABSTAIN'
        if name == 'exploration-lattice' and key[:2] not in seen_exports:
            seen_exports.add(key[:2])
            exported_feasible = np.ones(len(Z), dtype=bool)
            for row, rhs in zip(json.loads(r['exported_A']), json.loads(r['exported_b'])):
                fs = [F(v) for v in row] + [F(rhs)]
                denominator = max(f.denominator for f in fs)
                integers = [int(f*denominator) for f in fs]
                dtype = np.int64 if sum(abs(t) for t in integers) < 2**62 else object
                exported_feasible &= Z@np.array(integers[:-1], dtype=dtype) <= integers[-1]
            stat = exact_export_equivalence[r['method']]
            stat['models'] += 1
            stat['same_binary_set'] += bool(np.array_equal(exported_feasible, original_feasible))
            stat['models_with_excluded_points'] += bool(np.any(original_feasible & ~exported_feasible))
            stat['models_with_added_points'] += bool(np.any(~original_feasible & exported_feasible))
            export_equivalence_rows.append({'model_id': r['model_id'], 'method': r['method'],
                'assignments': len(Z), 'original_feasible': int(original_feasible.sum()),
                'exported_feasible': int(exported_feasible.sum()),
                'excluded_original_feasible': int(np.sum(original_feasible & ~exported_feasible)),
                'added_original_infeasible': int(np.sum(~original_feasible & exported_feasible)),
                'same_binary_set': bool(np.array_equal(exported_feasible, original_feasible))})
    result['campaigns'][name] = {'configurations': len(data), 'summary': dict(summary),
                                'actual_binary64_export_equivalence': dict(exact_export_equivalence)}
    result['hashes'][str(path.relative_to(ROOT))] = sha(path)
    protocol = json.loads((AUDIT/name/'protocol.json').read_text())
    if name == 'exploration-lattice':
        for filename, expected in protocol['model_sha256'].items():
            assert sha(AUDIT/'budget-final/models'/filename) == expected
        result['campaigns'][name]['input_hashes_checked'] = len(protocol['model_sha256'])

op = rows(AUDIT/'operational/reconstructed_runs.csv')
rx = re.compile(r'Explored [^\n]*? in [\d.eE+-]+ seconds \(([\d.eE+-]+) work units\)')
cells = defaultdict(dict)
operational_sources = {}
for source in (ROOT/'results-revision/final-variants').glob('*/resumen.csv'):
    for row in rows(source):
        operational_sources[(source.parent.name, row['instancia'], row['variante'])] = row
for r in op:
    source = operational_sources[r['cell'], r['instance'], r['variant']]
    assert source['status_solver'] == r['status_solver']
    complete = source['status'] == 'OK' and source['status_solver'] in {'OPTIMAL', 'OPTIMO', 'SOLVED', 'INTEGER OPTIMAL'}
    assert complete == (r['completed'] == 'True')
    assert float(source['tiempo_solver_s']) == float(r['solver_seconds'])
    log = ROOT/r['log']
    matches = rx.findall(log.read_text(errors='replace'))
    assert len(matches) == 1
    assert float(matches[0]) == float(r['work_native_log'])
    cells[r['cell']].setdefault(r['instance'], {})[r['variant']] = r
operational = {}
for cell, instances in cells.items():
    assert len(instances) == 15 and all(len(v) == 4 for v in instances.values())
    pool = [v for v in instances.values() if all(r['completed'] == 'True' and
            float(r['work_native_log']) > .005 for r in v.values())]
    contrasts = {}
    for variant in ('matricial_plano', 'matricial_plano_l2', 'role_hybrid'):
        work = math.exp(sum(math.log(float(v[variant]['work_native_log']) /
                   float(v['base']['work_native_log'])) for v in pool)/len(pool))
        numerator = sum(float(v[variant]['solver_seconds']) if v[variant]['completed'] == 'True'
                        else 18000 for v in instances.values())
        denominator = sum(float(v['base']['solver_seconds']) if v['base']['completed'] == 'True'
                          else 18000 for v in instances.values())
        contrasts[variant] = {'work_geometric_ratio': work, 'par10_mean_ratio': numerator/denominator}
    operational[cell] = {'assigned_per_variant': 15, 'common_completed': len(pool),
                          'contrasts_vs_base': contrasts,
                          'instance077_status': {k: v['status_solver'] for k, v in
                              instances.get('instance077.txt', {}).items()}}
result['operational'] = {'native_logs_checked': len(op), 'source_summary_records_checked': len(op), 'cells': operational}

exports = rows(AUDIT/'identifiability-final/exports.csv')
index = defaultdict(dict)
for r in exports:
    assert sha(AUDIT/'identifiability-final'/r['file']) == r['sha256']
    index[(r['block_range'], r['severity'], r['pattern'], r['seed'])][r['variant']] = r
assert len(index) == 180 and all(len(v) == 6 for v in index.values())
identity = {}
for control in ('Role-Hybrid', 'SA-Mat-permB', 'Flat-GM'):
    ratios = [float(v['SA-Mat']['kappa2_common_rank'])/float(v[control]['kappa2_common_rank'])
              for v in index.values()]
    identity[control] = {'count': len(ratios), 'minimum': min(ratios),
        'median': float(np.median(ratios)), 'maximum': max(ratios),
        'byte_identical': sum(v['SA-Mat']['sha256'] == v[control]['sha256'] for v in index.values()),
        'medians_by_range': {str(R): float(np.median([ratio for key, ratio in zip(index, ratios)
                                if int(key[0]) == R])) for R in (1, 2, 3)}}
audit_rows = rows(AUDIT/'identifiability-final/row_scaling_audit.csv')
assert len(audit_rows) == 1080 and all(r['row_scaling_with_serialization_verified'] == '1' for r in audit_rows)
result['identifiability'] = {'export_hashes_checked': len(exports), 'instances': len(index),
    'relative_rank_disagreements': sum(r['reference_rank'] != r['variant_relative_rank'] for r in exports),
    'row_scaling_audits_passed': len(audit_rows), 'contrasts': identity}
archived_sources = [ROOT/'results-revision/spectral-heterogeneous/coupling_blockhet_spectral.csv',
    ROOT/'results-revision/attribution-controls/kappa2_controls_blockhet_S6.csv',
    ROOT/'results-revision/attribution-controls/kappa2_localGMcouplingL2_blockhet_S6.csv',
    ROOT/'results-revision/attribution-controls/kappa2_optionB_blockhet_S6.csv',
    ROOT/'results-revision/attribution-controls/kappa2_perm24_blockhet_S6.csv']
archive = {}
for path in archived_sources[:4]:
    d = rows(path)
    archive[path.name] = {v: float(np.median([float(r['kappa2_pos']) for r in d if r['variant'] == v]))
                           for v in sorted({r['variant'] for r in d})}
old = defaultdict(dict)
for r in rows(archived_sources[2]):
    old[r['instance']][r['variant']] = float(r['kappa2_pos'])
assert len(old) == 30
assert all(v['SAMat'] == v['LocalGMCouplingL2'] for v in old.values())
ratios = [v['SAPre']/v['LocalGMCouplingL2'] for v in old.values()]
permutations = defaultdict(list)
for r in rows(archived_sources[4]):
    permutations[r['instance']].append(r)
ranks = []
for group in permutations.values():
    assert len(group) == 24
    true = [r for r in group if r['is_true_map'] == '1']
    assert len(true) == 1
    value = float(true[0]['kappa2_pos'])
    ranks.append(1+sum(float(r['kappa2_pos']) < value for r in group))
archive['paired_findings'] = {'matched_spectral_equal': 30,
    'prelocal_worse': sum(r > 1 for r in ratios), 'prelocal_median_ratio': float(np.median(ratios)),
    'permutation_instances': len(ranks), 'true_assignment_best': sum(r == 1 for r in ranks),
    'true_assignment_median_rank': float(np.median(ranks))}
result['archived_spectral'] = archive
eq_path = Path(__file__).with_name('final-lattice-export-equivalence-20260914.csv')
with eq_path.open('w', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=export_equivalence_rows[0].keys())
    writer.writeheader()
    writer.writerows(export_equivalence_rows)
for path in (AUDIT/'operational/reconstructed_runs.csv', AUDIT/'operational/paired_contrasts.csv',
             AUDIT/'identifiability-final/exports.csv', AUDIT/'identifiability-final/named_comparisons.csv',
             AUDIT/'identifiability-final/row_scaling_audit.csv',
             ROOT/'scripts/research/analyze_budget_experiment.py',
             ROOT/'scripts/research/verify_saved_experiment.py',
             ROOT/'scripts/audit_operational_evidence.py',
             ROOT/'scripts/research/explore_lattice_margin.py', eq_path, Path(__file__), *archived_sources):
    result['hashes'][str(path.relative_to(ROOT))] = sha(path)
OUT.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
