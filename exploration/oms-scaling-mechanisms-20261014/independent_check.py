#!/usr/bin/env python3
"""Replay original MPS, exact scaling and all final points without a solver."""
from collections import Counter
from fractions import Fraction as Q
import gzip
import hashlib
import json
import math
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent


def read(p):
    b=Path(p).read_bytes()
    return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)


def mps_check(path,data):
    section=None;rs={};cs={};rhs={};bounds={};integer=False;types={};obj=None
    for line in path.read_text().splitlines():
        if not line.strip() or line.startswith('*'):continue
        t=line.split()
        if not line[0].isspace():
            section=t[0];assert section in {'NAME','ROWS','COLUMNS','RHS','BOUNDS','ENDATA'}
            continue
        if section=='ROWS':
            if t[0]=='N':assert obj is None;obj=t[1]
            else:rs[t[1]]=t[0]
        elif section=='COLUMNS':
            if t[1]=="'MARKER'":integer=t[2]=="'INTORG'";continue
            c=cs.setdefault(t[0],{});types[t[0]]='I' if integer else 'C'
            for j in range(1,len(t),2):
                assert t[j] not in c;c[t[j]]=float(t[j+1])
        elif section=='RHS':
            for j in range(1,len(t),2):assert t[j] not in rhs;rhs[t[j]]=float(t[j+1])
        elif section=='BOUNDS':
            kind,_,n=t[:3];lo,hi=bounds.get(n,(0.,None));v=float(t[3]) if len(t)==4 else None
            if kind in {'LO','LI'}:lo=v
            elif kind in {'UP','UI'}:hi=v
            elif kind=='FX':lo=hi=v
            elif kind=='FR':lo=hi=None
            elif kind=='MI':lo=None
            elif kind=='PL':hi=None
            elif kind=='BV':lo,hi=0.,1.;types[n]='B'
            else:raise AssertionError(kind)
            bounds[n]=(lo,hi)
        else:raise AssertionError(section)
    vs=data['variables'];index={v['name']:j for j,v in enumerate(vs)}
    assert set(cs)==set(index) and set(rs)=={r['name'] for r in data['rows']}
    assert data['constant']==-rhs.get(obj,0.) and data['sense']==1
    actual={n:{} for n in rs}
    for v in vs:
        n=v['name'];assert cs[n].get(obj,0.)==v['obj']
        assert bounds.get(n,(0.,None))==(v['lb'],v['ub']) and types[n]==v['type']
        for r,a in cs[n].items():
            if r!=obj and a:actual[r][index[n]]=a
    for r in data['rows']:
        assert rs[r['name']]=={'<':'L','>':'G','=':'E'}[r['sense']]
        assert rhs.get(r['name'],0.)==r['rhs'] and actual[r['name']]==dict(r['terms'])


def units(row,vs):
    n=row['name'];terms={vs[j]['name']:a for j,a in row['terms']}
    if n.startswith(('gh_total(','gen_menor_demanda(')):
        return 'MW',abs(terms['g'+n[n.index('('):]])
    if re.match(r'a\d+_g4h_def\(',n):
        agent=n[1:n.index('_')];time=n[n.index('('):]
        return 'MW',abs(terms['g'+agent+time])
    if re.match(r'a\d+_salto_grande_tangente_\d+\(',n):
        agent=n[:n.index('_')];time=n[n.index('('):]
        return 'MW',abs(terms[agent+'_z4h'+time])
    if re.match(r'a\d+_balance\(',n):
        agent=n[:n.index('_')];vals=[abs(a) for name,a in terms.items() if name.startswith(agent+'_v4h(')]
        assert vals and len(set(vals))==1
        return 'm3',vals[0]
    return None


def exact_point(data,point,ex):
    xp=list(map(Q,point));maxrow=Q(0);maxexport=Q(0);worst='';ratios=[Q(0)]*3
    budgets=[(.01,100.),(.1,1000.),(1.,10000.)]
    for row,k in zip(data['rows'],ex):
        r=sum(Q(a)*xp[j] for j,a in row['terms'])-Q(row['rhs'])
        violation=abs(r) if row['sense']=='=' else max(Q(0),r if row['sense']=='<' else -r)
        if violation>maxrow:maxrow=violation;worst=row['name']
        alpha=Q(2**k) if k>=0 else Q(1,2**(-k));maxexport=max(maxexport,alpha*violation)
        spec=units(row,data['variables'])
        if spec:
            for j,(p,w) in enumerate(budgets):ratios[j]=max(ratios[j],violation/Q((p if spec[0]=='MW' else w)*spec[1]))
    bound=max([Q(0)]+[Q(v['lb'])-x for v,x in zip(data['variables'],xp) if v['lb'] is not None]
                      +[x-Q(v['ub']) for v,x in zip(data['variables'],xp) if v['ub'] is not None])
    integer=max([Q(0)]+[abs(x-round(x)) for x,v in zip(xp,data['variables']) if v['type']!='C'])
    objective=sum(Q(v['obj'])*x for x,v in zip(xp,data['variables']))+Q(data['constant'])
    return dict(exact_rational_point=True,max_row=float(maxrow),worst_row=worst,max_exported=float(maxexport),
                max_bound=float(bound),max_integer=float(integer),objective=float(objective),
                physical_ratios=list(map(float,ratios)))


def main():
    models={};preparations={};counts=Counter();contract_rows=[]
    for p in sorted((HERE/'inputs').glob('*/canonical.json.gz')):
        data=read(p);prep=read(p.parent/'preparation.json');instance=p.parent.name
        mps_check(p.parent/'Base.mps',data);counts['independent_mps_imports']+=1
        models[instance]=data;preparations[instance]=prep
        assert prep['policy_exponents']['Algebraic']==prep['policy_exponents']['Structural']
        counts['identical_algebraic_structural_models']+=1
        for policy,ex in prep['policy_exponents'].items():
            for row,k in zip(data['rows'],ex):
                alpha=Q(2**k) if k>=0 else Q(1,2**(-k))
                for a in [row['rhs']]+[a for _,a in row['terms']]:
                    assert Q(math.ldexp(a,k))==Q(a)*alpha;counts['exact_product_checks']+=1
        for scenario,(p,v) in zip(['Demanding','Reference','Permissive'],[(.01,100.),(.1,1000.),(1.,10000.)]):
            total=0;admissible=0
            for row,k in zip(data['rows'],prep['policy_exponents']['Structural']):
                spec=units(row,data['variables'])
                if spec:
                    total+=1;delta=(p if spec[0]=='MW' else v)*spec[1]
                    alpha=Q(2**k) if k>=0 else Q(1,2**(-k))
                    admissible+=alpha*Q(delta)>=Q(1e-6)
            assert total==admissible>0
            assert prep['contracts'][scenario]['changed_rows']==0
            contract_rows.append(dict(instance=instance,scenario=scenario,physical_rows=total,
                                      admissible=admissible,changed=0,incompatible=0))
    checks=[];native=0
    for p in sorted((HERE/'runs').glob('*/*.json.gz')):
        if '-diagnostic' in p.name or '-presolved' in p.name:continue
        r=read(p);j=r['job'];data=models[j['instance']];ex=preparations[j['instance']]['policy_exponents'][j['policy']]
        native+=not bool(r['alias_of'])
        if r['alias_of']:
            source=read(HERE/r['alias_of']);assert source['point']==r['point'] and source['work']==r['work']
            assert ex==preparations[j['instance']]['policy_exponents'][source['job']['policy']]
        if r['point'] is None:checks.append(dict(path=str(p.relative_to(HERE)),point=None));continue
        v=exact_point(data,r['point'],ex);stored=r['verification']
        # Original check summed rounded products; this replay multiplies exactly.
        # Record rather than hide discrepancies from cancellation at large RHS.
        v['float_product_check_difference']=v['max_row']-stored['max_original_row_residual']
        assert abs(v['objective']-r['objective'])<=1e-6*max(1.,abs(v['objective']))
        assert v['max_integer']==stored['max_integrality_violation']
        checks.append(dict(path=str(p.relative_to(HERE)),**j,status=r['status'],**v));counts['exact_final_points']+=1
    counts['arms']=len(checks);counts['native_mip_calls']=native
    for name in ('PROTOCOL.md','study.py'):
        assert (HERE/name).read_bytes()==(HERE/('snapshot-'+name)).read_bytes()
    witness=None
    if (HERE/'exact-witness/rational-point.json').exists():
        q=list(map(Q,read(HERE/'exact-witness/rational-point.json')));data=models['instance001']
        assert len(q)==len(data['variables'])
        for row in data['rows']:
            d=sum(Q(a)*q[j] for j,a in row['terms'])-Q(row['rhs'])
            assert d==0 if row['sense']=='=' else d<=0 if row['sense']=='<' else d>=0
        for x,var in zip(q,data['variables']):
            assert var['lb'] is None or x>=Q(var['lb'])
            assert var['ub'] is None or x<=Q(var['ub'])
            assert var['type']=='C' or x.denominator==1
        objective=Q(data['constant'])+sum(Q(v['obj'])*x for v,x in zip(data['variables'],q))
        result=read(HERE/'exact-witness/result.json')
        assert objective<=0 and objective==Q(result['objective_exact'])
        witness=dict(exact_feasible=True,objective_exact=str(objective),all_rows_bounds_and_integrality_verified=True)
    payload=dict(counts=dict(counts),contracts=contract_rows,point_checks=checks,exact_witness=witness,
                 replay='Python standard library only; no solver import or subprocess',
                 exact_feasibility_claim='Residuals evaluated rationally; nonzero residual is not an exact feasible certificate')
    (HERE/'independent-verification.json').write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps(dict(counts),indent=2))


if __name__=='__main__':main()
