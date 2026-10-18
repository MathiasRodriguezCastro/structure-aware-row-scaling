"""Prospective unit-covariance and shared-activity comparison.

All input variants and computational aliases are fixed before optimizing.
"""
import argparse
import collections
import copy
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import random
import time

import activity as a

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
F=Fraction.from_float
NAMES=('control30-3-2-3','neos-3421095-cinca','neos-1112787','beasleyC3','k16x240b')
POLICIES=('Budget-row','Raw-budget','Tight-raw','NF3-raw','SOS-unit','SOS-normalized',
          'SOS-range','Individual-budget','Shared-budget','Indicator-budget')
UNITS=(-20,-10,0,10,20)
SEEDS=(181,191,193)


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(p,obj):p.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')


def mps_model(path,env):
    import gurobipy as gp
    m=gp.read(str(path),env=env);vs=m.getVars();index={v.VarName:j for j,v in enumerate(vs)}
    assert m.ModelSense==1 and m.ObjCon==0 and not m.NumSOS and not m.NumGenConstrs
    rows=[]
    for c in m.getConstrs():
        r=m.getRow(c)
        rows.append({'name':c.ConstrName,'terms':{str(index[r.getVar(j).VarName]):r.getCoeff(j) for j in range(r.size())},
                     'rhs':c.RHS,'sense':c.Sense,'budget':1e-4*max(1.,abs(c.RHS)),'unit':'experimental algebraic units'})
    result={'name':path.name.replace('.mps.gz',''),'variables':[{'name':v.VarName,'cost':v.Obj,
             'lower':v.LB if abs(v.LB)<1e100 else None,'upper':v.UB if abs(v.UB)<1e100 else None,
             'integer':v.VType!=gp.GRB.CONTINUOUS,'bound_budget':1e-4} for v in vs],
            'rows':rows,'family':'fixed-charge network flow','source':str(path.relative_to(ROOT)),'source_sha256':sha(path)}
    m.dispose();return result


def sources(name,env):
    if name in ('beasleyC3','k16x240b'):
        model=mps_model(HERE/'sources'/(name+'.mps.gz'),env)
        return model,copy.deepcopy(model),None
    if name=='neos-1112787':
        p=ROOT/'exploration/oms-transfer-study-20261014/confirmation/models'/name/'original-model.json'
        m=json.loads(p.read_text());return m,copy.deepcopy(m),p
    p=ROOT/'exploration/oms-generalization-20261014/pilot/models'/name/'original-model.json'
    c=ROOT/'exploration/oms-budget-reformulation-20261017/diagnostic'/name/'reformulated-model.json'
    return json.loads(p.read_text()),json.loads(c.read_text()),p


def change_units(model,gate_rows,k):
    model=copy.deepcopy(model)
    for i in gate_rows:
        r=model['rows'][i]
        r['terms']={j:math.ldexp(float(c),k) for j,c in r['terms'].items()}
        r['rhs']=math.ldexp(float(r['rhs']),k);r['budget']=math.ldexp(float(r['budget']),k)
    return model


def target_groups(model):
    gates=a.gates(model);groups=collections.defaultdict(list)
    for g in gates:groups[g['z']].append(g)
    selected={}
    for z,group in groups.items():
        if any(a.factor([*g['g'].values(),-g['M']],delta=F(float(g['delta'])),
                        reserve=F(1e-5)*F(float(g['M']))) is None for g in group):selected[z]=group
    return gates,selected


def build(base,groups,policy):
    model=copy.deepcopy(base);epsilon=1e-9 if policy=='Tight-raw' else 1e-6
    gamma=1e-9 if policy=='Tight-raw' else 1e-5
    selected={g['row']:g for group in groups.values() for g in group}
    meta={'policy':policy,'epsilon':epsilon,'gamma':gamma,'selected_rows':sorted(selected),
          'original_variables':len(base['variables']),'original_rows':len(base['rows']),
          'factors':[],'sos':[],'links':[],'indicators':[],'groups':[]}
    for i,row in enumerate(model['rows']):
        reserve=F(gamma)*sum((abs(F(float(c))) for j,c in row['terms'].items() if model['variables'][int(j)]['integer']),Fraction(0)) if policy=='Budget-row' else Fraction(0)
        alpha=a.factor(list(row['terms'].values()),row['rhs'],
                       delta=None if i in selected and policy not in ('Budget-row','Raw-budget','Tight-raw','NF3-raw') else F(float(row['budget'])),
                       reserve=reserve,epsilon=epsilon)
        if alpha is None:return None,{'compatible':False,'row':i,'reason':'row_factor_incompatible','policy':policy}
        meta['factors'].append(alpha)
    if policy in ('Budget-row','Raw-budget','Tight-raw','NF3-raw'):return model,meta
    complement={}
    def newvar(name,upper):
        j=len(model['variables']);model['variables'].append({'name':name,'cost':0.,'lower':0.,'upper':upper,'integer':False,'bound_budget':1e-6});return j
    def new_complement(z):
        if z not in complement:
            w=newvar(f'complement_{z}',1.);c=len(model['rows'])
            model['rows'].append({'name':f'complement_{z}','terms':{str(w):1.,str(z):1.},'rhs':1.,'sense':'=','budget':1e-6,'unit':'auxiliary'})
            meta['factors'].append(1.);complement[z]=(w,c)
        return complement[z]
    for z,group in groups.items():
        if policy=='Shared-budget':
            dec=a.select_shared(group,epsilon=epsilon,gamma_sos=gamma)
            if not dec['compatible']:return None,{**dec,'policy':policy,'z':z}
            R=dec['radius'];y=newvar(f'shared_{z}',R);w,c=new_complement(z)
            meta['sos'].append({'z':z,'y':y,'w':w,'complement_row':c,'radius':R})
            meta['groups'].append({'z':z,**dec})
            decisions={d['row']:d for d in dec['decisions']}
        for g in group:
            i=g['row'];M=g['M'];delta=F(float(g['delta']))
            if policy=='Indicator-budget':
                alpha=a.factor(list(g['g'].values()),delta=delta,epsilon=epsilon)
                if alpha is None:return None,{'compatible':False,'reason':'indicator_row_factor','row':i}
                model['rows'][i]={'name':f'cap_{i}','terms':g['g'],'rhs':M,'sense':'<','budget':g['delta'],'unit':'auxiliary'}
                meta['factors'][i]=alpha;meta['indicators'].append({'row':i,'z':z,'terms':g['g'],'alpha':alpha,'M':M,'rhs':0.})
                continue
            if policy=='Shared-budget':
                d=decisions[i];h,alpha=d['h'],d['alpha']
            else:
                if policy=='Individual-budget':
                    d=a.select_individual(g,epsilon=epsilon,gamma_sos=gamma)
                    if not d['compatible']:return None,{**d,'row':i,'policy':policy}
                    h,R,alpha=d['h'],d['radius'],d['alpha']
                else:
                    h=1. if policy=='SOS-unit' else M if policy=='SOS-range' else float(a.pow2(a.flog(delta)))
                    R=a.exact(F(float(M))/F(h))
                    if R is None or R>float(a.CAP):return None,{'compatible':False,'reason':'activity_bound','row':i,'policy':policy}
                    reserve=F(h)*max(F(gamma),F(1e-6))
                    alpha=a.factor([*g['g'].values(),-h],delta=delta if policy=='SOS-normalized' else None,
                                   reserve=reserve,epsilon=epsilon)
                    if alpha is None:return None,{'compatible':False,'reason':'activity_factor','row':i,'policy':policy}
                y=newvar(f'activity_{i}',R);w,c=new_complement(z)
                meta['sos'].append({'z':z,'y':y,'w':w,'complement_row':c,'radius':R})
            model['rows'][i]={'name':f'activity_link_{i}','terms':{**g['g'],str(y):-h},'rhs':0.,'sense':'<','budget':g['delta'],'unit':'auxiliary'}
            meta['factors'][i]=alpha
            meta['links'].append({'row':i,'z':z,'y':y,'w':w,'complement_row':c,'M':M,'h':h,'radius':R,'sign':g['sign'],
                                  'bound':str(F(epsilon)/F(alpha)+F(h)*max(F(gamma),F(1e-6)))})
    return model,meta


def write_lp(path,model,meta):
    def expr(terms):return ' '.join(f'{"+" if c>=0 else "-"} {abs(c):.17g} x{int(j):05d}' for j,c in terms.items() if c) or '0'
    lines=['Minimize',' obj: '+expr({str(j):v['cost'] for j,v in enumerate(model['variables'])}),'Subject To']
    for i,(row,alpha) in enumerate(zip(model['rows'],meta['factors'])):
        terms={j:c*alpha for j,c in row['terms'].items()};rhs=row['rhs']*alpha
        assert all(F(float(c))*F(alpha)==F(float(terms[j])) for j,c in row['terms'].items())
        assert F(float(row['rhs']))*F(alpha)==F(float(rhs))
        lines.append(f' r{i:05d}: '+expr(terms)+' '+{'<':'<=','>':'>=','=':'='}[row['sense']]+f' {rhs:.17g}')
    for g in meta['indicators']:
        terms={j:c*g['alpha'] for j,c in g['terms'].items()}
        assert all(F(float(c))*F(g['alpha'])==F(float(terms[j])) for j,c in g['terms'].items())
        lines.append(f' ind{g["row"]:05d}: x{g["z"]:05d} = 0 -> '+expr(terms)+' <= 0')
    lines.append('Bounds');ints=[]
    for j,v in enumerate(model['variables']):
        lo,hi=v['lower'],v['upper'];lines.append(f" {'-inf' if lo is None else format(lo,'.17g')} <= x{j:05d} <= {'+inf' if hi is None else format(hi,'.17g')}")
        if v['integer']:ints.append(f' x{j:05d}')
    if ints:lines+=['Generals',*ints]
    if meta['sos']:
        lines.append('SOS')
        for j,g in enumerate(meta['sos']):lines.append(f' s{j:05d}: S1:: x{g["w"]:05d}:1 x{g["y"]:05d}:2')
    lines+=['End',''];path.write_text('\n'.join(lines))


def prepare():
    import gurobipy as gp
    output=HERE/'pilot'
    if output.exists():raise RuntimeError('do not overwrite a saved pilot')
    output.mkdir();env=gp.Env(empty=True);env.setParam('OutputFlag',0);env.start()
    design={'protocol_sha256':sha(HERE/'PROTOCOL.md'),'activity_sha256':sha(HERE/'activity.py'),'runner_sha256':sha(Path(__file__)),
            'models':[],'assignments':[],'calls':[],'abstentions':[],'aliases_fixed_before_optimize':True}
    for name in NAMES:
        original,base,path=sources(name,env);folder=output/'models'/name;folder.mkdir(parents=True)
        dump(folder/'original-model.json',original);dump(folder/'contracted-model.json',base)
        gates,groups=target_groups(base);rows=[g['row'] for g in gates]
        item={'name':name,'source':str(path.relative_to(ROOT)) if path else None,'source_sha256':sha(path) if path else None,
              'original_sha256':sha(folder/'original-model.json'),'contracted_sha256':sha(folder/'contracted-model.json'),
              'gate_rows':rows,'selected_rows':sorted(g['row'] for group in groups.values() for g in group),
              'selected_groups':len(groups),'all_gates':len(gates),'variants':[]}
        unique={}
        for k in UNITS:
            units=change_units(base,rows,k);_,converted_groups=target_groups(units)
            assert set(converted_groups)==set(groups)
            for policy in POLICIES:
                started=time.perf_counter();model,meta=build(units,converted_groups,policy)
                label=f'{policy}-u{k:+d}';arm=folder/label;arm.mkdir()
                if model is None:
                    dump(arm/'abstention.json',meta);design['abstentions'].append({'name':name,'policy':policy,'unit_exponent':k,**meta})
                    continue
                meta['unit_exponent']=k;meta['all_gate_rows']=rows
                dump(arm/'model.json',model);dump(arm/'selection.json',meta);write_lp(arm/'model.lp',model,meta)
                preparation=time.perf_counter()-started;export_sha=sha(arm/'model.lp')
                params={'Threads':4,'TimeLimit':30.,'WorkLimit':5.,'MIPGap':.01,'FeasibilityTol':meta['epsilon'],
                        'IntFeasTol':meta['gamma'],'Presolve':-1,'PreSOS1BigM':0,'NumericFocus':3 if policy=='NF3-raw' else 0}
                key=export_sha,json.dumps(params,sort_keys=True)
                canonical=unique.setdefault(key,label)
                assignment={'name':name,'policy':policy,'arm':label,'canonical_arm':canonical,'unit_exponent':k,
                            'export_sha256':export_sha,'parameters':params,'selection_export_seconds':preparation}
                design['assignments'].append(assignment);item['variants'].append({'policy':policy,'unit_exponent':k,'export_sha256':export_sha,'canonical_arm':canonical})
                if canonical==label:
                    for seed in SEEDS:design['calls'].append({**assignment,'seed':seed})
        design['models'].append(item)
        print(json.dumps({'prepared':name,'selected_groups':len(groups),'selected_rows':len(item['selected_rows']),
                          'calls_so_far':len(design['calls'])}),flush=True)
    env.dispose();random.Random(1700181).shuffle(design['calls']);dump(output/'design.json',design)
    print(json.dumps({'calls':len(design['calls']),'assignments':len(design['assignments']),'abstentions':len(design['abstentions'])}),flush=True)


def import_check(model,data,meta,gp):
    variables={v.VarName:v for v in model.getVars()}
    assert len(variables)==len(data['variables']) and model.ModelSense==1 and model.ObjCon==0
    assert model.NumConstrs==len(data['rows'])
    for j,v in enumerate(data['variables']):
        actual=variables[f'x{j:05d}'];assert F(actual.Obj)==F(float(v['cost']))
        assert (actual.VType!=gp.GRB.CONTINUOUS)==v['integer']
        for x,b in ((actual.LB,v['lower']),(actual.UB,v['upper'])):assert abs(x)>=1e100 if b is None else F(x)==F(float(b))
    for i,(row,alpha) in enumerate(zip(data['rows'],meta['factors'])):
        c=model.getConstrByName(f'r{i:05d}');r=model.getRow(c)
        actual={r.getVar(j).VarName:F(r.getCoeff(j)) for j in range(r.size())}
        assert actual=={f'x{int(j):05d}':F(float(x))*F(alpha) for j,x in row['terms'].items() if x}
        assert c.Sense==row['sense'] and F(c.RHS)==F(float(row['rhs']))*F(alpha)
    assert model.NumSOS==len(meta['sos']) and model.NumGenConstrs==len(meta['indicators'])
    for sos,gate in zip(model.getSOSs(),meta['sos']):
        kind,members,weights=model.getSOS(sos)
        assert kind==1 and {v.VarName:w for v,w in zip(members,weights)}=={f'x{gate["w"]:05d}':1.,f'x{gate["y"]:05d}':2.}
    for c,gate in zip(model.getGenConstrs(),meta['indicators']):
        var,value,expr,sense,rhs=model.getGenConstrIndicator(c)
        assert var.VarName==f'x{gate["z"]:05d}' and value==0 and sense=='<' and rhs==0
        assert {expr.getVar(j).VarName:F(expr.getCoeff(j)) for j in range(expr.size())}=={f'x{int(j):05d}':F(float(x))*F(gate['alpha']) for j,x in gate['terms'].items() if x}
    return variables


def solve():
    import gurobipy as gp
    import numpy as np
    design=json.loads((HERE/'pilot/design.json').read_text())
    for key,file in (('protocol_sha256','PROTOCOL.md'),('activity_sha256','activity.py'),('runner_sha256','study.py')):assert design[key]==sha(HERE/file)
    env=gp.Env(empty=True);env.setParam('OutputFlag',0);env.start()
    for index,call in enumerate(design['calls']):
        arm=HERE/'pilot/models'/call['name']/call['arm'];out=HERE/'pilot/runs'/call['name']/call['arm']/str(call['seed'])
        if (out/'run.json').exists():continue
        out.mkdir(parents=True,exist_ok=True);assert sha(arm/'model.lp')==call['export_sha256']
        started=time.perf_counter();model=gp.read(str(arm/'model.lp'),env=env)
        data=json.loads((arm/'model.json').read_text());meta=json.loads((arm/'selection.json').read_text())
        variables=import_check(model,data,meta,gp);import_seconds=time.perf_counter()-started
        for key,value in {**call['parameters'],'Seed':call['seed'],'OutputFlag':1,'LogToConsole':0,'LogFile':str(out/'solver.log')}.items():model.setParam(key,value)
        model.optimize()
        record={**call,'solver_version':list(gp.gurobi.version()),'status':model.Status,'has_point':model.SolCount>0,
                'solution_count':model.SolCount,'objective':model.ObjVal if model.SolCount else None,
                'reported_bound':model.ObjBound if math.isfinite(model.ObjBound) else None,'optimality_certified':False,
                'work':model.Work,'runtime':model.Runtime,'nodes':model.NodeCount,'import_check_seconds':import_seconds,
                'sos':model.NumSOS,'variables':model.NumVars,'constraints':model.NumConstrs,'indicators':model.NumGenConstrs}
        if model.SolCount:np.savez(out/'point.npz',x=np.array([variables[f'x{j:05d}'].X for j in range(len(data['variables']))]))
        record['process_through_persistence_seconds']=time.perf_counter()-started
        dump(out/'run.json',record)
        print(json.dumps({'completed':index+1,'of':len(design['calls']),'name':call['name'],'arm':call['arm'],'seed':call['seed'],
                          'status':model.Status,'point':model.SolCount>0,'work':model.Work,'objective':record['objective']}),flush=True)
        model.dispose()
    env.dispose()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('prepare','solve'));args=parser.parse_args()
    prepare() if args.action=='prepare' else solve()
