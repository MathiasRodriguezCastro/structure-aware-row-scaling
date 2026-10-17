#!/usr/bin/env python3
"""Bounded, staged mechanism experiment. No manuscript or generator mutation."""
import argparse
import csv
from datetime import datetime, timezone
from fractions import Fraction as F
import gzip
import hashlib
import json
import math
from pathlib import Path
import random
import re
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
THESIS = Path('/home/mathiasr/Escritorio/proyectoTesis/Implementacion_Cpp/Codigo_Cpp')
DISCOVERY = ['instance001','instance014','instance042']
HOLDOUT = ['instance002','instance003','instance004']
SEEDS = [307,331,353]
SCENARIOS = {'Demanding':(.01,100.),'Reference':(.1,1000.),'Permissive':(1.,10000.)}
PARAMS = dict(Threads=4,TimeLimit=12.,WorkLimit=12.,MIPGap=.001,
              FeasibilityTol=1e-6,IntFeasTol=1e-5,IntegralityFocus=0)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    raw=(json.dumps(value,indent=2,allow_nan=False)+'\n').encode()
    if str(path).endswith('.gz'):
        Path(path).write_bytes(gzip.compress(raw,mtime=0))
    else:
        Path(path).write_bytes(raw)


def read(path):
    raw=Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def csvwrite(path, rows):
    with Path(path).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def physical_spec(name, terms):
    """Pinned named-unit conversion from OMS audit, rechecked on canonical terms."""
    family=name.split('(')[0]
    if family in ('gh_total','gen_menor_demanda') or re.fullmatch(r'a\d+_gen_rio_negro',family):
        var='g' if family in ('gh_total','gen_menor_demanda') else 'g'+family.split('_')[0][1:]
        values=[abs(v) for n,v in terms.items() if n.split('(')[0]==var]
        if len(values)!=1:raise ValueError(('power units',name))
        return 'MW',values[0]
    if re.fullmatch(r'a\d+_g[1-4]h_def',family):
        values=[abs(v) for n,v in terms.items() if re.fullmatch(r'g\d+\(\d+\)',n)]
        if len(values)!=1:raise ValueError(('generation units',name))
        return 'MW',values[0]
    if re.fullmatch(r'a\d+_(bonete|baygorria|palmar|salto_grande)_tangente_\d+',family):
        values=[abs(v) for n,v in terms.items() if re.fullmatch(r'a\d+_z[1-4]h\(\d+\)',n)]
        if len(values)!=1:raise ValueError(('production units',name))
        return 'MW',values[0]
    if re.fullmatch(r'a\d+_v[1-3]h_din',family) or re.fullmatch(r'a\d+_balance',family):
        agent=family.split('_')[0];plant='4' if family.endswith('_balance') else family.split('_')[1][1]
        values=[abs(v) for n,v in terms.items() if n.split('(')[0]==agent+'_v'+plant+'h']
        if not values and plant=='2':
            values=[abs(v)/3600 for n,v in terms.items() if n.split('(')[0]==agent+'_x2h']
        if not values or len(set(values))!=1:raise ValueError(('water units',name))
        return 'm3',values[0]
    return None


def role(terms):
    owners=set()
    for name in terms:
        a=re.match(r'a(\d+)_',name)
        g=re.fullmatch(r'g(\d+)\(\d+\)',name)
        owners.add(a[1] if a else g[1] if g else 'master')
    return 'coupling' if len(owners)>1 else ('global' if owners=={'master'} else 'local')


def power(k):
    return F(2**k) if k>=0 else F(1,2**(-k))


def floorlog(q):
    k=q.numerator.bit_length()-q.denominator.bit_length()
    return k-1 if power(k)>q else k


def exponent(coeff, rhs, kernel, delta=None):
    nz=[abs(v) for v in coeff if v]
    if not nz:return 0
    lo,hi=min(nz),max(nz)
    lower=F(1e-9)/F(lo);upper=F(1e9)/F(hi)
    if delta is not None:lower=max(lower,F(1e-6)/F(delta))
    kl=floorlog(lower);kl+=power(kl)<lower
    kh=floorlog(upper)
    for v in [*coeff,rhs]:
        if not v:continue
        n,d=abs(v).as_integer_ratio();odd=(n&-n).bit_length()-1-(d.bit_length()-1)
        kl=max(kl,-1074-odd);kh=min(kh,1023-(math.frexp(abs(v))[1]-1))
    if kl>kh:return None
    if kernel=='gm':
        bracket=(-floorlog(F(lo)*F(hi))-1)//2
        choices=[bracket,bracket+1]
        k=min(choices,key=lambda j:(max(power(j)*F(hi),1/(power(j)*F(lo))),-j))
        proposal=1/math.sqrt(lo*hi)
    else:
        proposal=(1/math.sqrt(math.fsum(v*v for v in nz))) if kernel=='l2' else hi**(-15/16)
        k=math.floor(math.log2(proposal)+.5)
    if .5<=proposal<=2.:k=0
    return min(kh,max(kl,k))


def factors(data, policy, scenario='Reference'):
    names=[v['name'] for v in data['variables']]
    result=[]
    for row in data['rows']:
        terms={names[j]:v for j,v in row['terms']}
        spec=physical_spec(row['name'],terms)
        kernel='l2' if policy in ('Structural','Generator') and role(terms)=='coupling' else 'gm'
        if policy=='Ruiz':kernel='ruiz'
        delta=None
        if policy=='Generator' and spec:
            delta=SCENARIOS[scenario][0 if spec[0]=='MW' else 1]*spec[1]
        k=0 if policy=='Base' else exponent(list(terms.values()),row['rhs'],kernel,delta)
        if k is None:raise ValueError(('incompatible',policy,scenario,row['name']))
        alpha=math.ldexp(1.,k)
        for v in [*terms.values(),row['rhs']]:
            assert F(v*alpha)==F(v)*F(alpha),('inexact product',row['name'])
        result.append(k)
    return result


def canonical(model):
    vs=model.getVars();mat=model.getA().tocsr()
    return dict(sense=model.ModelSense,constant=model.ObjCon or 0.,
        variables=[dict(name=v.VarName,lb=v.LB if math.isfinite(v.LB) else None,
                        ub=v.UB if math.isfinite(v.UB) else None,obj=v.Obj,type=v.VType) for v in vs],
        rows=[dict(name=c.ConstrName,sense=c.Sense,rhs=c.RHS,
                   terms=[[int(j),float(v)] for j,v in zip(mat.indices[mat.indptr[i]:mat.indptr[i+1]],mat.data[mat.indptr[i]:mat.indptr[i+1]])])
              for i,c in enumerate(model.getConstrs())])


def build(data, exponents, env):
    import gurobipy as gp
    m=gp.Model(env=env)
    vs=[m.addVar(lb=v['lb'] if v['lb'] is not None else -gp.GRB.INFINITY,
                ub=v['ub'] if v['ub'] is not None else gp.GRB.INFINITY,
                obj=v['obj'],vtype=v['type'],name=v['name']) for v in data['variables']]
    m.ModelSense=data['sense'];m.ObjCon=data['constant'];m.update()
    for row,k in zip(data['rows'],exponents):
        expr=gp.LinExpr([math.ldexp(a,k) for _,a in row['terms']],[vs[j] for j,_ in row['terms']])
        m.addLConstr(expr,row['sense'],math.ldexp(row['rhs'],k),row['name'])
    m.update()
    return m


def fingerprint(data):
    names=[v['name'] for v in data['variables']]
    normalized=[]
    for row in data['rows']:
        pivot=max([abs(v) for _,v in row['terms']],default=abs(row['rhs']) or 1.)
        normalized.append([row['name'],row['sense'],str(F(row['rhs'])/F(pivot)),
                           sorted((names[j],str(F(v)/F(pivot))) for j,v in row['terms'])])
    payload=dict(variables=sorted(data['variables'],key=lambda v:v['name']),
                 sense=data['sense'],constant=data['constant'],rows=sorted(normalized))
    values=[abs(v) for r in data['rows'] for _,v in r['terms'] if v]
    return dict(rows=len(data['rows']),columns=len(names),integers=sum(v['type']!='C' for v in data['variables']),
                nonzeros=len(values),coefficient_min=min(values,default=None),coefficient_max=max(values,default=None),
                normalized_sha256=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest())


def verification(data, point, exponents):
    names=[v['name'] for v in data['variables']]
    maxrow=0.;worst='';physical={s:0. for s in SCENARIOS};contracts={s:0 for s in SCENARIOS}
    physical_worst={s:'' for s in SCENARIOS};physical_count=0;exported=0.
    for row,k in zip(data['rows'],exponents):
        lhs=math.fsum(a*point[j] for j,a in row['terms'])
        signed=lhs-row['rhs'];violation=abs(signed) if row['sense']=='=' else max(0.,signed if row['sense']=='<' else -signed)
        if violation>maxrow:maxrow=violation;worst=row['name']
        exported=max(exported,math.ldexp(violation,k))
        spec=physical_spec(row['name'],{names[j]:a for j,a in row['terms']})
        if spec:
            physical_count+=1
            for s,(p,w) in SCENARIOS.items():
                delta=(p if spec[0]=='MW' else w)*spec[1]
                ratio=violation/delta
                if ratio>physical[s]:physical[s]=ratio;physical_worst[s]=row['name']
                contracts[s]+=F(math.ldexp(1.,k))*F(delta)>=F(1e-6)
    return dict(objective=math.fsum(v['obj']*x for v,x in zip(data['variables'],point))+data['constant'],
        max_original_row_residual=maxrow,worst_row=worst,max_reconstructed_exported_residual=exported,
        max_bound_violation=max([0.]+[max((v['lb']-x) if v['lb'] is not None else 0.,
                                        (x-v['ub']) if v['ub'] is not None else 0.) for v,x in zip(data['variables'],point)]),
        max_integrality_violation=max([0.]+[abs(x-round(x)) for v,x in zip(data['variables'],point) if v['type']!='C']),
        physical_rows=physical_count,max_physical_ratio=physical,worst_physical_row=physical_worst,
        admissible_physical_rows=contracts)


def snapshot_protected():
    files=list((ROOT/'paper/submission/oms/releases/v1.3.5-oms-submission').rglob('*'))
    files += list((ROOT/'exploration').glob('*/*-artifact.zip'))
    files += [THESIS/'build/SistemaElectrico',THESIS/'SystemController/Problema/Problema.cpp',
              THESIS/'SystemController/Problema/ProblemaGurobi/ProblemaGurobi.cpp']
    return {str(p):sha(p) for p in files if p.is_file()}


def prepare():
    import gurobipy as gp
    if (HERE/'runs').exists():raise RuntimeError('optimization started; preparation frozen')
    (HERE/'inputs').mkdir(exist_ok=True)
    protected=snapshot_protected()
    dump(HERE/'protected-files.json',protected)
    for name in ('PROTOCOL.md','study.py'):
        shutil.copyfile(HERE/name,HERE/('snapshot-'+name))
    dump(HERE/'design.json',dict(frozen_utc=datetime.now(timezone.utc).isoformat(),
         discovery=DISCOVERY,holdout=HOLDOUT,seeds=SEEDS,parameters=PARAMS,
         solver_version=gp.gurobi.version(),protocol_sha256=sha(HERE/'PROTOCOL.md'),script_sha256=sha(HERE/'study.py'),
         note='Holdout optimization prohibited until discovery-conclusions.json exists'))
    with gp.Env(empty=True) as env:
        env.setParam('OutputFlag',0);env.start()
        for instance in DISCOVERY+HOLDOUT:
            folder=HERE/'inputs'/instance;folder.mkdir(exist_ok=True)
            source=THESIS/'entradas/entrada-SG-Ter-Mer'/(instance+'.txt')
            shutil.copyfile(source,folder/'original-input.txt')
            clean='\n'.join(line for line in source.read_text().splitlines() if not line.strip().startswith(('configurarSolver','preprocesar','resolver','grabar','finalizar','salir')))
            commands=clean+'\nconfigurarSolver --Gurobi\ng r a b a r\n'
            commands=commands.replace('g r a b a r','grabar '+str(folder/'Base.mps')+' --noConstante')+'salir\n'
            (folder/'commands.txt').write_text(commands)
            start=time.perf_counter()
            p=subprocess.run([str(THESIS/'build/SistemaElectrico')],input=commands,text=True,cwd=folder,capture_output=True,timeout=90)
            (folder/'generation.log').write_text(p.stdout+'\n'+p.stderr)
            assert p.returncode==0 and (folder/'Base.mps').exists(),p.stdout[-2000:]
            m=gp.read(str(folder/'Base.mps'),env=env);data=canonical(m);m.dispose()
            assert any(v['type']!='C' for v in data['variables'])
            dump(folder/'canonical.json.gz',data)
            record=dict(instance=instance,generation_import_seconds=time.perf_counter()-start,source_sha256=sha(source),
                        canonical_stats=fingerprint(data),policy_exponents={})
            for policy in ('Base','Algebraic','Structural','Ruiz'):
                record['policy_exponents'][policy]=factors(data,policy)
            record['contracts']={}
            for scenario in SCENARIOS:
                ex=factors(data,'Generator',scenario)
                changed=sum(a!=b for a,b in zip(ex,record['policy_exponents']['Structural']))
                record['contracts'][scenario]=dict(changed_rows=changed,incompatible_rows=0,
                    same_factors_as_structural=(changed==0),exponents_sha256=hashlib.sha256(json.dumps(ex).encode()).hexdigest())
            for policy,ex in record['policy_exponents'].items():
                transformed=build(data,ex,env);actual=canonical(transformed);transformed.dispose()
                assert actual['variables']==data['variables'] and actual['constant']==data['constant'] and actual['sense']==data['sense']
                for row,scaled,k in zip(data['rows'],actual['rows'],ex):
                    assert row['name']==scaled['name'] and row['sense']==scaled['sense']
                    assert F(scaled['rhs'])==F(row['rhs'])*power(k)
                    assert scaled['terms']==[[j,math.ldexp(a,k)] for j,a in row['terms']]
                assert fingerprint(actual)['normalized_sha256']==record['canonical_stats']['normalized_sha256']
            dump(folder/'preparation.json',record)
            print('Prepared',instance,record['canonical_stats'],record['contracts'],flush=True)


def jobs(stage):
    result=[]
    for instance in DISCOVERY if stage=='discovery' else HOLDOUT:
        variants=[(p,s,r) for p in ('Base','Structural') for s in (-1,0) for r in (-1,0)] if stage=='discovery' else []
        variants += [(p,-1,-1) for p in (('Algebraic','Ruiz') if stage=='discovery' else ('Base','Structural','Algebraic','Ruiz'))]
        for policy,scale,presolve in variants:
            for seed in SEEDS:result.append(dict(instance=instance,policy=policy,scale=scale,presolve=presolve,seed=seed))
    random.Random(20261014).shuffle(result)
    return result


def key(job):
    return '{instance}-{policy}-s{scale}-p{presolve}-seed{seed}'.format(**job)


def run(stage):
    import gurobipy as gp
    if stage=='holdout' and not (HERE/'discovery-conclusions.json').exists():raise RuntimeError('freeze discovery conclusions before holdout')
    folder=HERE/'runs'/stage;folder.mkdir(parents=True,exist_ok=True)
    joblist=jobs(stage);dump(HERE/(stage+'-schedule.json'),joblist)
    with gp.Env(empty=True) as env:
        env.setParam('OutputFlag',0);env.start()
        cache={};diagnostics=set()
        for position,job in enumerate(joblist):
            name=key(job);target=folder/(name+'.json.gz')
            if target.exists():continue
            inp=HERE/'inputs'/job['instance'];data=read(inp/'canonical.json.gz');prep=read(inp/'preparation.json')
            ex=prep['policy_exponents'][job['policy']]
            representation=hashlib.sha256(json.dumps(ex).encode()).hexdigest()
            ck=(job['instance'],representation,job['scale'],job['presolve'],job['seed'])
            if ck in cache:
                prior=read(cache[ck]);prior.update(job=job,alias_of=str(cache[ck].relative_to(HERE)))
                dump(target,prior);print(position+1,'Alias',name,flush=True);continue
            diagkey=(job['instance'],job['policy'],job['scale'],job['presolve'])
            diagname='{instance}-{policy}-s{scale}-p{presolve}'.format(**job)
            diagpath=folder/(diagname+'-diagnostic.json.gz')
            if diagkey not in diagnostics and not diagpath.exists():
                start=time.perf_counter();d=build(data,ex,env)
                for p,v in PARAMS.items():d.setParam(p,v)
                d.Params.ScaleFlag=job['scale'];d.Params.Presolve=job['presolve'];d.Params.Seed=SEEDS[0]
                try:
                    presolved=d.presolve();presolveddata=canonical(presolved);presolved.dispose()
                    dump(folder/(diagname+'-presolved.json.gz'),presolveddata)
                    diag=dict(presolve=fingerprint(presolveddata),presolve_seconds=time.perf_counter()-start)
                except gp.GurobiError as e:diag=dict(presolve_error=str(e),presolve_seconds=time.perf_counter()-start)
                relaxed=d.relax();relaxed.Params.Method=1;relaxed.optimize()
                diag['relaxed_lp']=dict(status=relaxed.Status,objective=relaxed.ObjVal if relaxed.SolCount else None,
                       work=relaxed.Work,runtime=relaxed.Runtime,iterations=relaxed.IterCount)
                dump(diagpath,diag);relaxed.dispose();d.dispose();diagnostics.add(diagkey)
            start=time.perf_counter();m=build(data,ex,env);construction=time.perf_counter()-start
            for p,v in PARAMS.items():m.setParam(p,v)
            m.Params.ScaleFlag=job['scale'];m.Params.Presolve=job['presolve'];m.Params.Seed=job['seed']
            m.Params.LogFile=str(folder/(name+'.log'));m.Params.OutputFlag=1;m.Params.LogToConsole=0
            progress=[];last=[None,None]
            def callback(model,where):
                if where==gp.GRB.Callback.MIP:
                    incumbent=model.cbGet(gp.GRB.Callback.MIP_OBJBST);bound=model.cbGet(gp.GRB.Callback.MIP_OBJBND)
                    if [incumbent,bound]!=last:
                        progress.append(dict(runtime=model.cbGet(gp.GRB.Callback.RUNTIME),work=model.cbGet(gp.GRB.Callback.WORK),
                                      incumbent=incumbent if abs(incumbent)<1e99 else None,bound=bound if abs(bound)<1e99 else None,
                                      nodes=model.cbGet(gp.GRB.Callback.MIP_NODCNT)))
                        last[:]=[incumbent,bound]
            start=time.perf_counter();m.optimize(callback);wall=time.perf_counter()-start
            point=m.getAttr('X') if m.SolCount else None
            record=dict(job=job,alias_of=None,status=m.Status,solution_count=m.SolCount,work=m.Work,runtime=m.Runtime,
                        optimizer_wall_seconds=wall,construction_seconds=construction,nodes=m.NodeCount,iterations=m.IterCount,
                        objective=m.ObjVal if point is not None else None,bound=m.ObjBound,gap=m.MIPGap if point is not None else None,
                        point=point,progress=progress,verification=None)
            if point is not None:
                start=time.perf_counter();record['verification']=verification(data,point,ex)
                record['verification_seconds']=time.perf_counter()-start
            dump(target,record);cache[ck]=target;m.dispose()
            print(position+1,'/',len(joblist),name,'status',record['status'],'W',round(record['work'],4),
                  'obj',record['objective'],'gap',record['gap'],flush=True)


def summarize():
    rows=[];diagnostics=[]
    for stage in ('discovery','holdout'):
        for p in sorted((HERE/'runs'/stage).glob('*.json.gz')):
            r=read(p)
            if p.name.endswith('-presolved.json.gz'):continue
            if p.name.endswith('-diagnostic.json.gz'):
                diagnostics.append(dict(stage=stage,name=p.name,**r));continue
            j=r['job'];v=r['verification'] or {}
            rows.append(dict(stage=stage,**j,status=r['status'],alias_of=r['alias_of'] or '',work=r['work'],
                 runtime=r['runtime'],objective=r['objective'],bound=r['bound'],gap=r['gap'],nodes=r['nodes'],
                 original_row_residual=v.get('max_original_row_residual'),integrality_residual=v.get('max_integrality_violation'),
                 bound_violation=v.get('max_bound_violation'),
                 demanding_ratio=v.get('max_physical_ratio',{}).get('Demanding'),
                 reference_ratio=v.get('max_physical_ratio',{}).get('Reference'),
                 permissive_ratio=v.get('max_physical_ratio',{}).get('Permissive')))
    if rows:csvwrite(HERE/'runs-summary.csv',rows)
    dump(HERE/'diagnostics-summary.json',diagnostics)
    print('Recorded arms',len(rows),'actual MIP calls',sum(not r['alias_of'] for r in rows),flush=True)


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('action',choices=['prepare','discovery','holdout','summarize']);args=a.parse_args()
    if args.action=='prepare':prepare()
    elif args.action=='summarize':summarize()
    else:run(args.action)
