#!/usr/bin/env python3
"""Cofactor inverses, Farkas sums and direct-prefix storage replay, no solver."""
import argparse
from fractions import Fraction as Q
import gzip
import hashlib
from io import BytesIO
from itertools import product
import json
from pathlib import Path
import zipfile
import numpy as np

HERE=Path(__file__).resolve().parent;PREFIX='exploration/oms-precision-work-20261015/'


def det(a):
    if len(a)==1:return Q(a[0][0])
    return sum((-1)**j*Q(x)*det([[Q(v) for k,v in enumerate(row) if k!=j] for row in a[1:]]) for j,x in enumerate(a[0]))


def adj_inverse(a):
    n=len(a);d=det(a);assert d
    result=[[Q((-1)**(i+j))*det([[Q(v) for k,v in enumerate(row) if k!=i] for l,row in enumerate(a) if l!=j])/d for j in range(n)] for i in range(n)]
    assert all(sum(Q(a[i][k])*result[k][j] for k in range(n))==int(i==j) for i in range(n) for j in range(n))
    return result


def kappa(a,inv,alpha):
    largest=max(sum(abs(Q(v))*x for v in row) for row,x in zip(a,alpha))
    invlargest=max(sum(abs(v)/x for v,x in zip(row,alpha)) for row in inv)
    return largest*invlargest


def main():
    p=argparse.ArgumentParser();p.add_argument('--parent',type=Path,required=True);args=p.parse_args()
    design=json.loads((HERE/'design.json').read_text())
    assert hashlib.sha256(args.parent.read_bytes()).hexdigest()==design['parent_archive_sha256']
    math=json.loads((HERE/'mathematical-checks.json').read_text())
    for r in math['random_cases']:
        a=[[Q(v) for v in row] for row in r['A']];inv=adj_inverse(a);lo=list(map(Q,r['lower']));hi=list(map(Q,r['upper']))
        rs=[sum(abs(v) for v in row) for row in a];t=max(x*y for x,y in zip(lo,rs));alpha=[min(h,t/s) for h,s in zip(hi,rs)]
        assert kappa(a,inv,alpha)==Q(r['continuous_minimum'])
        options=[]
        for l,h in zip(lo,hi):options.append([Q(2**k) if k>=0 else Q(1,2**-k) for k in range(-10,11) if l<=(Q(2**k) if k>=0 else Q(1,2**-k))<=h])
        best=min(kappa(a,inv,list(xs)) for xs in product(*options));assert best==Q(r['dyadic_minimum'])
        approx=list(map(Q,r['approximate_alpha']));assert all(l<=x<=h for l,x,h in zip(lo,approx,hi))
        assert kappa(a,inv,approx)==Q(r['approximate_value'])<=2*best
    case=math['conflicting_condition_and_accuracy'];rows={r['name']:r for r in case['joint_lp']['rows']}
    expected={'row_norm_0':([-1,0,0],-2),'max_factor_0':([-1,0,1],0),'min_factor_0':([1,0,-1],0),
        'row_norm_1':([0,-1,0],-1),'max_factor_1':([0,-1,Q(1,128)],0),'min_factor_1':([0,1,-1],0),
        'kappa_0':([1,1,0],10),'forward_0':([1,1,-2],0),'kappa_1':([0,1,0],10),'forward_1':([0,1,-Q(1,128)],0)}
    assert set(rows)==set(expected)
    for n,(a,b) in expected.items():assert list(map(Q,rows[n]['coeff']))==a and Q(rows[n]['rhs'])==b
    mu={n:Q(v) for n,v in case['exact_farkas_certificate']['weights'].items()};assert all(v>=0 for v in mu.values())
    assert all(sum(mu[n]*Q(rows[n]['coeff'][j]) for n in mu)==0 for j in range(3))
    assert sum(mu[n]*Q(rows[n]['rhs']) for n in mu)==-119
    data=json.loads((HERE/'storage-audit.json').read_text());saved={r['source']:r for r in data['runs']};count=0;assignment_count=0
    with zipfile.ZipFile(args.parent) as z:
        post=json.loads(z.read(PREFIX+'posthoc-design.json'))
        outcomes=json.loads(z.read(PREFIX+'outcomes.json'))
        jobs={(o['job']['instance'],o['job']['policy'],o['job']['seed']):o for o in outcomes}
        for instance in ['instance001','instance022','instance046']:
            model=json.loads(gzip.decompress(z.read(PREFIX+'inputs/'+instance+'/canonical.json.gz')))
            names={v['name']:j for j,v in enumerate(model['variables'])};rs={r['name']:r for r in model['rows']};n=360
            indices=[[names[f'a1_{v}4h({t})'] for v in ['v','x','y']] for t in range(1,n+1)]
            rhs=[]
            for t in range(1,n+1):
                row=rs[f'a1_balance({t})'];expected={names[f'a1_v4h({t})']:1,names[f'a1_x4h({t})']:3600,names[f'a1_y4h({t})']:3600}
                if t>1:expected[names[f'a1_v4h({t-1})']]=-1
                assert dict(row['terms'])==expected and float(row['rhs']).is_integer();rhs.append(int(row['rhs']))
            summary=next(r for r in data['original_models'] if r['instance']==instance)
            assert summary['minimum_row_scaled_kappa_infinity']==2*n-1 and summary['base_kappa_infinity']==2*n
            # Also link every parent first-hit claim to the actual integer
            # pattern certified, rather than trusting its cache label alone.
            point_cache={};lp_cache={}
            for assignment in post['assignments']:
                job=assignment['job']
                if job['instance']!=instance:continue
                o=jobs[(instance,job['policy'],job['seed'])]
                assert assignment['candidate']==o['first_hit'][assignment['scenario']]['candidate']
                source=o['source']
                if source not in point_cache:
                    with np.load(BytesIO(z.read(PREFIX+source+'/candidates.npz')),allow_pickle=False) as f:point_cache[source]=f['x']
                point=point_cache[source][assignment['candidate']]
                actual={str(j):str(round(float(point[j]))) for j,var in enumerate(model['variables']) if var['type']!='C'}
                key=assignment['pattern_key'];assert actual==post['queue'][key]['pattern']
                if key not in lp_cache:
                    lp=json.loads(gzip.decompress(z.read(PREFIX+'certificates/'+key+'/lp.json.gz')))
                    witness=json.loads(z.read(PREFIX+'certificates/'+key+'/rational-point.json'))
                    lp_cache[key]=(lp,witness)
                lp,witness=lp_cache[key]
                assert {j:Q(x) for j,x in lp['integers'].items()}=={j:Q(x) for j,x in actual.items()}
                assert all(Q(witness[int(j)])==Q(x) for j,x in actual.items());assignment_count+=1
            for path,r in saved.items():
                if r['instance']!=instance:continue
                raw=z.read(PREFIX+path);assert hashlib.sha256(raw).hexdigest()==r['source_npz_sha256']
                with np.load(BytesIO(raw),allow_pickle=False) as f:points=f['x']
                maximum=Q(0)
                for point in points:
                    values=[[float(point[j]).as_integer_ratio() for j in row] for row in indices]
                    e=max(d.bit_length()-1 for row in values for num,d in row)
                    outflow=0;right=0;peak=0
                    for row,b in zip(values,rhs):
                        volume,x,y=[num<<(e-(den.bit_length()-1)) for num,den in row]
                        outflow+=3600*(x+y);right+=b<<e
                        peak=max(peak,abs(volume+outflow-right))
                    maximum=max(maximum,Q(peak,2**e));count+=1
                assert maximum==Q(r['max_cumulative_water_error_exact'])
    assert count==1093
    result=dict(cofactor_inverse_cases=24,exact_farkas_combined_rhs='-119',candidate_prefix_errors_replayed=count,
                source_blocks=3,parent_first_hit_pattern_assignments_checked=assignment_count,
                native_optimizer_calls=0,parent_archive_sha256=design['parent_archive_sha256'])
    (HERE/'independent-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
