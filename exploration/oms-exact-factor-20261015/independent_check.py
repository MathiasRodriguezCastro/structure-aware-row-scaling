#!/usr/bin/env python3
"""Independent replay; no import of the producer or a numerical optimizer.

Checks full-grid optimality by excluding any factor with a strictly better
objective, rather than rerunning the producer's candidate minimizer.
"""
from collections import Counter
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
import gzip
import hashlib
import json
import math

HERE=Path(__file__).resolve().parent


def power(k):return F(2)**k
def log2floor(x):
    k=x.numerator.bit_length()-x.denominator.bit_length()
    return k-(power(k)>x)
def ceil(x):return -((-x.numerator)//x.denominator)
def odd(x):
    n=abs(x.numerator);p=-(x.denominator.bit_length()-1)
    while n%2==0:n//=2;p+=1
    return n,p


@lru_cache(maxsize=100000)
def exists(zs,lo,hi,strict_lo=False,strict_hi=False,powers=False):
    if lo>hi or (lo==hi and (strict_lo or strict_hi)):return False
    entries=[odd(z) for z in zs if z]
    mmax=1 if powers else min(((1<<53)-1)//m for m,p in entries)
    lowexp=max([-1074]+[-1074-p for _,p in entries])
    # A safe exponent bracket; at most 53 extra exponents over a power grid.
    lowexp=max(lowexp,log2floor(lo/F(mmax)))
    highexp=min(1023,log2floor(hi))
    for k in range(lowexp,highexp+1):
        unit=power(k);left=lo/unit;right=hi/unit
        l=ceil(left);h=right.numerator//right.denominator
        if strict_lo and F(l)==left:l+=1
        if strict_hi and F(h)==right:h-=1
        h=min(h,mmax);l=max(l,1)
        if not l%2:l+=1
        if l>h:continue
        # The smallest candidate suffices for upper exponent restrictions.
        factor=l*unit
        if k+l.bit_length()-1>1023:continue
        if all(k+p+(l*n).bit_length()-1<=1023 for n,p in entries):
            return True
    return False


def box_defect(row,variables,factor):
    alpha=F(factor);c=F(factor*row['rhs'])/alpha-F(row['rhs'])
    mn=mx=c
    for j,a in row['terms']:
        q=(F(a)*alpha-F(factor*a))/alpha
        if q==0:continue
        v=variables[j]
        if v['lb'] is None or v['ub'] is None:return None
        if q>0:mn+=q*F(v['lb']);mx+=q*F(v['ub'])
        else:mn+=q*F(v['ub']);mx+=q*F(v['lb'])
    return max(abs(mn),abs(mx))


def physical(row,variables):
    name=row['name'];terms={variables[j]['name']:F(a) for j,a in row['terms']}
    if name.startswith('gh_total(') or name.startswith('gen_menor_demanda('):
        suffix=name[name.index('('):]
        return 'MW',abs(terms['g'+suffix])
    if '_balance(' in name:
        vals=[abs(a) for n,a in terms.items() if '_v4h(' in n]
        assert vals and len(set(vals))==1
        return 'm3',vals[0]
    if '_activacion_' in name:return 'm3',F(1)
    if '_g4h_def(' in name:
        agent=name.split('_')[0][1:];suffix=name[name.index('('):]
        return 'MW',abs(terms['g'+agent+suffix])
    if '_salto_grande_tangente_' in name:
        agent=name.split('_')[0];suffix=name[name.index('('):]
        return 'MW',abs(terms[agent+'_z4h'+suffix])
    return None


def main():
    design=json.loads((HERE/'design.json').read_text());models={}
    sha=lambda b:hashlib.sha256(b).hexdigest()
    for n,h in design['inputs'].items():
        raw=(HERE/n).read_bytes();assert sha(raw)==h
        models[Path(n).parts[1]]=json.loads(gzip.decompress(raw))
    data=json.loads(gzip.decompress((HERE/'decisions.json.gz').read_bytes()))
    stress=json.loads(gzip.decompress((HERE/'stress.json.gz').read_bytes()))
    counters=Counter();seen=set();coverage=Counter();only_power=0
    for model in models.values():
        for row in model['rows']:
            z=[F(a) for _,a in row['terms'] if a]+[F(row['rhs'])]
            only_power+=min(((1<<53)-1)//odd(q)[0] for q in z if q)<3
    for rec in data:
        d=models[rec['instance']];row=d['rows'][rec['row']];vs=d['variables']
        assert row['name']==rec['name'];key=(rec['instance'],rec['row'],rec['scenario'])
        assert key not in seen;seen.add(key);coverage[(rec['instance'],rec['scenario'])]+=1
        aa=[abs(F(a)) for _,a in row['terms'] if a];m,M=min(aa),max(aa)
        zs=tuple([F(a) for _,a in row['terms'] if a]+[F(row['rhs'])])
        E=F(1e-9)*sum(abs(F(a)) for j,a in row['terms'] if vs[j]['type']!='C')
        assert str(E)==rec['reserve_exact']
        lo,hi=F(1e-9)/m,F(1e9)/M;delta=None
        if rec['scenario']!='Unbudgeted':
            unit,conversion=physical(row,vs)
            p,w={'Demanding':(.01,100.),'Reference':(.1,1000.),'Permissive':(1.,10000.)}[rec['scenario']]
            delta=F(p if unit=='MW' else w)*conversion
            assert delta==F(rec['delta_exact']) and delta>E
            lo=max(lo,F(1e-6)/(delta-E))
        assert lo==F(rec['lower_exact']) and hi==F(rec['upper_exact'])
        for policy,p in rec['policies'].items():
            h=p['alpha_hex'];a=None if h is None else F(float.fromhex(h))
            if a is None:
                if policy in ('Pow2','Exact'):assert not exists(zs,lo,hi,powers=policy=='Pow2')
                else:assert policy=='Aware'
                continue
            assert lo<=a<=hi
            f=float(a);products=[f*float(z) for z in zs]
            assert all(map(math.isfinite,products))
            exact=all(F(p)==a*z for p,z in zip(products,zs))
            assert exact==p['products_exact'];counters['native_product_checks']+=len(products)
            c=max(a*M,1/(a*m));assert c==F(p['score_exact'])
            rho=box_defect(row,vs,f)
            assert rho==(None if p['defect_exact'] is None else F(p['defect_exact']))
            bound=None if rho is None else F(1e-6)/a+E+rho
            assert bound==(None if p['bound_exact'] is None else F(p['bound_exact']))
            if delta is not None:assert p['contract_pass']==(bound is not None and bound<=delta)
            if policy in ('Pow2','Exact'):
                assert exact and rho==0
                if policy=='Pow2':assert odd(a)[0]==1
                # Any smaller score would require strict inequalities below.
                l,h=max(lo,1/(c*m)),min(hi,c/M)
                assert not exists(zs,l,h,strict_lo=l==1/(c*m),strict_hi=h==c/M,powers=policy=='Pow2')
                # Equal-score alternative can only improve the tie by being larger.
                assert not exists(zs,max(lo,a),min(hi,c/M),strict_lo=True,powers=policy=='Pow2')
                counters['complete_optimality_checks']+=1
            if policy=='Aware':
                assert p['contract_pass']
                for _,v in row['terms']:
                    assert F(1e-9)<=abs(F(f*v))<=F(1e9)
                pool={F(float.fromhex(rec['policies'][key]['alpha_hex'])) for key in ('Pow2','Exact','Rounded')
                      if rec['policies'][key]['alpha_hex'] is not None}
                down=up=float.fromhex(rec['policies']['Rounded']['alpha_hex'])
                for _ in range(8):
                    down=math.nextafter(down,0.);up=math.nextafter(up,math.inf)
                    if math.isfinite(down):pool.add(F(down))
                    if math.isfinite(up):pool.add(F(up))
                for endpoint,is_lower in [(lo,True),(hi,False)]:
                    fendpoint=float(endpoint)
                    if is_lower and F(fendpoint)<endpoint:fendpoint=math.nextafter(fendpoint,math.inf)
                    if not is_lower and F(fendpoint)>endpoint:fendpoint=math.nextafter(fendpoint,0.)
                    pool.add(F(fendpoint))
                viable=[]
                for candidate in pool:
                    if not lo<=candidate<=hi:continue
                    cf=float(candidate)
                    if not all(F(1e-9)<=abs(F(cf*v))<=F(1e9) for _,v in row['terms']):continue
                    error=box_defect(row,vs,cf)
                    if error is None:continue
                    cbound=F(1e-6)/candidate+E+error
                    if cbound<=delta:viable.append((max(candidate*M,1/(candidate*m)),cbound,-candidate,candidate))
                assert viable and min(viable)[-1]==a
                counters['finite_aware_pool_minima_checked']+=1
            counters['factor_decisions_checked']+=1
    for name,d in models.items():
        assert coverage[(name,'Unbudgeted')]==len(d['rows'])
        nr=sum(physical(r,d['variables']) is not None for r in d['rows'])
        for s in ('Demanding','Reference','Permissive'):assert coverage[(name,s)]==nr
    stress_seen=set()
    for rec in stress:
        d=models[rec['instance']];r=d['rows'][rec['row']];vs=d['variables']
        key=(rec['instance'],rec['row'],rec['theta']);assert key not in stress_seen;stress_seen.add(key)
        assert physical(r,vs) is not None
        a=[abs(F(v)) for _,v in r['terms'] if v];m,M=min(a),max(a)
        H=F(1e9)/M;L=max(F(1e-9)/m,F(rec['theta'])*H)
        zs=tuple([F(v) for _,v in r['terms'] if v]+[F(r['rhs'])])
        for policy in ('pow2','exact'):
            s=rec[policy]
            if s is None:assert not exists(zs,L,H,powers=policy=='pow2')
            else:
                alpha=F(float.fromhex(s));assert L<=alpha<=H
                assert all(F(float(alpha)*float(z))==alpha*z for z in zs)
                if policy=='pow2':assert odd(alpha)[0]==1
        counters['stress_interval_checks']+=1
    nphysical=sum(sum(physical(r,d['variables']) is not None for r in d['rows']) for d in models.values())
    assert len(stress)==5*nphysical
    result=dict(counters,models=len(models),rows=sum(len(d['rows']) for d in models.values()),
        physical_rows=nphysical,only_power_two_exact_possible_corrected=only_power,
        full_stored_data_replay=True,optimizer_calls=0)
    (HERE/'independent-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
