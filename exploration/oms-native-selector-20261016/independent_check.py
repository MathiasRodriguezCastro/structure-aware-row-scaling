#!/usr/bin/env python3
"""Audit model identity, exact contracts and every timing record, solver free."""
import csv
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT/'scripts/research'),str(ROOT/'scripts')]
from audit_identifiability_grid import parse
from audit_fixed_basis import read_lp
from oms_dispatch_validation import physical_spec
F=Fraction.from_float
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def factors(p):return {r['row']:float(r['factor']) for r in csv.DictReader(p.open())}

def main():
    design=load(HERE/'design.json');timings=load(HERE/'timings.json')
    assert len(timings)==len(design['jobs'])==168 and [r['id'] for r in timings]==[j['id'] for j in design['jobs']]
    assert all(r['returncode']==0 for r in timings)
    for p,h in design['dependencies'].items():assert sha(ROOT/p)==h,p
    for p,h in load(HERE/'original-source-sha256.json').items():assert sha(ROOT/'code'/p)==h,p
    row_checks=0;contract_checks=0;models=0
    for instance in ['instance001','instance005','instance022','instance027','instance031','instance046']:
        base=ROOT/'exploration/oms-matched-accuracy-20261016/inputs'/instance/'Base.lp'
        original,_=parse(base);_,lp,_=read_lp(base)
        integers={n for n,k in zip(lp.col_names_,lp.integrality_) if str(k)!='HighsVarType.kContinuous'}
        boxes={n:max(abs(l),abs(h)) for n,l,h in zip(lp.col_names_,lp.col_lower_,lp.col_upper_)}
        for policy in ['L2','Budget-L2']:
            template=HERE/'preflight'/instance/policy
            pyf=factors(template/'python/factors.csv');cppf=factors(template/'cpp/factors.csv')
            assert cppf==pyf and set(cppf)==set(original)
            cppr,_=parse(template/'cpp/scaled.lp');pyr,_=parse(template/'python/scaled.lp')
            assert list(cppr)==list(pyr)==list(original)
            for n,row in cppr.items():
                f=cppf[n];source=original[n];assert float(row['rhs'])==float(pyr[n]['rhs'])==float(source['rhs'])*f
                assert row['sense']==source['sense']==pyr[n]['sense']
                for j,a in row['terms'].items():
                    assert float(a)==float(pyr[n]['terms'][j])==float(source['terms'][j])*f
                    assert 1e-9<=abs(float(a))<=1e9
                if policy=='Budget-L2':
                    spec=physical_spec(n,source['terms']);activation=re.fullmatch(r'a\d+_activacion_[1-4]\(\d+\)',n)
                    if spec or activation:
                        unit,conversion=(spec[1],spec[2]) if spec else ('m3',1.)
                        delta=F((.01 if unit=='MW' else 100.)*conversion)
                        E=F(1e-9)*sum((F(abs(float(a))) for j,a in source['terms'].items() if j in integers),Fraction(0))
                        rho=Fraction(0)
                        if activation:
                            rho=F(2.**-52)*(sum((F(abs(float(a)))*F(float(boxes[j])) for j,a in source['terms'].items()),Fraction(0))+F(abs(float(source['rhs']))))
                        assert F(1e-6)/F(f)+E+rho<=delta,n;contract_checks+=1
                row_checks+=1
            _,native,_=read_lp(template/'cpp/scaled.lp')
            native_data={n:(c,l,h,str(k)) for n,c,l,h,k in zip(native.col_names_,native.col_cost_,native.col_lower_,native.col_upper_,native.integrality_)}
            original_data={n:(c,l,h,str(k)) for n,c,l,h,k in zip(lp.col_names_,lp.col_cost_,lp.col_lower_,lp.col_upper_,lp.integrality_)}
            assert native_data==original_data and native.offset_==lp.offset_;models+=1
            for arm in ['python','cpp']:
                reference=sha(template/arm/'scaled.lp');rf=sha(template/arm/'factors.csv')
                selected=[r for r in timings if r['instance']==instance and r['policy']==policy and r['backend']==arm]
                assert sorted(r['repeat'] for r in selected)==list(range(7))
                for r in selected:
                    folder=HERE/'runs'/r['id'];outcome=load(folder/'result.json')
                    assert sha(folder/'scaled.lp')==reference==outcome['export_sha256']
                    assert sha(folder/'factors.csv')==rf
                    assert 0<=outcome['generator_seconds']<=r['total_seconds']
                    assert sum(outcome['stages'].values())+outcome['generator_seconds']<=r['total_seconds']
    summary=[]
    for instance in ['instance001','instance005','instance022','instance027','instance031','instance046']:
        for policy in ['L2','Budget-L2']:
            arms={b:[r['total_seconds'] for r in timings if r['instance']==instance and r['policy']==policy and r['backend']==b] for b in ['python','cpp']}
            med={b:statistics.median(t) for b,t in arms.items()}
            summary.append({'instance':instance,'policy':policy,'repetitions_per_arm':7,'median_python_seconds':med['python'],
                'median_cpp_seconds':med['cpp'],'ratio_cpp_python':med['cpp']/med['python'],'preparation_speedup':med['python']/med['cpp']})
    with (HERE/'verified-summary.csv').open('w',newline='') as out:
        w=csv.DictWriter(out,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
    result={'timed_preparations':168,'preflight_preparations':24,'binary64_equal_model_pairs':models,
        'exact_row_comparisons':row_checks,'exact_contract_checks':contract_checks,
        'all_timed_exports_and_factors_repeated_identically':True,'new_MIP_calls':0,
        'shared_machine_with_concurrent_experiments':True,'solver_acceleration_measured':False,
        'summary':summary}
    first=HERE/'first-pass';old=load(first/'timings.json')
    prefix='exploration/oms-native-selector-20261016/'
    for rel,h in load(first/'design.json')['dependencies'].items():
        path=first/rel[len(prefix):] if rel.startswith(prefix) else ROOT/rel
        assert sha(path)==h,rel
    assert len(old)==168 and [{k:r[k] for k in ['instance','policy','backend','repeat','id']} for r in old]==design['jobs']
    for job in design['jobs']:
        assert sha(first/'runs'/job['id']/'scaled.lp')==sha(HERE/'runs'/job['id']/'scaled.lp')
        # Old C++ CSV has unquoted commas in names. Retain the raw file and parse
        # its last delimiter explicitly solely for this first-pass audit.
        if job['backend']=='cpp':
            lines=(first/'runs'/job['id']/'factors.csv').read_text().splitlines()[1:]
            previous={line.rsplit(',',1)[0]:float(line.rsplit(',',1)[1]) for line in lines}
            assert previous==factors(HERE/'runs'/job['id']/'factors.csv')
    result.update(first_pass_timed_preparations_retained=168,total_timed_preparations=336,
        first_pass_source_dependencies_verified_after_relocation=True,
        first_and_corrected_pass_model_exports_identical=True,
        first_pass_median_seconds={policy:{arm:statistics.median(r['total_seconds'] for r in old if r['policy']==policy and r['backend']==arm) for arm in ['python','cpp']} for policy in ['L2','Budget-L2']})
    dump(HERE/'VALIDATION.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__':main()
