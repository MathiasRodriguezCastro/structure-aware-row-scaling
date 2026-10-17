#!/usr/bin/env python3
"""Descriptive paired endpoints; no fitting, solver calls or censored speedups."""
from collections import Counter,defaultdict
import csv
import gzip
import json
from pathlib import Path
from statistics import median

HERE=Path(__file__).resolve().parent


def read(p):
    b=Path(p).read_bytes();return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)


def main():
    groups=defaultdict(list);runs={};diag={};rows=[];paired=[]
    for p in sorted((HERE/'runs').glob('*/*.json.gz')):
        if '-presolved' in p.name:continue
        r=read(p)
        if '-diagnostic' in p.name:diag[p.name.removesuffix('-diagnostic.json.gz')]=r;continue
        j=r['job'];groups[(p.parent.name,j['instance'],j['policy'],j['scale'],j['presolve'])].append(r)
        runs[(j['instance'],j['policy'],j['scale'],j['presolve'],j['seed'])]=r
    for (stage,instance,policy,scale,presolve),rs in sorted(groups.items()):
        d=diag.get(f'{instance}-{policy}-s{scale}-p{presolve}')
        if d is None:
            aliases=[r for r in rs if r['alias_of']]
            if aliases:
                name=Path(aliases[0]['alias_of']).name.split('-seed')[0];d=diag.get(name)
        record=dict(stage=stage,instance=instance,policy=policy,scale=scale,presolve=presolve,
                    arms=len(rs),actual_calls=sum(not r['alias_of'] for r in rs),completed=sum(r['status']==2 for r in rs),
                    statuses=dict(Counter(r['status'] for r in rs)),median_work=median(r['work'] for r in rs),
                    median_seconds=median(r['runtime'] for r in rs),minimum_objective=min((r['objective'] for r in rs if r['objective'] is not None),default=None),
                    maximum_objective=max((r['objective'] for r in rs if r['objective'] is not None),default=None),
                    maximum_gap=max((r['gap'] for r in rs if r['gap'] is not None),default=None),
                    max_physical_ratio=max((r['verification']['max_physical_ratio']['Reference'] for r in rs if r['verification']),default=None),
                    diagnostic=d)
        rows.append(record)
        if policy=='Structural':
            ratios=[];incomparable=[]
            for r in rs:
                b=runs[(instance,'Base',scale,presolve,r['job']['seed'])]
                comparable=(r['status']==2 and b['status']==2 and
                            abs(r['objective']-b['objective'])<=1e-6*max(1.,abs(b['objective']),abs(r['objective'])))
                if comparable:ratios.append(r['work']/b['work'])
                else:incomparable.append(dict(seed=r['job']['seed'],base_status=b['status'],scaled_status=r['status'],
                                              base_objective=b['objective'],scaled_objective=r['objective']))
            paired.append(dict(stage=stage,instance=instance,scale=scale,presolve=presolve,comparable_pairs=len(ratios),
                               median_work_ratio=median(ratios) if ratios else None,incomparable=incomparable))
    exact_path=HERE/'exact-witness/result.json';witness=read(exact_path) if exact_path.exists() else None
    contradicted=[]
    if witness and witness['outcome']=='exact_feasible':
        for key,r in runs.items():
            if key[0]=='instance001' and r['bound']>witness['objective']+1e-6:
                contradicted.append(dict(**r['job'],status=r['status'],bound=r['bound'],
                                         excess_over_witness=r['bound']-witness['objective']))
    payload=dict(groups=rows,paired_comparisons=paired,
                 paired_comparability='Both status 2 at gap .001, objectives differ <=1e-6 max(1,abs(U1),abs(U2)); no speed ratio otherwise',
                 native_mip_calls=sum(r['actual_calls'] for r in rows),arms=sum(r['arms'] for r in rows),
                 diagnostics=len(diag),separate_lp_calls=len(diag),exact_witness=witness,contradicted_bounds=contradicted)
    (HERE/'analysis.json').write_text(json.dumps(payload,indent=2)+'\n')
    flat=[{k:v for k,v in r.items() if k not in {'statuses','diagnostic'}} for r in rows]
    with (HERE/'group-summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
    for r in rows:
        if r['scale']==r['presolve']==-1:
            print(r['stage'],r['instance'],r['policy'],r['completed'],'/3',round(r['median_work'],4),
                  r['minimum_objective'],r['maximum_objective'],r['maximum_gap'])
    print('Arms',payload['arms'],'MIP calls',payload['native_mip_calls'],'LP diagnostics',payload['diagnostics'])


if __name__=='__main__':main()
