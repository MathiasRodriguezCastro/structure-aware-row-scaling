#!/usr/bin/env python3
"""Rational replay, independent LP-source adaptation, and candidate policy audit."""
import csv
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np
from rational_lp import verify,verify_ray
from policy import choose

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OLD=ROOT/'exploration/oms-transfer-study-20261014'
ARITH=ROOT/'exploration/oms-decision-study-20261014'
F=Fraction.from_float


def load(p):return json.loads(Path(p).read_text())
def dump(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def csvwrite(p,records):
    keys=list(dict.fromkeys(k for r in records for k in r))
    with p.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(records)


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def source_adaptation(lp,model,pattern,task):
    """Rebuild each row from original units; never imports experimental builder."""
    z={int(i):Fraction(v) for i,v in pattern['integers'].items()}
    continuous=[i for i,v in enumerate(model['variables']) if not v['integer']];index={j:i for i,j in enumerate(continuous)}
    assert set(z)=={i for i,v in enumerate(model['variables']) if v['integer']}
    assert lp['continuous_original_indices']==continuous
    const=sum((F(float(model['variables'][i]['cost']))*v for i,v in z.items()),Fraction(0))
    param=task['mode']!='cost';lam=Fraction(task['lambda']);target=Fraction(task['target']) if 'target' in task else None
    costs=[F(float(model['variables'][i]['cost'])) for i in continuous]
    assert list(map(Fraction,lp['cost']))==([Fraction(0)]*len(continuous)+[Fraction(1)] if param else costs)
    assert Fraction(lp['offset'])==(0 if param else const)
    assert lp['mode']==task['mode'] and Fraction(lp['lambda_exact'])==lam
    assert lp['target_exact']==(str(target) if target is not None else None)
    expected={}
    def add(source,terms,rhs,weight):
        terms={str(i):v for i,v in terms.items() if v}
        if param and weight:terms[str(len(continuous))]=-weight
        elif not param:rhs+=lam*weight
        expected[json.dumps(source,sort_keys=True)]={'terms':terms,'rhs':rhs,'weight':weight}
    for i,row in enumerate(model['rows']):
        terms={index[int(j)]:F(float(a)) for j,a in row['terms'].items() if int(j) in index}
        rhs=F(float(row['rhs']))-sum((F(float(a))*z[int(j)] for j,a in row['terms'].items() if int(j) in z),Fraction(0))
        for sign in ([1,-1] if row['sense']=='=' else [1] if row['sense']=='<' else [-1]):
            add({'row':i,'sign':sign},{j:sign*a for j,a in terms.items()},sign*rhs,F(float(row['budget'])))
    for j in continuous:
        v=model['variables'][j]
        for endpoint,sign in (('lower',-1),('upper',1)):
            if v[endpoint] is not None:add({'bound':j,'endpoint':endpoint},{index[j]:Fraction(sign)},sign*F(float(v[endpoint])),F(float(v['bound_budget'])))
    if param:
        add({'lambda_bound':'lower'},{len(continuous):Fraction(-1)},Fraction(0),Fraction(0))
        add({'lambda_bound':'upper'},{len(continuous):Fraction(1)},Fraction(1),Fraction(0))
        if task['mode']=='cost-threshold':add({'cost_threshold':True},dict(enumerate(costs)),target-const,Fraction(0))
        else:assert task['mode']=='feasibility-threshold'
    assert len(expected)==len(lp['rows'])
    for row in lp['rows']:
        key=json.dumps(row['source'],sort_keys=True);ex=expected.pop(key)
        assert {j:Fraction(v) for j,v in row['terms'].items()}==ex['terms']
        assert Fraction(row['rhs'])==ex['rhs'] and Fraction(row['weight'])==ex['weight']
    assert not expected


def q_original(model,pattern,lp,point):
    q=[Fraction(0)]*len(model['variables'])
    for i,x in pattern['integers'].items():q[int(i)]=Fraction(x)
    for i,x in zip(lp['continuous_original_indices'],point):q[i]=Fraction(x)
    return q


def dyadic_at_most(x):
    q=Fraction(1)
    while q>x:q/=2
    return q


def main():
    d=load(HERE/'design.json')
    for name,h in d['source_hashes'].items():assert sha(ROOT/name)==h,name
    for name,h in d['input_hashes'].items():assert sha(HERE/name)==h,name
    assert sha(HERE/'source-snapshot.py')==sha(HERE/'sensitivity.py')
    assert sha(OLD/'VALIDATION.json')==d['prior_validation_sha256']
    for folder,file in ((OLD,'mps_check.py'),(ARITH,'independent_check.py')):
        manifest=load(folder/'MANIFEST.json');expected=next(r['sha256'] for r in manifest['files'] if r['path'].endswith('/'+file))
        assert sha(folder/file)==expected
    a=module(ARITH/'independent_check.py','pinned_original_arithmetic')
    parser=module(OLD/'mps_check.py','pinned_mps_checker')
    models={};sources=[];patterns={p['id']:p for p in d['patterns']}
    for name in {p['model'] for p in d['patterns']}:
        model=load(HERE/'inputs/models'/name/'original-model.json');models[name]=model
        sources.append(parser.check(model,OLD/'sources/miplib-models'))
        assert sha(HERE/'inputs/models'/name/(name+'.mps.gz'))==model['source_sha256']
    stages=[('characterization',d['queue'])]
    adaptive=load(HERE/'adaptive-design.json');safe=load(HERE/'safe-design.json')
    assert adaptive['parent_design_sha256']==sha(HERE/'design.json') and safe['parent_design_sha256']==sha(HERE/'adaptive-design.json')
    stages += [('adaptive',adaptive['queue']),('safe',safe['queue'])]
    results={};counts={};costrows=[];solvetime=total=0.;certcheck=0.
    for stage,queue in stages:
        for t in queue:
            folder=HERE/stage/t['pattern']/t['label'];r=load(folder/'result.json')
            assert all(r[k]==v for k,v in t.items())
            lp=load(folder/'model.json');assert sha(folder/'model.json')==r['model_sha256'] and sha(folder/'model.lp')==r['lp_sha256']
            p=patterns[t['pattern']];source_adaptation(lp,models[p['model']],p,t)
            c={};q=None
            if (folder/'primal.json').exists():
                q=list(map(Fraction,load(folder/'primal.json')));c=verify(lp,q,load(folder/'dual.json'));assert c==load(folder/'certificate.json')
                assert r['outcome']==('optimum_certified' if c['optimum_certified'] else 'primal_only' if c['primal_feasible'] else 'unverified')
                if t['mode']=='cost' and Fraction(t['lambda'])==0 and c['primal_feasible']:
                    original=q_original(models[p['model']],p,lp,q);check=a.rational_check(models[p['model']],original)
                    assert check['exact_feasible'] and Fraction(check['objective_exact'])==Fraction(c['primal_value_exact'])
            elif (folder/'ray.json').exists():
                c=verify_ray(lp,load(folder/'ray.json'));assert c==load(folder/'certificate.json')
                assert r['outcome']==('infeasibility_certified' if c['infeasibility_certified'] else 'unverified')
            else:assert r['outcome']=='unverified'
            results[(stage,t['pattern'],t['label'])]=(r,c,lp,q)
            counts[r['outcome']]=counts.get(r['outcome'],0)+1
            solvetime+=r['solver_seconds'];total+=r['total_seconds'];certcheck+=r['certificate_check_seconds']
            if stage=='characterization' and t['mode']=='cost':
                costrows.append({'pattern':p['id'],'model':p['model'],'members':len(p['members']),'lambda_exact':t['lambda'],'lambda':float(Fraction(t['lambda'])),
                                 'outcome':r['outcome'],'value_exact':c.get('primal_value_exact') if c.get('optimum_certified') else None,
                                 'value':float(Fraction(c['primal_value_exact'])) if c.get('optimum_certified') else None})
    csvwrite(HERE/'curves.csv',costrows)
    endpoints=[];fact=[];derived=[]
    for p in d['patterns']:
        r0,c0,lp0,q0=results[('characterization',p['id'],'cost-0')]
        r1,c1,lp1,q1=results[('characterization',p['id'],'cost-1')]
        v0=Fraction(c0['primal_value_exact']) if c0.get('optimum_certified') else None
        v1=Fraction(c1['primal_value_exact']) if c1.get('optimum_certified') else None
        loss=v0-v1 if v0 is not None and v1 is not None else None
        if loss is not None:assert loss>=0
        curve=sorted((Fraction(r['lambda_exact']),Fraction(r['value_exact'])) for r in costrows if r['pattern']==p['id'] and r['value_exact'] is not None)
        assert all(a[1]>=b[1] for a,b in zip(curve,curve[1:]))
        slopes=[(b[1]-a[1])/(b[0]-a[0]) for a,b in zip(curve,curve[1:])]
        assert all(a<=b for a,b in zip(slopes,slopes[1:]))
        endpoints.append({'pattern':p['id'],'model':p['model'],'members':len(p['members']),'v0_outcome':r0['outcome'],'v1_outcome':r1['outcome'],
                          'v0_exact':str(v0) if v0 is not None else None,'v1_exact':str(v1) if v1 is not None else None,
                          'v0':float(v0) if v0 is not None else None,'v1':float(v1) if v1 is not None else None,
                          'loss':float(loss) if loss is not None else None,'relative_loss':float(loss/abs(v0)) if loss is not None and v0 else None})
        if p['model']=='neos-3083784-nive':
            r,c,lp,q=results[('characterization',p['id'],'feasibility-threshold')]
            if not c.get('optimum_certified') and v0 is not None:
                lower=next(i for i,row in enumerate(lp['rows']) if row['source']=={'lambda_bound':'lower'})
                alt=verify(lp,list(q0)+[Fraction(0)],{str(lower):'-1'});assert alt['optimum_certified']
                derived.append({'pattern':p['id'],'source':'already certified v(0) primal plus lambda>=0','native_outcome_retained':r['outcome'],
                                'certificate':alt,'point':[str(x) for x in q0]+['0'],'dual':{str(lower):'-1'}})
                c=alt
            threshold=Fraction(c['primal_value_exact']) if c.get('optimum_certified') else None
            if v0 is not None:assert threshold==0
            if r0['outcome']=='infeasibility_certified':assert threshold is not None and 0<threshold<=1
            fact.append({'pattern':p['id'],'members':len(p['members']),'lambda_feas_exact':str(threshold) if threshold is not None else None,
                         'lambda_feas':float(threshold) if threshold is not None else None,'native_outcome':r['outcome'],'derived_proof':not load(HERE/'characterization'/p['id']/'feasibility-threshold/certificate.json').get('optimum_certified',False) if (HERE/'characterization'/p['id']/'feasibility-threshold/certificate.json').exists() else True})
    csvwrite(HERE/'endpoints.csv',endpoints);csvwrite(HERE/'feasibility-thresholds.csv',fact);dump(HERE/'derived-feasibility-proofs.json',derived)
    protection=[]
    for t in safe['queue']:
        p=patterns[t['pattern']];r0,c0,lp0,q0=results[('characterization',p['id'],'cost-0')]
        rt,ct,lpt,qt=results[('adaptive',p['id'],'cost-threshold')];r,c,lp,q=results[('safe',p['id'],'safe-cost')]
        assert sha(HERE/'characterization'/p['id']/'cost-0/certificate.json')==next(a['v0_certificate_sha256'] for a in adaptive['queue'] if a['pattern']==p['id'])
        assert sha(HERE/'adaptive'/p['id']/'cost-threshold/certificate.json')==t['threshold_certificate_sha256']
        v0=Fraction(t['v0']);eps=Fraction(t['epsilon']);target=Fraction(t['target']);assert v0==Fraction(c0['primal_value_exact'])
        assert eps==max(F(1e-6),abs(v0)/100) and v0-eps<=target<v0
        assert (target*2**40).denominator==1 and target-Fraction(1,2**40)<v0-eps
        lam=Fraction(t['lambda'])
        if ct.get('optimum_certified'):
            threshold=Fraction(ct['primal_value_exact']);assert threshold==Fraction(t['cost_threshold']) and 0<lam<threshold and 2*lam>=threshold
        else:assert ct.get('infeasibility_certified') and lam==1
        loss=v0-Fraction(c['primal_value_exact']) if c.get('optimum_certified') else None
        if loss is not None:assert 0<=loss<=eps and Fraction(c['primal_value_exact'])>=target
        dual=load(HERE/'characterization'/p['id']/'cost-0/dual.json')
        delta=sum((-Fraction(dual.get(str(i),'0'))*Fraction(row['weight']) for i,row in enumerate(lp0['rows'])),Fraction(0))
        fixed=dyadic_at_most(eps/delta) if delta else Fraction(1)
        assert fixed*delta<=eps
        protection.append({'pattern':p['id'],'v0':float(v0),'epsilon':float(eps),'cost_threshold':float(Fraction(t['cost_threshold'])) if t['cost_threshold'] else None,
                           'safe_factor_exact':str(lam),'safe_factor':float(lam),'loss':float(loss) if loss is not None else None,
                           'fixed_dual_delta':float(delta),'fixed_dual_factor_exact':str(fixed),'same_dyadic_factor':lam==fixed,
                           'ratio_safe_to_fixed':float(lam/fixed),'safe_cost_certified':c.get('optimum_certified',False)})
    csvwrite(HERE/'protected-budgets.csv',protection)
    selective=load(HERE/'selective-design.json');assert selective['parent_safe_design_sha256']==sha(HERE/'safe-design.json')
    for name,h in selective['source_hashes'].items():assert sha(ROOT/name)==h
    selectedrows=[]
    for task in selective['queue']:
        p=patterns[task['pattern']];folder=HERE/'selective'/p['id'];source=models[p['model']]
        budgetmodel=load(folder/'budget-model.json');assert sha(folder/'budget-model.json')==task['budget_model_sha256']
        originalfolder=HERE/'characterization'/p['id']/'cost-0';original_lp=load(originalfolder/'model.json');original_dual=load(originalfolder/'dual.json')
        assert sha(originalfolder/'dual.json')==task['v0_dual_sha256'];active_rows=set();active_bounds=set()
        for j,row in enumerate(original_lp['rows']):
            if Fraction(original_dual.get(str(j),'0')):
                if 'row' in row['source']:active_rows.add(row['source']['row'])
                if 'bound' in row['source']:active_bounds.add(row['source']['bound'])
        assert sorted(active_rows)==task['active_rows'] and sorted(active_bounds)==task['active_bound_variables']
        factor=Fraction(task['factor']);expected=json.loads(json.dumps(source))
        for i,row in enumerate(expected['rows']):
            if i in active_rows:row['budget']=float(F(float(row['budget']))*factor)
        for i,var in enumerate(expected['variables']):
            if i in active_bounds:var['bound_budget']=float(F(float(var['bound_budget']))*factor)
        assert budgetmodel==expected
        for i,row in enumerate(budgetmodel['rows']):assert F(float(row['budget']))==F(float(source['rows'][i]['budget']))*(factor if i in active_rows else 1)
        for i,v in enumerate(budgetmodel['variables']):assert F(float(v['bound_budget']))==F(float(source['variables'][i]['bound_budget']))*(factor if i in active_bounds else 1)
        r=load(folder/'result.json');assert all(r[k]==v for k,v in task.items());lp=load(folder/'model.json')
        assert sha(folder/'model.json')==r['model_sha256'] and sha(folder/'model.lp')==r['lp_sha256']
        source_adaptation(lp,budgetmodel,p,task)
        cert={};old_bound=None
        if (folder/'primal.json').exists():
            q=list(map(Fraction,load(folder/'primal.json')));cert=verify(lp,q,load(folder/'dual.json'));assert cert==load(folder/'certificate.json')
            old=verify(lp,q,original_dual);assert old['dual_feasible'];old_bound=Fraction(old['dual_value_exact'])
        elif (folder/'ray.json').exists():cert=verify_ray(lp,load(folder/'ray.json'));assert cert==load(folder/'certificate.json')
        assert r['outcome']==('optimum_certified' if cert.get('optimum_certified') else 'infeasibility_certified' if cert.get('infeasibility_certified') else 'unverified')
        v0=Fraction(task['v0']);eps=Fraction(task['epsilon']);value=Fraction(cert['primal_value_exact']) if cert.get('optimum_certified') else None
        delta=sum((-Fraction(original_dual.get(str(j),'0'))*Fraction(row['weight']) for j,row in enumerate(original_lp['rows'])),Fraction(0))
        if old_bound is not None:assert old_bound==v0-factor*delta>=v0-eps
        if value is not None:assert v0-eps<=value<=v0
        incompatible={}
        for label,bmodel in (('uniform',source),('selective',budgetmodel)):
            count=0
            for row in bmodel['rows']:
                mag=[abs(F(float(a))) for a in row['terms'].values() if a]
                budget=F(float(row['budget']))*(factor if label=='uniform' else 1)
                if max(F(1e-9)/min(mag),F(1e-6)/budget)>F(1e9)/max(mag):count+=1
            incompatible[label]=count
        selectedrows.append({'pattern':p['id'],'factor_exact':str(factor),'changed_rows':len(active_rows),'total_rows':len(source['rows']),
                             'changed_bound_variables':len(active_bounds),'continuous_variables':len(lp['cost']),
                             'value':float(value) if value is not None else None,'loss':float(v0-value) if value is not None else None,
                             'fixed_dual_lower':float(old_bound) if old_bound is not None else None,'objective_protection_certified':old_bound is not None,
                             'optimum_certified':cert.get('optimum_certified',False),'uniform_incompatible_rows':incompatible['uniform'],
                             'selective_incompatible_rows':incompatible['selective']})
        counts[r['outcome']]=counts.get(r['outcome'],0)+1
        solvetime+=r['solver_seconds'];total+=r['total_seconds'];certcheck+=r['certificate_check_seconds']
    csvwrite(HERE/'selective-budgets.csv',selectedrows)
    # A direct dual proof can leave the inexpensive bound allowances unchanged.
    # This is posthoc arithmetic, not another native LP experiment.
    rowonly=[];rowonly_models={}
    for task in selective['queue']:
        p=patterns[task['pattern']];model=models[p['model']];f=HERE/'characterization'/p['id']/'cost-0'
        original_lp=load(f/'model.json');pi=load(f/'dual.json');q=load(f/'primal.json')
        active=set(task['active_rows']);bound_effect=row_effect=Fraction(0)
        for j,row in enumerate(original_lp['rows']):
            effect=-Fraction(pi.get(str(j),'0'))*Fraction(row['weight'])
            if 'row' in row['source']:row_effect+=effect
            else:bound_effect+=effect
        eps=Fraction(task['epsilon']);assert bound_effect<eps and row_effect>0
        phi=dyadic_at_most((eps-bound_effect)/row_effect)
        expected=json.loads(json.dumps(model))
        for j,row in enumerate(expected['rows']):
            if j in active:
                exact_budget=F(float(row['budget']))*phi;row['budget']=float(exact_budget);assert F(row['budget'])==exact_budget
        lp=json.loads(json.dumps(original_lp));lp['lambda_exact']='1'
        for row in lp['rows']:
            weight=Fraction(row['weight'])*(phi if 'row' in row['source'] and row['source']['row'] in active else 1)
            row['weight']=str(weight);row['rhs']=str(Fraction(row['rhs'])+weight)
        source_adaptation(lp,expected,p,{'mode':'cost','lambda':'1'})
        cert=verify(lp,q,pi);v0=Fraction(task['v0']);lower=Fraction(cert['dual_value_exact'])
        assert cert['primal_feasible'] and cert['dual_feasible'] and Fraction(cert['primal_value_exact'])==v0
        assert lower==v0-phi*row_effect-bound_effect>=v0-eps
        rowonly.append({'pattern':p['id'],'factor_exact':str(phi),'changed_rows':len(active),'changed_bound_variables':0,
                        'bound_effect_exact':str(bound_effect),'row_effect_exact':str(row_effect),
                        'certified_lower_exact':str(lower),'exact_upper':str(v0),'epsilon':str(eps),
                        'loss_bound':float(v0-lower),'one_sided_cost_protection_certified':True,
                        'primal_dual_certificate':cert,'lp_model':lp,'native_solver_calls':0})
        rowonly_models[p['id']]=expected
    dump(HERE/'row-only-proofs.json',rowonly)
    cache={};policyrows=[];acquisitions=[];check_seconds=0.
    for record in d['records']:
        if not record['delivered']:
            policyrows.append({**{k:record[k] for k in ('order','model','arm','seed')},'numeric_accepted':False,'exact_repair_action':'abstain','cost_filter_action':'abstain','reason':'no_numeric_delivery'});continue
        folder=HERE/'inputs/runs'/f"r{record['order']:03d}";assert sha(folder/'point.npz')==record['point_sha256']
        with np.load(folder/'point.npz',allow_pickle=False) as z:x=list(z['x'])
        model=models[record['model']];p=patterns[record['pattern']]
        assert {str(i):int(x[i]) for i,v in enumerate(model['variables']) if v['integer']}==p['integers']
        start=time.perf_counter();numeric,raw,rounded=a.floating_check(model,x);assert numeric['primal_accepted'] and raw==rounded
        sourceq=list(map(lambda v:F(float(v)),x));exact=a.rational_check(model,sourceq);check_seconds+=time.perf_counter()-start
        nominal=a.objective(model,sourceq);key=p['id']
        if exact['exact_feasible']:
            if key not in cache or cache[key]['upper'] is None or nominal<cache[key]['upper']:
                cache[key]={'upper':nominal,'q':sourceq,'infeasible':False,'source':'exact input point'}
        elif key not in cache:
            r,c,lp,q=results[('characterization',key,'cost-0')]
            witness=q_original(model,p,lp,q) if c.get('primal_feasible') else None
            upper=Fraction(c['primal_value_exact']) if witness is not None else None
            cache[key]={'upper':upper,'q':witness,'infeasible':c.get('infeasibility_certified',False),'source':'fixed-pattern LP'}
            acquisitions.append({'pattern':key,'first_record':record['order'],'observed_acquisition_seconds':r['total_seconds'],'outcome':r['outcome']})
        witness=cache[key];upper=witness['upper'];repair_ok=False;repair_cost=None
        if witness['q'] is not None:
            q=witness['q'];assert a.rational_check(model,q)['exact_feasible']
            repairx=list(map(float,q));rc,rr,rz=a.floating_check(model,repairx);repair_ok=rc['primal_accepted'] and rr==rz
            repair_cost=a.objective(model,list(map(lambda v:F(float(v)),repairx)))
            eps=max(F(1e-6),abs(upper)/100);repair_ok &= upper<=repair_cost+eps
        decision=choose(nominal,upper,witness['infeasible'],repair_ok,repair_cost)
        baseline='accept_exact_source' if exact['exact_feasible'] else 'repair' if repair_ok else 'abstain'
        if decision['action']!='abstain':
            chosen_cost=nominal if decision['action']=='accept_nominal' else repair_cost
            assert upper is not None and upper<=chosen_cost+Fraction(decision['epsilon'])
        policyrows.append({**{k:record[k] for k in ('order','model','arm','seed')},'pattern':key,'numeric_accepted':True,
                           'source_exact_feasible':exact['exact_feasible'],'nominal_cost':float(nominal),'exact_upper':float(upper) if upper is not None else None,
                           'observed_understatement':float(upper-nominal) if upper is not None else None,
                           'exact_repair_action':baseline,'cost_filter_action':decision['action'],'reason':decision.get('reason'),
                           'epsilon':float(Fraction(decision['epsilon'])) if 'epsilon' in decision else None,'witness_source':witness['source'],
                           'row_only_budget_met':a.floating_check(rowonly_models[key],x)[0]['primal_accepted'] if key in rowonly_models else None})
    csvwrite(HERE/'policy-outcomes.csv',policyrows);dump(HERE/'policy-acquisitions.json',acquisitions)
    summary={'original_treatments':80,'original_numeric_deliveries':72,'unique_integer_patterns':41,
             'unique_nive_patterns':12,'new_lp_calls':sum(len(q) for _,q in stages)+len(selective['queue']),'lp_native_outcomes':counts,
             'derived_feasibility_zero_proofs':len(derived),'endpoint_pairs':len(endpoints),
             'infeasible_original_patterns':sum(e['v0_outcome']=='infeasibility_certified' for e in endpoints),
             'feasible_patterns_loss_above_one_percent':sum(e['relative_loss'] is not None and e['relative_loss']>.01 for e in endpoints),
             'safe_budget_certificates':sum(p['safe_cost_certified'] for p in protection),
             'same_safe_and_fixed_dual_dyadic_factor':sum(p['same_dyadic_factor'] for p in protection),
             'selective_protection_certificates':sum(r['objective_protection_certified'] for r in selectedrows),
             'selective_minimum_changed_rows':min(r['changed_rows'] for r in selectedrows),
             'selective_maximum_changed_rows':max(r['changed_rows'] for r in selectedrows),
             'row_only_protection_certificates':len(rowonly),'row_only_budget_native_deliveries_covered':sum(r.get('row_only_budget_met') is not None for r in policyrows),
             'row_only_budget_native_deliveries_accepted':sum(r.get('row_only_budget_met') is True for r in policyrows),
             'cost_filter_actions':{name:sum(r['cost_filter_action']==name for r in policyrows) for name in ('accept_nominal','repair','abstain')},
             'exact_repair_actions':{name:sum(r['exact_repair_action']==name for r in policyrows) for name in ('accept_exact_source','repair','abstain')},
             'shared_certificate_acquisitions':len(acquisitions),'shared_acquisition_seconds':sum(r['observed_acquisition_seconds'] for r in acquisitions),
             'new_lp_solver_seconds':solvetime,'new_lp_total_seconds':total,'native_certificate_check_seconds':certcheck,
             'solver_calls_during_replay':0,'global_mip_certification':False,
             'policy_timing_scope':'both policies use the same certificate cache; acquisition costs observed in new LP tasks, allocated in retrospective replay; no end-to-end speed comparison',
             'original_mps_checks':sorted(sources,key=lambda x:x['name'])}
    dump(HERE/'independent-verification.json',summary)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
