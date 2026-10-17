#!/usr/bin/env python3
"""Numerical first-hit frontiers and separate exact-pattern support."""
from collections import Counter,defaultdict
from fractions import Fraction as Q
import csv
import json
from pathlib import Path
from statistics import median

from common import load,dump,SCENARIOS

HERE=Path(__file__).resolve().parent
CONTROLS=['Base','Tight','GM','Ruiz','L2','NumericFocus']


def csvwrite(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main():
    design=load(HERE/'design.json');outcomes=load(HERE/'outcomes.json')
    post=load(HERE/'posthoc-design.json') if (HERE/'posthoc-design.json').exists() else dict(queue={},assignments=[])
    support={};certificates={};certcounts=Counter();lpseconds=0.;native_lp=0
    for key in post['queue']:
        r=load(HERE/'certificates'/key/'result.json');certificates[key]=r
        certcounts[r['outcome']]+=1;lpseconds+=r['total_seconds'];native_lp+=r['native_lp_called']
    for t in post['assignments']:
        r=certificates[t['pattern_key']];u=Q(r['objective_exact']) if 'objective_exact' in r else None
        cap=Q(design['references'][t['job']['instance']]['objective_cap_exact']);c=Q(t['nominal_cost_exact'])
        support[(t['job']['instance'],t['job']['policy'],t['job']['seed'],t['scenario'])]=dict(
            outcome=r['outcome'],pattern_key=t['pattern_key'],target_supported=u is not None and u<=cap,
            nominal_supported=u is not None and u<=c+Q(1,100)*max(Q(1),abs(u)),
            exact_feasible_cost=float(u) if u is not None else None)
    rows=[];groups=defaultdict(list);native=[];flags=[]
    for o in outcomes:
        j=o['job']
        if not o.get('alias_of'):
            r=load(HERE/o['source']/'run.json');native.append(r)
            ref=Q(design['references'][j['instance']]['objective_exact'])
            if Q(r['bound'])>ref:
                flags.append(dict(**j,bound=r['bound'],reference=float(ref),excess=float(Q(r['bound'])-ref),status=r['status']))
        for scenario in SCENARIOS:
            h=o.get('first_hit',{}).get(scenario);p=o.get('precision_only_first',{}).get(scenario)
            s=support.get((j['instance'],j['policy'],j['seed'],scenario),{})
            row=dict(**j,scenario=scenario,alias_of=o.get('alias_of') or '',numeric_hit=h is not None,
                     precision_only_hit=p is not None,first_work=h['work'] if h else None,
                     first_optimizer_seconds=h['runtime'] if h else None,
                     measured_prefix_seconds=o['selection_seconds']+o['construction_seconds']+h['runtime'] if h else None,
                     target_pattern_supported=s.get('target_supported',False),nominal_cost_supported=s.get('nominal_supported',False),
                     exact_pattern_outcome=s.get('outcome','no_numeric_hit'),pattern_key=s.get('pattern_key',''),
                     selection_seconds=o['selection_seconds'],construction_seconds=o['construction_seconds'],
                     total_optimizer_seconds=o['optimizer_seconds'],all_candidates_verification_seconds=o['verification_seconds'],
                     candidate=h['candidate'] if h else None,objective=h['check']['objective'] if h else None,
                     physical_ratio=h['check']['physical_ratios'][list(SCENARIOS).index(scenario)] if h else None)
            rows.append(row);groups[(j['instance'],j['policy'],scenario)].append(row)
    summaries=[]
    for (instance,policy,scenario),rs in sorted(groups.items()):
        works=[r['first_work'] for r in rs if r['numeric_hit']]
        summaries.append(dict(instance=instance,policy=policy,scenario=scenario,seeds=len(rs),numeric_hits=len(works),
                              exact_supported_hits=sum(r['numeric_hit'] and r['target_pattern_supported'] and r['nominal_cost_supported'] for r in rs),
                              precision_only_hits=sum(r['precision_only_hit'] for r in rs),
                              median_work_on_hits=median(works) if works else None,
                              median_work_all_three=median(works) if len(works)==3 else None,
                              median_selection_seconds=median(r['selection_seconds'] for r in rs)))
    indexed={(r['instance'],r['policy'],r['seed'],r['scenario']):r for r in rows};comparisons=[]
    for instance in design['instances']:
        for scenario in SCENARIOS:
            for seed in design['seeds']:
                budget=indexed[(instance,'Budget-'+scenario,seed,scenario)]
                controls=[indexed[(instance,p,seed,scenario)] for p in CONTROLS]
                successful=[r for r in controls if r['numeric_hit']]
                supported=[r for r in successful if r['target_pattern_supported'] and r['nominal_cost_supported']]
                best=min(successful,key=lambda r:(r['first_work'],r['policy'])) if successful else None
                best_supported=min(supported,key=lambda r:(r['first_work'],r['policy'])) if supported else None
                comparisons.append(dict(instance=instance,scenario=scenario,seed=seed,budget_hit=budget['numeric_hit'],
                    budget_supported=budget['target_pattern_supported'] and budget['nominal_cost_supported'],
                    budget_work=budget['first_work'],best_control=best['policy'] if best else None,
                    best_control_work=best['first_work'] if best else None,
                    budget_over_best_control_work_ratio=budget['first_work']/best['first_work'] if budget['numeric_hit'] and best else None,
                    budget_faster_than_every_control=bool(budget['numeric_hit'] and (best is None or budget['first_work']<best['first_work'])),
                    best_supported_control=best_supported['policy'] if best_supported else None,
                    best_supported_control_work=best_supported['first_work'] if best_supported else None,
                    budget_supported_faster=bool(budget['numeric_hit'] and budget['target_pattern_supported'] and budget['nominal_cost_supported'] and
                                                 (best_supported is None or budget['first_work']<best_supported['first_work']))))
    csvwrite(HERE/'first-hits.csv',rows);csvwrite(HERE/'summary.csv',summaries);csvwrite(HERE/'matched-comparisons.csv',comparisons)
    precision_independent=sum(len({o['first_hit'].get(s,{}).get('candidate') for s in SCENARIOS})==1 for o in outcomes)
    payload=dict(arms=len(outcomes),native_mip_calls=len(native),candidate_events=sum(len(r['events']) for r in native),
                 arms_with_identical_first_hits_across_precision_scenarios=precision_independent,
                 median_capture_seconds=median(r['capture_seconds'] for r in native),
                 groups=summaries,matched_comparisons=comparisons,
                 exact_pattern_counts=dict(certcounts),unique_posthoc_patterns=len(post['queue']),posthoc_native_lp_calls=native_lp,
                 posthoc_acquisition_total_seconds=lpseconds,bound_contradictions_against_prior_exact_reference=flags,
                 native_statuses=dict(Counter(r['status'] for r in native)),
                 reference_lp_calls=len(design['references']),
                 causal_scope='same original models/parameters except declared policies; known cases, no generalization or MILP optimality claim')
    dump(HERE/'analysis.json',payload)
    for r in summaries:
        if r['scenario']=='Demanding' and r['policy'] not in ('GCD','Budget-Permissive','Budget-Reference'):
            print(r['instance'],r['policy'],r['numeric_hits'],r['exact_supported_hits'],r['median_work_on_hits'])
    print('Matched budget faster:',sum(r['budget_faster_than_every_control'] for r in comparisons),'/',len(comparisons))
    print('Pattern-supported faster:',sum(r['budget_supported_faster'] for r in comparisons),'/',len(comparisons))
    print('Bound contradictions',len(flags),'patterns',dict(certcounts))


if __name__=='__main__':main()
