"""Bounded pilot for lattice copies, with matrix-matched continuous controls."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import random
import time
from fractions import Fraction

import method

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRIOR=ROOT/'exploration/oms-activity-scaling-20261017/pilot/models'
F=Fraction.from_float
NAMES=('control30-3-2-3','neos-3421095-cinca')
SEEDS=(167,173,179)


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')


def write_lp(path,model,meta):
    def expr(terms):
        return ' '.join(f'{"+" if a>=0 else "-"} {abs(a):.17g} x{int(j):05d}' for j,a in terms.items() if a) or '0'
    lines=['Minimize',' obj: '+expr({str(j):v['cost'] for j,v in enumerate(model['variables'])}), 'Subject To']
    for i,(row,alpha) in enumerate(zip(model['rows'],meta['factors'])):
        terms={j:a*alpha for j,a in row['terms'].items()};rhs=row['rhs']*alpha
        assert all(F(float(a))*F(alpha)==F(float(terms[j])) for j,a in row['terms'].items())
        assert F(float(row['rhs']))*F(alpha)==F(float(rhs))
        lines.append(f' r{i:05d}: '+expr(terms)+' '+{'<':'<=','>':'>=','=':'='}[row['sense']]+f' {rhs:.17g}')
    lines.append('Bounds');integers=[]
    for j,v in enumerate(model['variables']):
        lo,hi=v['lower'],v['upper']
        lines.append(f" {'-inf' if lo is None else format(lo,'.17g')} <= x{j:05d} <= {'+inf' if hi is None else format(hi,'.17g')}")
        if v['integer']:integers.append(f' x{j:05d}')
    if integers:lines+=['Generals',*integers]
    if meta['gates']:
        lines.append('SOS')
        for g in meta['gates']:lines.append(f' s{g["row"]:05d}: S1:: x{g["w"]:05d}:1 x{g["y"]:05d}:2')
    lines+=['End',''];path.write_text('\n'.join(lines))


def prepare():
    output=HERE/'pilot'
    if output.exists():raise RuntimeError('preserve pilot; use a new directory')
    output.mkdir()
    design={'protocol_sha256':sha(HERE/'PROTOCOL.md'),'method_sha256':sha(HERE/'method.py'),
            'runner_sha256':sha(Path(__file__)),'models':[],'calls':[],'abstentions':[]}
    for name in NAMES:
        base=PRIOR/name/'Contracted-L2'
        contracted=json.loads((base/'model.json').read_text());base_meta=json.loads((base/'selection.json').read_text())
        targets=base_meta['selected_rows']; original_path=ROOT/'exploration/oms-generalization-20261014/pilot/models'/name/'original-model.json'
        rows=[]
        for i in targets:
            r=contracted['rows'][i];disc=[int(j) for j in r['terms'] if contracted['variables'][int(j)]['integer']]
            assert len(disc)==1
            z=disc[0];rows.append({'row':i,'z':z,'M':abs(r['terms'][str(z)]),'terms':r['terms']})
        item={'name':name,'original':str(original_path.relative_to(ROOT)),'original_sha256':sha(original_path),
              'contracted':str((base/'model.json').relative_to(ROOT)),'contracted_sha256':sha(base/'model.json'),
              'selected_rows':targets,'selections':{}}
        plans=[('Contracted-L2',None,copy.deepcopy(contracted),copy.deepcopy(base_meta))]
        sos=PRIOR/name/'SOS-unit-1e-04'
        plans.append(('SOS-unit',None,json.loads((sos/'model.json').read_text()),json.loads((sos/'selection.json').read_text())))
        for budget in (1e-4,1e-8):
            raw=copy.deepcopy(base_meta);raw_factors={r['row']:method.factor(r,F(budget),Fraction(0),method.LOW,method.HIGH) for r in rows}
            if all(a is not None for a in raw_factors.values()):
                for i,a in raw_factors.items():raw['factors'][i]=a
                plans.append(('Raw-budget',budget,copy.deepcopy(contracted),raw))
            else:design['abstentions'].append({'name':name,'policy':'Raw-budget','budget':budget})
            selected=method.select(rows,budget);item['selections'][f'{budget:.0e}']=selected
            if not selected['compatible']:
                for policy in ('Integer-copy','Continuous-copy'):design['abstentions'].append({'name':name,'policy':policy,'budget':budget})
                continue
            for policy in ('Integer-copy','Continuous-copy'):
                model=copy.deepcopy(contracted);meta=copy.deepcopy(base_meta);meta['copies']=[]
                for z,g in selected['groups'].items():
                    q=len(model['variables']);K=g['K'];sigma=g['sigma'];idx=len(model['rows'])
                    model['variables'].append({'name':f'copy_{z}','cost':0.,'lower':0.,'upper':float(K),
                                               'integer':policy=='Integer-copy','bound_budget':1e-6})
                    model['rows'].append({'name':f'copy_link_{z}','terms':{str(z):float(K),str(q):-1.},
                                          'rhs':0.,'sense':'=','budget':1e-6,'unit':'auxiliary'})
                    meta['factors'].append(sigma)
                    for i,a in g['factors'].items():meta['factors'][i]=a
                    meta['copies'].append({'z':z,'q':q,'row':idx,'K':K,'sigma':sigma,
                                           'gamma_effective':g['gamma_effective'],'k':g['k']})
                meta['selector_t']=selected['t']
                plans.append((policy,budget,model,meta))
        design['models'].append(item)
        for policy,budget,model,meta in plans:
            label=policy+(f'-{budget:.0e}' if budget is not None else '')
            folder=output/'models'/name/label;folder.mkdir(parents=True)
            meta.update({'policy':policy,'activation_budget':budget,'original_variables':len(contracted['variables']),
                         'original_rows':len(contracted['rows'])});meta.setdefault('copies',[])
            dump(folder/'model.json',model);dump(folder/'selection.json',meta);write_lp(folder/'model.lp',model,meta)
            for presolve in (-1,0):
                for seed in SEEDS:design['calls'].append({'name':name,'arm':label,'seed':seed,'presolve':presolve,
                                                         'export_sha256':sha(folder/'model.lp')})
    random.Random(171017).shuffle(design['calls']);dump(output/'design.json',design)
    print(json.dumps({'calls':len(design['calls']),'abstentions':design['abstentions'],
                      'selections':{m['name']:m['selections'] for m in design['models']}},indent=2))


def solve():
    import gurobipy as gp
    import numpy as np
    design=json.loads((HERE/'pilot/design.json').read_text())
    for key,file in (('protocol_sha256','PROTOCOL.md'),('method_sha256','method.py'),('runner_sha256','study.py')):
        assert design[key]==sha(HERE/file)
    env=gp.Env(empty=True);env.setParam('OutputFlag',0);env.start()
    for index,call in enumerate(design['calls']):
        folder=HERE/'pilot/models'/call['name']/call['arm']
        out=HERE/'pilot/runs'/call['name']/call['arm']/f'p{call["presolve"]}-s{call["seed"]}'
        if (out/'run.json').exists():continue
        out.mkdir(parents=True,exist_ok=True);assert sha(folder/'model.lp')==call['export_sha256']
        before=time.perf_counter();model=gp.read(str(folder/'model.lp'),env=env)
        data=json.loads((folder/'model.json').read_text());meta=json.loads((folder/'selection.json').read_text())
        variables={v.VarName:v for v in model.getVars()}
        assert len(variables)==len(data['variables'])
        for j,v in enumerate(data['variables']):
            got=variables[f'x{j:05d}'];assert F(got.Obj)==F(float(v['cost']))
            assert (got.VType!=gp.GRB.CONTINUOUS)==v['integer']
            for actual,want in ((got.LB,v['lower']),(got.UB,v['upper'])):
                assert abs(actual)>=1e100 if want is None else F(actual)==F(float(want))
        for i,(r,a) in enumerate(zip(data['rows'],meta['factors'])):
            c=model.getConstrByName(f'r{i:05d}');e=model.getRow(c)
            actual={e.getVar(j).VarName:F(e.getCoeff(j)) for j in range(e.size())}
            want={f'x{int(j):05d}':F(float(x))*F(float(a)) for j,x in r['terms'].items() if x}
            assert actual==want and c.Sense==r['sense'] and F(c.RHS)==F(float(a))*F(float(r['rhs']))
        assert model.NumSOS==len(meta['gates'])
        params={'OutputFlag':0,'LogFile':str(out/'solver.log'),'Seed':call['seed'],'Threads':4,
                'TimeLimit':30.,'WorkLimit':1.,'MIPGap':.01,'FeasibilityTol':1e-6,'IntFeasTol':1e-9,
                'Presolve':call['presolve'],'PreSOS1BigM':0,'NumericFocus':0}
        for k,v in params.items():model.setParam(k,v)
        prep=time.perf_counter()-before;model.optimize()
        record={**call,'policy':meta['policy'],'budget':meta['activation_budget'],
                'parameters':{k:v for k,v in params.items() if k!='LogFile'},'solver_version':list(gp.gurobi.version()),
                'status':model.Status,'has_point':model.SolCount>0,'solution_count':model.SolCount,
                'work':model.Work,'runtime':model.Runtime,'nodes':model.NodeCount,'prepare_seconds':prep,
                'objective':model.ObjVal if model.SolCount else None,'reported_bound':model.ObjBound if math.isfinite(model.ObjBound) else None,
                'optimality_certified':False}
        if model.SolCount:np.savez(out/'point.npz',x=np.array([variables[f'x{j:05d}'].X for j in range(len(data['variables']))]))
        dump(out/'run.json',record)
        print(json.dumps({'completed':index+1,**call,'status':model.Status,'point':model.SolCount>0,'work':model.Work}),flush=True)
        model.dispose()
    env.dispose()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('prepare','solve'));args=parser.parse_args()
    prepare() if args.action=='prepare' else solve()
