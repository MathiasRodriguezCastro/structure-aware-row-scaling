#!/usr/bin/env python3
"""Isolated temporal multicut Benders screen on archived dispatch LPs."""
import argparse
import csv
from fractions import Fraction as Q
import hashlib
import json
import math
from pathlib import Path
import re
import time
import traceback

import gurobipy as gp
import numpy as np
import sympy as sy

HERE=Path(__file__).resolve().parent
POLICIES=('All','Top','RawDiverse','ProjectedDiverse','Physical')
SEEDS=(211,223,227)


def load(p):return json.loads(Path(p).read_text())
def dump(p,v):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rational(v):return Q(float(v))


def split(model):
    vs=model['variables'];master=[];groups={}
    for i,v in enumerate(vs):
        t=re.search(r'\((\d+)\)$',v['name'])
        if v['integer'] or t is None or re.search(r'_[vxy][1-4]h\(',v['name']):master.append(i)
        else:groups.setdefault(int(t[1]),[]).append(i)
    assert all(not v['integer'] for v in vs),'This screen is limited to stored continuous dispatch models'
    ui={i:j for j,i in enumerate(master)};local={i:t for t,indices in groups.items() for i in indices};masterrows=[]
    stages={t:{'indices':indices,'rows':[],'cost':[vs[i]['cost'] for i in indices]} for t,indices in groups.items()}
    def add(row,sign,t=None):
        terms={int(i):sign*float(a) for i,a in row['terms'].items()};rhs=sign*float(row['rhs'])
        if t is None:
            masterrows.append({'name':row['name'],'terms':{str(ui[i]):v for i,v in terms.items()},'rhs':rhs,'sense':'<'})
        else:
            yi={i:j for j,i in enumerate(groups[t])}
            stages[t]['rows'].append({'name':row['name'],'a':{str(yi[i]):v for i,v in terms.items() if i in yi},
                                     'b':{str(ui[i]):v for i,v in terms.items() if i in ui},'rhs':rhs})
    for row in model['rows']:
        ts={local[int(i)] for i in row['terms'] if int(i) in local};assert len(ts)<=1,(row['name'],ts)
        t=next(iter(ts)) if ts else None
        for sign in ([1,-1] if row['sense']=='=' else [1] if row['sense']=='<' else [-1]):add(row,sign,t)
    for t,stage in stages.items():
        for j,i in enumerate(stage['indices']):
            v=vs[i]
            for side,sign in (('lower',-1),('upper',1)):
                if v[side] is not None:stage['rows'].append({'name':'bound:'+v['name']+':'+side,'a':{str(j):float(sign)},'b':{},'rhs':sign*v[side]})
    equalities=[]
    for row in model['rows']:
        if row['sense']=='=' and all(int(i) in ui for i in row['terms']):
            a=np.zeros(len(master))
            for i,v in row['terms'].items():a[ui[int(i)]]=v
            equalities.append(a)
    widths=np.array([max(1.,vs[i]['upper']-vs[i]['lower']) if vs[i]['lower'] is not None and vs[i]['upper'] is not None else 1. for i in master])
    E=np.asarray(equalities)*widths if equalities else np.zeros((0,len(master)))
    if len(E):
        E=E/np.maximum(1e-300,np.linalg.norm(E,axis=1))[:,None]
        _,singular,vh=np.linalg.svd(E,full_matrices=False);rank=int(np.sum(singular>1e-12))
        projector=np.eye(len(master))-vh[:rank].T@vh[:rank]
    else:singular=np.array([]);rank=0;projector=np.eye(len(master))
    assert np.linalg.norm(E@projector,ord=np.inf)<1e-8 if len(E) else True
    return {'master':master,'masterrows':masterrows,'stages':stages,'widths':widths,
            'projector':projector,'equality_rank_numeric':rank,'equality_singular_values':singular.tolist()}


def new_model(env,seed,name):
    m=gp.Model(name,env=env)
    for k,v in {'Threads':1,'Method':1,'Presolve':-1,'ScaleFlag':-1,'Seed':seed,
                'FeasibilityTol':1e-9,'OptimalityTol':1e-9,'InfUnbdInfo':1,'DualReductions':0,'TimeLimit':10.}.items():m.setParam(k,v)
    return m


def lp(env,seed,c,rows):
    m=new_model(env,seed,'recourse');y=[m.addVar(lb=-gp.GRB.INFINITY,name=f'y{j}',obj=float(v)) for j,v in enumerate(c)]
    cs=[m.addConstr(gp.LinExpr([float(a) for a in r['a'].values()],[y[int(i)] for i in r['a']])<=r['rhs']) for r in rows]
    m.update();return m,y,cs


def exact_multipliers(stage,values,kind):
    S=[i for i,v in enumerate(values) if v!=0.];n=len(stage['cost'])
    assert S,'empty multiplier support'
    T=sy.Matrix([[Q(stage['rows'][i]['a'].get(str(j),0.)) for i in S] for j in range(n)])
    if kind=='cost':
        answer,params=T.gauss_jordan_solve(sy.Matrix([Q(float(v)) for v in stage['cost']]))
        if params:answer=answer.subs({p:0 for p in params})
        mu=[Q(v) for v in answer]
    else:
        null=T.nullspace();assert len(null)==1,'nonextreme Farkas support'
        mu=[Q(v) for v in null[0]]
        if all(v>=0 for v in mu):mu=[-v for v in mu]
    assert all(v<=0 for v in mu)
    result={str(i):str(v) for i,v in zip(S,mu) if v}
    for j in range(n):
        actual=sum(Q(stage['rows'][int(i)]['a'].get(str(j),0.))*Q(v) for i,v in result.items())
        assert actual==(Q(float(stage['cost'][j])) if kind=='cost' else 0)
    return result


def cut_from(stage,mu,kind,t,u,y):
    g0=sum(Q(v)*rational(stage['rows'][int(i)]['rhs']) for i,v in mu.items());g={};weights={}
    for i,v in mu.items():
        row=stage['rows'][int(i)];v=Q(v)
        for j,a in row['b'].items():g[j]=g.get(j,Q(0))-v*rational(a)
        name=row['name']
        role='production' if any(s in name for s in ('tangente','discretizacion','cota_altura')) else 'capacity' if name.startswith('bound:') else 'demand'
        activity=abs(rational(row['rhs'])-sum(rational(a)*rational(u[int(j)]) for j,a in row['b'].items()))
        activity+=sum(abs(rational(a)*rational(y[int(j)])) for j,a in row['a'].items()) if y is not None else 0
        weights[role]=weights.get(role,0.)+float(abs(v)*activity)
    g={i:v for i,v in g.items() if v}
    value=g0+sum(v*rational(u[int(i)]) for i,v in g.items())
    if kind=='ray':assert value>0
    return {'kind':kind,'t':t,'g0':str(g0),'g':{i:str(v) for i,v in g.items()},'mu':mu,
            'role':max(weights,key=weights.get),'role_weights':weights,'value_at_source':str(value)}


def export_cut(cut,variables):
    # theta - g.u >= g0, or -g.u >= g0. Dyadic scaling, exact support
    # error over finite original master bounds; theta's exact coefficient
    # is a power of two and needs no bound in the outward-rounding check.
    terms={i:-Q(v) for i,v in cut['g'].items()};rhs=Q(cut['g0'])
    maximum=max([Q(1)]+[abs(v) for v in terms.values()]);exponent=-max(0,maximum.numerator.bit_length()-maximum.denominator.bit_length())
    alpha=Q(2**exponent) if exponent>=0 else Q(1,2**(-exponent));support=Q(0);exported={}
    for i,a in terms.items():
        value=float(alpha*a);exported[i]=value;error=alpha*a-Q(value)
        if not error:continue
        bound=variables[int(i)]['upper' if error>0 else 'lower'];assert bound is not None
        support+=error*rational(bound)
    limit=alpha*rhs-support;b=float(limit)
    if Q(b)>limit:b=math.nextafter(b,-math.inf)
    assert Q(b)<=limit
    return {'terms':exported,'rhs':b,'alpha':str(alpha),'support':str(support),'theta':float(alpha) if cut['kind']=='cost' else 0.}


def vectors(candidates,decomp):
    n=len(decomp['master']);widths=decomp['widths'];P=decomp['projector']
    for c in candidates:
        v=np.zeros(n)
        for i,a in c['g'].items():v[int(i)]=float(Q(a))
        c['_raw']=v;c['_projected']=P@(v*widths)
        c['efficacy']=c['violation']/max(1.,np.linalg.norm(v*widths))


def cosine(a,b):
    d=np.linalg.norm(a)*np.linalg.norm(b)
    return min(1.,abs(float(a@b))/d) if d>1e-300 else 0.


def select(candidates,policy,k=4):
    ranked=sorted(candidates,key=lambda c:(-c['efficacy'],c['t']))
    if policy=='All':return ranked
    if policy=='Top':return ranked[:k]
    chosen=ranked[:1];remaining=ranked[1:];key='_raw' if policy=='RawDiverse' else '_projected'
    while remaining and len(chosen)<k:
        roles={c['role'] for c in chosen}
        def score(c):
            diversity=1-max(cosine(c[key],d[key]) for d in chosen)
            bonus=.2 if policy=='Physical' and c['role'] not in roles else 0.
            return c['efficacy']*(.25+.75*diversity+bonus)
        best=max(remaining,key=lambda c:(score(c),-c['t']));chosen.append(best);remaining=[c for c in remaining if c is not best]
    return chosen


def point_check(model,x):
    rows=[];worst=0.;normalized=0.;bound=0.
    for r in model['rows']:
        activity=sum(float(a)*x[int(i)] for i,a in r['terms'].items());d=activity-r['rhs']
        violation=abs(d) if r['sense']=='=' else max(0.,d if r['sense']=='<' else -d)
        worst=max(worst,violation);normalized=max(normalized,violation/max(1.,abs(r['rhs'])))
    for v,value in zip(model['variables'],x):
        if v['lower'] is not None:bound=max(bound,v['lower']-value)
        if v['upper'] is not None:bound=max(bound,value-v['upper'])
    return {'max_row_residual':worst,'max_rhs_normalized_row_residual':normalized,'max_bound_residual':max(0.,bound),
            'objective':sum(v['cost']*a for v,a in zip(model['variables'],x))+model['objective_constant']}


def reference(env,seed,model):
    m=new_model(env,seed,'compact');vs=[]
    for i,v in enumerate(model['variables']):vs.append(m.addVar(lb=-gp.GRB.INFINITY if v['lower'] is None else v['lower'],ub=gp.GRB.INFINITY if v['upper'] is None else v['upper'],obj=v['cost'],name=f'x{i}'))
    m.ObjCon=model['objective_constant']
    for r in model['rows']:
        a=gp.LinExpr([v for v in r['terms'].values()],[vs[int(i)] for i in r['terms']]);m.addLConstr(a,r['sense'],r['rhs'])
    m.optimize();assert m.Status==gp.GRB.OPTIMAL
    x=[v.X for v in vs];result={'objective':m.ObjVal,'x':x,'check':point_check(model,x),'status':m.Status};m.dispose();return result


def lower_floors(env,model,decomp):
    result={};uvars=[model['variables'][i] for i in decomp['master']]
    for t,stage in decomp['stages'].items():
        n=len(stage['cost']);rows=[]
        for row in stage['rows']:
            terms=dict(row['a']);terms.update({str(n+int(i)):v for i,v in row['b'].items()});rows.append({'name':row['name'],'a':terms,'rhs':row['rhs']})
        for i,v in enumerate(uvars):
            for side,sign in (('lower',-1),('upper',1)):
                if v[side] is not None:rows.append({'name':'master-bound','a':{str(n+i):float(sign)},'rhs':sign*v[side]})
        joint={'cost':stage['cost']+[0.]*len(uvars),'rows':rows};m,y,cs=lp(env,211,joint['cost'],rows);m.optimize();assert m.Status==gp.GRB.OPTIMAL
        mu=exact_multipliers(joint,[c.Pi for c in cs],'cost');floor=sum(Q(v)*rational(rows[int(i)]['rhs']) for i,v in mu.items())
        exported=float(floor)
        if Q(exported)>floor:exported=math.nextafter(exported,-math.inf)
        result[t]={'exact_floor':str(floor),'exported_floor':exported,'mu':mu,'joint':joint};m.dispose()
    return result


def run_arm(env,model,decomp,floors,prep_seconds,policy,seed,folder):
    began=time.perf_counter();vs=model['variables'];uvars=[vs[i] for i in decomp['master']]
    master=new_model(env,seed,'master');u=[master.addVar(lb=-gp.GRB.INFINITY if v['lower'] is None else v['lower'],ub=gp.GRB.INFINITY if v['upper'] is None else v['upper'],obj=v['cost']) for v in uvars]
    theta={t:master.addVar(lb=floors[t]['exported_floor'],obj=1.,name=f'theta{t}') for t in decomp['stages']};master.ObjCon=model['objective_constant']
    for r in decomp['masterrows']:master.addConstr(gp.LinExpr(list(r['terms'].values()),[u[int(i)] for i in r['terms']])<=r['rhs'])
    subs={t:lp(env,seed,s['cost'],s['rows']) for t,s in decomp['stages'].items()};cache={};history=[];best=None;cuts_count=0;master_s=sub_s=exact_s=selection_s=0.;calls=0;error=None
    try:
        for iteration in range(80):
            if prep_seconds+time.perf_counter()-began>60:break
            tick=time.perf_counter();master.optimize();master_s+=time.perf_counter()-tick;assert master.Status==gp.GRB.OPTIMAL
            uv=[v.X for v in u];etas={t:v.X for t,v in theta.items()};lower=master.ObjVal
            candidates=[];feasibility=[];sources=[];x=[0.]*len(vs)
            for i,v in zip(decomp['master'],uv):x[i]=v
            all_feasible=True
            for t,stage in decomp['stages'].items():
                sm,y,cs=subs[t]
                for row,c in zip(stage['rows'],cs):c.RHS=row['rhs']-sum(a*uv[int(j)] for j,a in row['b'].items())
                tick=time.perf_counter();sm.optimize();sub_s+=time.perf_counter()-tick;calls+=1
                kind='cost' if sm.Status==gp.GRB.OPTIMAL else 'ray' if sm.Status==gp.GRB.INFEASIBLE else None
                assert kind is not None,sm.Status
                yy=[v.X for v in y] if kind=='cost' else None;values=[c.Pi if kind=='cost' else c.FarkasDual for c in cs]
                support=tuple(i for i,v in enumerate(values) if v!=0.);key=(t,kind,support)
                tick=time.perf_counter()
                if key not in cache:cache[key]=exact_multipliers(stage,values,kind)
                cut=cut_from(stage,cache[key],kind,t,uv,yy);cut['export']=export_cut(cut,uvars);exact_s+=time.perf_counter()-tick
                if kind=='cost':
                    for i,v in zip(stage['indices'],yy):x[i]=v
                    cut['violation']=float(Q(cut['value_at_source']))-etas[t]
                    if cut['violation']>1e-7:candidates.append(cut)
                    sources.append({'t':t,'kind':kind,'x':yy,'native_value':sm.ObjVal,'cut':cut})
                else:
                    all_feasible=False;cut['violation']=float(Q(cut['value_at_source']));feasibility.append(cut)
                    sources.append({'t':t,'kind':kind,'cut':cut})
            if all_feasible:
                check=point_check(model,x);upper=check['objective']
                if best is None or upper<best['objective']:best={'objective':upper,'x':x,'check':check}
            gap=(best['objective']-lower) if best else None
            tick=time.perf_counter();vectors(candidates,decomp);selected=select(candidates,policy);selection_s+=time.perf_counter()-tick
            angles={key:[cosine(a[key],b[key]) for i,a in enumerate(candidates) for b in candidates[i+1:]] for key in ('_raw','_projected')}
            record={'iteration':iteration,'master':uv,'theta':{str(t):v for t,v in etas.items()},'lower_numeric':lower,'best_upper_numeric':best['objective'] if best else None,
                    'gap_numeric':gap,'recourse_sources':sources,'selected_cost_periods':[c['t'] for c in selected],
                    'feasibility_periods':[c['t'] for c in feasibility],
                    'mean_abs_cosine_raw':float(np.mean(angles['_raw'])) if angles['_raw'] else None,
                    'mean_abs_cosine_projected':float(np.mean(angles['_projected'])) if angles['_projected'] else None}
            # Only JSON scalars persist; arrays are transient selector data.
            for source in sources:
                for key in ('_raw','_projected'):source['cut'].pop(key,None)
            history.append(record)
            if best and gap>=-1e-7*max(1.,abs(best['objective'])) and gap<=1e-7*max(1.,abs(best['objective'])) and all_feasible:break
            assert selected or feasibility,'no separating cut and no convergence'
            for cut in feasibility+selected:
                e=cut['export'];expr=gp.LinExpr(list(e['terms'].values()),[u[int(i)] for i in e['terms']])
                if cut['kind']=='cost':expr+=e['theta']*theta[cut['t']]
                master.addConstr(expr>=e['rhs']);cuts_count+=1
        result={'model':model['name'],'policy':policy,'seed':seed,'iterations':len(history),'cuts':cuts_count,'subproblem_calls':calls,
                'objective':best['objective'] if best else None,'lower_numeric':history[-1]['lower_numeric'] if history else None,
                'converged_numeric':bool(best and history[-1]['gap_numeric']<=1e-7*max(1.,abs(best['objective'])) and history[-1]['gap_numeric']>=-1e-7*max(1.,abs(best['objective']))),
                'best':best}
    except Exception as exc:
        error={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
        result={'model':model['name'],'policy':policy,'seed':seed,'error':error,'iterations':len(history),'cuts':cuts_count,'subproblem_calls':calls,'best':best,'converged_numeric':False}
    result.update(preparation_seconds_charged=prep_seconds,total_seconds=prep_seconds+time.perf_counter()-began,master_seconds=master_s,
                  subproblem_seconds=sub_s,exact_reconstruction_seconds=exact_s,selection_seconds=selection_s)
    dump(folder/'history.json',history);dump(folder/'result.json',result)
    for sm,_,_ in subs.values():sm.dispose()
    master.dispose();return result


def prepare():
    assert not (HERE/'design.json').exists()
    structural=[]
    for path in sorted((HERE/'inputs').glob('*/model.json')):
        model=load(path);d=split(model)
        structural.append({'name':model['name'],'master_variables':len(d['master']),'master_rows_expanded':len(d['masterrows']),
                           'periods':list(d['stages']),'recourse_variables':{str(t):len(s['indices']) for t,s in d['stages'].items()},
                           'equality_rank_numeric':d['equality_rank_numeric'],'equality_singular_values':d['equality_singular_values'],
                           'partition':'all original rows/bounds/objective assigned once; no row joins recourse periods'})
    jobs=[{'model':r['name'],'policy':policy,'seed':seed} for r in structural for policy in POLICIES for seed in SEEDS]
    rng=np.random.default_rng(20261014);jobs=[jobs[i] for i in rng.permutation(len(jobs))]
    files=[HERE/n for n in ('dispatch.py','preventive.py','PROTOCOL.md')]+sorted((HERE/'inputs').rglob('*'))
    dump(HERE/'design.json',{'status':'fixed before any new LP optimization','jobs':jobs,'structural':structural,
                           'hashes':{str(p.relative_to(HERE)):sha(p) for p in files if p.is_file()},
                           'policies':POLICIES,'seeds':SEEDS,'solver':'Gurobi 13.0.2','max_iterations':80,'total_reference_seconds':60,
                           'scope':'three archived conditional LPs, two related RN variants; no full dispatch MILP optimality claim'})
    print('Frozen 45 Benders arms, nine compact references, three conditional dispatch LPs',flush=True)


def run():
    d=load(HERE/'design.json')
    for name,h in d['hashes'].items():assert sha(HERE/name)==h,name
    env=gp.Env(params={'OutputFlag':0});models={};decomps={};floors={};preptimes={}
    for record in d['structural']:
        name=record['name'];began=time.perf_counter();model=load(HERE/'inputs'/name/'model.json');decomp=split(model)
        floor=lower_floors(env,model,decomp);duration=time.perf_counter()-began
        models[name]=model;decomps[name]=decomp;floors[name]=floor;preptimes[name]=duration
        dump(HERE/'preparation'/name/'floors.json',{str(t):f for t,f in floor.items()});dump(HERE/'preparation'/name/'timing.json',{'seconds':duration,'native_lp_calls':len(floor)})
        for seed in SEEDS:
            t=time.perf_counter();ref=reference(env,seed,model);ref['seconds']=time.perf_counter()-t;dump(HERE/'references'/f'{name}-{seed}.json',ref)
    for job in d['jobs']:
        name=job['model'];folder=HERE/'runs'/f"{name}-{job['policy']}-{job['seed']}"
        assert not (folder/'result.json').exists(),'do not overwrite stored outcomes'
        result=run_arm(env,models[name],decomps[name],floors[name],preptimes[name],job['policy'],job['seed'],folder)
        print(name,job['policy'],job['seed'],'it',result['iterations'],'s',round(result['total_seconds'],3),'ok',result['converged_numeric'],'error',result.get('error',{}).get('message'),flush=True)
    env.dispose()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('prepare','run'));args=p.parse_args();globals()[args.stage]()
