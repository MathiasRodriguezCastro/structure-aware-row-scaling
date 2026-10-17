#!/usr/bin/env python3
"""Exact replay of original rows, references and fixed-pattern certificates."""
from fractions import Fraction as F
from pathlib import Path
from collections import Counter
import gzip
import hashlib
import json
import math
import numpy as np

HERE=Path(__file__).resolve().parent


def load(p):
    b=p.read_bytes();return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def feasible(d,x):
    assert len(x)==len(d['variables']);objective=F(d['constant'])
    for v,z in zip(d['variables'],x):
        assert v['type']=='C' or z.denominator==1
        assert v['lb'] is None or z>=F(v['lb'])
        assert v['ub'] is None or z<=F(v['ub'])
        objective+=F(v['obj'])*z
    for r in d['rows']:
        w=sum(F(a)*x[j] for j,a in r['terms'])-F(r['rhs'])
        assert w==0 if r['sense']=='=' else w<=0 if r['sense']=='<' else w>=0
    return objective


def certificate(d,folder):
    r=load(folder/'result.json');lp=load(folder/'lp.json.gz');ints={int(j):F(z) for j,z in r['pattern'].items()}
    js=[j for j,v in enumerate(d['variables']) if v['type']=='C'];index={j:k for k,j in enumerate(js)}
    assert lp['continuous_indices']==js and {int(j):F(z) for j,z in lp['integers'].items()}==ints
    assert set(ints)=={j for j,v in enumerate(d['variables']) if v['type']!='C'}
    expected=[]
    for row in d['rows']:
        rhs=F(row['rhs']);co={}
        for j,a in row['terms']:
            if j in ints:rhs-=F(a)*ints[j]
            else:co[index[j]]=F(a)
        signs=[1,-1] if row['sense']=='=' else [1] if row['sense']=='<' else [-1]
        for sign in signs:expected.append(({j:sign*a for j,a in co.items()},sign*rhs,row['name']))
    for j in js:
        for key,sign in [('lb',-1),('ub',1)]:
            if d['variables'][j][key] is not None:
                expected.append(({index[j]:F(sign)},sign*F(d['variables'][j][key]),d['variables'][j]['name']+':'+key))
    assert len(expected)==len(lp['rows'])
    for (a,b,n),row in zip(expected,lp['rows']):
        assert a=={int(j):F(c) for j,c in row['terms'].items()} and b==F(row['rhs']) and n==row['source']
    offset=F(d['constant'])+sum(F(d['variables'][j]['obj'])*z for j,z in ints.items())
    assert F(lp['offset'])==offset and list(map(F,lp['cost']))==[F(d['variables'][j]['obj']) for j in js]
    if r['outcome']=='infeasible_constant_row':
        assert any(not a and b<0 for a,b,n in expected);return 'infeasible_constant_row'
    if not r.get('exact_feasible'):return r['outcome']
    x=list(map(F,load(folder/'rational-point.json')));obj=feasible(d,x)
    assert obj==F(r['objective_exact']) and all(x[j]==z for j,z in ints.items())
    primal=list(map(F,load(folder/'primal.json')));assert primal==[x[j] for j in js]
    dual=load(folder/'dual.json')
    if r['outcome']=='optimum_certified':
        pi={int(i):F(z) for i,z in dual.items()};assert all(0<=i<len(expected) and z<=0 for i,z in pi.items())
        reduced=[F(d['variables'][j]['obj']) for j in js];lb=offset
        for i,(a,b,n) in enumerate(expected):
            v=pi.get(i,F(0));lb+=v*b
            for j,c in a.items():reduced[j]-=v*c
        assert not any(reduced) and lb==obj
    return r['outcome']


def main():
    d=load(HERE/'design.json');rd=load(HERE/'run-design.json');counts=Counter()
    for n,h in d['inputs'].items():assert sha(HERE/n)==h
    for n,h in rd['inputs'].items():assert sha(HERE/n)==h
    models={n:load(HERE/'inputs'/n/'canonical.json.gz') for n in d['instances']}
    for name in d['instances']:
        result=certificate(models[name],HERE/'references'/name);counts['reference_'+result]+=1
        start=load(HERE/'references'/name/'start.json')
        exact=load(HERE/'references'/name/'rational-point.json')
        assert start==list(map(lambda q:float(F(q)),exact))
    queue=load(HERE/'posthoc-design.json')
    for key,pattern in queue['queue'].items():
        folder=HERE/'certificates'/key
        assert load(folder/'result.json')['pattern']==pattern
        counts['final_pattern_'+certificate(models[key.split('/')[0]],folder)]+=1
    for job in rd['schedule']:
        name='{instance}-{policy}-{start}-s{seed}'.format(**job);folder=HERE/'runs'/name;r=load(folder/'run.json')
        assert r['job']==job and r['parameters']=={**d['parameters'],'Seed':job['seed']}
        model=models[job['instance']];prep=load(HERE/'inputs'/job['instance']/'preparation.json')
        ex=prep['policy_exponents']['Base' if job['policy']=='Base' else 'Algebraic']
        for row,k in zip(model['rows'],ex):
            for v in [row['rhs']]+[a for j,a in row['terms']]:
                assert F(float(v)*(2.**k))==F(v)*F(2)**k;counts['exact_product_checks']+=1
        points=np.load(folder/'candidates.npz')['x'];assert len(points)==len(r['events'])
        # Row-local denominator alignment is independent of the producer's global exponent.
        audits=load(HERE/'point-audits.json.gz')
        for position,(event,x) in enumerate(zip(r['events'],points)):
            raw=[F(float(v)) for v in x];rounded=[q if v['type']=='C' else F(round(float(q))) for q,v in zip(raw,model['variables'])]
            cost=F(model['constant'])+sum(F(v['obj'])*q for v,q in zip(model['variables'],raw))
            assert abs(float(cost)-event['reported_objective'])<=1e-5*max(1,abs(float(cost)))
            if position==len(points)-1:
                maxrow=F(0)
                for row in model['rows']:
                    qs=[F(a) for _,a in row['terms']]+[F(row['rhs'])]+[rounded[j] for j,_ in row['terms']]
                    e=max(q.denominator.bit_length()-1 for q in qs)
                    def integer(q):return q.numerator<<(e-(q.denominator.bit_length()-1))
                    lhs=sum(integer(F(a))*integer(rounded[j]) for j,a in row['terms'])
                    residual=lhs-(integer(F(row['rhs']))<<e)
                    violation=abs(residual) if row['sense']=='=' else max(0,residual if row['sense']=='<' else -residual)
                    maxrow=max(maxrow,F(violation,1<<(2*e)))
                assert float(maxrow)==audits[name]['max_original_row_residual']
                counts['final_original_row_replays']+=1
            counts['candidate_exact_objective_checks']+=1
        assert r['events'][-1]['kind']=='final' and r['objective'] is not None
        final=points[-1];pattern={str(j):str(round(float(final[j]))) for j,v in enumerate(model['variables']) if v['type']!='C'}
        assignment=queue['assignments'][name];assert pattern==queue['queue'][assignment]
        counts['final_pattern_assignments_checked']+=1
        if job['start']=='CommonStart':
            log=(folder/'solver.log').read_text();assert 'Loaded user MIP start with objective' in log
            ref=load(HERE/'references'/job['instance']/'result.json');u=F(ref['objective_exact'])
            rp=load(HERE/'references'/job['instance']/'rational-point.json')
            reference_pattern={j:F(rp[j]) for j,v in enumerate(model['variables']) if v['type']!='C'}
            tol=max(F(1e-6),F(8*math.ulp(float(u))))
            found=False
            for event,x in zip(r['events'],points):
                if all(F(round(float(x[j])))==z for j,z in reference_pattern.items()) and abs(F(event['reported_objective'])-u)<=tol and event['nodes']==0 and event['work']==0:found=True
            assert found;counts['loaded_common_start_pattern_cost_checks']+=1
    result=dict(counts,native_mip_calls=len(rd['schedule']),native_lp_reference_calls=len(rd['references']),
        native_lp_posthoc_calls=sum(load(HERE/'certificates'/k/'result.json')['native_lp_called'] for k in queue['queue']),
        no_optimizer_calls_during_replay=True)
    (HERE/'independent-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
