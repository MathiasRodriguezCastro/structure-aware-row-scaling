#!/usr/bin/env python3
"""Post hoc scenario-cluster bootstrap of all primary, unfiltered paired runs."""
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CONTROLS = ['Base', 'Base-tight', 'L2', 'L2-NF3']
SEED = 2026101902
RESAMPLES = 100000
TIE = 1e-12


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    pairs = list(csv.DictReader((HERE/'verified-pairs.csv').open()))
    design = json.loads((HERE/'design.json').read_text())
    names = sorted(design['models'])
    assert len(names) == 24 and len(pairs) == 288
    values = np.empty((24, 4, 2))
    scenario_rows = []
    for i, name in enumerate(names):
        for j, control in enumerate(CONTROLS):
            group = sorted((r for r in pairs if r['instance'] == name and r['control'] == control),
                           key=lambda r: int(r['seed']))
            assert [int(r['seed']) for r in group] == [101, 137, 173]
            assert {int(r['horizon']) for r in group} == {design['models'][name]['horizon']}
            for k, metric in enumerate(['work_ratio', 'time_ratio']):
                ratios = np.array([float(r[metric]) for r in group])
                assert np.all(np.isfinite(ratios)) and np.all(ratios > 0)
                values[i, j, k] = np.log(ratios).mean()
            scenario_rows.append(dict(instance=name, horizon=design['models'][name]['horizon'],
                control=control, seeds=3, work_ratio=float(np.exp(values[i, j, 0])),
                time_ratio=float(np.exp(values[i, j, 1]))))
    rng = np.random.Generator(np.random.PCG64(SEED))
    rows = []
    selection_hashes = {}
    for horizon in [None, 24, 72, 168]:
        ids = [i for i, n in enumerate(names) if horizon is None or design['models'][n]['horizon'] == horizon]
        v = values[ids]
        draws = rng.integers(0, len(ids), size=(RESAMPLES, len(ids)), dtype=np.int64)
        selection_hashes[str(horizon)] = hashlib.sha256(draws.astype('<i8').tobytes()).hexdigest()
        # Retain each scenario's complete paired three-seed mean for every metric.
        boot = v[draws].mean(axis=1)
        for j, control in enumerate(CONTROLS):
            record = dict(horizon=horizon, control=control, scenarios=len(ids), seed_pairs=3*len(ids))
            for k, metric in enumerate(['work', 'time']):
                lo, hi = np.exp(np.quantile(boot[:, j, k], [.025, .975], method='linear'))
                record[metric] = dict(ratio=float(np.exp(v[:, j, k].mean())),
                    lower95=float(lo), upper95=float(hi),
                    scenarios_favor_budget=int(np.sum(v[:, j, k] < -TIE)),
                    scenario_ties=int(np.sum(np.abs(v[:, j, k]) <= TIE)),
                    scenarios_favor_control=int(np.sum(v[:, j, k] > TIE)))
            rows.append(record)
    with (HERE/'cluster-scenarios.csv').open('w', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=list(scenario_rows[0]))
        writer.writeheader(); writer.writerows(scenario_rows)
    result = dict(analysis='post_hoc_scenario_cluster_bootstrap', scenarios=24, seeds_per_scenario=3,
        primary_MIP_calls=360, additional_optimizer_calls=0, filtered_pairs=0,
        resamples=RESAMPLES, PRNG='NumPy PCG64', random_seed=SEED,
        quantiles=[.025, .975], quantile_method='linear_on_log_scale', tie_log_tolerance=TIE,
        clusters_sampled_with_replacement=True, seeds_resampled=False,
        logging_replication_used_as_new_observations=False,
        scope='Conditional descriptive uncertainty within the six known parents; not external validation.',
        input_sha256={p:sha(HERE/p) for p in ['CLUSTER_ANALYSIS_PLAN.md','verified-pairs.csv','design.json']},
        selection_sha256=selection_hashes, comparisons=rows)
    (HERE/'CLUSTER_ANALYSIS.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    for r in rows[:4]:
        print(r['control'],json.dumps({k:r[k] for k in ['work','time']}))


if __name__ == '__main__':
    main()
