#!/usr/bin/env python3
"""Prospective timed acceptance/repair experiment, source frozen before solving."""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import time

import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PILOT=ROOT/'exploration/oms-generalization-20261014'
sys.path.insert(0,str(PILOT))
import generalization_study as original
from repair import repair,delivery_check,sha,dump

F=Fraction.from_float
ARMS=('Default-check','Tight-check','NumericFocus-check','IntegralityFocus-check',
      'Base-check-repair','L2-check-repair','Budget-check-repair','Diagnostic-check-repair')
SEEDS=(11,23)


def nominal_mu(model,alphas,gamma):
    if any(a is None for a in alphas):return None
    return max(float((F(1e-6)/F(float(a))+F(float(gamma))*sum((abs(F(float(c))) for i,c in r['terms'].items()
                     if model['variables'][int(i)]['integer']),Fraction(0)))/F(float(r['budget'])))
               for a,r in zip(alphas,model['rows']))


def choices(model):
    factors={};reasons={}
    for policy in ('Dyadic-L2','Budget-dyadic-L2'):
        selected=[original.factor(r,model,policy.startswith('Budget'),'l2') for r in model['rows']]
        factors[policy]=[v[0] for v in selected];reasons[policy]=[v[1] for v in selected]
    factors['Base']=[1.]*len(model['rows'])
    gamma=model['guided_gamma'] or 1e-5
    maximum_integer=max((abs(c) for r in model['rows'] for i,c in r['terms'].items() if model['variables'][int(i)]['integer']),default=0.)
    maximum_continuous=max((abs(c) for r in model['rows'] for i,c in r['terms'].items() if not model['variables'][int(i)]['integer']),default=0.)
    dominance=maximum_integer/maximum_continuous if maximum_continuous else None
    mu_l2=nominal_mu(model,factors['Dyadic-L2'],gamma)
    mu_budget=nominal_mu(model,factors['Budget-dyadic-L2'],gamma)
    if mu_l2 is not None and mu_l2<=1:route='Dyadic-L2';reason='conventional_nominal_rounding_bound_met'
    elif dominance is not None and dominance>=1e6:route='Base';reason='large_coefficients_removed_by_integer_fixing'
    elif mu_budget is not None and mu_budget<=1:route='Budget-dyadic-L2';reason='contract_nominal_rounding_bound_met'
    else:route='Base';reason='posterior_verification_required_no_prior_rounding_bound'
    return factors,{'maximum_integer_coefficient':maximum_integer,'maximum_continuous_coefficient':maximum_continuous,
        'integer_coefficient_dominance':dominance,'mu_l2':mu_l2,'mu_budget':mu_budget,
        'diagnostic_route':route,'diagnostic_reason':reason,
        'incompatible_rows':{p:sum(a is None for a in v) for p,v in factors.items()}}


def prepare():
    if (HERE/'confirmation/design.json').exists():raise SystemExit('Design already frozen')
    out=HERE/'confirmation';out.mkdir(exist_ok=True)
    models=[original.scheduling_model(h) for h in (14,16)]
    models += [json.loads((PILOT/'pilot/models'/name/'original-model.json').read_text())
               for name in ('control30-3-2-3','neos-3421095-cinca','ta1-UUM')]
    prepared=[]
    for model in models:
        folder=out/'models'/model['name'];folder.mkdir(parents=True)
        dump(folder/'original-model.json',model)
        factors,diagnostic=choices(model);dump(folder/'factors.json',factors)
        dump(folder/'diagnostic.json',diagnostic)
        for source,alphas in factors.items():
            if all(a is not None for a in alphas):original.write_lp(folder/(source+'.lp'),model,alphas)
        prepared.append({'name':model['name'],'family':model['family'],'rows':len(model['rows']),
            'columns':len(model['variables']),'guided_gamma':model['guided_gamma'],
            'model_sha256':sha(folder/'original-model.json'),'diagnostic':diagnostic,
            'exports':{p:sha(folder/(p+'.lp')) for p in factors if (folder/(p+'.lp')).exists()}})
    queue=[{'model':m['name'],'seed':s,'arm':a} for m in prepared for s in SEEDS for a in ARMS]
    rng=np.random.default_rng(20261015);queue=[queue[i] for i in rng.permutation(len(queue))]
    design={'stage':'prospective follow-up; development seed 17 excluded','seeds':SEEDS,'arms':ARMS,
        'assigned_arms':len(queue),'queue':queue,'models':prepared,'global_wall_reference_seconds':20.,
        'mip_limit_seconds':15.,'floating_lp_limit_seconds':2.,'exact_lp_limit_seconds':3.,
        'parameters':{'Threads':4,'MIPGap':.01,'Presolve':-1,'ScaleFlag':-1,'FeasibilityTol':1e-6,'IntFeasTol':1e-5},
        'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in
            (Path(__file__),HERE/'repair.py',HERE/'PROTOCOL.md',PILOT/'generalization_study.py',ROOT/'scripts/research/budget_scaling.py')},
        'held_out_horizons':[14,16],'shared_miplib_families':'fresh seeds, not new generators',
        'scope':'verified binary64 delivery, optional exact feasible witness; no global MILP optimality certification'}
    dump(out/'design.json',design)
    (out/'source-snapshot.py').write_bytes(Path(__file__).read_bytes())
    (out/'repair-source-snapshot.py').write_bytes((HERE/'repair.py').read_bytes())
    print('Frozen',len(queue),'prospective assignments')


def solve():
    import gurobipy as gp
    out=HERE/'confirmation';design=json.loads((out/'design.json').read_text())
    for path,digest in design['source_hashes'].items():assert sha(ROOT/path)==digest,'Frozen source changed: '+path
    env=gp.Env(params={'OutputFlag':0})
    for task in design['queue']:
        name,arm,seed=task['model'],task['arm'],task['seed']
        folder=out/'models'/name;run_dir=out/'runs'/name/f'{arm}-s{seed}'
        if (run_dir/'run.json').exists():continue
        run_dir.mkdir(parents=True,exist_ok=True)
        model=json.loads((folder/'original-model.json').read_text())
        item=next(m for m in design['models'] if m['name']==name)
        assert sha(folder/'original-model.json')==item['model_sha256']
        started=time.perf_counter();deadline=started+20.;record={**task,'delivered':False,'reported_completion':False,
            'source_point_budget_met':False,'repair_attempts':[],'exact_witness_available':False,
            'optimality_status':'unverified'}
        try:
            if arm=='Diagnostic-check-repair':
                factors,diagnostic=choices(model)
                assert diagnostic==item['diagnostic'];source=diagnostic['diagnostic_route']
                record['diagnostic_reason']=diagnostic['diagnostic_reason']
            else:
                source='Dyadic-L2' if arm=='L2-check-repair' else 'Budget-dyadic-L2' if arm=='Budget-check-repair' else 'Base'
                if source=='Base':factors={'Base':[1.]*len(model['rows'])}
                else:
                    selected=[original.factor(r,model,source.startswith('Budget'),'l2')[0] for r in model['rows']]
                    factors={source:selected}
            record['selected_representation']=source
            alpha=factors[source]
            if any(a is None for a in alpha):
                record.update(outcome='contract_abstention',incompatible_rows=sum(a is None for a in alpha),
                    preparation_seconds=time.perf_counter()-started,total_seconds=time.perf_counter()-started)
                dump(run_dir/'run.json',record);print(name,seed,arm,'contract abstention',flush=True);continue
            path=run_dir/'imported.lp';original.write_lp(path,model,alpha)
            assert sha(path)==item['exports'][source]
            record['lp_sha256']=sha(path);record['preparation_seconds']=time.perf_counter()-started
            import_started=time.perf_counter();m=gp.read(str(path),env=env)
            m.Params.LogToConsole=0;m.Params.OutputFlag=1;m.Params.LogFile=str(run_dir/'solver.log')
            params={**design['parameters'],'Seed':seed,'TimeLimit':min(15.,max(.1,deadline-time.perf_counter()-.3))}
            if source in ('Dyadic-L2','Budget-dyadic-L2') and model['guided_gamma']:params['IntFeasTol']=model['guided_gamma']
            if arm=='Tight-check':params.update(FeasibilityTol=1e-9,IntFeasTol=1e-9)
            if arm=='NumericFocus-check':params['NumericFocus']=3
            if arm=='IntegralityFocus-check':params['IntegralityFocus']=1
            for k,v in params.items():m.setParam(k,v)
            variables=m.getVars();names=[v.VarName for v in variables];rows=[]
            for c in m.getConstrs():
                e=m.getRow(c);rows.append((c.ConstrName,{e.getVar(j).VarName:float(e.getCoeff(j)) for j in range(e.size())},c.Sense,float(c.RHS)))
            data=[(v.VarName,float(v.LB) if abs(v.LB)<1e100 else None,float(v.UB) if abs(v.UB)<1e100 else None,v.VType!='C',float(v.Obj)) for v in variables]
            original.check_import(model,alpha,names,rows,data)
            record['import_preserved_original_exactly']=True;record['parameters']=params
            record['import_seconds']=time.perf_counter()-import_started
            mip_started=time.perf_counter();m.optimize()
            record.update(mip_seconds=time.perf_counter()-mip_started,work=float(m.Work),status=m.Status,
                reported_completion=m.Status==gp.GRB.OPTIMAL,bound=float(m.ObjBound) if math.isfinite(m.ObjBound) else None,
                has_source_point=m.SolCount>0,solver_version=gp.gurobi.version())
            point=[m.getVarByName(f'x{i:05d}').X for i in range(len(model['variables']))] if m.SolCount else None
            m.dispose();verify_started=time.perf_counter()
            if point is not None:
                rounded=[float(round(x)) if v['integer'] else float(x) for x,v in zip(point,model['variables'])]
                source_check,deliverable=delivery_check(model,rounded)
                record.update(source_point_budget_met=source_check['primal_accepted'],
                    original_source_objective=float(sum((F(float(v['cost']))*F(float(x)) for x,v in zip(point,model['variables'])),Fraction(0))),
                    source_maximum_delivery_ratio=source_check['integer_rounded']['maximum_row_budget_ratio'])
            else:source_check=None;deliverable=None
            record['source_verification_seconds']=time.perf_counter()-verify_started
            if source_check and source_check['primal_accepted']:
                delivered=deliverable;record['delivered']=True;record['outcome']='verified_source_delivery'
            else:
                delivered=None;record['outcome']='no_verified_source_delivery'
                if point is not None and arm.endswith('-repair'):
                    for mode,limit in (('floating',2.),('exact',3.)):
                        remaining=deadline-time.perf_counter()-.25
                        if remaining<=0:record['outcome']='budget_abstention';break
                        result,candidate=repair(model,point,run_dir/f'repair-{mode}',mode,min(limit,remaining))
                        record['repair_attempts'].append(result)
                        if result['exact_feasible']:record['exact_witness_available']=True
                        if result['delivered']:
                            delivered=candidate;record['delivered']=True;record['outcome']='verified_'+mode+'_repair_delivery';break
            if delivered is not None:
                final_check,_=delivery_check(model,delivered);assert final_check['primal_accepted']
                record['delivered_objective']=float(sum((F(float(v['cost']))*F(float(x)) for x,v in zip(delivered,model['variables'])),Fraction(0)))
                record['delivered_maximum_ratio']=final_check['integer_rounded']['maximum_row_budget_ratio']
                record['source_gap_transferred_to_delivery']=False
            record['total_seconds']=time.perf_counter()-started
            record['wall_reference_exceeded']=record['total_seconds']>20.
            save_started=time.perf_counter()
            if point is not None:
                with (run_dir/'source-point.npz').open('wb') as stream:np.savez_compressed(stream,x=np.array(point))
                dump(run_dir/'source-check.json',source_check)
            if delivered is not None:
                with (run_dir/'delivered-point.npz').open('wb') as stream:np.savez_compressed(stream,x=np.array(delivered))
                dump(run_dir/'delivered-check.json',final_check)
            record['outer_persistence_seconds']=time.perf_counter()-save_started
        except Exception as error:
            record.update(outcome='execution_failure',error_type=type(error).__name__,error=str(error),total_seconds=time.perf_counter()-started)
        dump(run_dir/'run.json',record)
        print(name,seed,arm,record['outcome'],'s',round(record['total_seconds'],3),flush=True)
    env.dispose()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=('prepare','solve'))
    globals()[parser.parse_args().stage]()
