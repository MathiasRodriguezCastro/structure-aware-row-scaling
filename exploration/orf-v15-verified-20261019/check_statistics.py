#!/usr/bin/env python3
"""Recompute grouped PAR2 ratios from saved target indices and cluster counts."""
import hashlib
import json
import math
from pathlib import Path
import statistics

import numpy as np

HERE=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text())


def main():
    result=load(HERE/'COMPUTATIONAL_RESULTS.json');d=load(HERE/'design.json')
    technical=load(HERE/'TECHNICAL_REPEAT.json');records=[]
    for j in d['jobs']:
        root=HERE/'technical-repeat' if technical['standardized_timing_replacement_permitted'] and j['id']==technical['job_id'] else HERE
        records.append(load(root/'runs'/j['id']/'result.json'))
    scopes=[(result['experiment_I'],[r for r in records if r['job']['experiment']=='I'],2026101906),
            (result['CPLEX'],[r for r in records if r['job']['experiment']=='III-cplex'],2026101908)]
    subset={j['instance'] for j in d['jobs'] if j['experiment']=='III-scale'}
    for sf in [-1,0,2]:
        rr=[r for r in records if r['job']['instance'] in subset and r['job']['solver']=='gurobi' and r['job']['scale']==sf
            and r['job']['policy'] in ['Base','L2','Budget-L2'] and r['job']['contract']=='b100']
        scopes.append((result['Gurobi_internal_scaling'][str(sf)],rr,2026101910+sf))
    checked=0
    for output,rr,seed in scopes:
        names=sorted({r['job']['instance'] for r in rr});n=len(names)
        assert output['scenarios']==n
        lookup={(r['job']['instance'],r['job']['seed'],r['job']['policy']):r for r in rr}
        draws=np.random.Generator(np.random.PCG64(seed)).integers(0,n,size=(100000,n))
        counts=np.zeros((100000,n),dtype=np.int64)
        np.add.at(counts,(np.arange(100000)[:,None],draws),1)
        for c in output['comparisons']:
            for metric in ['process_discovery','offline_verified_available']:
                logmeans=[]
                for name in names:
                    values=[]
                    for s in d['seeds']:
                        b=lookup[name,s,'Budget-L2'];control=lookup[name,s,c['control']]
                        times=[]
                        for r in [b,control]:
                            f=r['first_qualified'][str(c['tau'])]
                            times.append(f[metric] if f is not None else 60+r['solve_started_process_seconds'])
                        values.append(math.log(times[0])-math.log(times[1]))
                    logmeans.append(statistics.mean(values))
                samples=counts@np.array(logmeans)/n
                low,high=np.exp(np.percentile(samples,[2.5,97.5],method='linear'))
                expected=c[metric]
                for observed,want in [(math.exp(statistics.mean(logmeans)),expected['PAR2_paired_geometric_ratio']),
                                      (low,expected['lower95']),(high,expected['upper95'])]:
                    assert math.isclose(observed,want,rel_tol=2e-12,abs_tol=2e-14),(observed,want)
                assert expected['scenarios_favor_budget']==sum(v < -1e-12 for v in logmeans)
                checked+=1
        for p in output['policy_results']:
            group=[r for r in rr if r['job']['policy']==p['policy']]
            assert len(group)==p['runs']
            for tau in [.001,.01]:assert sum(r['first_qualified'][str(tau)] is not None for r in group)==p['targets'][str(tau)]
    report=dict(status='passed',grouped_intervals_independently_recomputed=checked,
        scenario_scopes=len(scopes),all_three_seeds_retained=True,additional_optimizer_calls=0,
        results_sha256=hashlib.sha256((HERE/'COMPUTATIONAL_RESULTS.json').read_bytes()).hexdigest())
    (HERE/'STATISTICS_VALIDATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
