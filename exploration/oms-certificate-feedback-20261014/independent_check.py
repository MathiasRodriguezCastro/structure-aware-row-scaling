#!/usr/bin/env python3
"""Solver-free replay of exact cuts, native exports, audits, and paired outcomes."""
import csv
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

import numpy as np
from verify_cuts import check as check_cut

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
OLD=ROOT/'exploration/oms-objective-budget-20261014'
ARITH=ROOT/'exploration/oms-decision-study-20261014'
TRANSFER=ROOT/'exploration/oms-transfer-study-20261014'
sys.path.insert(0,str(OLD))
from rational_lp import verify,verify_ray
F=Fraction.from_float;TARGET=Fraction(2812951,100)


def load(p):return json.loads(Path(p).read_text())
def dump(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def point(p):
    with np.load(p,allow_pickle=False) as z:return list(z['x'])
def csvwrite(path,records):
    keys=list(dict.fromkeys(k for r in records for k in r))
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(records)
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def pin(folder,name):
    manifest=load(folder/'MANIFEST.json');digest=next(r['sha256'] for r in manifest['files'] if r['path']==str((folder/name).relative_to(ROOT)))
    assert sha(folder/name)==digest


def native_lp(path,model,factors,cuts):
    lines=path.read_text().splitlines();assert lines[0]=='Minimize' and lines[2]=='Subject To'
    def expr(t):
        if t==['0']:return {}
        assert len(t)%3==0;v={}
        for j in range(0,len(t),3):
            assert t[j] in ('+','-') and t[j+2].startswith('x');i=str(int(t[j+2][1:]));assert i not in v
            v[i]=(1 if t[j]=='+' else -1)*F(float(t[j+1]))
        return v
    assert expr(lines[1].split(':',1)[1].split())=={str(i):F(float(v['cost'])) for i,v in enumerate(model['variables']) if v['cost']}
    bound=lines.index('Bounds');rows=lines[3:bound];assert len(rows)==len(model['rows'])+len(cuts)
    for j,line in enumerate(rows):
        name,body=line.split(':',1);assert name.strip()==f'r{j:05d}';t=body.split();terms=expr(t[:-2]);rhs=F(float(t[-1]))
        if j<len(model['rows']):
            source=model['rows'][j];alpha=F(float(factors[j]));expected={i:alpha*F(float(a)) for i,a in source['terms'].items() if a}
            assert terms==expected and rhs==alpha*F(float(source['rhs'])) and t[-2]=={'=':'=','<':'<=','>':'>='}[source['sense']]
        else:
            e=cuts[j-len(model['rows'])]['export'];assert terms=={i:F(float(a)) for i,a in e['terms'].items()} and rhs==F(float(e['rhs'])) and t[-2]=='>='
    generals=lines.index('Generals');bounds=lines[bound+1:generals];assert len(bounds)==len(model['variables'])
    for i,(line,v) in enumerate(zip(bounds,model['variables'])):
        t=line.split();assert t[1]=='<=' and t[2]==f'x{i:05d}' and t[3]=='<='
        assert (None if t[0]=='-inf' else F(float(t[0])))==(None if v['lower'] is None else F(float(v['lower'])))
        assert (None if t[4]=='+inf' else F(float(t[4])))==(None if v['upper'] is None else F(float(v['upper'])))
    assert {int(s[1:]) for s in lines[generals+1].split()}=={i for i,v in enumerate(model['variables']) if v['integer']}
    assert lines[-1]=='End'


def main():
    d=load(HERE/'design.json');assert d['target_exact']==str(TARGET)
    for path,digest in d['source_hashes'].items():assert sha(ROOT/path)==digest,path
    for path,digest in d['input_hashes'].items():assert sha(HERE/path)==digest,path
    for name in ('run_feedback.py','infra.py','cuts.py','PROTOCOL.md','verify_cuts.py'):assert sha(HERE/('snapshot-'+name))==sha(HERE/name)
    for folder,name in ((ARITH,'independent_check.py'),(TRANSFER,'mps_check.py'),(OLD,'independent_check.py'),(OLD,'policy.py'),(OLD,'rational_lp.py')):pin(folder,name)
    a=module(ARITH/'independent_check.py','pinned_arithmetic')
    construction=module(OLD/'independent_check.py','pinned_budget_lp_adaptation')
    parser=module(TRANSFER/'mps_check.py','pinned_mps_parser')
    model=load(HERE/'inputs/original-model.json');factors=load(HERE/'inputs/factors.json')
    sourcecheck=parser.check(model,TRANSFER/'sources/miplib-models');assert sha(HERE/'inputs/neos-3083784-nive.mps.gz')==model['source_sha256']
    pre=load(HERE/'preflight-verification.json');assert sha(HERE/'preflight-verification.json')==d['preflight_verification_sha256'] and pre['new_optimization_calls']==0
    patterns={p['id']:p for p in load(OLD/'design.json')['patterns']};precounts={}
    for r in pre['proofs']:
        p=patterns[r['source_pattern']];folder=OLD/'characterization'/p['id']/'cost-0';lp=load(folder/'model.json');cert=load(folder/'certificate.json')
        kind='cost' if cert.get('optimum_certified') else 'ray';mu=load(folder/('dual.json' if kind=='cost' else 'ray.json'))
        if kind=='ray':mu={i:str(Fraction(v)*cert['orientation']) for i,v in mu.items()}
        check=check_cut(model,lp,p['integers'],mu,kind,r['exact'],r['export']);assert check==r['certificate']
        precounts[r['exact']['kind']]=precounts.get(r['exact']['kind'],0)+1
    audit_data={};exactwitnesses=[];lp_count=cache_count=0
    auditfolders=sorted(set(HERE/p['audit_path'] for f in list((HERE/'initial').glob('*/phase-*/phase.json'))+list((HERE/'branches').glob('*/phase-*/phase.json')) for p in [load(f)]))
    def audit_check(folder):
        nonlocal lp_count,cache_count
        key=str(folder.relative_to(HERE))
        if key in audit_data:return audit_data[key]
        r=load(folder/'audit.json')
        if r.get('cache_hit'):
            cache_count+=1;target=audit_check(HERE/r['proof_path']);assert target['record']['pattern_sha256']==r['pattern_sha256']
            audit_data[key]={**target,'local':r};return audit_data[key]
        entry={'record':r,'local':r,'folder':folder,'certificate':{},'upper':None,'point':None}
        if (folder/'pattern.json').exists():
            z=load(folder/'pattern.json');assert hashlib.sha256(json.dumps(z,sort_keys=True).encode()).hexdigest()==r['pattern_sha256'];entry['z']=z
        if r.get('lp_called'):
            lp_count+=1;lp=load(folder/'model.json');assert sha(folder/'model.lp')==r['lp_sha256']
            construction.source_adaptation(lp,model,{'integers':z},{'mode':'cost','lambda':'0'})
            if (folder/'primal.json').exists():
                q=load(folder/'primal.json');c=verify(lp,q,load(folder/'dual.json'));assert c==load(folder/'certificate.json')
                assert r['outcome']==('optimum_certified' if c['optimum_certified'] else 'primal_only' if c['primal_feasible'] else 'unverified')
            elif (folder/'ray.json').exists():
                c=verify_ray(lp,load(folder/'ray.json'));assert c==load(folder/'certificate.json')
                assert r['outcome']==('infeasibility_certified' if c['infeasibility_certified'] else 'unverified')
            else:c={};assert r['outcome']=='unverified'
            entry.update(lp=lp,certificate=c)
        if (folder/'witness.json').exists():
            q=list(map(Fraction,load(folder/'witness.json')));c=a.rational_check(model,q);assert c['exact_feasible']
            upper=Fraction(c['objective_exact']);assert upper==Fraction(r['exact_upper'])
            converted=list(map(float,q));check,_,_=a.floating_check(model,converted);assert check==load(folder/'witness-float-check.json')
            assert check['primal_accepted']==r['float_deliverable'] and r['target_met']==(check['primal_accepted'] and upper<=TARGET)
            if r['float_deliverable']:assert point(folder/'witness-float.npz')==converted
            entry.update(upper=upper,point=q);exactwitnesses.append({'upper':upper,'path':str((folder/'witness.json').relative_to(HERE))})
        audit_data[key]=entry;return entry
    for folder in auditfolders:audit_check(folder)
    phase_data={};cutrows=[];status_counts={};bounds=[];native_count=0;numeric_sources=0;false_pattern_occurrences=0;gap_reports=[]
    phasefiles=sorted(list((HERE/'initial').glob('*/phase-*/phase.json'))+list((HERE/'branches').glob('*/phase-*/phase.json')))
    for f in phasefiles:
        p=load(f);folder=f.parent;relative=str(f.relative_to(HERE));n=p['native'];native_count+=1
        solver=folder.parent.name.split('-')[0];seed=int(folder.parent.name.split('-')[1][1:]);params=n['parameters'];tight='Base-tight' in folder.parent.name
        limit=params['TimeLimit'] if solver=='gurobi' else params['time_limit'];assert 0<limit<=30
        if solver=='gurobi':
            assert params['Threads']==4 and params['Seed']==seed and params['MIPGap']==.01 and params['Presolve']==params['ScaleFlag']==-1 and params['IntegralityFocus']==1
            assert params['FeasibilityTol']==(1e-9 if tight else 1e-6) and params['IntFeasTol']==(1e-9 if tight else 1e-5) and params['BestObjStop']==float(TARGET)
            gamma=F(params['IntFeasTol'])
        else:
            assert params['threads']==4 and params['random_seed']==seed and params['mip_rel_gap']==.01 and params['presolve']=='on' and params['objective_target']==float(TARGET)
            assert params['primal_feasibility_tolerance']==params['mip_feasibility_tolerance']==(1e-9 if tight else 1e-6);gamma=F(params['mip_feasibility_tolerance'])
        active=load(folder/'active-cuts.json');policy='Base' if 'Base-' in folder.parent.name else 'Dyadic-L2'
        native_lp(folder/'imported.lp',model,factors[policy],active);assert sha(folder/'imported.lp')==n['export_sha256'] and n['import_preserved_original_exactly']
        ad=audit_check(HERE/p['audit_path']);assert str(ad['folder'].relative_to(HERE))==p['proof_path'] and ad['record']['outcome']==p['proof_outcome']
        assert p['exact_upper']==(str(ad['upper']) if ad['upper'] is not None else None)
        if p['has_source']:
            x=point(folder/'source-point.npz');rounded=[float(round(v)) if model['variables'][i]['integer'] else float(v) for i,v in enumerate(x)]
            assert point(folder/'audit/rounded-point.npz')==rounded
            numeric,raw,zpoint=a.floating_check(model,rounded);assert numeric==load(folder/'audit/numeric-check.json');numeric_sources+=numeric['primal_accepted']
            assert ad['z']=={str(i):int(v) for i,v in enumerate(rounded) if model['variables'][i]['integer']}
            if ad['certificate'].get('infeasibility_certified'):false_pattern_occurrences+=1
            maximum_integer_distance=max((abs(F(float(v))-round(float(v))) for v,w in zip(x,model['variables']) if w['integer']),default=Fraction(0))
            for j,cut in enumerate(active):
                ex=cut['exact'];e=cut['export'];raw_violation=max(Fraction(0),F(float(e['rhs']))-sum((F(float(c))*F(float(x[int(i)])) for i,c in e['terms'].items()),Fraction(0)))
                rounded_violation=max(Fraction(0),Fraction(ex['rhs'])-sum((Fraction(c)*F(float(rounded[int(i)])) for i,c in ex['terms'].items()),Fraction(0)))
                cutrows.append({'phase':relative,'solver':solver,'seed':seed,'kind':ex['kind'],'signature':ex['signature'],
                                'support_size':len(ex.get('support',[])),'raw_export_violation':float(raw_violation),
                                'raw_export_epsilon_holds':raw_violation<=F(1e-6),'integer_gamma_holds':maximum_integer_distance<=gamma,
                                'rounded_exact_cut_violation':float(rounded_violation),'rounded_cut_violated':rounded_violation>0})
        status_counts[solver+':'+str(n['status'])]=status_counts.get(solver+':'+str(n['status']),0)+1
        if n['reported_completion']:gap_reports.append({'phase':relative,'native_objective':n['objective_api'],'native_gap':n['mip_gap_api'],'exact_pattern_outcome':ad['record']['outcome']})
        phase_data[relative]={'record':p,'audit':ad,'limit':limit,'solver':solver}
    learned=[]
    for f in sorted((HERE/'branches').glob('*/learn-*/learned-cut.json')):
        r=load(f)
        if not r['generated']:continue
        ad=audit_check(HERE/r['proof_path']);c=ad['certificate'];mu=load(ad['folder']/('dual.json' if r['proof_kind']=='cost' else 'ray.json'))
        if r['proof_kind']=='ray':mu={i:str(Fraction(v)*c['orientation']) for i,v in mu.items()}
        check=check_cut(model,ad['lp'],ad['z'],mu,r['proof_kind'],r['exact'],r['export']);assert check==r['verification']
        learned.append({'kind':r['exact']['kind'],'support_size':len(r['exact'].get('support',[])),'exported':r['export']['exported'],
                        'conditional':check.get('nominal_transfer_bounds'),'path':str(f.relative_to(HERE))})
    outcomes=[];errors=[]
    def summarize(job,result,method,seconds):
        phases=[phase_data[s] for s in result['phases']];uppers=[p['audit']['upper'] for p in phases if p['audit']['upper'] is not None and p['audit']['record'].get('float_deliverable')]
        upper=min(uppers) if uppers else None
        assert result['exact_upper']==(str(upper) if upper is not None else None) and result['target_met']==(upper is not None and upper<=TARGET)
        assert sum(p['limit'] for p in phases)<=30+1e-9
        outcome={'solver':job['solver'],'seed':job['seed'],'method':method,'total_seconds':seconds,'exact_upper':float(upper) if upper is not None else None,
                 'target_met':upper is not None and upper<=TARGET,'phases':len(phases),'infeasible_pattern_occurrences':sum(p['audit']['certificate'].get('infeasibility_certified',False) for p in phases),
                 'cache_hits':sum(p['record']['audit'].get('cache_hit',False) for p in phases),'native_gap_certified':False,
                 'applied_distinct_cuts':result.get('applied_distinct_cuts',0),'wall_reference_exceeded':seconds>45}
        return outcome
    for job in d['initial_jobs']:
        label=f"{job['solver']}-s{job['seed']}-{job['kind']}";r=load(HERE/'initial'/label/'result.json')
        if 'error' in r:errors.append({'label':label,'error':r['error']});continue
        if job['kind']=='prefix':continue
        method={'L2-direct':'B-repair','Base-direct':'Base-B','Base-tight':'Base-tight-B'}[job['kind']]
        outcomes.append(summarize(job,r,method,r['total_seconds']))
        if job['kind']=='L2-direct':
            ph=phase_data[r['phases'][0]]['record'];n=ph['native'];outcomes.append({'solver':job['solver'],'seed':job['seed'],'method':'A-numeric',
              'total_seconds':ph['native_elapsed_seconds'],'exact_upper':None,'target_met':False,'phases':1,
              'nominal_objective':n['objective_api'],'nominal_target_met':n['objective_api'] is not None and F(float(n['objective_api']))<=TARGET,
              'assessment_pattern_upper':float(Fraction(r['exact_upper'])) if r['exact_upper'] is not None else None,
              'infeasible_pattern_occurrences':ph['proof_outcome']=='infeasibility_certified','native_gap_certified':False})
            assessed=phase_data[r['phases'][0]]['audit']['certificate']
            assert assessed.get('infeasibility_certified') or (assessed.get('optimum_certified') and Fraction(assessed['dual_value_exact'])>TARGET)
    for job in d['branch_jobs']:
        label=f"{job['solver']}-s{job['seed']}-{job['kind']}";r=load(HERE/'branches'/label/'result.json')
        if 'error' in r:errors.append({'label':label,'error':r['error']});continue
        prefix=load(HERE/r['shared_prefix']);assert r['phases'][0]==prefix['phases'][0]
        known=set();best=None;seen={}
        for index,name in enumerate(r['phases']):
            phase=phase_data[name];ph=phase['record'];ad=phase['audit'];nativefolder=(HERE/name).parent
            assert phase['limit']<=10+1e-9
            if index:
                assert best is None or best[0]>TARGET
                for cut in load(nativefolder/'active-cuts.json'):
                    assert cut['proof_path'] in known
                    assert cut['exact']['kind'].startswith('aggregate' if job['kind']=='C-aggregate' else 'partial')
                if job['kind']=='B-restart':assert not load(nativefolder/'active-cuts.json')
                assert ph['native']['start_supplied']==(best is not None)
                if best is not None:assert point(nativefolder/'start-point.npz')==list(map(float,best[1]))
            if ph['audit'].get('cache_hit'):
                assert ph['audit']['proof_path'] in known and seen[ph['audit']['pattern_sha256']]==ph['audit']['proof_path']
            if ad['record'].get('pattern_sha256'):seen[ad['record']['pattern_sha256']]=ph['proof_path']
            known.add(ph['proof_path'])
            if ad['upper'] is not None and ad['record'].get('float_deliverable') and (best is None or ad['upper']<best[0]):best=(ad['upper'],ad['point'],ph['proof_path'])
        assert r['best_proof_path']==(best[2] if best is not None else None)
        outcomes.append(summarize(job,r,job['kind'],r['total_seconds']))
    assert len(outcomes)+len(errors)==42
    if exactwitnesses:
        best=min(exactwitnesses,key=lambda r:r['upper'])
        for name,p in phase_data.items():
            n=p['record']['native']
            if n['bound'] is not None:
                b=F(float(n['bound']));guard=max(F(1e-6),8*F(math.ulp(float(b))))
                if b>best['upper']+guard:bounds.append({'phase':name,'native_bound':float(b),'exact_upper':float(best['upper']),'witness':best['path']})
    comparisons=[]
    for solver in d['solvers']:
        for seed in d['seeds']:
            per={r['method']:r for r in outcomes if r['solver']==solver and r['seed']==seed}
            for method in ('C-aggregate','C-guard'):
                for control in ('B-repair','B-restart','Base-B','Base-tight-B'):
                    r,c=per[method],per[control];better=(r['exact_upper'] is not None and (c['exact_upper'] is None or r['exact_upper']<c['exact_upper']-1e-6))
                    comparisons.append({'solver':solver,'seed':seed,'method':method,'control':control,'better_exact_upper':better,
                                        'target_gain':r['target_met'] and not c['target_met'],'seconds_difference':r['total_seconds']-c['total_seconds']})
    csvwrite(HERE/'outcomes.csv',outcomes);csvwrite(HERE/'cut-observations.csv',cutrows);csvwrite(HERE/'paired-comparisons.csv',comparisons)
    dump(HERE/'global-cut-proofs.json',learned);dump(HERE/'bound-discrepancies.json',bounds);dump(HERE/'reported-gaps.json',gap_reports)
    summary={'strategy_results':len(outcomes),'native_mip_calls':native_count,'native_sources_budget_compliant':numeric_sources,
             'native_reported_optimal_calls':len(gap_reports),'native_status_counts':status_counts,'exact_lp_calls':lp_count,'audit_cache_hits':cache_count,
             'fresh_exact_witnesses':len(exactwitnesses),'fresh_lp_optimum_certificates':sum(v['certificate'].get('optimum_certified',False) for k,v in audit_data.items() if not v['local'].get('cache_hit')),
             'fresh_lp_infeasibility_certificates':sum(v['certificate'].get('infeasibility_certified',False) for k,v in audit_data.items() if not v['local'].get('cache_hit')),
             'unique_audited_patterns':len({v['record']['pattern_sha256'] for v in audit_data.values() if 'pattern_sha256' in v['record']}),
             'unique_infeasible_patterns':len({v['record']['pattern_sha256'] for v in audit_data.values() if v['certificate'].get('infeasibility_certified')}),
             'infeasible_pattern_source_occurrences':false_pattern_occurrences,'preflight_global_cut_proofs':precounts,
             'online_global_cut_proofs':len(learned),'online_exported_cut_proofs':sum(r['exported'] for r in learned),
             'active_cut_source_observations':len(cutrows),'rounded_aggregate_cut_violations':sum(r['kind'].startswith('aggregate') and r['rounded_cut_violated'] for r in cutrows),
             'rounded_guard_cut_violations':sum(r['kind'].startswith('partial') and r['rounded_cut_violated'] for r in cutrows),
             'raw_export_epsilon_failures':sum(not r['raw_export_epsilon_holds'] for r in cutrows),
             'C_better_upper_than_matched_restart':sum(r['better_exact_upper'] for r in comparisons if r['control']=='B-restart'),
             'C_target_gains_over_matched_restart':sum(r['target_gain'] for r in comparisons if r['control']=='B-restart'),
             'bound_discrepancies':len(bounds),'execution_errors':errors,'original_mps_check':sourcecheck,
             'only_temporally_available_proofs_used_for_cuts':True,'matched_starts_and_best_retention_checked':True,
             'solver_calls_during_replay':0,'global_mip_optimality_status':'unverified','full_unknown_pattern_coverage':False}
    dump(HERE/'independent-verification.json',summary);print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
