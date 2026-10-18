"""Verify saved binary64 points against native network semantics with rational arithmetic.

Does not read optimizer residual attributes or reuse exported constraint matrices.
Reports approximate primal accuracy only; no global optimality assertions.
"""
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import sys

from screen import HERE, csvwrite, digest, dump
from pilot import factors


def verify(model, policy, point):
    expansion=model['family']=='Gunluk-expansion'
    n,e,k=model['nodes'],len(model['arcs']),len(model['demands'])
    q=2*e if expansion else e
    p=2*e if expansion else e
    assert len(point)==k*q+p
    x=list(map(F,point))
    design=x[k*q:]
    rounded=[F(round(v)) for v in design]
    gamma=F(1e-9); epsilon=F(1e-6)
    distance=max(abs(v-w) for v,w in zip(design,rounded))
    local, coupling=factors(model,policy)
    aggregates=[F(0)]*q
    balance_max=F(0);raw_cap=F(0);rounded_cap=F(0)
    bounds=max(F(0),-min(x))
    rounded_bounds=max(F(0),-min(rounded))
    if not expansion:
        bounds=max(bounds,max(design)-1)
        rounded_bounds=max(rounded_bounds,max(rounded)-1)
    objective=F(0);decoded_objective=F(0)
    hypothesis_failed=0;hypothesis_rows=0;export_residual_max=F(0);export_defect_max=F(0)
    decoded_transfer_checks=0

    def row_audit(raw_residual,rounded_residual,native_residual,alpha,E,equality):
        nonlocal hypothesis_failed,hypothesis_rows,export_residual_max,export_defect_max,decoded_transfer_checks
        violation=abs(native_residual) if equality else max(F(0),native_residual)
        defect=abs(F(float(alpha))*raw_residual-native_residual)
        export_residual_max=max(export_residual_max,violation)
        export_defect_max=max(export_defect_max,defect)
        hypothesis_rows+=1
        valid=violation+defect<=epsilon and (E==0 or distance<=gamma)
        if not valid:hypothesis_failed+=1
        decoded=abs(rounded_residual) if equality else max(F(0),rounded_residual)
        if valid:
            assert decoded<=epsilon/F(float(alpha))+E
            decoded_transfer_checks+=1

    for commodity,demand in enumerate(model['demands']):
        balances=[F(0)]*n
        for j,arc in enumerate(model['arcs']):
            forward=x[commodity*q+j]
            reverse=x[commodity*q+e+j] if expansion else F(0)
            net=forward-reverse
            balances[arc['u']]+=net;balances[arc['v']]-=net
            aggregates[j]+=forward
            if expansion:aggregates[e+j]+=reverse
            objective+=F(arc['cost'])*(forward+reverse)
        for i,activity in enumerate(balances):
            rhs=F(demand['amount']) if i==demand['u'] else -F(demand['amount']) if i==demand['v'] else F(0)
            residual=activity-rhs
            balance_max=max(balance_max,abs(residual))
            alpha=float(local[i])
            native=F(alpha)*activity-F(alpha*float(rhs))
            row_audit(residual,residual,native,alpha,F(0),True)
    decoded_objective=objective
    for j,arc in enumerate(model['arcs']):
        if expansion:
            coeff=[F(1),F(model['large_capacity'])]
            indexes=[j,e+j]
            costs=[arc['small_cost'],arc['large_cost']]
            rhs=F(arc['existing'])
            directions=[j,e+j]
        else:
            coeff=[F(arc['capacity'])];indexes=[j];costs=[arc['fixed']]
            rhs=F(0);directions=[j]
        installed=sum((a*design[t] for a,t in zip(coeff,indexes)),F(0))
        installed_rounded=sum((a*rounded[t] for a,t in zip(coeff,indexes)),F(0))
        objective+=sum((F(c)*design[t] for c,t in zip(costs,indexes)),F(0))
        decoded_objective+=sum((F(c)*rounded[t] for c,t in zip(costs,indexes)),F(0))
        E=sum(coeff,F(0))*gamma
        for i in directions:
            alpha=float(coupling[i])
            raw=aggregates[i]-installed-rhs
            decoded=aggregates[i]-installed_rounded-rhs
            raw_cap=max(raw_cap,raw);rounded_cap=max(rounded_cap,decoded)
            native=F(alpha)*aggregates[i]-sum((F(alpha*float(a))*design[t]
                for a,t in zip(coeff,indexes)),F(0))-F(alpha*float(rhs))
            row_audit(raw,decoded,native,alpha,E,False)
    raw_max=max(balance_max,raw_cap)
    rounded_max=max(balance_max,rounded_cap)
    rec=dict(balance_max_exact=str(balance_max),raw_capacity_max_exact=str(raw_cap),
        rounded_capacity_max_exact=str(rounded_cap),raw_row_max_exact=str(raw_max),
        rounded_row_max_exact=str(rounded_max),raw_row_max=float(raw_max),
        rounded_row_max=float(rounded_max),bound_max=float(bounds),rounded_bound_max=float(rounded_bounds),
        integrality_distance=float(distance),objective_exact=str(objective),
        rounded_objective_exact=str(decoded_objective),objective=float(objective),
        exported_row_max=float(export_residual_max),pointwise_export_defect_max=float(export_defect_max),
        conditional_hypothesis_rows=hypothesis_rows,conditional_hypothesis_failures=hypothesis_failed,
        conditional_transfer_checks=decoded_transfer_checks,
        exactly_feasible_decoded=rounded_max==0 and bounds==0 and rounded_bounds==0,
        checked_global_optimality=False)
    for delta in (1e-3,1e-5,1e-7):
        rec[f'raw_pass_{delta:g}']=raw_max<=F(delta) and bounds<=F(delta) and distance<=gamma
        rec[f'rounded_pass_{delta:g}']=rounded_max<=F(delta) and bounds<=F(delta) and rounded_bounds==0
    return rec


def main():
    replication='--replication' in sys.argv
    study='replication' if replication else 'runs'
    prefix='replication' if replication else 'pilot'
    design=json.loads((HERE/'replication-design.json').read_text()) if replication else None
    models={m['name']:m for m in json.loads((HERE/'models.json').read_text())}
    rows=[]
    for path in sorted((HERE/study).glob('*/*/*/run.json' if replication else '*/*/run.json')):
        record=json.loads(path.read_text())
        name,policy=record['instance'],record['policy']
        item={key:record[key] for key in ('instance','policy','status','sol_count','work','solver_seconds','objective','best_bound')}
        item['seed']=record.get('seed',record['parameters']['Seed'])
        folder=path.parent
        if record['sol_count']:
            point_path=folder/'point.json.gz'
            assert digest(point_path.read_bytes())==record['point_sha256']
            with gzip.open(point_path,'rt') as stream:point=json.load(stream)
            check=verify(models[name],policy,point)
            dump(folder/'verification.json',check)
            item.update(check)
            if replication:
                cap=F(design['references'][name]['target_exact'])
                item['common_target_pass']=check['rounded_pass_1e-05'] and F(check['rounded_objective_exact'])<=cap
        rows.append(item)
    keys=list(dict.fromkeys(key for r in rows for key in r))
    csvwrite(HERE/f'{prefix}-results.csv',[{key:r.get(key) for key in keys} for r in rows])
    report=dict(completed_runs=len(rows),points=sum(bool(r['sol_count']) for r in rows),
        transfer_checks=sum(r.get('conditional_transfer_checks',0) for r in rows),
        all_completed=len(rows)==(126 if replication else 84))
    dump(HERE/f'verification-{prefix}-points.json',report)
    print(report)
    for policy in dict.fromkeys(r['policy'] for r in rows):
        selected=[r for r in rows if r['policy']==policy]
        print(policy,'points',sum(bool(r['sol_count']) for r in selected),'/',len(selected),
            'raw1e-5',sum(r.get('raw_pass_1e-05',False) for r in selected),
            'rounded1e-5',sum(r.get('rounded_pass_1e-05',False) for r in selected),
            'max',max((r.get('rounded_row_max',0) for r in selected),default=0))


if __name__=='__main__':
    main()
