#!/usr/bin/env python3
"""Original-LP parser and row-local exact replay, without optimizer imports."""
from collections import Counter
from fractions import Fraction as Q
import gzip
import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np

HERE=Path(__file__).resolve().parent


def read(p):
    b=p.read_bytes();return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def source_check(path,data):
    rows={};obj={};bounds={};integers=set();section='obj';name=None
    for line in path.read_text().splitlines():
        s=line.strip()
        if not s or s in {'min','obj:'}:continue
        if s in {'s.t.','bounds','binary','end'}:section=s;continue
        if section in {'obj','s.t.'}:
            if s.endswith(':'):
                assert section=='s.t.';name=s[:-1];rows[name]=dict(terms={});continue
            t=s.split()
            if t[0] in {'<=','>=','='}:
                rows[name].update(rhs=float(t[1]),sense={'<=':'<','>=':'>','=':'='}[t[0]])
            else:
                assert len(t)==2;tgt=obj if section=='obj' else rows[name]['terms'];assert t[1] not in tgt;tgt[t[1]]=float(t[0])
        elif section=='bounds':
            t=s.split();assert len(t)==5 and t[1]==t[3]=='<='
            lo,hi=float(t[0]),float(t[4]);bounds[t[2]]=(lo if math.isfinite(lo) else None,hi if math.isfinite(hi) else None)
        elif section=='binary':assert len(s.split())==1;integers.add(s)
        else:raise AssertionError(section)
    names={v['name']:j for j,v in enumerate(data['variables'])}
    assert set(bounds)==set(names) and len(rows)==len(data['rows']) and data['sense']==1 and data['constant']==0
    for v in data['variables']:
        lo,hi=bounds[v['name']]
        effective_lo=None if lo is None or lo<=-1e20 else lo
        effective_hi=None if hi is None or hi>=1e20 else hi
        assert (effective_lo,effective_hi)==(v['lb'],v['ub']),v['name']
        assert v['type']==('B' if v['name'] in integers else 'C') and obj.get(v['name'],0.)==v['obj']
    for r in data['rows']:
        s=rows[r['name']];assert s['rhs']==r['rhs'] and s['sense']==r['sense']
        assert {names[n]:a for n,a in s['terms'].items() if a}=={j:a for j,a in r['terms'] if a}
    return bounds


def family(row,vs):
    n=row['name'];terms={vs[j]['name']:a for j,a in row['terms']}
    if n.startswith(('gh_total(','gen_menor_demanda(')):
        assert abs(terms['g'+n[n.index('('):]])==1.;return 'MW'
    if re.match(r'a\d+_g4h_def\(',n):
        assert abs(next(a for v,a in terms.items() if re.fullmatch(r'g\d+\(\d+\)',v)))==1.;return 'MW'
    if re.match(r'a\d+_salto_grande_tangente_\d+\(',n):
        assert abs(next(a for v,a in terms.items() if '_z4h(' in v))==1.;return 'MW'
    if re.match(r'a\d+_balance\(',n):
        assert {abs(a) for v,a in terms.items() if '_v4h(' in v}=={1.};return 'm3'
    if re.match(r'a\d+_activacion_[1-4]\(',n):
        assert next(a for v,a in terms.items() if '_v4h(' in v)==-1.;return 'm3'
    return None


def compile_rows(data):
    result=[]
    for r in data['rows']:
        values=[Q(a) for _,a in r['terms']]+[Q(r['rhs'])];e=max(q.denominator.bit_length()-1 for q in values)
        ints=[q.numerator<<(e-(q.denominator.bit_length()-1)) for q in values]
        result.append((r,[(j,a) for (j,_),a in zip(r['terms'],ints[:-1])],ints[-1],e,family(r,data['variables'])))
    return result


def check_point(data,compiled,point):
    rounded=[float(round(float(x))) if v['type']!='C' else float(x) for x,v in zip(point,data['variables'])]
    ratios=[x.as_integer_ratio() for x in rounded];ex=max(d.bit_length()-1 for _,d in ratios)
    xs=[n<<(ex-(d.bit_length()-1)) for n,d in ratios]
    maxima={'MW':(0,0),'m3':(0,0)};aux=Q(0);rowmax=(0,0)
    for row,terms,b,e,group in compiled:
        r=sum(a*xs[j] for j,a in terms)-(b<<ex)
        v=abs(r) if row['sense']=='=' else max(0,r if row['sense']=='<' else -r)
        er=e+ex
        if (v<<rowmax[1])>(rowmax[0]<<er):rowmax=(v,er)
        if group:
            old=maxima[group]
            if (v<<old[1])>(old[0]<<er):maxima[group]=(v,er)
        elif v:
            aux=max(aux,Q(v,1<<er)/(Q(1e-8)*max(Q(1),abs(Q(row['rhs'])))))
    physical=[max(Q(maxima['MW'][0],1<<maxima['MW'][1])/Q(p),Q(maxima['m3'][0],1<<maxima['m3'][1])/Q(w)) for p,w in [(.01,100.),(.1,1000.),(1.,10000.)]]
    bound=Q(0);cost=Q(data['constant'])
    for x,v in zip(rounded,data['variables']):
        if v['lb'] is not None:bound=max(bound,Q(v['lb'])-Q(x))
        if v['ub'] is not None:bound=max(bound,Q(x)-Q(v['ub']))
        if v['obj']:cost+=Q(v['obj'])*Q(x)
    return dict(physical=list(map(str,physical)),aux=str(aux),objective=str(cost),bounds_pass=bound<=Q(1e-6),
                max_bound=float(bound),max_residual=float(Q(rowmax[0],1<<rowmax[1])))


def rational_point(data,point):
    q=list(map(Q,point));cost=Q(data['constant'])
    for r in data['rows']:
        d=sum(Q(a)*q[j] for j,a in r['terms'])-Q(r['rhs'])
        assert d==0 if r['sense']=='=' else d<=0 if r['sense']=='<' else d>=0
    for v,x in zip(data['variables'],q):
        assert v['lb'] is None or x>=Q(v['lb'])
        assert v['ub'] is None or x<=Q(v['ub'])
        assert v['type']=='C' or x.denominator==1
        cost+=Q(v['obj'])*x
    return cost


def lp_certificate(data,folder):
    lp=read(folder/'lp.json.gz');ci=[j for j,v in enumerate(data['variables']) if v['type']=='C'];idx={j:i for i,j in enumerate(ci)}
    assert ci==lp['continuous_indices'];z={int(j):Q(x) for j,x in lp['integers'].items()}
    assert set(z)=={j for j,v in enumerate(data['variables']) if v['type']!='C'} and all(x.denominator==1 for x in z.values())
    offset=Q(data['constant'])+sum(Q(data['variables'][j]['obj'])*x for j,x in z.items())
    assert Q(lp['offset'])==offset and list(map(Q,lp['cost']))==[Q(data['variables'][j]['obj']) for j in ci]
    expected=[]
    for r in data['rows']:
        rhs=Q(r['rhs'])-sum(Q(a)*z[j] for j,a in r['terms'] if j in z)
        terms={str(idx[j]):Q(a) for j,a in r['terms'] if j in idx}
        for sign in ([1,-1] if r['sense']=='=' else [1] if r['sense']=='<' else [-1]):expected.append(({j:sign*a for j,a in terms.items()},sign*rhs))
    for j in ci:
        for k,sign in [('lb',-1),('ub',1)]:
            if data['variables'][j][k] is not None:expected.append(({str(idx[j]):Q(sign)},sign*Q(data['variables'][j][k])))
    assert len(expected)==len(lp['rows'])
    for (terms,rhs),r in zip(expected,lp['rows']):assert terms=={j:Q(a) for j,a in r['terms'].items()} and rhs==Q(r['rhs'])
    if not (folder/'certificate.json').exists():return dict(constructed=True,dual_checked=False)
    q=list(map(Q,read(folder/'primal.json')));raw=read(folder/'dual.json');pi={int(j):Q(v) for j,v in (raw or {}).items()}
    assert len(q)==len(ci) and all(0<=j<len(expected) for j in pi)
    primal_ok=all(sum(a*q[int(j)] for j,a in terms.items())<=rhs for terms,rhs in expected)
    reduced=list(map(Q,lp['cost']));lb=offset
    for i,(terms,rhs) in enumerate(expected):
        p=pi.get(i,Q(0));lb+=p*rhs
        for j,a in terms.items():reduced[int(j)]-=p*a
    dual_ok=raw is not None and all(x<=0 for x in pi.values()) and not any(reduced)
    value=offset+sum(Q(c)*x for c,x in zip(lp['cost'],q));stored=read(folder/'certificate.json')
    assert stored['primal_feasible']==primal_ok and stored['dual_feasible']==dual_ok
    assert Q(stored['primal_value_exact'])==value and Q(stored['dual_value_exact'])==lb
    assert stored['optimum_certified']==bool(primal_ok and dual_ok and value==lb)
    return dict(constructed=True,dual_checked=True,optimum_certified=stored['optimum_certified'])


def main():
    design=read(HERE/'design.json');models={};counts=Counter();compiled={};declared_bounds={}
    for n,h in design['sources'].items():assert sha(HERE/n)==h and (HERE/n).read_bytes()==(HERE/('snapshot-'+n)).read_bytes()
    for n,h in read(HERE/'input-hashes-before-mip.json')['files'].items():assert sha(HERE/n)==h,n
    for instance in design['instances']:
        folder=HERE/'inputs'/instance;data=read(folder/'canonical.json.gz');models[instance]=data
        declared_bounds[instance]=source_check(folder/'Base.lp',data);counts['original_lp_imports']+=1;compiled[instance]=compile_rows(data)
        counts['finite_source_bounds_imported_as_infinite']+=sum((hi is not None and hi>=1e20) or (lo is not None and lo<=-1e20) for lo,hi in declared_bounds[instance].values())
        q=read(HERE/'references'/instance/'rational-point.json');u=rational_point(data,q)
        for var,x in zip(data['variables'],map(Q,q)):
            lo,hi=declared_bounds[instance][var['name']]
            assert lo is None or x>=Q(lo)
            assert hi is None or x<=Q(hi)
        assert u==Q(design['references'][instance]['objective_exact'])
        assert Q(design['references'][instance]['objective_cap_exact'])==u+Q(1,100)*max(Q(1),abs(u))
        counts['exact_feasible_references']+=1
        cert=lp_certificate(data,HERE/'references'/instance);counts['reference_lp_certificates_checked']+=1
        prep=read(folder/'preparation.json')
        for policy,p in prep['policies'].items():
            for r,k in zip(data['rows'],p['exponents']):
                alpha=Q(2**k) if k>=0 else Q(1,2**(-k))
                for a in [r['rhs']]+[a for _,a in r['terms']]:assert Q(math.ldexp(a,k))==Q(a)*alpha;counts['exact_product_checks']+=1
    for path in sorted((HERE/'runs').glob('*/run.json')):
        r=read(path)
        if r.get('alias_of'):continue
        if r.get('incompatible'):counts['incompatible_arms']+=1;continue
        instance=r['job']['instance'];data=models[instance];stored=read(path.parent/'checks.json.gz')
        with np.load(path.parent/'candidates.npz',allow_pickle=False) as f:points=f['x']
        assert len(points)==len(r['events'])==len(stored)
        # These unusually large source caps are documented infinity sentinels
        # in Gurobi. Also verify the literal finite caps on every saved point.
        for j,var in enumerate(data['variables']):
            lo,hi=declared_bounds[instance][var['name']]
            if lo is not None and lo<=-1e20:assert np.all(points[:,j]>=lo)
            if hi is not None and hi>=1e20:assert np.all(points[:,j]<=hi)
        for i,(point,s) in enumerate(zip(points,stored)):
            q=check_point(data,compiled[instance],point)
            assert q['physical']==s['physical_ratios_exact'],(path,i)
            assert q['aux']==s['max_auxiliary_budget_ratio_exact'] and q['objective']==s['objective_exact']
            assert q['bounds_pass']==s['bounds_pass'] and q['max_bound']==s['max_bound_residual']
            assert q['max_residual']==s['max_original_row_residual']
            counts['candidate_vectors_checked']+=1
        counts['native_mip_calls']+=1
        print('Replayed',path.parent.name,len(points),flush=True)
    outcomes=read(HERE/'outcomes.json')
    for o in outcomes:
        if o.get('incompatible'):continue
        r=read(HERE/o['source']/'run.json');checks=read(HERE/o['source']/'checks.json.gz')
        cap=Q(design['references'][o['job']['instance']]['objective_cap_exact'])
        for j,s in enumerate(['Demanding','Reference','Permissive']):
            ids=[i for i,c in enumerate(checks) if c['auxiliary_pass'] and c['bounds_pass'] and Q(c['physical_ratios_exact'][j])<=1 and Q(c['objective_exact'])<=cap]
            assert (s in o['first_hit'])==bool(ids)
            if ids:assert o['first_hit'][s]['candidate']==ids[0] and o['first_hit'][s]['work']==r['events'][ids[0]]['work']
        if o.get('alias_of'):
            native=read(HERE/o['alias_of']/'run.json');prep=read(HERE/'inputs'/o['job']['instance']/'preparation.json')
            assert prep['policies'][o['job']['policy']]['exponents']==prep['policies'][native['job']['policy']]['exponents']
        counts['arms_checked']+=1
    if (HERE/'posthoc-design.json').exists():
        post=read(HERE/'posthoc-design.json')
        for key,t in post['queue'].items():
            folder=HERE/'certificates'/key;r=read(folder/'result.json')
            cert=lp_certificate(models[t['instance']],folder);counts['posthoc_lp_models_checked']+=1
            counts['posthoc_exact_optimum_certificates_checked']+=bool(cert.get('optimum_certified'))
            if r['outcome'] in ('optimum_certified','exact_primal_only'):
                q=read(folder/'rational-point.json');u=rational_point(models[t['instance']],q)
                for var,x in zip(models[t['instance']]['variables'],map(Q,q)):
                    lo,hi=declared_bounds[t['instance']][var['name']]
                    assert lo is None or x>=Q(lo)
                    assert hi is None or x<=Q(hi)
                assert u==Q(r['objective_exact']);counts['posthoc_exact_feasible_patterns']+=1
            elif r['outcome']=='infeasible_constant_row':
                assert not r['contradiction']['terms'] and Q(r['contradiction']['rhs'])<0
                assert r['contradiction'] in read(folder/'lp.json.gz')['rows']
                counts['posthoc_constant_infeasibility_proofs']+=1
            else:counts['posthoc_unknown']+=1
    payload=dict(counts=dict(counts),native_solver_calls_in_replay=0,
                 method='Independent original LP grammar parser; per-row integer exponents versus producer global exponent; exact rational full witnesses',
                 limitation='Numerical first hits and rational pattern feasibility are distinct; no MILP optimum certified')
    (HERE/'independent-verification.json').write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps(payload,indent=2),flush=True)


if __name__=='__main__':main()
