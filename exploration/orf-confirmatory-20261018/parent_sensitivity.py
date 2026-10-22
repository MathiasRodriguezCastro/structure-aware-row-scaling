#!/usr/bin/env python3
"""Post hoc deletion of each known parent; replay against native saved metrics."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

HERE = Path(__file__).resolve().parent
CONTROLS = ['Base', 'Base-tight', 'L2', 'L2-NF3']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    design = json.loads((HERE/'design.json').read_text())
    parents = sorted({m['parent'] for m in design['models'].values()})
    assert len(parents) == 6 and len(design['models']) == 24
    timing = json.loads((HERE/'timing.json').read_text())
    elapsed = {(r['job']['instance'], r['job']['seed'], r['job']['policy']):
               r['total_seconds'] for r in timing}
    work = {}
    native_hashes = []
    for job in sorted(design['jobs'], key=lambda x: x['id']):
        path = HERE/'runs'/job['id']/'result.json'
        native_hashes.append(f"{sha(path)}  runs/{job['id']}/result.json\n")
        result = json.loads(path.read_text())
        work[job['instance'], job['seed'], job['policy']] = result['outcome']['work']
    pairs = list(csv.DictReader((HERE/'verified-pairs.csv').open()))
    assert len(pairs) == 288
    # The producer uses audited ratios; checking starts again from native work
    # and the external process clock, with a separate summation operation.
    ratios = []
    for r in pairs:
        name, seed, control = r['instance'], int(r['seed']), r['control']
        values = {}
        for metric, source in [('work', work), ('time', elapsed)]:
            raw = source[name, seed, 'Budget-L2']/source[name, seed, control]
            assert raw > 0 and math.isfinite(raw)
            assert math.isclose(raw, float(r[metric+'_ratio']), rel_tol=2e-12)
            values[metric] = raw if args.check else float(r[metric+'_ratio'])
        ratios.append(dict(instance=name, parent=design['models'][name]['parent'],
                           seed=seed, control=control, **values))
    comparisons = []
    for excluded in [None]+parents:
        for control in CONTROLS:
            group = [r for r in ratios if r['control'] == control and r['parent'] != excluded]
            names = {r['instance'] for r in group}
            assert len(group) == (72 if excluded is None else 60)
            assert len(names) == (24 if excluded is None else 20)
            record = dict(excluded_parent=excluded, control=control,
                          retained_scenarios=len(names), retained_seed_pairs=len(group))
            for metric in ['work', 'time']:
                logs = [math.log(r[metric]) for r in group]
                mean = math.fsum(logs)/len(logs) if args.check else statistics.mean(logs)
                record[metric+'_ratio'] = math.exp(mean)
            comparisons.append(record)
    runs = list(csv.DictReader((HERE/'verified-runs.csv').open()))
    domains = {}
    for policy in CONTROLS+['Budget-L2']:
        group = [r for r in runs if r['policy'] == policy]
        assert len(group) == 72
        failures = [dict(instance=r['instance'], seed=int(r['seed']),
                         max_bound_violation=r['max_bound_violation'],
                         max_integrality=r['max_integrality']) for r in group
                    if float(r['max_bound_violation']) != 0 or float(r['max_integrality']) != 0]
        domains[policy] = dict(physical_budgets_passed=sum(r['budgets_passed'] == 'True' for r in group),
                               exact_domains_passed=72-len(failures), total=72,
                               failures=sorted(failures, key=lambda r: (r['instance'], r['seed'])))
    inputs = {n:sha(HERE/n) for n in ['design.json', 'timing.json',
                                     'verified-pairs.csv', 'verified-runs.csv']}
    inputs['native_results_digest'] = hashlib.sha256(''.join(native_hashes).encode()).hexdigest()
    result = dict(analysis='post_hoc_leave_one_known_parent_out', parents=parents,
                  independent_external_families=False, additional_optimizer_calls=0,
                  filtered_pairs=0, uncertainty_intervals=False,
                  scope='Descriptive sensitivity to each known parent; not external validation.',
                  input_sha256=inputs, domains=domains, comparisons=comparisons)
    target = HERE/'PARENT_SENSITIVITY.json'
    if args.check:
        saved = json.loads(target.read_text())
        expected = saved.pop('comparisons')
        actual = result.pop('comparisons')
        assert saved == result
        assert len(expected) == len(actual) == 28
        for a, b in zip(expected, actual):
            for k in a:
                if k.endswith('_ratio'):
                    assert math.isclose(a[k], b[k], rel_tol=2e-12, abs_tol=2e-14)
                else:
                    assert a[k] == b[k]
        validation = dict(status='passed', native_MIP_results=360,
                          independently_reconstructed_ratios=56,
                          parent_deletions=6, domain_counts_checked=5,
                          analysis_sha256=sha(target), input_sha256=inputs)
        (HERE/'PARENT_SENSITIVITY_VALIDATION.json').write_text(json.dumps(validation, indent=2)+'\n')
        print('Parent deletion replay passed: 56 ratios and five domain counts; no optimizer calls.')
    else:
        target.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
        for r in comparisons:
            if r['control'] in ['Base', 'L2']:
                print(r)


if __name__ == '__main__':
    main()
