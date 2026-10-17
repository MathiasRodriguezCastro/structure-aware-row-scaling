#!/usr/bin/env python3
from collections import Counter
from fractions import Fraction as Q
from pathlib import Path
import hashlib
import json
import statistics
import numpy as np
from common import load,dump,ExactData
from metrics import refuted,supported,root_line,start_loaded,tolerance

HERE=Path(__file__).resolve().parent


def main():
    d=load(HERE/'design.json');rd=load(HERE/'run-design.json');post=load(HERE/'posthoc-design.json')
    result=[];audits={};references={}
    for instance in d['instances']:
        data=load(HERE/'inputs'/instance/'canonical.json.gz');checker=ExactData(data)
        reference=rd['references'][instance]
        if not reference.get('exact_feasible'):continue
        u=Q(reference['objective_exact']);references[instance]=dict(objective_exact=str(u),acquisition_seconds=reference['total_seconds'])
        q=load(HERE/'references'/instance/'rational-point.json')
        p0={str(j):str(Q(q[j])) for j,v in enumerate(data['variables']) if v['type']!='C'}
        for job in (j for j in rd['schedule'] if j['instance']==instance):
            name='{instance}-{policy}-{start}-s{seed}'.format(**job);folder=HERE/'runs'/name
            r=load(folder/'run.json');xs=np.load(folder/'candidates.npz')['x'];log=(folder/'solver.log').read_text()
            final=checker.check(xs[-1]);audits[name]=final
            observed_same=[]
            for event,x in zip(r['events'],xs):
                p={str(j):str(round(float(x[j]))) for j,v in enumerate(data['variables']) if v['type']!='C'}
                if p==p0 and Q(event['reported_objective'])+tolerance(u)>=u and Q(event['reported_objective'])<=u+tolerance(u):observed_same.append(event)
            cert=load(HERE/'certificates'/post['assignments'][name]/'result.json')
            minimum=cert.get('objective_exact') if cert['outcome']=='optimum_certified' else None
            root=[p for p in r['progress'] if p['nodes']==0 and p['incumbent'] is not None]
            result.append(dict(name=name,**job,status=r['status'],work=r['work'],runtime=r['runtime'],nodes=r['nodes'],
                objective=r['objective'],bound=r['bound'],start_loaded=start_loaded(log),
                common_pattern_cost_seen=bool(observed_same),common_pattern_first_event=observed_same[0] if observed_same else None,
                root_relaxation_printed=root_line(log),root_best_native_incumbent=min((p['incumbent'] for p in root),default=None),
                lower_bound_refuted=refuted(r['bound'],u),
                claimed_gap_refuted=(r['objective'] is not None and u<Q(r['objective'])-Q(.001)*abs(Q(r['objective']))-tolerance(u)),
                final_pattern_certificate=cert['outcome'],final_pattern_optimum_exact=minimum,
                final_nominal_cost_supported=None if minimum is None else supported(r['objective'],Q(minimum)),
                demanding_physical_budget_pass=all(v<=1 for v in final['physical_ratios'][:1]),
                root_start_same_point_claim=(job['start']=='CommonStart' and start_loaded(log) and bool(observed_same))))
    groups={};paired={}
    for name in references:
        groups[name]={};paired[name]={}
        for mode in ['Cold','CommonStart']:
            by_policy={}
            for policy in ['Base','GM']:
                rs=[r for r in result if r['instance']==name and r['start']==mode and r['policy']==policy]
                by_policy[policy]=dict(n=len(rs),native_completions=sum(r['status']==2 for r in rs),median_work=statistics.median(r['work'] for r in rs),
                    start_loaded=sum(r['start_loaded'] for r in rs),same_pattern_cost_seen=sum(r['common_pattern_cost_seen'] for r in rs),
                    lower_bound_refutations=sum(r['lower_bound_refuted'] for r in rs),nominal_cost_unsupported=sum(r['final_nominal_cost_supported'] is False for r in rs),
                    root_objectives=[r['root_relaxation_printed']['objective'] if r['root_relaxation_printed'] else None for r in rs],
                    final_objectives=[r['objective'] for r in rs])
            groups[name][mode]=by_policy
            pairs=[]
            for seed in d['seeds']:
                a=next(r for r in result if r['instance']==name and r['start']==mode and r['policy']=='Base' and r['seed']==seed)
                b=next(r for r in result if r['instance']==name and r['start']==mode and r['policy']=='GM' and r['seed']==seed)
                comparable=all(x['status']==2 and x['final_nominal_cost_supported'] is True and not x['lower_bound_refuted'] for x in [a,b])
                comparable &= abs(a['objective']-b['objective'])<=1e-6*max(1,abs(a['objective']),abs(b['objective']))
                if mode=='CommonStart':comparable &= a['root_start_same_point_claim'] and b['root_start_same_point_claim']
                pairs.append(dict(seed=seed,comparable=bool(comparable),GM_over_Base_work=b['work']/a['work'] if comparable and a['work']>0 else None))
            paired[name][mode]=pairs
    root_pairs=[]
    for name in references:
        for mode in ['Cold','CommonStart']:
            for seed in d['seeds']:
                both=[r for r in result if r['instance']==name and r['start']==mode and r['seed']==seed]
                roots=[r['root_relaxation_printed'] for r in both]
                if all(roots):root_pairs.append(roots[0]['objective']==roots[1]['objective'])
    dump(HERE/'point-audits.json.gz',audits)
    dump(HERE/'analysis.json',dict(rows=result,groups=groups,paired=paired,references=references,
        native_mip_calls=len(result),all_start_rows_same_point_verified=all(r['root_start_same_point_claim'] for r in result if r['start']=='CommonStart'),
        printed_root_pairs=len(root_pairs),printed_root_pairs_matching=sum(root_pairs),
        retrospective_case_selection=True,general_speedup_claim=False,global_optimality_certified=False))
    print(json.dumps(groups,indent=2),flush=True)


if __name__=='__main__':main()
