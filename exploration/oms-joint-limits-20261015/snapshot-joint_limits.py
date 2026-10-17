#!/usr/bin/env python3
"""Exact boxed row conditioning and a pinned hydro-storage audit. No solver."""
import argparse
from fractions import Fraction as Q
import gzip
import hashlib
from io import BytesIO
from itertools import product
import json
from pathlib import Path
import random
import re
import zipfile

import numpy as np

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PARENT=ROOT/'exploration/oms-precision-work-20261015/precision-work-artifact.zip'
PREFIX='exploration/oms-precision-work-20261015/'


def dump(path,data):path.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def serial(x):
    if isinstance(x,Q):return str(x)
    if isinstance(x,list):return [serial(y) for y in x]
    if isinstance(x,dict):return {k:serial(v) for k,v in x.items()}
    return x


def inverse(a):
    n=len(a);w=[[Q(x) for x in row]+[Q(i==j) for j in range(n)] for i,row in enumerate(a)]
    for j in range(n):
        pivot=next((i for i in range(j,n) if w[i][j]),None)
        if pivot is None:raise ValueError('singular')
        w[j],w[pivot]=w[pivot],w[j];p=w[j][j];w[j]=[x/p for x in w[j]]
        for i in range(n):
            if i!=j:
                p=w[i][j];w[i]=[x-p*y for x,y in zip(w[i],w[j])]
    inv=[row[n:] for row in w]
    assert all(sum(Q(a[i][k])*inv[k][j] for k in range(n))==int(i==j) for i in range(n) for j in range(n))
    return inv


def rowsums(a):return [sum(abs(Q(v)) for v in row) for row in a]


def condition(a,inv,alpha):
    r=rowsums(a)
    return max(x*y for x,y in zip(alpha,r))*max(sum(abs(c)/x for c,x in zip(row,alpha)) for row in inv)


def boxed(a,lower,upper):
    inv=inverse(a);r=rowsums(a)
    assert all(0<l<=h for l,h in zip(lower,upper))
    t=max(l*x for l,x in zip(lower,r));alpha=[min(h,t/x) for h,x in zip(upper,r)]
    minimum=max(sum(abs(c)*max(x,t/h) for c,x,h in zip(row,r,upper)) for row in inv)
    assert all(l<=x<=h for l,x,h in zip(lower,alpha,upper))
    assert condition(a,inv,alpha)==minimum
    skeel=max(sum(abs(c)*x for c,x in zip(row,r)) for row in inv)
    return dict(alpha=alpha,t=t,minimum=minimum,skeel=skeel,inverse=inv)


def power(k):return Q(2**k) if k>=0 else Q(1,2**(-k))
def logfloor(q):
    k=q.numerator.bit_length()-q.denominator.bit_length();return k-1 if power(k)>q else k


def dyadic_approx(a,low,high):
    lo=[power(logfloor(x)+(power(logfloor(x))<x)) for x in low]
    hi=[power(logfloor(x)) for x in high]
    assert all(l<=h for l,h in zip(lo,hi))
    real=boxed(a,lo,hi);alpha=[power(logfloor(x)) for x in real['alpha']]
    value=condition(a,real['inverse'],alpha)
    assert value<2*real['minimum']
    return alpha,value,real


def joint_lp(a,lower,upper,kappa,epsilon,delta):
    """Variables (v_0,...,v_n-1,t), all rows <=. Exact equivalence in the note."""
    inv=inverse(a);n=len(a);r=rowsums(a);rows=[]
    def add(name,coeff,rhs):rows.append(dict(name=name,coeff=list(map(Q,coeff)),rhs=Q(rhs)))
    for i in range(n):
        coeff=[Q(0)]*(n+1);coeff[i]=-1;add('row_norm_'+str(i),coeff,-r[i])
        coeff=[Q(0)]*(n+1);coeff[i]=-1;coeff[-1]=1/upper[i];add('max_factor_'+str(i),coeff,0)
        coeff=[Q(0)]*(n+1);coeff[i]=1;coeff[-1]=-1/lower[i];add('min_factor_'+str(i),coeff,0)
    for j,row in enumerate(inv):
        add('kappa_'+str(j),[abs(x) for x in row]+[0],kappa)
        add('forward_'+str(j),[epsilon*abs(x) for x in row]+[-delta[j]],0)
    return dict(variables=['v'+str(i) for i in range(n)]+['t'],rows=rows)


def lp_point(lp,x):return all(sum(a*v for a,v in zip(r['coeff'],x))<=r['rhs'] for r in lp['rows'])


def farkas(lp,weights):
    rows={r['name']:r for r in lp['rows']};assert all(w>=0 for w in weights.values())
    coeff=[sum(w*rows[n]['coeff'][j] for n,w in weights.items()) for j in range(len(lp['variables']))]
    rhs=sum(w*rows[n]['rhs'] for n,w in weights.items())
    assert not any(coeff) and rhs<0
    return dict(weights=weights,combined_coefficients=coeff,combined_rhs=rhs,infeasibility_certified=True)


def mathematical_checks():
    eps=power(-20);a=[[Q(1),Q(1)],[Q(1),1+eps]]
    near=boxed(a,[Q(1,100000)]*2,[Q(10**9),Q(10**9)/(1+eps)])
    assert near['minimum']==4194307 and near['skeel']==4194307
    ident=boxed([[Q(1),Q(0)],[Q(0),Q(1)]],[Q(1),Q(1,16)],[Q(10**9),Q(1,8)])
    assert ident['minimum']==8 and ident['skeel']==1
    a=[[Q(1),Q(-1)],[Q(0),Q(1)]];inv=inverse(a)
    low=[Q(1),Q(1)];high=[Q(1),Q(128)];c=boxed(a,low,high)
    assert c['alpha']==[1,2] and c['minimum']==3
    accuracy_alpha=[Q(1),Q(128)];minimum_under_accuracy=condition(a,inv,accuracy_alpha)
    assert minimum_under_accuracy==129
    # epsilon normalized to one: |A^-1|/alpha = (129/128,1/128).
    forward=[sum(abs(v)/alpha for v,alpha in zip(row,accuracy_alpha)) for row in inv]
    assert forward[0]<=2 and forward[1]==Q(1,128)
    # The second forward target forces alpha2=128; box forces alpha1=1.
    assert minimum_under_accuracy>10 and all(x.denominator==1 for x in accuracy_alpha)
    lp=joint_lp(a,low,high,Q(10),Q(1),[Q(2),Q(1,128)])
    certificate=farkas(lp,{'row_norm_1':Q(129),'kappa_0':Q(1),'max_factor_0':Q(1),'forward_1':Q(128)})
    assert certificate['combined_rhs']==-119
    relaxed=joint_lp(a,low,high,Q(129),Q(1),[Q(2),Q(1,128)])
    assert lp_point(relaxed,[Q(128),Q(1),Q(128)])
    rng=random.Random(20261015);random_cases=[];gridchecks=0
    while len(random_cases)<24:
        a=[[Q(rng.randint(-3,3)) for _ in range(3)] for _ in range(3)]
        try:inv=inverse(a)
        except ValueError:continue
        kl=[rng.randint(-3,0) for _ in range(3)];kh=[rng.randint(0,3) for _ in range(3)]
        lo=[power(k) for k in kl];hi=[power(k) for k in kh];real=boxed(a,lo,hi)
        exact=min(condition(a,inv,list(alpha)) for alpha in product(*[[power(k) for k in range(l,h+1)] for l,h in zip(kl,kh)]))
        approx,value,_=dyadic_approx(a,lo,hi)
        assert real['minimum']<=exact and value<=2*exact
        count=1
        for l,h in zip(kl,kh):count*=h-l+1
        gridchecks+=count
        # Sample a separate rational grid, containing non-dyadic points.
        for alpha in product(*[[l+(h-l)*Q(k,4) for k in range(5)] for l,h in zip(lo,hi)]):
            assert condition(a,inv,list(alpha))>=real['minimum'];gridchecks+=1
        alpha=[(l+h)/2 for l,h in zip(lo,hi)];t=max(x*r for x,r in zip(alpha,rowsums(a)))
        v=[t/x for x in alpha]+[t]
        delta=[sum(abs(c)/x for c,x in zip(row,alpha)) for row in inv]
        joint=joint_lp(a,lo,hi,condition(a,inv,alpha),Q(1),delta)
        assert lp_point(joint,v)
        random_cases.append(dict(A=a,lower=lo,upper=hi,continuous_minimum=real['minimum'],dyadic_minimum=exact,
                                 approximate_alpha=approx,approximate_value=value))
    return serial(dict(near_collinear=near,individual_contracts_joint_condition=ident,
        conflicting_condition_and_accuracy=dict(A=[[1,-1],[0,1]],lower=[1,1],upper=[1,128],
            condition_only_minimum=3,condition_target=10,normalized_forward_targets=['2','1/128'],
            unique_accuracy_feasible_alpha=[1,128],condition_there=129,all_factors_dyadic=True,
            joint_lp=lp,exact_farkas_certificate=certificate),
        random_cases=random_cases,exact_grid_comparisons=gridchecks))


def data_audit(parent):
    results=[];runrows=[];candidate_count=0
    with zipfile.ZipFile(parent) as z:
        manifest=json.loads(z.read('MANIFEST.json'))
        relevant={r['path']:r['sha256'] for r in manifest['files']}
        def get(name):
            b=z.read(name);assert hashlib.sha256(b).hexdigest()==relevant[name];return b
        for instance in ['instance001','instance022','instance046']:
            raw=get(PREFIX+'inputs/'+instance+'/canonical.json.gz');model=json.loads(gzip.decompress(raw))
            vs=model['variables'];names={v['name']:j for j,v in enumerate(vs)}
            balances=[r for r in model['rows'] if re.fullmatch(r'a1_balance\(\d+\)',r['name'])]
            balances.sort(key=lambda r:int(r['name'].split('(')[1][:-1]));n=len(balances);assert n==360
            terms=[];limits=[]
            for t,r in enumerate(balances,1):
                assert r['sense']=='=' and float(r['rhs']).is_integer()
                vols={int(vs[j]['name'].split('(')[1][:-1]):Q(c) for j,c in r['terms'] if '_v4h(' in vs[j]['name']}
                assert vols==({1:Q(1)} if t==1 else {t-1:Q(-1),t:Q(1)})
                assert all(float(c).is_integer() for j,c in r['terms'])
                terms.append(([(j,int(c)) for j,c in r['terms']],int(r['rhs'])))
                nz=[abs(Q(c)) for j,c in r['terms']];m,M=min(nz),max(nz)
                l=max(Q(1e-6)/100,Q(1e-9)/m);h=Q(1e9)/M
                assert l<=Q(1,2)<=1<=h;limits.append([str(l),str(h)])
                for c in [r['rhs']]+[c for j,c in r['terms']]:assert Q(float(c)/2)==Q(c)/2
            # Closed form inverse L_ij=1(j<=i); verify B L=I exactly.
            for i in range(n):
                for j in range(n):assert int(j<=i)-(int(j<=i-1) if i else 0)==int(i==j)
            result=dict(instance=instance,periods=n,all_original_integers_retained=sum(v['type']!='C' for v in vs),
                subsystem='Only storage columns in water balances, all other columns held fixed; not the full MILP/basis',
                source_canonical_sha256=hashlib.sha256(raw).hexdigest(),storage_matrix='unit lower bidiagonal: diagonal 1, subdiagonal -1',
                base_kappa_infinity=2*n,minimum_row_scaled_kappa_infinity=2*n-1,skeel=2*n-1,
                attaining_dyadic_alpha='1 for first row, 1/2 otherwise',all_authorized_row_contracts_compatible=True,
                demanding_real_intervals=limits,prefix_matrices=[dict(T=t,minimum_kappa=2*t-1) for t in [8,24,360]],
                best_conditional_terminal_error_bound_exact=str(sum(Q(1e-6)/Q(h) for l,h in limits)))
            used=sorted({j for row,b in terms for j,c in row})
            for name in sorted(z.namelist()):
                if not name.startswith(PREFIX+'runs/'+instance+'-') or not name.endswith('/candidates.npz'):continue
                data=get(name)
                with np.load(BytesIO(data),allow_pickle=False) as f:points=f['x']
                maximum=Q(0);local_max=Q(0)
                for point in points:
                    ratios={j:float(point[j]).as_integer_ratio() for j in used}
                    ex=max(d.bit_length()-1 for num,d in ratios.values());xs={j:num<<(ex-(den.bit_length()-1)) for j,(num,den) in ratios.items()}
                    prefix=0;peak=0;local=0
                    for row,b in terms:
                        r=sum(c*xs[j] for j,c in row)-(b<<ex);prefix+=r;peak=max(peak,abs(prefix));local=max(local,abs(r))
                    direct=xs[names['a1_v4h(360)']]+3600*sum(xs[names[f'a1_x4h({t})']]+xs[names[f'a1_y4h({t})']] for t in range(1,n+1))-(sum(b for row,b in terms)<<ex)
                    assert direct==prefix
                    maximum=max(maximum,Q(peak,2**ex));local_max=max(local_max,Q(local,2**ex));candidate_count+=1
                runrows.append(dict(instance=instance,source=name.removeprefix(PREFIX),source_npz_sha256=hashlib.sha256(data).hexdigest(),
                                    candidates=len(points),max_cumulative_water_error_exact=str(maximum),max_cumulative_water_error_m3=float(maximum),
                                    max_single_balance_residual_m3=float(local_max)))
            result['observed_max_cumulative_water_error_m3']=max(r['max_cumulative_water_error_m3'] for r in runrows if r['instance']==instance)
            result['within_demanding_100m3_cumulative_target']=result['observed_max_cumulative_water_error_m3']<=100
            results.append(result)
    assert candidate_count==1093
    return dict(parent_archive_sha256=sha(parent),parent_version=manifest['version'],native_solver_calls=0,
                original_models=results,candidates_checked=candidate_count,runs=runrows)


def main():
    p=argparse.ArgumentParser();p.add_argument('--parent',type=Path,default=PARENT);p.add_argument('--math-only',action='store_true');args=p.parse_args()
    math=mathematical_checks();dump(HERE/'mathematical-checks.json',math)
    print('Exact grid comparisons',math['exact_grid_comparisons'],flush=True)
    if not args.math_only:
        if (HERE/'design.json').exists():
            assert sha(args.parent)==json.loads((HERE/'design.json').read_text())['parent_archive_sha256'],'wrong parent archive'
        data=data_audit(args.parent);dump(HERE/'storage-audit.json',data)
        print('Candidate cumulative errors checked',data['candidates_checked'],flush=True)
        for r in data['original_models']:print(r['instance'],'minimum kappa',r['minimum_row_scaled_kappa_infinity'],'observed max cumulative m3',r['observed_max_cumulative_water_error_m3'],flush=True)


if __name__=='__main__':main()
