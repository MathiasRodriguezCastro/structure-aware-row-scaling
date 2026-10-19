#!/usr/bin/env python3
"""Reconstruct cluster statistics from native API work and outer process timings."""
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

import numpy as np

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(a, b):
    assert math.isclose(a, b, rel_tol=2e-12, abs_tol=2e-14), (a, b)


def main():
    saved = json.loads((HERE/'CLUSTER_ANALYSIS.json').read_text())
    assert saved['analysis'] == 'post_hoc_scenario_cluster_bootstrap'
    assert saved['resamples'] == 100000 and saved['random_seed'] == 2026101902
    assert saved['additional_optimizer_calls'] == saved['filtered_pairs'] == 0
    assert not saved['seeds_resampled'] and not saved['logging_replication_used_as_new_observations']
    assert saved['scenarios'] == 24 and saved['seeds_per_scenario'] == 3
    assert saved['tie_log_tolerance'] == 1e-12
    for p, h in saved['input_sha256'].items():
        assert sha(HERE/p) == h, p
    design = json.loads((HERE/'design.json').read_text())
    timing = json.loads((HERE/'timing.json').read_text())
    elapsed = {(r['job']['instance'],r['job']['seed'],r['job']['policy']):r['total_seconds'] for r in timing}
    controls = ['Base', 'Base-tight', 'L2', 'L2-NF3']
    names = sorted(design['models'])
    work = {}
    for job in design['jobs']:
        r = json.loads((HERE/'runs'/job['id']/'result.json').read_text())
        work[job['instance'],job['seed'],job['policy']] = r['outcome']['work']
    raw = {}
    for name in names:
        for c in controls:
            for metric, source in [('work', work), ('time', elapsed)]:
                raw[name,c,metric] = statistics.mean(
                    math.log(source[name,s,'Budget-L2']/source[name,s,c]) for s in [101,137,173])
    csv_rows = list(csv.DictReader((HERE/'cluster-scenarios.csv').open()))
    assert len(csv_rows) == 96
    assert len({(r['instance'],r['control']) for r in csv_rows}) == 96
    for r in csv_rows:
        assert int(r['seeds']) == 3 and int(r['horizon']) == design['models'][r['instance']]['horizon']
        for metric in ['work','time']:
            close(float(r[metric+'_ratio']),math.exp(raw[r['instance'],r['control'],metric]))
    rng = np.random.Generator(np.random.PCG64(2026101902))
    checked = 0
    for h in [None,24,72,168]:
        group = [n for n in names if h is None or design['models'][n]['horizon'] == h]
        n = len(group)
        draws = rng.integers(0,n,size=(100000,n),dtype=np.int64)
        assert hashlib.sha256(draws.astype('<i8').tobytes()).hexdigest() == saved['selection_sha256'][str(h)]
        # Independent calculation: frequencies of entire clusters, then weighted sums.
        counts = np.zeros((100000,n),dtype=np.int64)
        np.add.at(counts,(np.arange(100000)[:,None],draws),1)
        assert np.all(counts.sum(axis=1) == n)
        matrix = np.array([[raw[name,c,m] for c in controls for m in ['work','time']] for name in group])
        boot = counts @ matrix / n
        for j, c in enumerate(controls):
            r = next(v for v in saved['comparisons'] if v['horizon'] == h and v['control'] == c)
            assert r['scenarios'] == n and r['seed_pairs'] == 3*n
            for k, metric in enumerate(['work','time']):
                v = [raw[name,c,metric] for name in group]
                result = r[metric]
                close(result['ratio'],math.exp(statistics.mean(v)))
                lo, hi = np.exp(np.percentile(boot[:,2*j+k],[2.5,97.5],method='linear'))
                close(result['lower95'],lo); close(result['upper95'],hi)
                assert result['scenarios_favor_budget'] == sum(x < -1e-12 for x in v)
                assert result['scenario_ties'] == sum(abs(x) <= 1e-12 for x in v)
                assert result['scenarios_favor_control'] == sum(x > 1e-12 for x in v)
                assert sum(result[t] for t in ['scenarios_favor_budget','scenario_ties','scenarios_favor_control']) == n
                checked += 1
    validation = dict(status='passed', scenario_clusters=24, seeds_per_cluster=3,
        confidence_intervals_reconstructed_from_native_work_and_outer_timings=checked,
        bootstrap_resamples_per_scope=100000, scopes=4, additional_optimizer_calls=0,
        analysis_sha256=sha(HERE/'CLUSTER_ANALYSIS.json'),
        scenario_aggregates_sha256=sha(HERE/'cluster-scenarios.csv'),
        plan_sha256=sha(HERE/'CLUSTER_ANALYSIS_PLAN.md'))
    (HERE/'CLUSTER_VALIDATION.json').write_text(json.dumps(validation,indent=2)+'\n')
    print(json.dumps(validation,indent=2))


if __name__ == '__main__':
    main()
