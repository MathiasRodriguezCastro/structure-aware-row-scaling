"""Quality-first comparison of all registered calls; produce report inputs."""
import csv
import json
import math
import statistics

from screen import HERE, csvwrite, dump


def read(name):
    return list(csv.DictReader((HERE/name).open()))


def gm(values):
    return math.exp(statistics.mean(math.log(x) for x in values))


def main():
    pilot=read('pilot-results.csv')
    replication=read('replication-results.csv')
    assert len(pilot)==84 and len(replication)==126
    assert all(r['rounded_pass_1e-07']=='True' and r['raw_pass_1e-07']=='True' for r in pilot+replication)
    assert all(r['common_target_pass']=='True' for r in replication)
    preparations={(r['instance'],r['policy'],r['seed']):float(r['preparation_seconds']) for r in read('preparation-times.csv')}
    full=[]
    for row in replication:
        key=row['instance'],row['policy'],row['seed']
        policy='Flat-L2' if row['policy'] in ('Flat-L2-tight','Flat-L2-NF3') else row['policy']
        prep=preparations[row['instance'],policy,row['seed']]
        raw=json.loads((HERE/'replication'/row['instance']/row['policy']/('seed-'+row['seed'])/'run.json').read_text())
        full.append(dict(instance=row['instance'],policy=row['policy'],seed=row['seed'],
            work=float(row['work']),preparation_seconds=prep,read_solve_seconds=raw['read_and_solve_seconds'],
            full_cycle_seconds=prep+raw['read_and_solve_seconds'],
            common_target_pass=True,rounded_max=float(row['rounded_row_max'])))
    csvwrite(HERE/'replication-costs.csv',full)
    indexed={(r['instance'],r['policy'],r['seed']):r for r in full}
    budget=[r for r in full if r['policy']=='Budget-L2']
    comparisons=[]
    for control in dict.fromkeys(r['policy'] for r in full if r['policy']!='Budget-L2'):
        paired=[(r,indexed[r['instance'],control,r['seed']]) for r in budget]
        rec=dict(control=control,pairs=len(paired),models=len({r['instance'] for r in budget}))
        for metric in ('work','full_cycle_seconds'):
            ratios=[a[metric]/b[metric] for a,b in paired]
            rec['budget_over_control_'+metric]=gm(ratios)
            rec['budget_wins_'+metric]=sum(r<1 for r in ratios)
        comparisons.append(rec)
    csvwrite(HERE/'comparisons.csv',comparisons)
    per_model=[]
    for name in dict.fromkeys(r['instance'] for r in budget):
        selected=[r for r in budget if r['instance']==name]
        rec=dict(instance=name)
        for policy in ('Base','Flat-L2','Role-Hybrid','Flat-L2-NF3'):
            for metric in ('work','full_cycle_seconds'):
                ratios=[r[metric]/indexed[name,policy,r['seed']][metric] for r in selected]
                rec[policy+'_'+metric+'_median_ratio']=statistics.median(ratios)
        per_model.append(rec)
    csvwrite(HERE/'per-model-comparisons.csv',per_model)
    condition=read('conditioning.csv')
    by={(r['instance'],r['policy'],r['equilibration_passes']):float(r['kappa_positive']) for r in condition}
    all_models=list(dict.fromkeys(r['instance'] for r in condition))
    condition_summary=[]
    for policy in ('Role-Hybrid','Flat-L2','Budget-L2-1e-05'):
        for passes in ('0','10'):
            ratios=[by[n,policy,passes]/by[n,'Base',passes] for n in all_models]
            condition_summary.append(dict(policy=policy,passes=int(passes),ratio_over_base=gm(ratios),
                models_better_than_base=sum(r<1 for r in ratios)))
    source_structure=read('structure.csv')
    metadata=dict(pilot_runs=84,replication_runs=126,all_points_within_1e_minus7=True,
        pilot_max_raw=max(float(r['raw_row_max']) for r in pilot),
        pilot_max_rounded=max(float(r['rounded_row_max']) for r in pilot),
        replication_max_rounded=max(float(r['rounded_row_max']) for r in replication),
        coupling_rows=sum(int(r['coupling_rows']) for r in source_structure),
        local_rows=sum(int(r['local_rows']) for r in source_structure),
        incompatible_uniform_contracts_1e_minus7=sum(int(r['budget_1e-07_coupling_incompatible']) for r in source_structure),
        condition_summary=condition_summary,comparisons=comparisons,
        small_time_scope='individual solver calls and preprocessing are short; wall-time differences are descriptive on this shared machine',
        conclusion='active coupling and active contracts confirmed; no exclusive accuracy benefit and no general advantage over unscaled Base in the common-quality replication')
    dump(HERE/'summary.json',metadata)
    print(json.dumps(metadata,indent=2))


if __name__=='__main__':
    main()
