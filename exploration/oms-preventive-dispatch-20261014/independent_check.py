#!/usr/bin/env python3
"""Solver-free source, exact-cut, selection-history and outcome verification."""
from collections import Counter
import csv
from fractions import Fraction as Q
import hashlib
import json
import math
from pathlib import Path
import re
from statistics import median

import numpy as np

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]


def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def f(v):return Q(float(v))


def mps_check(path,model):
    section=None;rows={};columns={};rhs={};bounds={};objective=None
    for line in path.read_text().splitlines():
        if not line.strip() or line.startswith('*'):continue
        t=line.split()
        if not line[0].isspace():section=t[0];continue
        if section=='ROWS':
            if t[0]=='N':assert objective is None;objective=t[1]
            else:rows[t[1]]=t[0]
        elif section=='COLUMNS':
            assert len(t) in (3,5)
            c=columns.setdefault(t[0],{})
            for i in range(1,len(t),2):assert t[i] not in c;c[t[i]]=f(t[i+1])
        elif section=='RHS':
            for i in range(1,len(t),2):assert t[i] not in rhs;rhs[t[i]]=f(t[i+1])
        elif section=='BOUNDS':
            typ,_,name=t[:3];lo,up=bounds.get(name,(Q(0),None));value=f(t[3]) if len(t)==4 else None
            if typ=='LO':lo=value
            elif typ=='UP':up=value
            elif typ=='FX':lo=up=value
            elif typ=='FR':lo=up=None
            elif typ=='MI':lo=None
            elif typ=='PL':up=None
            else:raise AssertionError(typ)
            bounds[name]=(lo,up)
        else:raise AssertionError(section)
    assert set(columns)=={v['name'] for v in model['variables']}
    assert set(rows)=={r['name'] for r in model['rows']}
    assert f(model['objective_constant'])==-rhs.get(objective,Q(0))
    for v in model['variables']:
        assert not v['integer'] and columns[v['name']].get(objective,Q(0))==f(v['cost'])
        assert bounds.get(v['name'],(Q(0),None))==tuple(None if v[k] is None else f(v[k]) for k in ('lower','upper'))
    for r in model['rows']:
        assert rows[r['name']]=={'<':'L','>':'G','=':'E'}[r['sense']] and rhs.get(r['name'],Q(0))==f(r['rhs'])
        actual={i:columns[v['name']].get(r['name'],Q(0)) for i,v in enumerate(model['variables'])}
        assert {i:a for i,a in actual.items() if a}=={int(i):f(a) for i,a in r['terms'].items() if a}


def independent_partition(model):
    master=[];groups={}
    for i,v in enumerate(model['variables']):
        time=re.search(r'\((\d+)\)$',v['name'])
        if v['integer'] or time is None or re.search(r'_[vxy][1-4]h\(',v['name']):master.append(i)
        else:groups.setdefault(int(time[1]),[]).append(i)
    ui={i:j for j,i in enumerate(master)};stages={t:[] for t in groups};masterrows=[]
    for r in model['rows']:
        touched=[t for t,indices in groups.items() if any(str(i) in r['terms'] for i in indices)]
        assert len(touched)<=1
        for sign in ([1,-1] if r['sense']=='=' else [1] if r['sense']=='<' else [-1]):
            if not touched:
                masterrows.append(({ui[int(i)]:sign*f(a) for i,a in r['terms'].items()},sign*f(r['rhs'])))
                continue
            t=touched[0];yi={i:j for j,i in enumerate(groups[t])}
            stages[t].append({'name':r['name'],'a':{str(yi[int(i)]):sign*f(a) for i,a in r['terms'].items() if int(i) in yi},
                              'b':{str(ui[int(i)]):sign*f(a) for i,a in r['terms'].items() if int(i) in ui},'rhs':sign*f(r['rhs'])})
    for t,indices in groups.items():
        for j,i in enumerate(indices):
            v=model['variables'][i]
            for side,sign in (('lower',-1),('upper',1)):
                if v[side] is not None:stages[t].append({'name':'bound:'+v['name']+':'+side,'a':{str(j):Q(sign)},'b':{},'rhs':sign*f(v[side])})
    return master,groups,stages,masterrows


def dual(rows,cost,mu,ray=False):
    assert all(Q(v)<=0 for v in mu.values())
    for j,c in enumerate(cost):
        assert sum(Q(v)*Q(rows[int(i)]['a'].get(str(j),0)) for i,v in mu.items())==(0 if ray else f(c))


def cut_check(cut,rows,cost,variables,u):
    dual(rows,cost,cut['mu'],cut['kind']=='ray')
    g0=sum(Q(v)*Q(rows[int(i)]['rhs']) for i,v in cut['mu'].items());g={}
    for i,v in cut['mu'].items():
        for j,b in rows[int(i)]['b'].items():g[j]=g.get(j,Q(0))-Q(v)*Q(b)
    g={i:v for i,v in g.items() if v}
    assert g=={i:Q(a) for i,a in cut['g'].items()} and g0==Q(cut['g0'])
    value=g0+sum(a*f(u[int(i)]) for i,a in g.items());assert value==Q(cut['value_at_source'])
    if cut['kind']=='ray':assert value>0
    e=cut['export'];alpha=Q(e['alpha']);assert alpha>0 and alpha.numerator&(alpha.numerator-1)==0 and alpha.denominator&(alpha.denominator-1)==0
    assert set(e['terms'])==set(g)
    support=Q(0)
    for i,a in g.items():
        error=-alpha*a-f(e['terms'][i])
        if error:
            bound=variables[int(i)]['upper' if error>0 else 'lower'];assert bound is not None
            support+=error*f(bound)
    assert support==Q(e['support']) and f(e['rhs'])<=alpha*g0-support
    assert f(e['theta'])==(alpha if cut['kind']=='cost' else 0)


def point_check(model,x):
    worst=norm=bound=0.
    for r in model['rows']:
        d=sum(a*x[int(i)] for i,a in r['terms'].items())-r['rhs']
        violation=abs(d) if r['sense']=='=' else max(0.,d if r['sense']=='<' else -d)
        worst=max(worst,violation);norm=max(norm,violation/max(1.,abs(r['rhs'])))
    for v,value in zip(model['variables'],x):
        if v['lower'] is not None:bound=max(bound,v['lower']-value)
        if v['upper'] is not None:bound=max(bound,value-v['upper'])
    return {'max_row_residual':worst,'max_rhs_normalized_row_residual':norm,'max_bound_residual':max(0.,bound),
            'objective':sum(v['cost']*a for v,a in zip(model['variables'],x))+model['objective_constant']}


def fixed_lp(model,z):
    continuous=[i for i,v in enumerate(model['variables']) if not v['integer']];index={i:j for j,i in enumerate(continuous)}
    assert set(z)=={str(i) for i,v in enumerate(model['variables']) if v['integer']}
    for i,value in z.items():
        value=Q(value);v=model['variables'][int(i)];assert value.denominator==1
        assert v['lower'] is None or value>=f(v['lower'])
        assert v['upper'] is None or value<=f(v['upper'])
    rows=[]
    for r in model['rows']:
        base=f(r['rhs'])-sum(f(a)*Q(z[i]) for i,a in r['terms'].items() if i in z)
        for sign in ([1,-1] if r['sense']=='=' else [1] if r['sense']=='<' else [-1]):
            rows.append({'terms':{str(index[int(i)]):sign*f(a) for i,a in r['terms'].items() if int(i) in index},'rhs':sign*base})
    for i in continuous:
        for side,sign in (('lower',-1),('upper',1)):
            if model['variables'][i][side] is not None:
                rows.append({'terms':{str(index[i]):Q(sign)},'rhs':sign*f(model['variables'][i][side])})
    return {'cost':[f(model['variables'][i]['cost']) for i in continuous],
            'offset':sum(f(model['variables'][int(i)]['cost'])*Q(v) for i,v in z.items()),'rows':rows}


def key(row):return tuple(sorted((i,Q(a)) for i,a in row['terms'].items() if a)),Q(row['rhs'])


def source_lp_check(actual,expected):
    assert list(map(Q,actual['cost']))==expected['cost'] and Q(actual['offset'])==expected['offset']
    assert len(actual['rows'])==len(expected['rows'])
    assert all(key(a)==key(b) for a,b in zip(actual['rows'],expected['rows']))


def exact_lp_check(lp,primal,mu):
    cost=list(map(Q,lp['cost']));dual_rows=[{'a':row['terms']} for row in lp['rows']]
    assert all(Q(v)<=0 for v in mu.values())
    reduced=cost[:]
    for i,v in mu.items():
        for j,a in lp['rows'][int(i)]['terms'].items():reduced[int(j)]-=Q(v)*Q(a)
    assert not any(reduced)
    lower=Q(lp['offset'])+sum(Q(v)*Q(lp['rows'][int(i)]['rhs']) for i,v in mu.items())
    if primal is not None:
        q=list(map(Q,primal));assert len(q)==len(cost)
        for row in lp['rows']:assert sum(Q(a)*q[int(i)] for i,a in row['terms'].items())<=Q(row['rhs'])
        assert Q(lp['offset'])+sum(a*b for a,b in zip(cost,q))==lower
    return lower


def composed_dual(model,master,groups,floors):
    full=fixed_lp(model,{});lookup={key(row):i for i,row in enumerate(full['rows'])};mu={}
    for t,fl in floors.items():
        indices=groups[int(t)]+master
        for j,v in fl['mu'].items():
            r=fl['joint']['rows'][int(j)];terms={str(indices[int(i)]):f(a) for i,a in r['a'].items()}
            i=lookup[(tuple(sorted(terms.items())),f(r['rhs']))];mu[str(i)]=mu.get(str(i),Q(0))+Q(v)
    for i in master:
        v=model['variables'][i];c=f(v['cost'])
        if not c:continue
        sign=-1 if c>0 else 1;endpoint=v['lower' if c>0 else 'upper'];assert endpoint is not None
        j=lookup[(( (str(i),Q(sign)), ),sign*f(endpoint))];mu[str(j)]=mu.get(str(j),Q(0))-abs(c)
    mu={i:str(v) for i,v in mu.items() if v};lower=exact_lp_check(full,None,mu)
    return {'mu':mu,'lower_exact':str(lower),'common_dual_nonempty':True,
            'primal_feasibility_asserted':False,'proof':'sum exact stage-floor duals and finite master objective bounds'}


def geometry(model,master):
    ui={i:j for j,i in enumerate(master)};width=np.array([max(1.,model['variables'][i]['upper']-model['variables'][i]['lower'])
        if model['variables'][i]['lower'] is not None and model['variables'][i]['upper'] is not None else 1. for i in master])
    E=[]
    for r in model['rows']:
        if r['sense']=='=' and all(int(i) in ui for i in r['terms']):
            a=np.zeros(len(master))
            for i,c in r['terms'].items():a[ui[int(i)]]=c
            E.append(a*width)
    E=np.array(E)
    E/=np.maximum(1e-300,np.linalg.norm(E,axis=1))[:,None]
    _,s,vh=np.linalg.svd(E,full_matrices=False);rank=sum(s>1e-12);P=np.eye(len(master))-vh[:rank].T@vh[:rank]
    assert np.linalg.norm(E@P,ord=np.inf)<1e-8
    return width,P


def cos(a,b):
    length=np.linalg.norm(a)*np.linalg.norm(b)
    return min(1.,abs(float(a@b))/length) if length>1e-300 else 0.


def selection_check(candidates,policy,width,P,selected):
    data=[]
    for cut in candidates:
        v=np.zeros(len(width))
        for i,a in cut['g'].items():v[int(i)]=float(Q(a))
        eff=cut['violation']/max(1.,np.linalg.norm(v*width))
        assert math.isclose(eff,cut['efficacy'],rel_tol=1e-14,abs_tol=1e-20)
        data.append({'t':cut['t'],'raw':v,'projected':P@(v*width),'eff':eff,'role':cut['role']})
    data.sort(key=lambda c:(-c['eff'],c['t']))
    if policy in ('All','Top'):chosen=data if policy=='All' else data[:4]
    else:
        chosen=data[:1];rest=data[1:];metric='raw' if policy=='RawDiverse' else 'projected'
        while rest and len(chosen)<4:
            roles={d['role'] for d in chosen}
            def score(c):return c['eff']*(.25+.75*(1-max(cos(c[metric],d[metric]) for d in chosen))+(.2 if policy=='Physical' and c['role'] not in roles else 0.))
            c=max(rest,key=lambda c:(score(c),-c['t']));chosen.append(c);rest=[d for d in rest if d is not c]
    assert selected==[c['t'] for c in chosen]
    return {metric:float(np.mean([cos(a[metric],b[metric]) for i,a in enumerate(data) for b in data[i+1:]])) if len(data)>1 else None for metric in ('raw','projected')}


def preventive_bound_check(record):
    model=load(ROOT/record['input']);assert sha(ROOT/record['input'])==record['input_sha256']
    cont={i for i,v in enumerate(model['variables']) if not v['integer']};m=0;M=1;W=Q(0);largest_scale=1
    for r in model['rows']:
        values={int(i):f(a) for i,a in r['terms'].items()};rhs=f(r['rhs'])
        scale=math.lcm(rhs.denominator,*(a.denominator for a in values.values()));largest_scale=max(largest_scale,scale)
        M=max([M]+[abs(a.numerator*(scale//a.denominator)) for i,a in values.items() if i in cont])
        W=max(W,scale*f(r.get('budget',1e-4*max(1.,abs(r['rhs'])))));m+=1+(r['sense']=='=')
    for i in cont:
        v=model['variables'][i]
        for side in ('lower','upper'):
            if v[side] is None:continue
            scale=f(v[side]).denominator;largest_scale=max(largest_scale,scale);M=max(M,scale)
            W=max(W,scale*f(v.get('bound_budget',1e-4)));m+=1
    r=min(m,len(cont));G=(M-1).bit_length();L=(max(1,r)-1).bit_length()
    H=2**(r*(G+L));Hprevious=2**(max(0,r-1)*(G+L));C=max(abs(f(model['variables'][i]['cost'])) for i in cont)
    N=record['scale_exponent'];assert (r+1)*H*W<=Q(2**N,2) and r*r*C*Hprevious*W<=2**N
    if N:assert (r+1)*H*W>Q(2**(N-1),2) or r*r*C*Hprevious*W>2**(N-1)
    assert record['rank_upper']==r and record['rows']==m and record['integer_A_max_bits']==M.bit_length()


def main():
    design=load(HERE/'design.json')
    for name,h in design['hashes'].items():assert sha(HERE/name)==h,name
    models={};partitions={};preparation=0;composed={};reference_certificates={}
    for p in load(HERE/'inputs/provenance.json'):
        name=p['name'];path=HERE/'inputs'/name;model=load(path/'model.json');assert sha(path/'model.mps')==p['source_sha256']
        mps_check(path/'model.mps',model);models[name]=model;partitions[name]=independent_partition(model)
        master,groups,stages,masterrows=partitions[name];floors=load(HERE/'preparation'/name/'floors.json')
        for t,stage in stages.items():
            fl=floors[str(t)];joint=fl['joint'];n=len(groups[t]);expected=[]
            for r in stage:
                terms={i:float(a) for i,a in r['a'].items()};terms.update({str(n+int(i)):float(a) for i,a in r['b'].items()})
                expected.append({'name':r['name'],'a':terms,'rhs':float(r['rhs'])})
            for i,j in enumerate(master):
                v=model['variables'][j]
                for side,sign in (('lower',-1),('upper',1)):
                    if v[side] is not None:expected.append({'name':'master-bound','a':{str(n+i):float(sign)},'rhs':sign*v[side]})
            assert joint['rows']==expected
            cost=[model['variables'][i]['cost'] for i in groups[t]]+[0.]*len(master);assert joint['cost']==cost
            dual(expected,cost,fl['mu']);floor=sum(Q(v)*f(expected[int(i)]['rhs']) for i,v in fl['mu'].items())
            assert floor==Q(fl['exact_floor']) and f(fl['exported_floor'])<=floor;preparation+=1
        composed[name]=composed_dual(model,master,groups,floors)
        ef=HERE/'exact-references'/name;er=load(ef/'result.json')
        source_lp_check(load(ef/'model.json'),fixed_lp(model,{}))
        if er.get('optimum_certified'):
            value=exact_lp_check(load(ef/'model.json'),load(ef/'primal.json'),load(ef/'dual.json'))
            assert str(value)==er['primal_value_exact'];reference_certificates[name]={'optimum_certified':True,'value_exact':str(value),'value_float':float(value)}
        else:
            assert 'unknown' in (ef/'solver.log').read_text().lower()
            reference_certificates[name]={'optimum_certified':False,'status':'unknown; no primal/dual certificate; not an infeasibility claim'}
    old_certificates=[]
    for record in load(HERE/'assumptions-provenance.json'):
        name=record['model'];folder=HERE/'inputs/preventive-assumptions'/name
        for filename,h in record['files'].items():assert sha(folder/filename)==h
        model=load(ROOT/'exploration/oms-objective-budget-20261014/inputs/models'/name/'original-model.json')
        expected=fixed_lp(model,load(folder/'pattern.json'));actual=load(folder/'model.json');source_lp_check(actual,expected)
        exact_lp_check(actual,load(folder/'primal.json'),load(folder/'dual.json'));old_certificates.append(name)
    dump(HERE/'composed-duals.json',composed);dump(HERE/'exact-reference-verification.json',reference_certificates)
    preventive_records=load(HERE/'preventive-results.json')
    for record in preventive_records:preventive_bound_check(record)
    summaries=[];results=[];cut_checks=0;roles=Counter();raw_angles=[];projected_angles=[];applied=0;rays=0;max_residual=0.;max_ref_difference=0.;selected_same_top=0;compared_batches=0
    for job in design['jobs']:
        name,policy,seed=job['model'],job['policy'],job['seed'];folder=HERE/'runs'/f'{name}-{policy}-{seed}'
        r=load(folder/'result.json');history=load(folder/'history.json');assert not r.get('error') and r['converged_numeric']
        assert len(history)==r['iterations'] and r['iterations']<=80 and r['total_seconds']<60
        model=models[name];master,groups,stages,masterrows=partitions[name];variables=[model['variables'][i] for i in master]
        active=[];best=None;width,P=geometry(model,master)
        for iteration,it in enumerate(history):
            assert it['iteration']==iteration and set(it['theta'])=={str(t) for t in groups}
            u=it['master'];assert len(u)==len(master)
            for a,b in masterrows:
                violation=float(sum(c*f(u[i]) for i,c in a.items())-b)
                assert violation<=1e-6*max(1.,abs(float(b)))
            for c in active:
                e=c['export'];activity=sum(a*u[int(i)] for i,a in e['terms'].items())
                if c['kind']=='cost':activity+=e['theta']*it['theta'][str(c['t'])]
                assert e['rhs']-activity<=1e-6*max(1.,abs(e['rhs']))
            x=[0.]*len(model['variables'])
            for i,v in zip(master,u):x[i]=v
            costs=[];feas=[]
            for source in it['recourse_sources']:
                t=source['t'];stage=stages[t];cost=[model['variables'][i]['cost'] for i in groups[t]];c=source['cut']
                assert c['t']==t and c['kind']==source['kind'];cut_check(c,stage,cost,variables,u);cut_checks+=1;roles[c['role']]+=1
                if source['kind']=='cost':
                    y=source['x'];assert len(y)==len(groups[t])
                    for i,v in zip(groups[t],y):x[i]=v
                    expected=sum(a*v for a,v in zip(cost,y));assert math.isclose(expected,source['native_value'],rel_tol=1e-10,abs_tol=1e-7)
                    violation=float(Q(c['value_at_source']))-it['theta'][str(t)];assert violation==c['violation']
                    if violation>1e-7:costs.append(c)
                else:feas.append(c);rays+=1
            assert len(it['recourse_sources'])==len(groups) and {s['t'] for s in it['recourse_sources']}==set(groups)
            if not feas:
                check=point_check(model,x);best=check['objective'] if best is None else min(best,check['objective'])
                assert math.isclose(best,it['best_upper_numeric'],rel_tol=1e-13,abs_tol=1e-7)
            selected=it['selected_cost_periods'];assert len(selected)==len(set(selected)) and all(t in {c['t'] for c in costs} for t in selected)
            checked_angles=selection_check(costs,policy,width,P,selected)
            for field,keyname in (('raw','mean_abs_cosine_raw'),('projected','mean_abs_cosine_projected')):
                if checked_angles[field] is None:assert it[keyname] is None
                else:assert math.isclose(checked_angles[field],it[keyname],rel_tol=1e-10,abs_tol=1e-14)
            top=sorted(costs,key=lambda c:(-c['efficacy'],c['t']))
            expected=[c['t'] for c in top] if policy=='All' else [c['t'] for c in top[:4]]
            if policy in ('All','Top'):assert selected==expected
            elif costs:
                assert selected[0]==top[0]['t'] and len(selected)==min(4,len(costs));selected_same_top+=selected==expected;compared_batches+=1
            assert it['feasibility_periods']==[c['t'] for c in feas]
            if it['mean_abs_cosine_raw'] is not None:raw_angles.append(it['mean_abs_cosine_raw']);projected_angles.append(it['mean_abs_cosine_projected'])
            if iteration<len(history)-1:
                active+=feas+[c for c in costs if c['t'] in selected];applied+=len(feas)+len(selected)
        assert len(active)==r['cuts'] and r['subproblem_calls']==len(history)*len(groups)
        assert point_check(model,r['best']['x'])==r['best']['check'] and best==r['objective']
        max_residual=max(max_residual,r['best']['check']['max_row_residual'])
        assert r['best']['check']['max_rhs_normalized_row_residual']<1e-6 and r['best']['check']['max_bound_residual']<1e-6
        reference=load(HERE/'references'/f'{name}-{seed}.json');assert point_check(model,reference['x'])==reference['check']
        diff=abs(r['objective']-reference['objective']);max_ref_difference=max(max_ref_difference,diff)
        assert diff<=1e-7*max(1.,abs(reference['objective']))
        results.append(r)
    for name in models:
        for policy in design['policies']:
            group=[r for r in results if r['model']==name and r['policy']==policy];assert len(group)==3
            summaries.append({'model':name,'policy':policy,'iterations':group[0]['iterations'],
                              'cuts':group[0]['cuts'],'median_total_seconds':median(r['total_seconds'] for r in group),
                              'objective':group[0]['objective'],'all_converged':all(r['converged_numeric'] for r in group),
                              'median_compact_seconds':median(load(HERE/'references'/f"{name}-{r['seed']}.json")['seconds'] for r in group)})
    with (HERE/'dispatch-summary.csv').open('w',newline='') as stream:
        w=csv.DictWriter(stream,fieldnames=list(summaries[0]));w.writeheader();w.writerows(summaries)
    summary={'benders_arms':len(results),'compact_lp_references':9,'shared_floor_lp_calls':preparation,
             'native_subproblem_lp_calls':sum(r['subproblem_calls'] for r in results),
             'native_master_lp_calls':sum(r['iterations'] for r in results),
             'exact_online_dual_or_ray_checks':cut_checks,'applied_cuts':applied,'observed_feasibility_rays':rays,
             'source_mps_models_independently_parsed':len(models),'all_numeric_convergence_checks_passed':True,
             'maximum_original_row_residual':max_residual,'maximum_objective_difference_from_compact':max_ref_difference,
             'raw_mean_abs_cosine_max':max(raw_angles),'projected_mean_abs_cosine_max':max(projected_angles),
             'dominant_role_counts':dict(roles),'diverse_batches_same_order_as_top':selected_same_top,'compared_diverse_batches':compared_batches,
             'all_cut_floors_duals_and_outward_exports_rationally_checked':True,'solver_calls_during_replay':0,
             'post_experiment_exact_lp_attempts':3,'post_experiment_exact_lp_optima_certified':sum(c['optimum_certified'] for c in reference_certificates.values()),
             'post_experiment_exact_lp_unknown':[name for name,c in reference_certificates.items() if not c['optimum_certified']],
             'common_dual_nonemptiness_proofs':len(composed)+len(old_certificates),
             'independent_preventive_exponent_checks':len(preventive_records),'all_cut_filter_decisions_independently_replayed':True,
             'full_integer_dispatch_experiment':False,'full_integer_dispatch_rational_optimality_certified':False,
             'all_three_reference_lp_optima_certified':all(c['optimum_certified'] for c in reference_certificates.values()),
             'scope':'45 arms on three archived eight-period LPs; two related RN models; no population inference'}
    dump(HERE/'independent-verification.json',summary)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
