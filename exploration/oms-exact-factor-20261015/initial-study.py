#!/usr/bin/env python3
"""Retrospective factor decisions only; never imports an optimizer."""
from collections import Counter
from fractions import Fraction as Q
from pathlib import Path
import gzip
import hashlib
import json
import math
import re
import statistics
import time
from factors import select,score,interval,rounded_center,defect,export_aware,oddparts

HERE=Path(__file__).resolve().parent
SCENARIOS={'Demanding':(.01,100.),'Reference':(.1,1000.),'Permissive':(1.,10000.)}
EPS=Q(1e-6)


def dump(p,x):
    raw=(json.dumps(x,indent=2,allow_nan=False)+'\n').encode()
    p.write_bytes(gzip.compress(raw,mtime=0) if p.suffix=='.gz' else raw)


def units(r,vs):
    n=r['name'];a={vs[j]['name']:Q(v) for j,v in r['terms']}
    if n.startswith(('gh_total(','gen_menor_demanda(')):
        return 'MW',abs(a['g'+n[n.index('('):]])
    agent=n.split('_')[0];t=n[n.index('('):] if '(' in n else ''
    if re.fullmatch(r'a\d+_g4h_def\(\d+\)',n):return 'MW',abs(a['g'+agent[1:]+t])
    if re.fullmatch(r'a\d+_salto_grande_tangente_\d+\(\d+\)',n):return 'MW',abs(a[agent+'_z4h'+t])
    if re.fullmatch(r'a\d+_balance\(\d+\)',n):
        coeff=[abs(v) for key,v in a.items() if key.startswith(agent+'_v4h(')]
        assert len(set(coeff))==1
        return 'm3',coeff[0]
    if re.fullmatch(r'a\d+_activacion_[1-4]\(\d+\)',n):
        assert r['sense']=='<' and len(a)==2 and a[agent+'_v4h'+t]==-1
        return 'm3',Q(1)
    return None


def pack(alpha,r,vs,m,M,E,delta):
    if alpha is None:return dict(alpha_hex=None)
    f=float(alpha);rho=defect(r,vs,alpha)
    zs=[Q(a) for _,a in r['terms']]+[Q(r['rhs'])]
    exact=all(Q(f*float(z))==alpha*z for z in zs)
    bound=None if rho is None else EPS/alpha+E+rho
    return dict(alpha_hex=f.hex(),score_exact=str(score(alpha,m,M)),products_exact=exact,
        defect_exact=None if rho is None else str(rho),bound_exact=None if bound is None else str(bound),
        contract_pass=None if delta is None else bound is not None and bound<=delta)


def main():
    design=json.loads((HERE/'design.json').read_text())
    sha=lambda b:hashlib.sha256(b).hexdigest()
    assert sha((HERE/'PROTOCOL.md').read_bytes())==design['protocol_sha256']
    for name,h in design['inputs'].items():assert sha((HERE/name).read_bytes())==h
    sources={n:sha((HERE/n).read_bytes()) for n in ['factors.py','study.py','test_factors.py']}
    sourcefile=HERE/'sources-before-results.json'
    if sourcefile.exists():assert json.loads(sourcefile.read_text())==sources,'source drift'
    else:
        dump(sourcefile,sources)
        for n in sources:(HERE/('snapshot-'+n)).write_bytes((HERE/n).read_bytes())
    records=[];stress=[];counts=Counter();profiles=Counter();start=time.perf_counter()
    for name in design['instances']:
        data=json.loads(gzip.decompress((HERE/'inputs'/name/'canonical.json.gz').read_bytes()))
        vs=data['variables'];profiles[('variables',len(vs))]+=1
        print(name,'rows',len(data['rows']),'integer variables',sum(v['type']!='C' for v in vs),flush=True)
        for i,r in enumerate(data['rows']):
            spec=units(r,vs);zs=tuple(Q(a) for _,a in r['terms'] if a)+(Q(r['rhs']),)
            maxodd=max(oddparts(z)[0] for z in zs if z);counts['rows']+=1
            counts['only_power_two_exact_possible']+=((2**53-1)//maxodd==1)
            settings=[('Unbudgeted',None)]
            if spec:
                counts['physical_rows']+=1
                settings.extend((s,Q(p if spec[0]=='MW' else w)*spec[1]) for s,(p,w) in SCENARIOS.items())
            for scenario,delta in settings:
                m,M,lo,hi,E=interval(r,vs,delta)
                one=select(zs,m,M,lo,hi,True);exact=select(zs,m,M,lo,hi)
                rounded=rounded_center(m,M,lo,hi)
                aware=None if delta is None else export_aware(r,vs,delta)
                record=dict(instance=name,row=i,name=r['name'],scenario=scenario,
                    unit=None if spec is None else spec[0],max_odd_significand=str(maxodd),
                    lower_exact=str(lo),upper_exact=str(hi),reserve_exact=str(E),
                    delta_exact=None if delta is None else str(delta),
                    policies={p:pack(a,r,vs,m,M,E,delta) for p,a in [('Pow2',one),('Exact',exact),('Rounded',rounded)]})
                if delta is not None:record['policies']['Aware']=pack(aware,r,vs,m,M,E,delta)
                records.append(record)
            if spec:
                m,M,_,H,E=interval(r,vs)
                for theta in map(Q,design['theta']):
                    delta=E+EPS/(theta*H)
                    _,_,lo,hi,_=interval(r,vs,delta)
                    one=select(zs,m,M,lo,hi,True);exact=select(zs,m,M,lo,hi)
                    # This stress only compares exact sets, not rounded-product policies.
                    stress.append(dict(instance=name,row=i,theta=str(theta),
                        pow2=None if one is None else float(one).hex(),
                        exact=None if exact is None else float(exact).hex()))
        print(name,'completed; selection cache',select.cache_info(),flush=True)
    elapsed=time.perf_counter()-start
    dump(HERE/'decisions.json.gz',records);dump(HERE/'stress.json.gz',stress)
    dump(HERE/'selection-timing.json',dict(seconds=elapsed,scope='selection, metadata and exact export checks; not solver work',
        cache_info=str(select.cache_info()),optimizer_calls=0))
    summary=summarize(records,stress,counts)
    dump(HERE/'summary.json',summary)
    print(json.dumps(summary,indent=2),flush=True)


def summarize(records,stress,counts):
    groups={}
    for scenario in ['Unbudgeted',*SCENARIOS]:
        rows=[r for r in records if r['scenario']==scenario];g=dict(rows=len(rows))
        for policy in ['Pow2','Exact','Rounded']+([] if scenario=='Unbudgeted' else ['Aware']):
            ds=[r['policies'][policy] for r in rows];ok=[d for d in ds if d['alpha_hex'] is not None]
            g[policy]=dict(admissible=len(ok),abstentions=len(ds)-len(ok),
                non_power_two=sum(oddparts(Q(float.fromhex(d['alpha_hex'])))[0]!=1 for d in ok),
                nonzero_export_defects=sum(d['defect_exact'] not in ('0',None) for d in ok),
                unbounded_export_defects=sum(d['defect_exact'] is None for d in ok),
                contract_pass=None if scenario=='Unbudgeted' else sum(d.get('contract_pass',False) for d in ok))
        ratios=[];changed=0
        for r in rows:
            one,exact=r['policies']['Pow2'],r['policies']['Exact']
            if one['alpha_hex'] is not None and exact['alpha_hex'] is not None:
                changed+=one['alpha_hex']!=exact['alpha_hex']
                ratios.append(float(Q(exact['score_exact'])/Q(one['score_exact'])))
        g.update(exact_changed_from_pow2=changed,exact_center_score_ratio_median=statistics.median(ratios),
            exact_center_score_ratio_min=min(ratios),
            rounded_contract_failures=None if scenario=='Unbudgeted' else sum(not r['policies']['Rounded'].get('contract_pass',False) for r in rows),
            aware_differs_from_exact=None if scenario=='Unbudgeted' else sum(r['policies']['Aware']['alpha_hex']!=r['policies']['Exact']['alpha_hex'] for r in rows))
        if scenario!='Unbudgeted':
            finite=[float(Q(r['policies']['Rounded']['defect_exact'])/(Q(r['delta_exact'])-Q(r['reserve_exact'])))
                    for r in rows if r['policies']['Rounded'].get('defect_exact') is not None]
            g['rounded_max_export_defect_over_remaining_budget']=max(finite,default=0.)
        groups[scenario]=g
    ss={}
    for theta in sorted({r['theta'] for r in stress},key=Q):
        rows=[r for r in stress if r['theta']==theta]
        ss[theta]=dict(rows=len(rows),pow2_admissible=sum(r['pow2'] is not None for r in rows),
            exact_admissible=sum(r['exact'] is not None for r in rows),
            exact_rescues=sum(r['pow2'] is None and r['exact'] is not None for r in rows))
    return dict(counts=dict(counts),scenarios=groups,constructed_stress=ss,native_optimizer_calls=0,
        performance_claim=False,novelty_claim=False)


if __name__=='__main__':main()
