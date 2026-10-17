"""Independent arithmetic replay for tolerance and native-cycle data. No optimize calls."""
import argparse
import csv
from fractions import Fraction
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys
import numpy as np

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'scripts/research')]
from audit_identifiability_grid import parse
from audit_fixed_basis import read_lp
from oms_dispatch_validation import physical_spec
F=Fraction.from_float
FRONT=ROOT/'exploration/oms-frontier-20261016'
ACT=re.compile(r'a\d+_activacion_[1-4]\(\d+\)')

def load(p):return json.loads(Path(p).read_text())
def dump(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def gm(xs):return math.exp(statistics.mean(math.log(x) for x in xs))
def write(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows)
def dependencies(d):
    for p,h in d['dependencies'].items():assert sha(ROOT/p)==h,p

@lru_cache(None)
def data(path):
    rows,_=parse(path);_,lp,m=read_lp(path)
    assert len(rows)==lp.num_row_
    return rows,lp

def point(path):
    with np.load(path,allow_pickle=False) as p:return dict(zip(p['names'].tolist(),p['x'].tolist()))
def violation(row,x):
    v=sum((F(float(c))*x[n] for n,c in row['terms'].items()),Fraction(0))-F(float(row['rhs']))
    return abs(v) if row['sense']=='=' else max(Fraction(0),v if row['sense']=='<=' else -v)

def physical(base,export,values,budget):
    rows,lp=data(base);scaled,_=data(export)
    raw={n:F(float(v)) for n,v in values.items()};ints={n for n,k in zip(lp.col_names_,lp.integrality_) if str(k)!='HighsVarType.kContinuous'}
    rounded={n:Fraction(round(values[n])) if n in ints else v for n,v in raw.items()}
    group={};maxratio=Fraction(0);maxexport=Fraction(0);exportfail=0;count=0
    for n,r in rows.items():
        spec=physical_spec(n,r['terms'])
        if spec:g,u,c=spec
        elif ACT.fullmatch(n):g,u,c='Volume-dependent activation','m3',1.
        else:continue
        count+=1;key=g,u
        rec=group.setdefault(key,{'group':g,'unit':u,'rows':0,'raw_max':0.,'rounded_max':0.,'rounded_limiting_row':''})
        a=violation(r,raw)/F(c);b=violation(r,rounded)/F(c)
        rec['rows']+=1;rec['raw_max']=max(rec['raw_max'],float(a))
        if float(b)>rec['rounded_max']:rec['rounded_max']=float(b);rec['rounded_limiting_row']=n
        maxratio=max(maxratio,b/F(.01 if u=='MW' else float(budget)))
        v=violation(scaled[n],raw);maxexport=max(maxexport,v);exportfail+=v>F(1e-6)
    assert count==4320
    objective=sum((F(float(c))*raw[n] for n,c in zip(lp.col_names_,lp.col_cost_)),F(float(lp.offset_)))
    box_failures=sum((math.isfinite(lo) and raw[n]<F(float(lo))) or (math.isfinite(hi) and raw[n]>F(float(hi))) for n,lo,hi in zip(lp.col_names_,lp.col_lower_,lp.col_upper_))
    return {'physical':list(group.values()),'budget_pass':maxratio<=1,'rounded_max_ratio':float(maxratio),
        'observed_exported_max_violation':float(maxexport),'exported_epsilon_violations':exportfail,
        'integer_violation':max(float(abs(raw[n]-round(values[n]))) for n in ints),
        'objective_exact':str(objective),'raw_point_exact_box_violations':box_failures}

@lru_cache(None)
def witness(folder):
    folder=Path(folder);cert=load(folder/'independent-certificate.json');meta=load(folder/'mapping.json')
    p=ROOT/meta['original_model'];assert sha(p)==cert['original_model_sha256']
    assert sha(folder/'exact-witness.json')==cert['witness_sha256']
    x={n:Fraction(v) for n,v in load(folder/'exact-witness.json').items()};rows,lp=data(p)
    assert set(x)==set(lp.col_names_)
    for n,r in rows.items():assert violation(r,x)==0,n
    for n,l,u,k in zip(lp.col_names_,lp.col_lower_,lp.col_upper_,lp.integrality_):
        if math.isfinite(l):assert x[n]>=F(float(l))
        if math.isfinite(u):assert x[n]<=F(float(u))
        if str(k)!='HighsVarType.kContinuous':assert x[n].denominator==1
    U=sum((F(float(c))*x[n] for n,c in zip(lp.col_names_,lp.col_cost_)),F(float(lp.offset_)))
    assert str(U)==cert['objective_exact_fraction'];return U

def flags(outcome,U):
    b,c=outcome['bound'],outcome['objective']
    return (None if U is None or b is None else F(float(b))>U+F(max(1e-6,8*math.ulp(float(b)))),
        None if U is None or c is None else outcome['native_completed'] and U<F(float(c))-Fraction(1,100)*abs(F(float(c))))

def equal_models(pa,pb):
    ra,a=data(pa);rb,b=data(pb)
    assert list(a.col_names_)==list(b.col_names_) and list(a.row_names_)==list(b.row_names_)
    assert a.sense_==b.sense_ and a.offset_==b.offset_
    for attr in ['col_cost_','col_lower_','col_upper_','row_lower_','row_upper_','integrality_']:
        assert list(getattr(a,attr))==list(getattr(b,attr)),attr
    assert list(ra)==list(rb)
    for n,r in ra.items():
        s=rb[n];assert r['sense']==s['sense'] and F(float(r['rhs']))==F(float(s['rhs']))
        assert {j:F(float(v)) for j,v in r['terms'].items()}=={j:F(float(v)) for j,v in s['terms'].items()}

def tolerance():
    out=HERE/'tolerance';d=load(out/'design.json');dependencies(d)
    parent=load(out/'parent-timing.json');assert len(parent)==54 and all(p['returncode']==0 for p in parent)
    rows=[];index=load(out/'witness-index.json');calls=0;abstentions=0
    for p in parent:
        j=p['job'];entry=d['models'][j['instance']+'/'+j['key']]
        if p['abstained']:
            assert j['budget']==30 and entry['incompatible_count']==1440
            abstentions+=1;continue
        calls+=1;folder=out/'runs'/j['id'];r=load(folder/'result.json')
        assert r['job']==j and sha(folder/'scaled.lp')==entry['export_sha256']==r['export_sha256']
        oldfolder=FRONT/'runs'/j['id'];old=load(oldfolder/'result.json')
        assert {k:v for k,v in r['parameters'].items() if k!='IntFeasTol'}=={k:v for k,v in old['parameters'].items() if k!='IntFeasTol'}
        assert r['parameters']['IntFeasTol']==2.**-28
        q=physical(out/'models'/j['instance']/'Base.lp',folder/'scaled.lp',point(folder/'solution.npz'),j['budget'] or 100)
        assert q['physical']==r['checks']['physical']
        assert q['objective_exact']==r['checks']['point_objective_exact']
        assert q['exported_epsilon_violations']==r['checks']['exported_physical_rows_exceeding_epsilon']
        U=witness(ROOT/index[j['instance']+'/'+j['key']]['folder'])
        bf,gf=flags(r['outcome'],U)
        assert bf==r['checks']['bound_contradiction'] and gf==r['checks']['completion_contradiction']
        rows.append({**j,'gamma':2.**-28,'budget_pass':q['budget_pass'],'rounded_max_ratio':q['rounded_max_ratio'],
            'bound_contradiction':bf,'gap_contradiction':gf,'work':r['outcome']['work'],'total_seconds':p['total_fresh_process_seconds'],
            'raw_point_exact_box_violations':q['raw_point_exact_box_violations'],'exported_epsilon_violations':q['exported_epsilon_violations']})
    assert calls==36 and abstentions==18
    low=list(csv.DictReader((FRONT/'verified-runs.csv').open()))
    summary=[]
    for gamma in [1e-9,2.**-28]:
        for b in [30,100]:
            if gamma==1e-9:
                rr=[r for r in low if r['presolve']=='-1' and r['policy']=='Budget-L2' and r['evaluated_volume_budget']==str(b)]
                controls={(r['instance'],str(r['seed'])):r for r in low if r['presolve']=='-1' and r['policy']=='L2-NF3' and r['evaluated_volume_budget']==str(b)}
            else:
                rr=[r for r in rows if r['policy']=='Budget-L2' and r['budget']==b]
                controls={(r['instance'],str(r['seed'])):r for r in rows if r['policy']=='L2-NF3'}
            summary.append({'gamma':gamma,'budget':b,'calls':len(rr),'abstentions':18-len(rr),
                'primal_passes':sum(str(r['budget_pass'])=='True' for r in rr),
                'bound_flags':sum(str(r['bound_contradiction'])=='True' for r in rr),
                'gap_flags':sum(str(r['gap_contradiction'])=='True' for r in rr),
                'work_ratio_to_NF3':gm([float(r['work'])/float(controls[r['instance'],str(r['seed'])]['work']) for r in rr]) if rr else None})
    write(out/'verified-runs.csv',rows);write(out/'verified-summary.csv',summary)
    dump(out/'VALIDATION.json',{'new_MIP_calls':calls,'new_LP_calls':0,'borrowed_low_gamma_calls':54,
        'high_gamma_assignments':54,'high_gamma_abstentions':abstentions,'witnesses_independently_rechecked':len(index),
        'row_point_evaluations':calls*4320*3,'summary':summary,'parameter_comparisons_except_gamma_identical':True,
        'contract_factors_change_with_gamma':True,'no_solver_internal_causal_claim':True})
    print('Tolerance independently verified:',summary,flush=True)

def cycle():
    out=HERE/'native-cycle';d=load(out/'design.json');dependencies(d)
    parent=load(out/'parent-timing.json');assert len(parent)==36 and all(p['returncode']==0 for p in parent)
    rows=[]
    for p in parent:
        j=p['job'];folder=out/'runs'/j['id'];r=load(folder/'result.json')
        q=physical(FRONT/'models'/j['instance']/'Base.lp',folder/'scaled.lp',point(folder/'solution.npz'),100)
        assert q['physical']==r['verification']['physical']
        assert q['exported_epsilon_violations']==r['verification']['exported_physical_rows_exceeding_epsilon']
        rows.append({**j,'work':r['outcome']['work'],'total_seconds':p['total_fresh_process_seconds'],
            'budget_pass':q['budget_pass'],'exported_epsilon_violations':q['exported_epsilon_violations'],
            'ordered_binary64_model_fingerprint':r['ordered_binary64_model_fingerprint']})
    summary=[];workequal=endpointsequal=pointsequal=0;globalratios=[]
    for instance in d['models']:
        ratios=[];pts={'python':[],'cpp':[]}
        for seed in [59,71,89]:
            rs={r['backend']:r for r in rows if r['instance']==instance and r['seed']==seed}
            a,b=rs['python'],rs['cpp'];ratios.append(b['total_seconds']/a['total_seconds']);globalratios.append(ratios[-1])
            equal_models(out/'runs'/a['id']/'scaled.lp',out/'runs'/b['id']/'scaled.lp')
            assert a['ordered_binary64_model_fingerprint']==b['ordered_binary64_model_fingerprint']==d['models'][instance]['ordered_binary64_model_fingerprint']
            workequal+=a['work']==b['work']
            ra=load(out/'runs'/a['id']/'result.json');rb=load(out/'runs'/b['id']/'result.json')
            keys=['status','solutions','native_completed','work','objective','bound']
            endpointsequal+=all(ra['outcome'][k]==rb['outcome'][k] for k in keys)
            pointsequal+=point(out/'runs'/a['id']/'solution.npz')==point(out/'runs'/b['id']/'solution.npz')
            for backend in pts:pts[backend].append(rs[backend]['total_seconds'])
        summary.append({'instance':instance,'pairs':3,'python_geometric_seconds':gm(pts['python']),
            'cpp_geometric_seconds':gm(pts['cpp']),'cpp_to_python_full_time_ratio':gm(ratios)})
    write(out/'verified-runs.csv',rows);write(out/'verified-summary.csv',summary)
    dump(out/'VALIDATION.json',{'native_MIP_calls':36,'pairs':18,'primal_budget_passes':sum(r['budget_pass'] for r in rows),
        'equal_ordered_model_pairs':18,'equal_work_pairs':workequal,'equal_native_endpoint_pairs':endpointsequal,
        'equal_point_pairs':pointsequal,'cpp_to_python_full_time_ratio':gm(globalratios),'summary':summary,
        'standalone_preparation_speedup_not_extrapolated':True,'shared_machine':True,'optimizer_calls_during_replay':0})
    print('Native cycle independently verified; full-time ratio:',gm(globalratios),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['tolerance','cycle']);a=p.parse_args();globals()[a.stage]()
