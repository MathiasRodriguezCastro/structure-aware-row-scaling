#!/usr/bin/env python3
"""Independent saved-data verifier. No reducer, generator, or solver import."""
import argparse,csv,hashlib,json
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import numpy as np


def check_proof(a,b,proof):
    columns=proof['columns'];assert len(set(columns))==len(columns)
    assert all(a[j]==0 for j in range(len(a)) if j not in columns)
    factor=F(proof['input_normalization']);assert factor>0
    current=list(map(int,proof['canonical_a']));rhs=int(proof['canonical_b'])
    assert all(F(float(a[j]))*factor==v for j,v in zip(columns,current))
    assert F(float(b))*factor//1==rhs
    lo,hi=proof['lo'],proof['hi'];assert lo==[0]*len(columns) and hi==[1]*len(columns)
    for step in proof['steps']:
        assert current==list(map(int,step['a'])) and rhs==int(step['b'])
        v=step['v'];assert len(v)==len(current) and all(isinstance(x,int) for x in v)
        alpha=int(step['alpha']);assert alpha>0
        e=[x-alpha*y for x,y in zip(current,v)]
        assert e==list(map(int,step['residual']))
        lower=sum(min(x*l,x*u) for x,l,u in zip(e,lo,hi))
        upper=sum(max(x*l,x*u) for x,l,u in zip(e,lo,hi))
        assert lower==int(step['lower']) and upper==int(step['upper'])
        k,tau=int(step['k']),int(step['tau'])
        assert k==(rhs-lower)//alpha and tau==rhs-alpha*k
        assert alpha>=upper-tau and alpha>tau-lower
        if step['kind']=='aggregate_bound':
            assert tau>=upper;ar=v;br=k
        else:
            assert step['kind']=='coefficient_compression' and lower<=tau<upper
            beta=int(step['beta']);assert beta>=upper-tau and beta>tau-lower
            ar=[beta*y+x for x,y in zip(e,v)];br=beta*k+tau
        assert ar==list(map(int,step['output_a'])) and br==int(step['output_b'])
        post=F(step['post_factor']);assert post>0
        current=list(map(int,step['post_a']));rhs=int(step['post_b'])
        assert all(x*post==y for x,y in zip(ar,current)) and br*post//1==rhs
    assert current==proof['a'] and rhs==proof['b']
    return current,rhs


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);args=ap.parse_args()
    design=json.loads((args.root/'design.json').read_text());certs=json.loads((args.root/'certificates.json').read_text())
    q=design['local_size'];blocks=design['blocks'];m=design['local_rows']
    states=np.array(list(product([0,1],repeat=q)),np.int64)
    checked={};row_certificates=steps=local_checks=0;input_hashes={}
    for p in sorted(args.root.glob('M*_s*.npz')):
        raw=np.load(p);A,b,c=raw['A'],raw['b'],raw['c'];ai=A.astype(np.int64);ci=c.astype(np.int64)
        assert np.array_equal(A,ai) and np.array_equal(c,ci)
        assert float(np.max(abs(A)))*A.shape[1]<2**62
        cap=int(b[-1]);dp={0:0};good_sets=[]
        for k in range(blocks):
            sl=slice(k*q,k*q+q);rr=slice(k*m,k*m+m)
            good=np.all(states@ai[rr,sl].T<=np.floor(b[rr]).astype(np.int64),axis=1)
            good_sets.append(good);next_dp={}
            for z in states[good]:
                weight=int(z@ai[-1,sl]);value=int(z@ci[sl])
                for old_w,old_v in dp.items():
                    w=old_w+weight
                    if w<=cap:next_dp[w]=max(next_dp.get(w,-10**12),old_v+value)
            dp=next_dp
        opt=max(dp.values());assert opt==int(raw['optimum'])
        checked[p.stem]=(ai,np.floor(b).astype(np.int64),ci,opt)
        input_hashes[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
        for method in design['methods']:
            path=args.root/'exports'/(p.stem+'_'+method+'.npz')
            if not path.exists():continue
            exported=np.load(path);B,rhs=exported['A'],exported['b']
            if method in ['Rounded-direction','Rational-direction','Rounded-all']:
                proof=certs[p.stem+'_'+method];assert len(proof)==len(A)
                for i,item in enumerate(proof):
                    ar,br=check_proof(A[i],b[i],item)
                    if item['exported']:
                        full=[0]*A.shape[1]
                        for j,v in zip(item['columns'],ar):full[j]=v
                        assert all(F(float(x))==y for x,y in zip(B[i],full)) and F(float(rhs[i]))==br
                    else:assert np.array_equal(A[i],B[i]) and b[i]==rhs[i]
                    row_certificates+=1;steps+=len(item['steps'])
            for k in range(blocks):
                sl=slice(k*q,k*q+q);rr=slice(k*m,k*m+m)
                if np.array_equal(B[rr],np.rint(B[rr])):
                    assert float(np.max(abs(B[rr])))*q<2**62
                    got=np.all(states@B[rr,sl].astype(np.int64).T<=np.floor(rhs[rr]),axis=1)
                else:
                    # Exact dyadic row proportionality suffices to transport
                    # all binary assignments without floating activity sums.
                    for index in range(k*m,k*m+m):
                        nonzero=np.flatnonzero(A[index]);j=int(nonzero[0])
                        alpha=F(float(B[index,j]))/F(float(A[index,j]));assert alpha>0
                        assert all(F(float(x))*alpha==F(float(y)) for x,y in zip(A[index],B[index]))
                        assert F(float(b[index]))*alpha==F(float(rhs[index]))
                    got=good_sets[k]
                assert np.array_equal(got,good_sets[k]);local_checks+=1
            # These experiments retain the same integer resource row, possibly
            # with an exact positive scale in the GM control.
            j=int(np.flatnonzero(A[-1])[0]);alpha=F(float(B[-1,j]))/F(float(A[-1,j]))
            assert alpha>0 and all(F(float(x))*alpha==F(float(y)) for x,y in zip(A[-1],B[-1]))
            assert F(float(b[-1]))*alpha==F(float(rhs[-1]))
    counts={};runs=list(csv.DictReader((args.root/'runs.csv').open()))
    for row in runs:
        A,b,c,opt=checked[f"M{row['M']}_s{row['seed']}"];values=json.loads(row['x']);feasible=optimal=False
        if values is not None:
            z=np.rint(values).astype(np.int64)
            feasible=bool(np.all((z>=0)&(z<=1)) and np.all(A@z<=b))
            optimal=bool(feasible and c@z==opt)
        assert feasible==(row['rounded_feasible']=='True') and optimal==(row['rounded_optimal']=='True')
        key=row['solver']+'/'+row['method'];s=counts.setdefault(key,dict(n=0,feasible=0,optimal=0))
        s['n']+=1;s['feasible']+=feasible;s['optimal']+=optimal
    result=dict(models=len(checked),configurations=len(runs),row_certificates=row_certificates,
                compression_steps=steps,local_integer_equivalence_checks=local_checks,summary=counts,
                model_sha256=input_hashes,runs_sha256=hashlib.sha256((args.root/'runs.csv').read_bytes()).hexdigest(),
                checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (args.root/'independent-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='model_sha256'},indent=2))


if __name__=='__main__':main()
