"""Independent STN contract, export, primal-budget and witness replay; no solver calls."""
import csv
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics
import sys
import numpy as np

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'external'
sys.path[:0]=[str(HERE),str(ROOT/'scripts'),str(ROOT/'scripts/research')]
from audit_identifiability_grid import parse
from check_dispatch import witness,flags
F=Fraction.from_float
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def gm(xs):return math.exp(statistics.mean(math.log(x) for x in xs))
def write(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows)

def main():
    source=ROOT/'exploration/oms-generalization-20261014/independent_check.py'
    spec=importlib.util.spec_from_file_location('separate_STN_point_checker',source)
    checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
    d=load(OUT/'design.json')
    for p,h in d['dependencies'].items():assert sha(ROOT/p)==h,p
    modeldata={};changed=checked_factors=0
    for n,item in d['models'].items():
        folder=OUT/'models'/n;model=load(folder/'original-model.json');fs=load(folder/'factors.json')
        assert sha(folder/'original-model.json')==item['original_model_sha256']
        for policy,alphas in fs.items():
            if any(a is None for a in alphas):continue
            path=folder/(policy+'.lp');assert sha(path)==item['exports'][policy]
            rows,_=parse(path);assert len(rows)==len(model['rows'])
            for i,(r,alpha) in enumerate(zip(model['rows'],alphas)):
                actual=rows[f'r{i:05d}'];assert actual['sense']=={'<':'<=','>':'>=','=':'='}[r['sense']]
                expected={f'x{int(j):05d}':F(alpha)*F(float(c)) for j,c in r['terms'].items()}
                assert {j:F(float(v)) for j,v in actual['terms'].items()}==expected
                assert F(float(actual['rhs']))==F(alpha)*F(float(r['rhs']))
                if policy!='Base':
                    checked_factors+=1
                    assert math.frexp(alpha)[0]==.5
                    assert all(F(1e-9)<=abs(c)<=F(1e9) for c in expected.values())
                if policy=='Budget-L2':
                    E=F(1e-9)*sum((abs(F(float(c))) for j,c in r['terms'].items() if model['variables'][int(j)]['integer']),Fraction(0))
                    assert F(1e-6)/F(alpha)+E<=F(float(r['budget']))
        nc=sum(a!=b for a,b in zip(fs['L2'],fs['Budget-L2']));assert nc==item['changed_factors'];changed+=nc
        modeldata[n]=(model,fs)
    index=load(OUT/'witness-index.json');upper={}
    for n,r in index.items():upper[n]=witness(ROOT/r['folder']) if r.get('certificate') else None
    rows=[];references=[];row_evaluations=0
    for name,jobs,timing,basefolder in [('comparison',d['jobs'],'jobs-timing.json','runs'),('reference',d['references'],'references-timing.json','references')]:
        parent=load(OUT/timing);assert len(parent)==len(jobs) and all(p['returncode']==0 for p in parent)
        for p in parent:
            j=p['job'];folder=OUT/basefolder/j['id'];r=load(folder/'result.json');assert r['job']==j
            if r['abstained']:
                rows.append({**j,'abstained':True,'budget_pass':False});continue
            model,fs=modeldata[j['instance']]
            assert r['export_sha256']==sha(folder/'scaled.lp')==d['models'][j['instance']]['exports'][r['model_key']]
            with np.load(folder/'solution.npz',allow_pickle=False) as point:
                assert point['names'].tolist()==[f'x{i:05d}' for i in range(len(model['variables']))]
                q,raw,rounded=checker.check_point(model,point['x'])
            assert q==r['verification'];row_evaluations+=2*len(model['rows'])
            bf,gf=flags(r['outcome'],upper[j['instance']])
            if name=='comparison':assert bf==r['flags']['bound_contradiction'] and gf==r['flags']['completion_contradiction']
            alphas=fs[r['model_key']]
            epsfails=sum(F(a)*checker.row_violation(row,raw)>F(1e-6) for a,row in zip(alphas,model['rows']))
            record={**j,'abstained':False,'known_pilot_anchor':d['models'][j['instance']]['known_pilot_anchor'],
                'budget_pass':q['primal_accepted'],'max_rounded_budget_ratio':q['integer_rounded']['maximum_row_budget_ratio'],
                'max_mass_violation_kg':q['integer_rounded']['max_mass_violation_kg'],
                'exported_epsilon_violations':epsfails,'integer_distance':q['maximum_raw_integer_distance'],
                'integer_gamma_hypothesis_holds':q['maximum_raw_integer_distance']<=1e-9,
                'bound_flag':bf,'gap_flag':gf,'work':r['outcome']['work'],'status':r['outcome']['status'],
                'objective':r['outcome']['objective'],'total_seconds':p['total_fresh_process_seconds']}
            (rows if name=='comparison' else references).append(record)
    assert len(rows)==96 and len(references)==8
    summary=[];ratios=[];l2ratios=[]
    for n,item in d['models'].items():
        groups={p:[r for r in rows if r['instance']==n and r['policy']==p] for p in ['L2','Budget-L2','L2-tight','L2-NF3']}
        nf={r['seed']:r for r in groups['L2-NF3']};l2={r['seed']:r for r in groups['L2']}
        wr=[r['work']/nf[r['seed']]['work'] for r in groups['Budget-L2']]
        lr=[r['work']/l2[r['seed']]['work'] for r in groups['Budget-L2']]
        ratios.extend(wr);l2ratios.extend(lr)
        summary.append({'instance':n,'known_pilot_anchor':item['known_pilot_anchor'],'changed_factors':item['changed_factors'],
            **{p+'_primal_passes':sum(r['budget_pass'] for r in groups[p]) for p in groups},
            'known_bound_checks':sum(r['bound_flag'] is not None for r in rows if r['instance']==n),
            'bound_flags':sum(r['bound_flag'] is True for r in rows if r['instance']==n),
            'gap_flags':sum(r['gap_flag'] is True for r in rows if r['instance']==n),
            'Budget_to_NF3_work_ratio':gm(wr),'Budget_to_L2_work_ratio':gm(lr),
            'Budget_to_NF3_full_time_ratio':gm([r['total_seconds']/nf[r['seed']]['total_seconds'] for r in groups['Budget-L2']])})
    write(OUT/'verified-runs.csv',rows);write(OUT/'verified-references.csv',references);write(OUT/'verified-summary.csv',summary)
    result={'comparison_MIP_calls':96,'reference_MIP_calls':8,'reference_LP_attempts':8,
        'exact_feasible_reference_witnesses':sum(v is not None for v in upper.values()),
        'reference_refinement_unknown':sum(v is None for v in upper.values()),
        'comparison_primal_passes':sum(r['budget_pass'] for r in rows),
        'unknown_bound_checks':sum(r['bound_flag'] is None for r in rows),'detected_bound_flags':sum(r['bound_flag'] is True for r in rows),
        'original_row_point_evaluations':row_evaluations,'independently_checked_factor_intervals':checked_factors,
        'contract_changed_factors':changed,'Budget_to_NF3_geometric_work_ratio':gm(ratios),
        'Budget_to_L2_geometric_work_ratio':gm(l2ratios),'summary':summary,
        'no_exact_certification_of_all_native_reports':True,'previous_negative_pilot_retained':True,'optimizer_calls_during_replay':0}
    (OUT/'VALIDATION.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()
