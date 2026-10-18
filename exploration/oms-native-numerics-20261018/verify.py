"""Independent native-data rational point checks; no optimizer imports or attributes."""
from fractions import Fraction as F
import gzip
import json
import math
from pathlib import Path
import sys

from fetch import HERE,dump,sha
from native import read_mps
from screen import csvwrite


def violation(activity,rhs,sense):
    residual=activity-rhs
    return abs(residual) if sense=='=' else max(F(0),residual if sense=='<' else -residual)


def check_model(name,stage,entries,delta):
    model=read_mps(HERE/'sources'/(name+'.mps.gz'))
    saved=json.load(gzip.open(HERE/'models'/name/'original.json.gz','rt'))
    assert all(saved[k]==v for k,v in model.items())
    variables=model['variables'];rows=model['rows']
    terms=[[(int(j),F(c)) for j,c in r['terms'].items()] for r in rows]
    bounds=[(None if v['lower'] is None else F(v['lower']),None if v['upper'] is None else F(v['upper'])) for v in variables]
    integers=[j for j,v in enumerate(variables) if v['integer']]
    intset=set(integers);gamma=F(1e-9);eps=F(1e-6)
    outputs=[]
    for policy in entries:
        folder=HERE/f'stage-{stage}'/name/policy;path=folder/'run.json'
        if not path.exists():continue
        record=json.loads(path.read_text())
        item={k:record.get(k) for k in ('instance','policy','status','sol_count','work','solver_seconds','measured_cycle_seconds','objective','best_bound')}
        item.update(budget=delta,point_available=bool(record['sol_count']))
        if not record['sol_count']:
            item.update(accuracy_outcome='unknown-no-point',rounded_pass=None,raw_pass=None)
            outputs.append(item);continue
        point_path=folder/'point.json.gz';assert sha(point_path.read_bytes())==record['point_sha256']
        point=json.load(gzip.open(point_path,'rt'));assert len(point)==len(variables) and all(math.isfinite(v) for v in point)
        x=list(map(F,point));decoded=x.copy()
        for j in integers:decoded[j]=F(round(x[j]))
        integer_distance=max((abs(x[j]-decoded[j]) for j in integers),default=F(0))
        raw_bound=F(0);rounded_bound=F(0)
        for raw,z,(lo,hi) in zip(x,decoded,bounds):
            if lo is not None:raw_bound=max(raw_bound,lo-raw);rounded_bound=max(rounded_bound,lo-z)
            if hi is not None:raw_bound=max(raw_bound,raw-hi);rounded_bound=max(rounded_bound,z-hi)
        export='Base' if policy.startswith('Base') else 'Budget-L2' if policy=='Budget-L2' else 'Dyadic-L2'
        factors=json.loads((HERE/'exports'/name/(export+'-factors.json')).read_text())
        source_export=HERE/'exports'/name/(export+'.lp.gz')
        assert sha(source_export.read_bytes())==record['export_sha256']
        raw_max=F(0);rounded_max=F(0);raw_worst=None;rounded_worst=None
        exported_max=F(0);hypothesis_rows=0;hypothesis_failures=0;transfer_checks=0;row_failures=[]
        for i,(row,data,alpha) in enumerate(zip(rows,terms,factors)):
            a=F(alpha);rhs=F(row['rhs'])
            assert F(float(alpha*row['rhs']))==a*rhs
            for j,c in data:assert F(float(alpha*float(c)))==a*c
            activity=sum((c*x[j] for j,c in data),F(0))
            rounded_activity=activity+sum((c*(decoded[j]-x[j]) for j,c in data if j in intset),F(0))
            raw=violation(activity,rhs,row['sense']);rounded=violation(rounded_activity,rhs,row['sense'])
            if raw>raw_max:raw_max=raw;raw_worst=row['name']
            if rounded>rounded_max:rounded_max=rounded;rounded_worst=row['name']
            exported=a*raw;exported_max=max(exported_max,exported)
            E=gamma*sum((abs(c) for j,c in data if j in intset),F(0))
            hypothesis_rows+=1
            if exported<=eps and (E==0 or integer_distance<=gamma):
                assert rounded<=eps/a+E
                transfer_checks+=1
                if eps/a+E<=F(delta):assert rounded<=F(delta)
            else:hypothesis_failures+=1
            if rounded>F(delta):row_failures.append(dict(row=i,name=row['name'],rounded_violation_exact=str(rounded),
                ratio=float(rounded/F(delta)),raw_violation_exact=str(raw),exported_violation_exact=str(exported)))
        cost=sum((F(v['cost'])*value for v,value in zip(variables,x)),F(model['objective_offset']))
        decoded_cost=sum((F(v['cost'])*value for v,value in zip(variables,decoded)),F(model['objective_offset']))
        raw_ok=raw_max<=F(delta) and raw_bound<=F(delta) and integer_distance<=gamma
        decoded_ok=rounded_max<=F(delta) and rounded_bound<=F(delta)
        result=dict(raw_max_exact=str(raw_max),rounded_max_exact=str(rounded_max),raw_worst_row=raw_worst,
            rounded_worst_row=rounded_worst,raw_max=float(raw_max),rounded_max=float(rounded_max),
            rounded_ratio=float(rounded_max/F(delta)),raw_bound_max=float(raw_bound),rounded_bound_max=float(rounded_bound),
            integrality_distance=float(integer_distance),objective_exact=str(cost),rounded_objective_exact=str(decoded_cost),
            raw_pass=raw_ok,rounded_pass=decoded_ok,raw_exported_max=float(exported_max),
            hypothesis_rows=hypothesis_rows,hypothesis_failures=hypothesis_failures,conditional_transfer_checks=transfer_checks,
            exactly_feasible_decoded=rounded_max==0 and rounded_bound==0,
            global_optimality_certified=False,accuracy_outcome='pass' if decoded_ok else 'fail',
            failed_original_rows=row_failures)
        dump(folder/'verification.json',result)
        item.update({k:v for k,v in result.items() if k!='failed_original_rows'});outputs.append(item)
    return outputs


def main():
    stage=sys.argv[1] if len(sys.argv)>1 else 'b'
    design=json.loads((HERE/f'stage-{stage}-design.json').read_text())
    results=[]
    for entry in design['selected']:
        group=check_model(entry['instance'],stage,design['policies'],entry['budget']);results.extend(group)
        print(entry['instance'],[(r['policy'],r.get('accuracy_outcome'),r.get('rounded_ratio')) for r in group],flush=True)
    csvwrite(HERE/f'stage-{stage}-results.csv',results)
    report=dict(stage=stage,calls=len(results),expected_calls=len(design['selected'])*len(design['policies']),
        points=sum(r['point_available'] for r in results),verified_within_budget=sum(r.get('rounded_pass') is True for r in results),
        observed_failures=sum(r.get('rounded_pass') is False for r in results),unknown=sum(not r['point_available'] for r in results),
        conditional_transfer_checks=sum(r.get('conditional_transfer_checks',0) for r in results),
        solver_tolerance_is_not_a_residual_guarantee=True)
    dump(HERE/f'verification-{stage}.json',report)
    print(report)
    next_stage='c2' if stage=='b2' else 'c'
    if stage in ('b','b2') and not (HERE/f'stage-{next_stage}-design.json').exists():
        selected=[]
        for entry in design['selected']:
            observed=[r for r in results if r['instance']==entry['instance'] and r.get('rounded_pass') is False]
            if observed:selected.append(dict(entry,failing_controls=[r['policy'] for r in observed]))
        dump(HERE/f'stage-{next_stage}-design.json',dict(selected=selected,common=design['common'],policies=['Budget-L2'],
            source_control_stage=stage,
            stage_b_design_sha256=sha((HERE/f'stage-{stage}-design.json').read_bytes()),
            stage_b_results_sha256=sha((HERE/f'stage-{stage}-results.csv').read_bytes()),
            decision='only remedies for observed precision failures; no point is not a precision failure'))


if __name__=='__main__':main()
