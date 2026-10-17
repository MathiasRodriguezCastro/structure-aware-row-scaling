"""Independent rational replay of exports, lattice conditions, original points."""
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
F=Fraction.from_float
EPS,GAMMA=F(1e-6),F(1e-9)
spec=importlib.util.spec_from_file_location('independent_original_point_checks',ROOT/'exploration/oms-activity-scaling-20261017/verify.py')
replay=importlib.util.module_from_spec(spec);spec.loader.exec_module(replay)


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def integer_power(x):
    assert x>0
    return x.numerator&(x.numerator-1)==0 and x.denominator&(x.denominator-1)==0


def feasible_group(rows,delta,t,k):
    lo=max(F(1e-9),Fraction(2)**(-t));hi=min(F(1e9),Fraction(2)**t);K=Fraction(2)**k
    # Enumerate the finite relevant exponents independently of the new selector.
    sigma=max((Fraction(2)**r for r in range(-60,61) if lo<=Fraction(2)**r and K*Fraction(2)**r<=hi),default=None)
    if sigma is None:return False
    if K*GAMMA+EPS/sigma+GAMMA>=Fraction(1,2):return False
    effective=(GAMMA+EPS/sigma)/K
    for terms,M in rows:
        magnitudes=[abs(F(float(a))) for a in terms.values() if a]
        feasible=False
        for u in range(-60,61):
            a=Fraction(2)**u
            if min(magnitudes)*a>=lo and max(magnitudes)*a<=hi and EPS/a+M*effective<=delta:
                feasible=True;break
        if not feasible:return False
    return True


def main():
    design=json.loads((HERE/'pilot/design.json').read_text())
    for key,file in (('protocol_sha256','PROTOCOL.md'),('method_sha256','method.py'),('runner_sha256','study.py')):
        assert design[key]==sha(HERE/file)
    bank={};static_rows=0;copies=0;selector_certificates=0
    for item in design['models']:
        op=ROOT/item['original'];cp=ROOT/item['contracted']
        assert sha(op)==item['original_sha256'] and sha(cp)==item['contracted_sha256']
        original=json.loads(op.read_text());contracted=json.loads(cp.read_text());bank[item['name']]=original
        groups={}
        for i in item['selected_rows']:
            r=contracted['rows'][i];z=next(int(j) for j in r['terms'] if original['variables'][int(j)]['integer'])
            groups.setdefault(z,[]).append((r['terms'],abs(F(float(r['terms'][str(z)])))))
        for budget,selection in item['selections'].items():
            delta=F(float(budget))
            if selection['compatible']:
                t=selection['t']
                for z,group in groups.items():
                    chosen=selection['groups'][str(z)]
                    assert feasible_group(group,delta,t,chosen['k'])
                    assert not any(feasible_group(group,delta,t,k) for k in range(chosen['k']))
                if t:
                    assert any(not any(feasible_group(group,delta,t-1,k) for k in range(29)) for group in groups.values())
            else:
                assert any(not any(feasible_group(group,delta,30,k) for k in range(29)) for group in groups.values())
            selector_certificates+=1
        for folder in sorted((HERE/'pilot/models'/item['name']).iterdir()):
            model=json.loads((folder/'model.json').read_text());meta=json.loads((folder/'selection.json').read_text())
            assert model['variables'][:len(original['variables'])]==original['variables']
            if meta['policy']!='SOS-unit':assert model['rows'][:len(original['rows'])]==contracted['rows']
            byz={c['z']:c for c in meta['copies']}
            for c in meta['copies']:
                z,q=c['z'],c['q'];K=Fraction(c['K']);sigma=F(c['sigma'])
                assert K.denominator==1 and integer_power(K) and integer_power(sigma)
                v=model['variables'][q];r=model['rows'][c['row']]
                assert v['integer']==(meta['policy']=='Integer-copy') and v['lower']==0 and v['upper']==float(K)
                assert r['terms']=={str(z):float(K),str(q):-1.} and r['sense']=='=' and r['rhs']==0
                assert meta['factors'][c['row']]==float(sigma)
                assert K*GAMMA+EPS/sigma+GAMMA<Fraction(1,2)
                assert (GAMMA+EPS/sigma)/K==Fraction(c['gamma_effective'])
                copies+=1
            for i,(r,a) in enumerate(zip(model['rows'],meta['factors'])):
                alpha=F(float(a))
                assert all(F(float(x))*alpha==F(float(float(x)*float(alpha))) for x in [*r['terms'].values(),r['rhs']])
                assert all(F(1e-9)<=abs(F(float(x))*alpha)<=F(1e9) for x in r['terms'].values() if x)
                if i in meta['selected_rows'] and byz:
                    z=next(int(j) for j in r['terms'] if original['variables'][int(j)]['integer'])
                    M=abs(F(float(r['terms'][str(z)])));c=byz[z]
                    assert EPS/alpha+M*Fraction(c['gamma_effective'])<=F(float(meta['activation_budget']))
                static_rows+=1
            if meta['policy']=='Integer-copy':
                other=HERE/'pilot/models'/item['name']/folder.name.replace('Integer-copy','Continuous-copy')/'model.json'
                continuous=json.loads(other.read_text())
                for c in meta['copies']:continuous['variables'][c['q']]['integer']=True
                assert continuous==model
    results=[];attempts=0;points=0;hypotheses=0;valid_transfers=0
    for call in design['calls']:
        folder=HERE/'pilot/models'/call['name']/call['arm']
        out=HERE/'pilot/runs'/call['name']/call['arm']/f'p{call["presolve"]}-s{call["seed"]}'
        if not (out/'run.json').exists():continue
        attempts+=1;record=json.loads((out/'run.json').read_text())
        assert sha(folder/'model.lp')==call['export_sha256']
        data=json.loads((folder/'model.json').read_text());meta=json.loads((folder/'selection.json').read_text())
        original=bank[call['name']];started=time.perf_counter();ver={'has_point':record['has_point'],'original_optimality_certified':False}
        if record['has_point']:
            points+=1
            with np.load(out/'point.npz',allow_pickle=False) as saved:point=[F(float(x)) for x in saved['x']]
            ver['budgets']={}
            for budget in (1e-4,1e-8):
                met,_=replay.original_check(original,point,set(meta['selected_rows']),budget)
                ver['budgets'][f'{budget:.0e}']=met
            failed=[];effects=[];equalities=0
            for c in meta['copies']:
                z,q=point[c['z']],point[c['q']];K=Fraction(c['K']);sigma=F(c['sigma'])
                zd=abs(z-round(z));qd=abs(q-round(q));rd=abs(sigma*(K*z-q))
                # Continuous controls are also measured, never assumed integral.
                cond=(zd<=GAMMA,qd<=GAMMA,rd<=EPS)
                hypotheses+=1
                if not all(cond):failed.append({'z':c['z'],'conditions':list(cond),'original_distance':float(zd),'copy_distance':float(qd),'link_residual':float(rd)})
                else:
                    assert round(q)==K*round(z)
                    assert zd<=Fraction(c['gamma_effective'])
                    effects.append(float(zd));valid_transfers+=1
                equalities+=rd<=EPS
            ver['amplification_hypothesis_failures']=failed
            ver['checked_amplifications']=len(meta['copies'])-len(failed)
            ver['copy_links_within_epsilon']=equalities
            ver['exported_row_hypothesis_failures']=sum(replay.residual(r,point)*F(float(a))>EPS for r,a in zip(data['rows'],meta['factors']))
        ver['verification_seconds']=time.perf_counter()-started
        (out/'verification.json').write_text(json.dumps(ver,indent=2,allow_nan=False)+'\n')
        for budget in ((record['budget'],) if record['budget'] is not None else (1e-4,1e-8)):
            row={k:record[k] for k in ('name','arm','seed','presolve','policy','status','has_point','work','runtime','prepare_seconds','objective')}
            row['budget']=budget
            if record['has_point']:
                met=ver['budgets'][f'{budget:.0e}']
                row.update({'primal_pass':met['rounded']['all_primal_budgets_met'],'raw_primal_pass':met['raw']['all_primal_budgets_met'],
                            'maximum_rounded_ratio':met['rounded']['maximum_row_budget_ratio'],
                            'maximum_raw_ratio':met['raw']['maximum_row_budget_ratio'],
                            'activation_ratio':met['rounded']['activation_budget_ratio'],
                            'failed_amplifications':len(failed),'copy_count':len(meta['copies']),
                            'exported_row_hypothesis_failures':ver['exported_row_hypothesis_failures']})
            results.append(row)
    result={'planned_calls':len(design['calls']),'completed_calls':attempts,'points_checked':points,
            'static_rows_checked':static_rows,'static_copies_checked':copies,'selector_certificates':selector_certificates,
            'returned_amplification_hypotheses_checked':hypotheses,'valid_amplifications':valid_transfers,
            'optimizer_calls':0,'all_complete':len(design['calls'])==attempts}
    (HERE/'VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n')
    (HERE/'pilot/RESULTS.json').write_text(json.dumps(results,indent=2,allow_nan=False)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
