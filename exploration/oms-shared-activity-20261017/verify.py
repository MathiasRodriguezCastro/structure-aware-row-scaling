"""Independent rational audit of static contracts and original returned points.

Does not import the selector, runner or a solver. Aliases are checked as byte
identities with identical parameters, not counted as independent optimizations.
"""
import argparse
import collections
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np
import mps_check

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
F=Fraction.from_float


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def ceil_log(q):
    k=q.numerator.bit_length()-q.denominator.bit_length()
    while Fraction(2)**k<q:k+=1
    while Fraction(2)**(k-1)>=q:k-=1
    return k


def floor_log(q):
    k=ceil_log(q);return k-int(Fraction(2)**k>q)


def shifts(value):
    n,d=abs(float(value)).as_integer_ratio();lowbit=(n&-n).bit_length()-1
    return -1074-lowbit+d.bit_length()-1,1023-n.bit_length()+d.bit_length()


def interval(g,M,delta):
    numbers=[abs(F(float(x))) for x in g.values() if x]
    A=min(1023,floor_log(F(1e9)/max(numbers)),*(shifts(float(x))[1] for x in numbers))
    C=max(-1074,ceil_log(F(1e-9)/min(numbers)),*(shifts(float(x))[0] for x in numbers))
    loM,hiM=shifts(float(M));B=min(floor_log(F(1e9)/M),hiM);D=max(ceil_log(F(1e-9)/M),loM)
    P=F(1e-6)*Fraction(2)**(-A);Q=F(1e-6)*Fraction(2)**(-B);MT=M*F(1e-5)
    if A<C or B<D or delta<=P:return None
    low=max(-1074,-hiM,C-B,ceil_log(MT/(delta-P)),ceil_log((Q+MT)/delta))
    high=min(1023,floor_log(F(1e19)),-loM,A-D)
    return low,high,A,B,C,D


def violation(row,point):
    signed=sum((F(float(a))*point[int(j)] for j,a in row['terms'].items()),Fraction(0))-F(float(row['rhs']))
    return abs(signed) if row['sense']=='=' else max(Fraction(0),signed if row['sense']=='<' else -signed)


def point_metrics(original,point):
    n=len(original['variables']);raw=point[:n]
    rounded=[Fraction(round(x)) if v['integer'] else x for x,v in zip(raw,original['variables'])]
    metrics={}
    for label,values in (('raw',raw),('rounded',rounded)):
        ratios=[violation(r,values)/F(float(r['budget'])) for r in original['rows']]
        bound_errors=[];integer_failures=[]
        for j,(x,v) in enumerate(zip(values,original['variables'])):
            lo=Fraction(0) if v['lower'] is None else max(Fraction(0),F(float(v['lower']))-x)
            hi=Fraction(0) if v['upper'] is None else max(Fraction(0),x-F(float(v['upper'])))
            bound_errors.append(max(lo,hi)/F(float(v['bound_budget'])))
            if label=='rounded' and v['integer'] and (x.denominator!=1 or lo>0 or hi>0):integer_failures.append(j)
        objective=sum((F(float(v['cost']))*x for x,v in zip(values,original['variables'])),Fraction(0))
        metrics[label]={'maximum_row_budget_ratio':float(max(ratios,default=Fraction(0))),
                        'failed_rows':sum(r>1 for r in ratios),'maximum_bound_budget_ratio':float(max(bound_errors,default=Fraction(0))),
                        'integer_domain_failures':integer_failures,
                        'accepted':not any(q>1 for q in ratios) and not any(q>1 for q in bound_errors) and not integer_failures,
                        'objective':float(objective),'objective_exact':str(objective)}
    metrics['maximum_integer_distance']=float(max((abs(x-round(x)) for x,v in zip(raw,original['variables']) if v['integer']),default=Fraction(0)))
    return metrics,rounded


def scaled_source(base,scope,k):
    # A separate rational reconstruction of coherent row-unit changes.
    rows=[]
    for i,r in enumerate(base['rows']):
        scale=Fraction(2)**k if i in scope else Fraction(1)
        rows.append({'terms':{j:F(float(x))*scale for j,x in r['terms'].items()},'rhs':F(float(r['rhs']))*scale,
                     'sense':r['sense'],'budget':F(float(r['budget']))*scale})
    return rows


def check_static(base,model,meta,source_rows):
    n=len(base['variables']);selected=set(meta['selected_rows']);links={g['row']:g for g in meta['links']}
    indicators={g['row']:g for g in meta['indicators']};count=0
    assert model['variables'][:n]==base['variables'] and len(model['rows'])==len(meta['factors'])
    for i,source in enumerate(source_rows):
        r=model['rows'][i]
        if i not in links and i not in indicators:
            assert {j:F(float(x)) for j,x in r['terms'].items()}==source['terms']
            assert F(float(r['rhs']))==source['rhs'] and r['sense']==source['sense']
        else:
            g=links.get(i,indicators.get(i));z=g['z'];sign=1 if source['sense']=='<' else -1
            assert base['variables'][z]['integer'] and (base['variables'][z]['lower'],base['variables'][z]['upper'])==(0.,1.)
            terms={j:sign*x for j,x in source['terms'].items()};M=-terms.pop(str(z))
            assert all(not base['variables'][int(j)]['integer'] for j in terms)
            assert M==F(float(g['M'])) and source['rhs']==0
            if i in links:
                y,w=g['y'],g['w'];h=F(g['h']);R=F(g['radius'])
                assert h*R==M and {j:F(float(x)) for j,x in r['terms'].items()}=={**terms,str(y):-h}
                assert r['sense']=='<' and r['rhs']==0
                assert model['variables'][y]['lower']==0 and F(float(model['variables'][y]['upper']))==R
                assert not model['variables'][y]['integer'] and model['variables'][y]['cost']==0
                assert model['variables'][w]['lower']==0 and model['variables'][w]['upper']==1
                assert not model['variables'][w]['integer'] and model['variables'][w]['cost']==0
                c=model['rows'][g['complement_row']]
                assert c['terms']=={str(w):1.,str(z):1.} and c['rhs']==1 and c['sense']=='=' and meta['factors'][g['complement_row']]==1
                bound=F(meta['epsilon'])/F(meta['factors'][i])+h*max(F(meta['gamma']),F(1e-6))
                assert bound==Fraction(g['bound'])
                if meta['policy'] in ('Shared-budget','Individual-budget','SOS-normalized'):assert bound<=source['budget']
            else:
                assert {j:F(float(x)) for j,x in r['terms'].items()}==terms and F(float(r['rhs']))==M and r['sense']=='<'
                assert {j:F(float(x)) for j,x in g['terms'].items()}==terms
        count+=1
    for r,alpha in zip(model['rows'],meta['factors']):
        q=F(float(alpha));assert q>0
        assert all(F(float(x))*q==F(float(float(x)*float(alpha))) for x in [*r['terms'].values(),r['rhs']])
        assert all(F(1e-9)<=abs(F(float(x))*q)<=F(1e9) for x in r['terms'].values() if x)
    if meta['policy']=='Shared-budget':
        for group in meta['groups']:
            own=[g for g in meta['links'] if g['z']==group['z']];bounds=[]
            for g in own:
                source=source_rows[g['row']];sign=1 if source['sense']=='<' else -1
                terms={j:float(sign*x) for j,x in source['terms'].items() if int(j)!=g['z']}
                bound=interval(terms,F(float(g['M'])),source['budget']);assert bound is not None;bounds.append(bound)
            lo=max(b[0] for b in bounds);hi=min(b[1] for b in bounds)
            assert lo<=hi and group['r']==lo and F(group['radius'])==Fraction(2)**lo
            assert group['lower_r']==lo and group['upper_r']==hi
    return count


def main(partial=False):
    design=json.loads((HERE/'pilot/design.json').read_text())
    for key,file in (('protocol_sha256','PROTOCOL.md'),('activity_sha256','activity.py'),('runner_sha256','study.py'),
                     ('evaluation_addendum_sha256','EVALUATION_ADDENDUM.md')):assert design[key]==sha(HERE/file)
    bank={};static_rows=0;exports=0;covariance=[]
    for item in design['models']:
        folder=HERE/'pilot/models'/item['name'];original=json.loads((folder/'original-model.json').read_text())
        base=json.loads((folder/'contracted-model.json').read_text());assert sha(folder/'original-model.json')==item['original_sha256']
        assert sha(folder/'contracted-model.json')==item['contracted_sha256'];bank[item['name']]=(original,base)
        if item['source']:
            assert sha(ROOT/item['source'])==item['source_sha256'] and original==json.loads((ROOT/item['source']).read_text())
        if item['name'] in ('beasleyC3','k16x240b'):mps_check.check(HERE/'sources'/(item['name']+'.mps.gz'),original)
        hashes=[]
        for assignment in (d for d in design['assignments'] if d['name']==item['name']):
            arm=folder/assignment['arm'];canonical=folder/assignment['canonical_arm']
            assert sha(arm/'model.lp')==assignment['export_sha256']==sha(canonical/'model.lp')
            meta=json.loads((arm/'selection.json').read_text());model=json.loads((arm/'model.json').read_text())
            rows=scaled_source(base,set(item['gate_rows']),assignment['unit_exponent'])
            static_rows+=check_static(base,model,meta,rows);exports+=1
            if assignment['policy']=='Shared-budget':hashes.append(assignment['export_sha256'])
        assert len(hashes)==5 and len(set(hashes))==1
        covariance.append({'name':item['name'],'unit_variants':len(hashes),'identical_shared_exports':True})
    records={};results=[];point_count=0;hypotheses=0;certified=0
    for call in design['calls']:
        out=HERE/'pilot/runs'/call['name']/call['arm']/str(call['seed'])
        if not (out/'run.json').exists():continue
        try:record=json.loads((out/'run.json').read_text())
        except json.JSONDecodeError:
            if partial:continue
            raise
        records[(call['name'],call['arm'],call['seed'])]=record
        assert all(record[k]==call[k] for k in ('name','arm','seed','export_sha256','parameters'))
        original,_=bank[call['name']];arm=HERE/'pilot/models'/call['name']/call['arm'];meta=json.loads((arm/'selection.json').read_text())
        model=json.loads((arm/'model.json').read_text());started=time.perf_counter();verification={'has_point':record['has_point'],'original_optimality_certified':False}
        if record['has_point']:
            with np.load(out/'point.npz',allow_pickle=False) as saved:point=[F(float(x)) for x in saved['x']]
            assert len(point)==len(model['variables']);point_count+=1
            metrics,rounded=point_metrics(original,point);verification['original']=metrics
            failures=[];protected=0
            for g in meta['links']:
                z,y,w=(point[g[k]] for k in ('z','y','w'));i=g['row']
                conditions=(round(z) in (0,1),abs(w+z-1)<=F(1e-6),min(abs(w),abs(y))<=F(meta['gamma']),
                            violation(model['rows'][i],point)*F(meta['factors'][i])<=F(meta['epsilon']),y<=F(g['radius'])+F(1e-6))
                hypotheses+=1
                if not all(conditions):failures.append({'row':i,'conditions':list(conditions)})
                else:
                    bound=Fraction(g['bound'])/(Fraction(2)**meta['unit_exponent'])
                    assert violation(original['rows'][i],rounded)<=bound
                    protected+=1;certified+=1
            verification.update({'activity_hypothesis_failures':failures,'checked_row_transfers':protected,
                                 'exported_row_hypothesis_failures':sum(violation(r,point)*F(float(alpha))>F(meta['epsilon']) for r,alpha in zip(model['rows'],meta['factors']))})
        verification['verification_seconds']=time.perf_counter()-started
        (out/'verification.json').write_text(json.dumps(verification,indent=2,allow_nan=False)+'\n')
        row={k:record[k] for k in ('name','policy','arm','unit_exponent','seed','status','has_point','work','runtime','objective','import_check_seconds','process_through_persistence_seconds')}
        if record['has_point']:
            m=verification['original'];reference=F(float(design['reference_objectives'][call['name']]))
            row.update({'primal_pass':m['rounded']['accepted'],'raw_primal_pass':m['raw']['accepted'],
                        'maximum_ratio':m['rounded']['maximum_row_budget_ratio'],'verified_objective':m['rounded']['objective'],
                        'objective_exact':m['rounded']['objective_exact'],'quality_target_met':m['rounded']['accepted'] and Fraction(m['rounded']['objective_exact'])<=reference+abs(reference)/100,
                        'activity_hypothesis_failures':len(failures),'exported_row_hypothesis_failures':verification['exported_row_hypothesis_failures'],
                        'verification_seconds':verification['verification_seconds']})
        results.append(row)
    if not partial:assert len(records)==len(design['calls'])
    summary={'planned_calls':len(design['calls']),'completed_calls':len(records),'saved_points_checked':point_count,
             'static_variants_checked':exports,'static_source_rows_checked':static_rows,'returned_activity_hypotheses_checked':hypotheses,
             'valid_conditional_row_transfers':certified,'unit_covariance':covariance,'new_optimizer_calls':0,
             'all_complete':len(records)==len(design['calls'])}
    (HERE/'VALIDATION.json').write_text(json.dumps(summary,indent=2)+'\n')
    (HERE/'pilot/RESULTS.json').write_text(json.dumps(results,indent=2,allow_nan=False)+'\n');print(json.dumps(summary,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--partial',action='store_true');args=parser.parse_args();main(args.partial)
