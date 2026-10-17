"""Solver-free rational replay; does not import method.py or study.py."""
import copy
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
F = Fraction.from_float
EPS, GAMMA, TAU = F(1e-6), F(1e-9), F(1e-6)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def residual(row, x):
    gap = sum((F(float(a))*x[int(j)] for j,a in row['terms'].items()), Fraction(0))-F(float(row['rhs']))
    return abs(gap) if row['sense']=='=' else max(Fraction(0),gap if row['sense']=='<' else -gap)


def bounds(model, point):
    ratios=[]
    for v,x in zip(model['variables'],point):
        d=F(float(v['bound_budget']))
        lo=Fraction(0) if v['lower'] is None else max(Fraction(0),F(float(v['lower']))-x)
        hi=Fraction(0) if v['upper'] is None else max(Fraction(0),x-F(float(v['upper'])))
        ratios.append(max(lo,hi)/d)
    return max(ratios,default=Fraction(0))


def original_check(original, point, selected, budget):
    raw=point[:len(original['variables'])]
    rounded=[Fraction(round(x)) if v['integer'] else x for x,v in zip(raw,original['variables'])]
    metrics={}
    for label,x in (('raw',raw),('rounded',rounded)):
        ratios=[residual(r,x)/F(float(budget if i in selected else r['budget'])) for i,r in enumerate(original['rows'])]
        target=max((ratios[i] for i in selected),default=Fraction(0))
        br=bounds(original,x)
        metrics[label]={'maximum_row_budget_ratio':float(max(ratios)), 'activation_budget_ratio':float(target),
                        'failed_rows':sum(q>1 for q in ratios),'maximum_bound_budget_ratio':float(br),
                        'all_primal_budgets_met':max(ratios)<=1 and br<=1,
                        'objective':float(sum((F(float(v['cost']))*p for v,p in zip(original['variables'],x)),Fraction(0)))}
    metrics['maximum_integer_distance']=float(max((abs(x-round(x)) for x,v in zip(raw,original['variables']) if v['integer']),default=Fraction(0)))
    return metrics,rounded


def static_check(original, contracted, model, meta):
    n=len(original['variables']); chosen=set(meta['selected_rows'])
    assert model['variables'][:n]==original['variables']
    ref=original if meta['policy'] in ('Linear-L2','Linear-NF3') else contracted
    gates={g['row']:g for g in meta['gates']}
    checks=0
    for i,source in enumerate(ref['rows']):
        row=model['rows'][i];alpha=F(float(meta['factors'][i]))
        if i in gates:
            g=gates[i];z=g['z'];h=F(g['h']);M=F(float(g['M']))
            assert original['variables'][z]['integer'] and (original['variables'][z]['lower'],original['variables'][z]['upper'])==(0.,1.)
            assert source['rhs']==0 and source['sense']!='='
            sign=1 if source['sense']=='<' else -1
            terms={j:sign*F(float(a)) for j,a in source['terms'].items()}
            assert terms.pop(str(z))==-M
            assert all(not original['variables'][int(j)]['integer'] for j in terms)
            assert {j:F(float(a)) for j,a in row['terms'].items()}=={**terms,str(g['y']):-h}
            assert row['sense']=='<' and row['rhs']==0
            assert F(float(model['variables'][g['y']]['upper']))==M/h
            assert F(float(g['auxiliary_upper']))==M/h and M/h<=F(1e19)
            complement=model['rows'][g['complement_row']]
            assert complement['terms']=={str(g['w']):1.,str(z):1.} and complement['sense']=='=' and complement['rhs']==1
            assert meta['factors'][g['complement_row']]==1.
            predicted=EPS/alpha+h*max(GAMMA,TAU)
            assert predicted==Fraction(g['rounded_residual_bound'])
            if meta['policy']=='Activity-budget':
                delta=F(float(meta['activation_budget']))
                assert predicted<=delta
                # No larger h can work: even ignoring row residual it exhausts delta.
                assert 2*h*max(GAMMA,TAU)>=delta
        else:
            assert row==source
        for a in [*row['terms'].values(),row['rhs']]:
            assert F(float(a)*float(alpha))==F(float(a))*alpha
        assert all(F(1e-9)<=abs(F(float(a))*alpha)<=F(1e9) for a in row['terms'].values() if a)
        if i not in chosen:
            reserve=GAMMA*sum((abs(F(float(a))) for j,a in row['terms'].items() if original['variables'][int(j)]['integer']),Fraction(0))
            assert EPS/alpha+reserve<=F(float(source['budget']))
        checks+=1
    assert set(gates)==chosen if gates else not meta['gates']
    assert 1-GAMMA-EPS>GAMMA
    return checks


def main():
    design=json.loads((HERE/'pilot/design.json').read_text())
    assert design['protocol_sha256']==sha(HERE/'PROTOCOL.md')
    assert design['method_sha256']==sha(HERE/'method.py')
    assert design['runner_sha256']==sha(HERE/'study.py')
    bank={}; static_rows=0; exports=0
    for item in design['models']:
        source=ROOT/item['source'];contracted=ROOT/item['contracted_source']
        assert sha(source)==item['source_sha256'] and sha(contracted)==item['contracted_sha256']
        original=json.loads(source.read_text());cmodel=json.loads(contracted.read_text())
        bank[item['name']]=original
        for arm in sorted((HERE/'pilot/models'/item['name']).iterdir()):
            model=json.loads((arm/'model.json').read_text());meta=json.loads((arm/'selection.json').read_text())
            static_rows+=static_check(original,cmodel,model,meta);exports+=1
    results=[];attempts=0;point_count=0;hypchecks=0
    for call in design['calls']:
        output=HERE/'pilot/runs'/call['name']/call['arm']/str(call['seed'])
        if not (output/'run.json').exists():continue
        attempts+=1
        record=json.loads((output/'run.json').read_text())
        arm=HERE/'pilot/models'/call['name']/call['arm']
        assert sha(arm/'model.lp')==call['export_sha256']
        meta=json.loads((arm/'selection.json').read_text());model=json.loads((arm/'model.json').read_text())
        original=bank[call['name']]
        started=time.perf_counter()
        verification={'original_optimality_certified':False,'has_point':record['has_point']}
        if record['has_point']:
            with np.load(output/'point.npz',allow_pickle=False) as saved:
                point=[F(float(x)) for x in saved['x']]
            assert len(point)==len(model['variables']) and all(math.isfinite(float(x)) for x in point)
            point_count+=1
            verification['budgets']={}
            for budget in (1e-4,1e-8):
                metrics,rounded=original_check(original,point,set(meta['selected_rows']),budget)
                verification['budgets'][f'{budget:.0e}']=metrics
            gate_failures=[]; measured=[];theorem_protected=0
            for g in meta['gates']:
                z,y,w=(point[g[k]] for k in ('z','y','w'))
                row=g['row'];alpha=F(meta['factors'][row]);h=F(g['h'])
                conditions=(abs(z-round(z))<=GAMMA,round(z) in (0,1),
                            abs(w+z-1)<=EPS,min(abs(w),abs(y))<=GAMMA,
                            residual(model['rows'][row],point)*alpha<=EPS,
                            y-F(float(g['auxiliary_upper']))<=TAU)
                hypchecks+=1
                if not all(conditions):gate_failures.append({'row':row,'conditions':list(conditions)})
                else:
                    # Independent original-row transfer, including changed M'.
                    raw=point[:len(original['variables'])]
                    rpoint=[Fraction(round(x)) if v['integer'] else x for x,v in zip(raw,original['variables'])]
                    violation=residual(original['rows'][row],rpoint)
                    assert violation<=EPS/alpha+h*max(GAMMA,TAU)
                    theorem_protected+=1
                measured.append(float(residual(original['rows'][row],point[:len(original['variables'])])))
            exported_failures=sum(residual(r,point)*F(float(a))>EPS for r,a in zip(model['rows'],meta['factors']))
            verification['sos_hypothesis_failures']=gate_failures
            verification['gates_with_checked_transfer']=theorem_protected
            verification['exported_row_hypothesis_failures']=exported_failures
        verification['verification_seconds']=time.perf_counter()-started
        (output/'verification.json').write_text(json.dumps(verification,indent=2,allow_nan=False)+'\n')
        for budget in ((record['activation_budget'],) if record['activation_budget'] is not None else (1e-4,1e-8)):
            item={**{k:record[k] for k in ('name','arm','seed','policy','status','has_point','work','runtime','prepare_and_import_seconds','objective')},
                  'budget':budget,'original_optimality_certified':False}
            if record['has_point']:
                met=verification['budgets'][f'{budget:.0e}']
                item.update({'raw_primal_pass':met['raw']['all_primal_budgets_met'],
                             'rounded_primal_pass':met['rounded']['all_primal_budgets_met'],
                             'maximum_rounded_ratio':met['rounded']['maximum_row_budget_ratio'],
                             'activation_rounded_ratio':met['rounded']['activation_budget_ratio'],
                             'hypothesis_failure_gates':len(verification['sos_hypothesis_failures']),
                             'exported_row_hypothesis_failures':verification['exported_row_hypothesis_failures']})
            results.append(item)
    result={'planned_calls':len(design['calls']),'completed_calls':attempts,'saved_points':point_count,
            'static_exports_checked':exports,'static_original_rows_checked':static_rows,
            'returned_gate_hypotheses_checked':hypchecks,'optimizer_calls':0,
            'all_complete':attempts==len(design['calls'])}
    (HERE/'VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n')
    (HERE/'pilot/RESULTS.json').write_text(json.dumps(results,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
