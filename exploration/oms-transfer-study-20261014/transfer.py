#!/usr/bin/env python3
"""Prospective held-out-group and two-solver study using existing row factors."""
import argparse
from fractions import Fraction
import gzip
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
PREVIOUS=ROOT/'exploration/oms-decision-study-20261014'
QUALITY=ROOT/'exploration/oms-quality-followup-20261014'
sys.path.insert(0,str(PILOT));sys.path.insert(0,str(PREVIOUS));sys.path.insert(0,str(QUALITY))
import generalization_study as original
from repair import repair,exact_check,delivery_check,dump,sha
from controller import accept,best,cost,model_digest,screen_bound

F=Fraction.from_float
ARMS=('gurobi-Base-IF1','gurobi-L2-IF1','gurobi-Budget-IF1','gurobi-Base-tight',
      'highs-Base','highs-L2','highs-Budget','highs-Base-tight')


def save(path,values):
    with Path(path).open('wb') as stream:np.savez_compressed(stream,x=np.array(values))


def finite(v):return float(v) if math.isfinite(float(v)) and abs(float(v))<1e100 else None


def read_source(path,env):
    import gurobipy as gp
    m=gp.read(str(path),env=env)
    assert m.ObjCon==0 and m.ModelSense==1,'Nonzero offsets/maximization require another explicit adapter'
    variables=m.getVars();assert all(v.VType in ('C','B','I') for v in variables),'Semi-continuous/integer domains unsupported'
    index={v.VarName:i for i,v in enumerate(variables)};rows=[];actual={}
    for v in variables:
        if v.Obj:actual[v.VarName,'__objective__']=F(float(v.Obj))
    for c in m.getConstrs():
        e=m.getRow(c);terms={}
        for j in range(e.size()):
            name=e.getVar(j).VarName;value=float(e.getCoeff(j));terms[str(index[name])]=value
            if value:actual[name,c.ConstrName]=F(value)
        rows.append({'name':c.ConstrName,'terms':terms,'sense':c.Sense,'rhs':float(c.RHS),
                     'budget':1e-4*max(1.,abs(float(c.RHS))),'unit':'experimental algebraic units'})
    section='';objective=None;literals={};rhs={}
    for line in gzip.decompress(path.read_bytes()).decode('latin1').splitlines():
        if not line.strip() or line.startswith('*'):continue
        tokens=line.split()
        if not line[0].isspace():
            section=tokens[0];assert section in ('NAME','ROWS','COLUMNS','RHS','BOUNDS','ENDATA'),section;continue
        if section=='ROWS' and tokens[0]=='N':assert objective is None;objective=tokens[1]
        if section=='COLUMNS' and "'MARKER'" not in tokens:
            assert len(tokens) in (3,5)
            for j in range(1,len(tokens),2):
                key=tokens[0],('__objective__' if tokens[j]==objective else tokens[j]);assert key not in literals
                value=F(float(tokens[j+1].replace('D','E')))
                if value:literals[key]=value
        if section=='RHS':
            assert len(tokens) in (3,5)
            for j in range(1,len(tokens),2):assert tokens[j] not in rhs;rhs[tokens[j]]=F(float(tokens[j+1].replace('D','E')))
    assert actual==literals,'Source reader changed original coefficients'
    assert all(F(r['rhs'])==rhs.get(r['name'],Fraction(0)) for r in rows)
    model={'name':path.name.replace('.mps.gz',''),'family':'MIPLIB Numerics',
           'variables':[{'name':v.VarName,'cost':float(v.Obj),'lower':finite(v.LB),'upper':finite(v.UB),
                         'integer':v.VType!='C','bound_budget':1e-4} for v in variables],
           'rows':rows,'source':'sources/miplib-models/'+path.name,'source_sha256':sha(path),
           'source_nonzeros':sum(len(r['terms']) for r in rows),'guided_gamma':None,
           'integer_rounding_allowance_in_selection':False,'objective':'original minimization',
           'source_column_and_rhs_literals_checked':True}
    m.dispose();return model


def prepare():
    import gurobipy as gp
    began=time.perf_counter();out=HERE/'confirmation';assert not (out/'design.json').exists()
    selected=json.loads((HERE/'SELECTION.json').read_text())
    reference=json.loads((PILOT/'MIPLIB_SELECTION.json').read_text())['selected'][0]
    oldsource=PILOT/'sources/miplib-models/control30-3-2-3.mps.gz'
    shutil.copy2(oldsource,HERE/'sources/miplib-models'/oldsource.name)
    source_records=json.loads((HERE/'sources/miplib-models/provenance.json').read_text())
    source_records.append({**reference,'url':'https://miplib.zib.de/WebData/instances/'+oldsource.name,
                           'sha256':sha(oldsource),'bytes':oldsource.stat().st_size,'known_reference':True})
    dump(HERE/'sources/miplib-models/provenance.json',source_records)
    env=gp.Env(params={'OutputFlag':0});items=[]
    for metadata in selected['selected']+[reference]:
        name=metadata['name'];folder=out/'models'/name;folder.mkdir(parents=True,exist_ok=True)
        item={'name':name,'group':metadata['group'],'known_reference':name==reference['name'],'metadata':metadata}
        try:
            model=read_source(HERE/'sources/miplib-models'/(name+'.mps.gz'),env)
            dump(folder/'original-model.json',model)
            factors={'Base':[1.]*len(model['rows'])}
            for policy in ('Dyadic-L2','Budget-dyadic-L2'):
                factors[policy]=[original.factor(r,model,policy.startswith('Budget'),'l2')[0] for r in model['rows']]
            dump(folder/'factors.json',factors)
            for p,alphas in factors.items():
                if all(a is not None for a in alphas):original.write_lp(folder/(p+'.lp'),model,alphas)
            mi=max((abs(c) for r in model['rows'] for i,c in r['terms'].items() if model['variables'][int(i)]['integer']),default=0.)
            mc=max((abs(c) for r in model['rows'] for i,c in r['terms'].items() if not model['variables'][int(i)]['integer']),default=0.)
            item.update(prepared=True,model_sha256=sha(folder/'original-model.json'),rows=len(model['rows']),variables=len(model['variables']),
                        actual_nonzeros=model['source_nonzeros'],maximum_integer_coefficient=mi,maximum_continuous_coefficient=mc,
                        exports={p:sha(folder/(p+'.lp')) for p in factors if (folder/(p+'.lp')).exists()},
                        incompatible_rows={p:sum(a is None for a in alphas) for p,alphas in factors.items()},
                        modified_factors=sum(a is not None and b is not None and a!=b for a,b in zip(factors['Dyadic-L2'],factors['Budget-dyadic-L2'])))
            if item['known_reference']:
                q=json.loads((QUALITY/'confirmation/runs/control30-3-2-3/Cold-IF1-s31/final-exact-audit/rational-point.json').read_text())
                assert exact_check(model,q)['exact_feasible']
                dump(folder/'prior-witness.json',{'model_digest':model_digest(model),'point':q,'label':'reference-prior-exact-witness'})
                item['prior_witness_sha256']=sha(folder/'prior-witness.json')
        except Exception as e:item.update(prepared=False,preparation_error_type=type(e).__name__,preparation_error=str(e))
        items.append(item);print(name,'prepared',item['prepared'],'rows',item.get('rows'),'contract_changes',item.get('modified_factors'),flush=True)
    env.dispose()
    queue=[{'model':m['name'],'seed':s,'arm':a} for m in items for s in (83,97) for a in ARMS]
    rng=np.random.default_rng(20261018);queue=[queue[i] for i in rng.permutation(len(queue))]
    design={'assigned_treatments':80,'models':items,'seeds':[83,97],'arms':ARMS,'queue':queue,
            'selection_sha256':sha(HERE/'SELECTION.json'),'shared_preparation_seconds':time.perf_counter()-began,
            'mip_limit_seconds':15.,'wall_reference_seconds':20.,'factor_export_epsilon':1e-6,
            'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__),HERE/'PROTOCOL.md',QUALITY/'controller.py',PREVIOUS/'repair.py',PILOT/'generalization_study.py',ROOT/'scripts/research/budget_scaling.py')},
            'scope':'four previously unused labeled groups plus separate known reference; exact primal witness does not certify global MILP optimality'}
    dump(out/'design.json',design);shutil.copy2(Path(__file__),out/'source-snapshot.py')
    print('Frozen 80 assignments before any new optimization call',flush=True)


def native(model,alphas,solver,tight,folder,env,seed,limit):
    began=time.perf_counter();lp=folder/'imported.lp';original.write_lp(lp,model,alphas)
    record={'export_sha256':sha(lp)}
    if solver=='gurobi':
        import gurobipy as gp
        m=gp.read(str(lp),env=env);m.Params.LogToConsole=0;m.Params.OutputFlag=1;m.Params.LogFile=str(folder/'solver.log')
        params={'Threads':4,'MIPGap':.01,'TimeLimit':limit,'Seed':seed,'Presolve':-1,'ScaleFlag':-1,
                'FeasibilityTol':1e-9 if tight else 1e-6,'IntFeasTol':1e-9 if tight else 1e-5}
        if not tight:params['IntegralityFocus']=1
        for k,v in params.items():m.setParam(k,v)
        variables=m.getVars();names=[v.VarName for v in variables];rows=[]
        for c in m.getConstrs():
            e=m.getRow(c);rows.append((c.ConstrName,{e.getVar(j).VarName:float(e.getCoeff(j)) for j in range(e.size())},c.Sense,float(c.RHS)))
        data=[(v.VarName,finite(v.LB),finite(v.UB),v.VType!='C',float(v.Obj)) for v in variables]
        original.check_import(model,alphas,names,rows,data);assert m.ObjCon==0 and m.ModelSense==1
        record['import_seconds']=time.perf_counter()-began;start=time.perf_counter();m.optimize()
        point=[m.getVarByName(f'x{i:05d}').X for i in range(len(model['variables']))] if m.SolCount else None
        record.update(solver_seconds=time.perf_counter()-start,status=m.Status,reported_completion=m.Status==2,
                      bound=finite(m.ObjBound),objective_api=finite(m.ObjVal) if point is not None else None,
                      mip_gap_api=finite(m.MIPGap) if point is not None else None,absolute_gap_target=float(m.Params.MIPGapAbs),
                      work=float(m.Work),parameters=params,solver_version=gp.gurobi.version());m.dispose()
    else:
        import highspy
        h=highspy.Highs();h.setOptionValue('log_to_console',False);h.setOptionValue('log_file',str(folder/'solver.log'))
        params={'threads':4,'time_limit':limit,'mip_rel_gap':.01,'random_seed':seed,'presolve':'on',
                'primal_feasibility_tolerance':1e-9 if tight else 1e-6,'mip_feasibility_tolerance':1e-9 if tight else 1e-6}
        for k,v in params.items():assert h.setOptionValue(k,v)==highspy.HighsStatus.kOk
        read=h.readModel(str(lp));assert read!=highspy.HighsStatus.kError,'HiGHS import rejected by default numerical limits'
        data=h.getLp();names=list(data.col_names_);matrix=data.a_matrix_;byrow=[{} for _ in range(data.num_row_)]
        if matrix.format_==highspy.MatrixFormat.kColwise:
            for j in range(data.num_col_):
                for k in range(matrix.start_[j],matrix.start_[j+1]):byrow[matrix.index_[k]][names[j]]=float(matrix.value_[k])
        else:
            byrow=[{names[matrix.index_[k]]:float(matrix.value_[k]) for k in range(matrix.start_[j],matrix.start_[j+1])} for j in range(data.num_row_)]
        rows=[]
        for j,terms in enumerate(byrow):
            lo,hi=data.row_lower_[j],data.row_upper_[j];sense='=' if lo==hi else '<' if math.isfinite(hi) else '>'
            rows.append((data.row_names_[j],terms,sense,float(hi if sense!='>' else lo)))
        variables=[(names[j],finite(data.col_lower_[j]),finite(data.col_upper_[j]),data.integrality_[j]!=highspy.HighsVarType.kContinuous,float(data.col_cost_[j])) for j in range(data.num_col_)]
        original.check_import(model,alphas,names,rows,variables);assert data.offset_==0
        record['import_seconds']=time.perf_counter()-began;start=time.perf_counter();h.run();info=h.getInfo();solution=h.getSolution()
        values=dict(zip(names,solution.col_value));point=[values[f'x{i:05d}'] for i in range(len(model['variables']))] if solution.value_valid else None
        record.update(solver_seconds=time.perf_counter()-start,status=h.modelStatusToString(h.getModelStatus()),
                      reported_completion=h.getModelStatus()==highspy.HighsModelStatus.kOptimal,bound=finite(info.mip_dual_bound),
                      objective_api=finite(info.objective_function_value) if point is not None else None,
                      mip_gap_api=finite(info.mip_gap) if point is not None else None,
                      absolute_gap_target=float(h.getOptionValue('mip_abs_gap')[1]),work=None,parameters=params,solver_version=h.version())
        h.clear()
    record['import_preserved_original_exactly']=True;return record,point


def solve():
    import gurobipy as gp
    out=HERE/'confirmation';design=json.loads((out/'design.json').read_text())
    assert sha(HERE/'SELECTION.json')==design['selection_sha256']
    for path,digest in design['source_hashes'].items():assert sha(ROOT/path)==digest,path
    env=gp.Env(params={'OutputFlag':0})
    for task in design['queue']:
        folder=out/'runs'/task['model']/f"{task['arm']}-s{task['seed']}"
        if (folder/'run.json').exists():continue
        folder.mkdir(parents=True,exist_ok=True);item=next(m for m in design['models'] if m['name']==task['model'])
        record={**task,'known_reference':item['known_reference'],'delivered':False,'source_budget_met':False,
                'has_source_point':False,'repairs':[],'candidate_labels':[],'new_exact_witnesses':[],'optimality_status':'unverified'}
        if not item['prepared']:
            record.update(outcome='preparation_failure',error=item['preparation_error'],total_seconds=0.)
            dump(folder/'run.json',record);continue
        inputs=out/'models'/task['model'];assert sha(inputs/'original-model.json')==item['model_sha256']
        model=json.loads((inputs/'original-model.json').read_text());began=time.perf_counter();deadline=began+20.;candidates=[]
        solver=task['arm'].split('-')[0];policy='Budget-dyadic-L2' if 'Budget' in task['arm'] else 'Dyadic-L2' if 'L2' in task['arm'] else 'Base'
        alpha=[1.]*len(model['rows']) if policy=='Base' else [original.factor(r,model,policy.startswith('Budget'),'l2')[0] for r in model['rows']]
        record.update(representation=policy,selection_seconds=time.perf_counter()-began)
        if any(a is None for a in alpha):
            record.update(outcome='factor_incompatibility_abstention',incompatible_rows=sum(a is None for a in alpha),total_seconds=time.perf_counter()-began)
            dump(folder/'run.json',record);print(task['model'],task['arm'],task['seed'],'abstention',flush=True);continue
        try:
            result,point=native(model,alpha,solver,task['arm'].endswith('tight'),folder,env,task['seed'],min(15.,max(.01,deadline-time.perf_counter()-3.)))
            assert result['export_sha256']==item['exports'][policy];record.update(native=result,has_source_point=point is not None)
            verify=time.perf_counter()
            if point is not None:
                save(folder/'source-point.npz',point);raw=original.verify_point(model,point);dump(folder/'raw-source-check.json',raw)
                delivered=accept(model,point);record.update(source_budget_met=delivered is not None,raw_source_budget_met=raw['raw']['all_row_and_bound_budgets_met'],source_objective=float(cost(model,point)))
                if delivered is not None:candidates.append(('source-checked',delivered));save(folder/'source-checked.npz',delivered)
                else:
                    for mode,cap in (('floating',.5),('exact',1.)):
                        remaining=deadline-time.perf_counter()-.25
                        if remaining<=0:break
                        rf=folder/('repair-'+mode);r,converted=repair(model,point,rf,mode,min(cap,remaining));record['repairs'].append({'folder':rf.name,**r})
                        if r['exact_feasible']:record['new_exact_witnesses'].append(rf.name+'/rational-point.json')
                        if converted is not None:candidates.append((rf.name,converted));save(folder/(rf.name+'.npz'),converted);break
            record['source_check_and_repair_seconds']=time.perf_counter()-verify
            label,selected=best(model,candidates)
            if selected is not None:
                verify=time.perf_counter();q=[F(float(x)) for x in selected];exact=exact_check(model,q)
                dump(folder/'best-pre-audit-exact-check.json',exact)
                if exact['exact_feasible']:
                    dump(folder/'best-pre-audit-exact-point.json',[str(x) for x in q]);record['new_exact_witnesses'].append('best-pre-audit-exact-point.json')
                elif deadline-time.perf_counter()>.25:
                    r,converted=repair(model,selected,folder/'final-exact-audit','exact',min(1.,deadline-time.perf_counter()-.25))
                    record.update(final_exact_audit=r,final_audit_source_label=label)
                    if r['exact_feasible']:record['new_exact_witnesses'].append('final-exact-audit/rational-point.json')
                    if converted is not None:candidates.append(('final-exact-audit',converted));save(folder/'final-exact-audit.npz',converted)
                record['exact_audit_seconds']=time.perf_counter()-verify
            if item['known_reference']:
                assert sha(inputs/'prior-witness.json')==item['prior_witness_sha256']
                prior=json.loads((inputs/'prior-witness.json').read_text());record['prior_witness_screen']=screen_bound(model,result['bound'],prior)
        except Exception as e:record.update(execution_error_type=type(e).__name__,execution_error=str(e))
        label,selected=best(model,candidates);record.update(candidate_labels=[l for l,p in candidates],selected_candidate=label,delivered=selected is not None)
        if selected is not None:
            check,_=delivery_check(model,selected);assert check['primal_accepted']
            record.update(delivery_check=check,delivered_objective=float(cost(model,selected)),delivered_objective_exact=str(cost(model,selected)))
        record.update(total_seconds=time.perf_counter()-began,outcome='verified_delivery' if selected is not None else 'no_verified_delivery')
        if 'execution_error' in record:record['outcome']+='-with-execution-error'
        before=time.perf_counter()
        if selected is not None:save(folder/'delivered-point.npz',selected)
        record['outer_persistence_seconds']=time.perf_counter()-before
        dump(folder/'run.json',record)
        print(task['model'],task['arm'],task['seed'],record['outcome'],'objective',record.get('delivered_objective'),'seconds',round(record['total_seconds'],3),flush=True)
    env.dispose()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('prepare','solve'));globals()[p.parse_args().stage]()
