#!/usr/bin/env python3
"""Bounded prospective pilot; existing exact-dyadic row rules, independent sources.

No manuscript changes. All attempted arms, abstentions and import failures are kept.
Model data and saved points suffice for the solver-free verification stage.
"""
import argparse
import csv
from fractions import Fraction
import gzip
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts/research'))
from budget_scaling import dyadic_factor

F = Fraction.from_float
POLICIES = ('Base', 'Dyadic-GM', 'Dyadic-L2', 'Budget-dyadic-L2',
            'Dyadic-L2-tight', 'Dyadic-L2-NumericFocus3')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def csvwrite(path, rows):
    with Path(path).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def finite(value):
    return float(value) if value is not None and math.isfinite(float(value)) else None


def export_support(a, b, alpha, ahat, bhat, lower, upper, sign=1):
    """Exact one-sided support; None means a necessary endpoint is unbounded."""
    result = -sign * (F(alpha) * F(b) - F(bhat))
    for coefficient, exported, lo, hi in zip(a, ahat, lower, upper):
        error = sign * (F(alpha) * F(coefficient) - F(exported))
        if error == 0:
            continue
        endpoint = hi if error > 0 else lo
        if endpoint is None:
            return None
        result += error * F(endpoint)
    return result


def external_mps(path, env):
    """Check all MPS column/RHS literals against the solver reader before export."""
    import gurobipy as gp
    model = gp.read(str(path), env=env)
    text = gzip.decompress(path.read_bytes()).decode('latin1')
    section = None; objective_name = None; literals = {}; rhs = {}
    for line in text.splitlines():
        if not line.strip() or line.startswith('*'):
            continue
        tokens = line.split()
        if not line[0].isspace():
            section = tokens[0]; continue
        if section == 'ROWS' and tokens[0] == 'N':
            assert objective_name is None
            objective_name = tokens[1]
        if section == 'COLUMNS' and "'MARKER'" not in tokens:
            assert len(tokens) in (3, 5)
            for k in range(1, len(tokens), 2):
                key = tokens[0], tokens[k]
                number = float(tokens[k+1].replace('D', 'E'))
                literals[key] = literals.get(key, 0.) + number
        if section == 'RHS':
            assert len(tokens) in (3, 5)
            for k in range(1, len(tokens), 2):
                rhs[tokens[k]] = float(tokens[k+1].replace('D', 'E'))
        if section == 'RANGES':
            raise ValueError('Range rows require an explicit source adapter')
    variables = model.getVars(); index = {v.VarName: i for i, v in enumerate(variables)}
    actual = {(v.VarName, objective_name): float(v.Obj) for v in variables if v.Obj}
    rows = []
    for constraint in model.getConstrs():
        expression = model.getRow(constraint)
        terms = {}
        for j in range(expression.size()):
            name = expression.getVar(j).VarName; value = float(expression.getCoeff(j))
            actual[name, constraint.ConstrName] = value
            terms[str(index[name])] = value
        assert F(float(constraint.RHS)) == F(rhs.get(constraint.ConstrName, 0.))
        rows.append({'name':constraint.ConstrName, 'terms':terms, 'sense':constraint.Sense,
                     'rhs':float(constraint.RHS), 'budget':1e-4*max(1., abs(float(constraint.RHS))),
                     'unit':'experimental algebraic units'})
    assert {k:F(v) for k,v in actual.items() if v} == {k:F(v) for k,v in literals.items() if v}
    assert model.ObjCon == 0 and model.ModelSense == 1
    result = {'name':path.name.replace('.mps.gz',''), 'family':'MIPLIB Numerics',
        'variables':[{'name':v.VarName,'cost':float(v.Obj),'lower':finite(v.LB) if abs(v.LB)<1e100 else None,
                      'upper':finite(v.UB) if abs(v.UB)<1e100 else None,
                      'integer':v.VType != gp.GRB.CONTINUOUS,
                      'bound_budget':1e-4} for v in variables], 'rows':rows,
        'source':str(path.relative_to(HERE)), 'source_sha256':sha(path),
        'source_column_and_rhs_literals_checked':True,
        'integer_rounding_allowance_in_selection':False,
        'rounding_scope':'raw-point factor contract; integer-rounded point independently checked after solving',
        'guided_gamma':None, 'objective':'original minimization',
        'source_nonzeros':sum(len(r['terms']) for r in rows)}
    model.dispose()
    return result


def scheduling_model(horizon):
    sys.path.insert(0, str(HERE / '.deps'))
    sys.path.insert(0, str(HERE / 'sources/STN-Scheduler/STN'))
    from pyomo.environ import Var, Constraint, Objective, value
    from pyomo.repn.standard_repn import generate_standard_repn
    source = HERE / 'sources/STN-Scheduler/STN/kondili.py'
    prefix = source.read_text().split('\nH = 10\n', 1)[0]
    scope = {}; exec(compile(prefix, str(source), 'exec'), scope)
    stn = scope['stn']; stn.build(range(horizon+1)); model = stn.model
    constraints = []; used = set(); skipped = 0
    for constraint in model.component_data_objects(Constraint, active=True):
        lower, upper = finite(value(constraint.lower)), finite(value(constraint.upper))
        if lower is None and upper is None:
            skipped += 1; continue
        rep = generate_standard_repn(constraint.body)
        assert rep.is_linear()
        terms = {v.name:float(c) for v,c in zip(rep.linear_vars, rep.linear_coefs) if c}
        used.update(terms)
        constant = float(rep.constant or 0.)
        endpoints = [('=', upper)] if constraint.equality else [('<',upper),('>',lower)]
        for sense, endpoint in endpoints:
            if endpoint is None:
                continue
            financial = 'Value' in terms or 'Cost' in terms
            logical = not financial and all(n.startswith('W[') for n in terms)
            constraints.append({'name':constraint.name+':'+sense,'terms':terms, 'sense':sense,
                'rhs':endpoint-constant, 'budget':1e-3 if financial else 1e-5,
                'unit':'source monetary units' if financial else 'dimensionless' if logical else 'kg'})
    objective = next(model.component_data_objects(Objective, active=True))
    rep = generate_standard_repn(objective.expr)
    assert rep.is_linear() and float(rep.constant or 0.) == 0
    costs = {v.name:-float(c) for v,c in zip(rep.linear_vars,rep.linear_coefs)}
    used.update(costs)
    variables = sorted((v for v in model.component_data_objects(Var) if v.name in used),key=lambda v:v.name)
    index = {v.name:i for i,v in enumerate(variables)}
    for row in constraints:
        row['terms'] = {str(index[n]):v for n,v in row['terms'].items()}
    data = [{'name':v.name,'cost':costs.get(v.name,0.), 'lower':finite(value(v.lb)),
             'upper':finite(value(v.ub)), 'integer':v.is_integer() or v.is_binary(),
             'bound_budget':1e-3 if v.name in ('Value','Cost') else 1e-5} for v in variables]
    ratios = [r['budget']/(2*sum(abs(v) for i,v in r['terms'].items() if data[int(i)]['integer']))
              for r in constraints if any(data[int(i)]['integer'] for i in r['terms'])]
    gamma = math.ldexp(1., math.floor(math.log2(min(1e-5, *ratios))))
    assert gamma >= 1e-9
    return {'name':f'Kondili-H{horizon}', 'family':'independent batch scheduling',
        'variables':data,'rows':constraints,'source':str(source.relative_to(HERE)),
        'source_sha256':sha(source),'generator_sha256':sha(HERE/'sources/STN-Scheduler/STN/STN.py'),
        'source_commit':'3b1d5f3adfb1165c06ca496775047d683886ab52',
        'source_quantity_unit_evidence':'STN.py trace reports batch/inventory quantities in kg',
        'integer_rounding_allowance_in_selection':True,'guided_gamma':gamma,
        'objective':'negative original maximization profit',
        'unconstraining_infinite_rows_omitted':skipped,
        'unused_declared_variables_omitted':sum(1 for v in model.component_data_objects(Var) if v.name not in used),
        'source_nonzeros':sum(len(r['terms']) for r in constraints)}


def factor(row, model, budget, kernel):
    a = list(row['terms'].values())
    if not a:
        raise ValueError('Constant rows require separate feasibility treatment')
    reserve = (model['guided_gamma'] or 0.) * sum(abs(c) for i,c in row['terms'].items()
                 if model['variables'][int(i)]['integer']) if budget and model['integer_rounding_allowance_in_selection'] else 0.
    decision = dyadic_factor(a, row['rhs'], delta=row['budget'] if budget else None,
                            epsilon=1e-6, rounding_allowance=reserve)
    if decision.factor is None:
        return None, decision.reason, reserve
    if kernel == 'gm':
        return decision.factor, decision.reason, reserve
    wanted = 1. / math.sqrt(sum(c*c for c in a))
    lo,hi = round(math.log2(decision.lower)),round(math.log2(decision.upper))
    z = math.log2(wanted)
    candidates = {min(hi,max(lo,math.floor(z))), min(hi,max(lo,math.ceil(z)))}
    k = min(candidates,key=lambda k:(abs(k-z),-k))
    return math.ldexp(1.,k), 'exact_dyadic_l2', reserve


def write_lp(path, model, factors):
    def expression(terms):
        return ' '.join(f'{"+" if c>=0 else "-"} {abs(c):.17g} x{int(i):05d}' for i,c in terms.items() if c) or '0'
    lines=['Minimize',' obj: '+expression({str(i):v['cost'] for i,v in enumerate(model['variables'])}), 'Subject To']
    for j,(row,alpha) in enumerate(zip(model['rows'],factors)):
        assert alpha is not None and alpha > 0
        terms={i:alpha*c for i,c in row['terms'].items()}
        assert all(F(terms[i])==F(alpha)*F(c) for i,c in row['terms'].items())
        rhs=alpha*row['rhs'];assert F(rhs)==F(alpha)*F(row['rhs'])
        symbol={'<':'<=','>':'>=','=':'='}[row['sense']]
        lines.append(f' r{j:05d}: {expression(terms)} {symbol} {rhs:.17g}')
    lines.append('Bounds')
    for i,v in enumerate(model['variables']):
        lo,hi=v['lower'],v['upper'];name=f'x{i:05d}'
        if lo is None and hi is None: lines.append(f' {name} free')
        else:lines.append(f' {"-inf" if lo is None else format(lo,".17g")} <= {name} <= {"+inf" if hi is None else format(hi,".17g")}')
    ints=[f'x{i:05d}' for i,v in enumerate(model['variables']) if v['integer']]
    if ints:lines.extend(['Generals',' '+' '.join(ints)])
    lines.append('End');Path(path).write_text('\n'.join(lines)+'\n')


def prepare():
    import gurobipy as gp
    if (HERE/'pilot/design.json').exists():
        raise SystemExit('Design exists; do not overwrite a prepared study')
    output=HERE/'pilot';output.mkdir(exist_ok=True)
    env=gp.Env(params={'OutputFlag':0})
    models=[scheduling_model(h) for h in (10,12)]
    models += [external_mps(HERE/'sources/miplib-models'/(r['name']+'.mps.gz'), env)
               for r in json.loads((HERE/'MIPLIB_SELECTION.json').read_text())['selected']]
    prepared=[]
    for model in models:
        folder=output/'models'/model['name'];folder.mkdir(parents=True)
        dump(folder/'original-model.json',model)
        choices={};decisions=[]
        for policy in ('Dyadic-GM','Dyadic-L2','Budget-dyadic-L2'):
            choices[policy]=[]
            for j,row in enumerate(model['rows']):
                alpha,reason,reserve=factor(row,model,policy.startswith('Budget'), 'gm' if policy=='Dyadic-GM' else 'l2')
                choices[policy].append(alpha)
                decisions.append({'row':j,'source_row':row['name'],'policy':policy,'factor':alpha,
                    'reason':reason,'budget':row['budget'],'rounding_reserve':reserve,
                    'mu_raw':1e-6/alpha/row['budget'] if alpha else None,
                    'mu_rounded':(1e-6/alpha+reserve)/row['budget'] if alpha else None})
        choices['Base']=[1.]*len(model['rows'])
        exports={}
        for policy,alphas in choices.items():
            if all(a is not None for a in alphas):
                write_lp(folder/(policy+'.lp'),model,alphas)
                exports[policy]=sha(folder/(policy+'.lp'))
        csvwrite(folder/'factor-decisions.csv',decisions)
        dump(folder/'factors.json',choices)
        changes=sum(a!=b for a,b in zip(choices['Dyadic-L2'],choices['Budget-dyadic-L2']) if a is not None and b is not None)
        prepared.append({'name':model['name'],'family':model['family'],'rows':len(model['rows']),
            'columns':len(model['variables']),'guided_gamma':model['guided_gamma'],
            'contract_modified_rows':changes,'exports':exports,
            'incompatible_rows':{p:sum(a is None for a in v) for p,v in choices.items()}})
        print('Prepared',model['name'],len(model['rows']),len(model['variables']),'changed',changes,'incompatibilities',prepared[-1]['incompatible_rows'],flush=True)
    env.dispose()
    design={'stage':'preliminary pilot; not confirmatory or manuscript evidence','source_sha256':sha(__file__),
        'preprocessing':'existing dyadic representability interval and L2 projection; exact proportionality of full rows and RHS',
        'coefficient_window':[1e-9,1e9],'epsilon_hypothesis':1e-6,
        'budgets':{'STN_mass_kg':1e-5,'STN_logical':1e-5,'STN_financial':1e-3,
                  'MIPLIB':'1e-4 * max(1, abs(original RHS)), experimental algebraic units'},
        'models':prepared,'seed':17,'solvers':['gurobi','highs'],'policies':POLICIES,
        'parameters':{'threads':4,'time_limit_seconds':15,'relative_gap':.01,
                      'presolve':'normal/automatic','internal_scaling':'normal/default'},
        'MIPLIB_rounding_scope':'selection certifies raw-point transfer only; rounded full-model point checked independently',
        'STN_rounding_scope':'shared budget-guided integer allowance on Dyadic-L2 and Budget; source kg units',
        'acceptance':'all original-row numerical budgets, variable bounds and integer-rounded domains; no optimality certificate'}
    dump(output/'design.json',design)
    (output/'source-snapshot.py').write_bytes(Path(__file__).read_bytes())


def check_import(model, factors, names, rows, variable_data):
    assert len(names)==len(model['variables']) and len(rows)==len(model['rows'])
    expected_names={f'x{i:05d}':i for i in range(len(model['variables']))}
    assert set(names)==set(expected_names)
    for name,lower,upper,integer,cost in variable_data:
        original=model['variables'][expected_names[name]]
        for current,target in ((lower,original['lower']),(upper,original['upper'])):
            assert (current is None and target is None) or current is not None and target is not None and F(current)==F(target)
        assert bool(integer)==original['integer'] and F(cost)==F(original['cost'])
    for name,terms,sense,rhs in rows:
        j=int(name[1:]);original=model['rows'][j];alpha=factors[j]
        assert sense==original['sense'] and F(rhs)==F(alpha)*F(original['rhs'])
        mapped={str(expected_names[n]):F(c) for n,c in terms.items() if c}
        assert mapped=={i:F(alpha)*F(c) for i,c in original['terms'].items() if c}


def verify_point(model, x):
    assert len(x)==len(model['variables']) and all(math.isfinite(float(v)) for v in x)
    raw=[F(float(v)) for v in x]
    rounded=[Fraction(round(float(v))) if d['integer'] else q for v,d,q in zip(x,model['variables'],raw)]
    def assessment(point):
        max_ratio=Fraction(0);failed=[];mass=Fraction(0);bound_failures=0
        for j,row in enumerate(model['rows']):
            signed=sum((F(c)*point[int(i)] for i,c in row['terms'].items()),Fraction(0))-F(row['rhs'])
            violation=abs(signed) if row['sense']=='=' else max(Fraction(0),signed if row['sense']=='<' else -signed)
            ratio=violation/F(row['budget']);max_ratio=max(max_ratio,ratio)
            if row['unit']=='kg':mass=max(mass,violation)
            if ratio>1:failed.append(j)
        for q,v in zip(point,model['variables']):
            violation=max(Fraction(0),F(v['lower'])-q if v['lower'] is not None else Fraction(0),q-F(v['upper']) if v['upper'] is not None else Fraction(0))
            bound_failures+=violation>F(v['bound_budget'])
        return {'maximum_row_budget_ratio':float(max_ratio),'failed_rows':failed,'bound_failures':bound_failures,
                'max_mass_violation_kg':float(mass),'all_row_and_bound_budgets_met':not failed and not bound_failures}
    result={'raw':assessment(raw),'integer_rounded':assessment(rounded),
        'original_objective':float(sum((F(v['cost'])*q for v,q in zip(model['variables'],raw)),Fraction(0))),
        'maximum_raw_integer_distance':max((abs(float(q)-round(float(q))) for q,v in zip(raw,model['variables']) if v['integer']),default=0.)}
    result['primal_accepted']=result['integer_rounded']['all_row_and_bound_budgets_met']
    result['optimality_status']='unverified'
    return result


def solve():
    import gurobipy as gp
    import highspy
    out=HERE/'pilot';design=json.loads((out/'design.json').read_text())
    assert sha(__file__)==design['source_sha256'], 'Prepared source must remain unchanged'
    env=gp.Env(params={'OutputFlag':0})
    queue=[(item,solver,policy) for item in design['models'] for solver in design['solvers'] for policy in design['policies']
           if solver!='highs' or policy!='Dyadic-L2-NumericFocus3']
    rng=np.random.default_rng(20261014);queue=[queue[i] for i in rng.permutation(len(queue))]
    for item,solver,policy in queue:
        folder=out/'models'/item['name'];run_dir=out/'runs'/item['name']/f'{solver}-{policy}'
        run_dir.mkdir(parents=True,exist_ok=True)
        if (run_dir/'run.json').exists():continue
        model=json.loads((folder/'original-model.json').read_text())
        source='Dyadic-L2' if policy.startswith('Dyadic-L2-') else policy
        record={'model':item['name'],'family':item['family'],'solver':solver,'policy':policy,'seed':design['seed'],
                'reported_completion':False,'has_point':False,'primal_accepted':False}
        if source not in item['exports']:
            record.update(outcome='contract_or_coefficient_window_abstention',incompatible_rows=item['incompatible_rows'][source])
            dump(run_dir/'run.json',record);print(item['name'],solver,policy,record['outcome'],flush=True);continue
        path=folder/(source+'.lp');assert sha(path)==item['exports'][source]
        record['export_sha256']=sha(path)
        factors=json.loads((folder/'factors.json').read_text())[source]
        tolerance=1e-9 if policy=='Dyadic-L2-tight' else (item['guided_gamma'] if source in ('Dyadic-L2','Budget-dyadic-L2') and item['guided_gamma'] else None)
        started=time.perf_counter()
        try:
            if solver=='gurobi':
                m=gp.read(str(path),env=env)
                m.Params.LogToConsole=0;m.Params.OutputFlag=1;m.Params.LogFile=str(run_dir/'solver.log')
                params={'Threads':4,'TimeLimit':15,'MIPGap':.01,'Seed':17,'Presolve':-1,'ScaleFlag':-1,'FeasibilityTol':1e-6,'IntFeasTol':tolerance or 1e-5}
                if policy=='Dyadic-L2-tight':params['FeasibilityTol']=1e-9
                if policy=='Dyadic-L2-NumericFocus3':params['NumericFocus']=3
                for k,v in params.items():m.setParam(k,v)
                rows=[]
                for c in m.getConstrs():
                    expr=m.getRow(c);rows.append((c.ConstrName,{expr.getVar(k).VarName:float(expr.getCoeff(k)) for k in range(expr.size())},c.Sense,float(c.RHS)))
                vars=m.getVars();names=[v.VarName for v in vars]
                data=[(v.VarName,finite(v.LB) if abs(v.LB)<1e100 else None,finite(v.UB) if abs(v.UB)<1e100 else None,v.VType!='C',float(v.Obj)) for v in vars]
                check_import(model,factors,names,rows,data)
                load_seconds=time.perf_counter()-started;optimize=time.perf_counter();m.optimize()
                record.update(outcome=f'gurobi_status_{m.Status}',reported_completion=m.Status==2,has_point=m.SolCount>0,
                    optimizer_seconds=time.perf_counter()-optimize,load_seconds=load_seconds,work=float(m.Work),
                    bound=float(m.ObjBound) if math.isfinite(m.ObjBound) else None,parameters=params,version=gp.gurobi.version())
                x=np.array([m.getVarByName(f'x{i:05d}').X for i in range(len(model['variables']))]) if m.SolCount else None
                m.dispose()
            else:
                h=highspy.Highs();h.setOptionValue('log_to_console',False);h.setOptionValue('log_file',str(run_dir/'solver.log'))
                params={'threads':4,'time_limit':15.,'mip_rel_gap':.01,'random_seed':17,'presolve':'on',
                        'primal_feasibility_tolerance':1e-9 if policy=='Dyadic-L2-tight' else 1e-6,
                        'mip_feasibility_tolerance':tolerance or 1e-6}
                for k,v in params.items():assert h.setOptionValue(k,v)==highspy.HighsStatus.kOk
                read=h.readModel(str(path))
                if read==highspy.HighsStatus.kError:raise ValueError('HiGHS model import rejected by default numerical limits')
                lp=h.getLp();names=list(lp.col_names_);rows=[];matrix=h.getModel().lp_.a_matrix_
                if matrix.format_==highspy.MatrixFormat.kColwise:
                    byrow=[{} for _ in range(lp.num_row_)]
                    for j in range(lp.num_col_):
                        for k in range(matrix.start_[j],matrix.start_[j+1]):byrow[matrix.index_[k]][names[j]]=matrix.value_[k]
                else:
                    byrow=[{names[matrix.index_[k]]:matrix.value_[k] for k in range(matrix.start_[j],matrix.start_[j+1])} for j in range(lp.num_row_)]
                for j,terms in enumerate(byrow):
                    lo,hi=lp.row_lower_[j],lp.row_upper_[j]
                    sense='=' if lo==hi else '<' if math.isfinite(hi) else '>'
                    rows.append((lp.row_names_[j],terms,sense,float(hi if sense!='>' else lo)))
                data=[(names[j],finite(lp.col_lower_[j]),finite(lp.col_upper_[j]),lp.integrality_[j]!=highspy.HighsVarType.kContinuous,float(lp.col_cost_[j])) for j in range(lp.num_col_)]
                check_import(model,factors,names,rows,data)
                load_seconds=time.perf_counter()-started;optimize=time.perf_counter();h.run();info=h.getInfo();solution=h.getSolution()
                record.update(outcome=h.modelStatusToString(h.getModelStatus()),reported_completion=h.getModelStatus()==highspy.HighsModelStatus.kOptimal,
                    has_point=solution.value_valid,optimizer_seconds=time.perf_counter()-optimize,load_seconds=load_seconds,
                    work=None,bound=finite(info.mip_dual_bound),parameters=params,version=h.version())
                values=dict(zip(names,solution.col_value));x=np.array([values[f'x{i:05d}'] for i in range(len(model['variables']))]) if solution.value_valid else None
                h.clear()
            record['import_matches_original_exactly']=True
            if x is not None:
                with (run_dir/'solution.tmp').open('wb') as stream:np.savez_compressed(stream,x=x)
                (run_dir/'solution.tmp').replace(run_dir/'solution.npz')
                verification=verify_point(model,x);dump(run_dir/'verification.json',verification)
                record.update(primal_accepted=verification['primal_accepted'],original_objective=verification['original_objective'])
            record['total_seconds']=time.perf_counter()-started
        except Exception as error:
            record.update(outcome='import_or_execution_failure',error_type=type(error).__name__,error=str(error),total_seconds=time.perf_counter()-started)
        dump(run_dir/'run.json',record)
        print(item['name'],solver,policy,record['outcome'],'accepted',record['primal_accepted'],flush=True)
    env.dispose()


def verify():
    out=HERE/'pilot';design=json.loads((out/'design.json').read_text());records=[];checked=0
    for path in sorted((out/'runs').glob('*/*/run.json')):
        run=json.loads(path.read_text());folder=out/'models'/run['model']
        model=json.loads((folder/'original-model.json').read_text())
        if run['has_point']:
            with np.load(path.parent/'solution.npz',allow_pickle=False) as saved:verified=verify_point(model,saved['x'])
            assert verified==json.loads((path.parent/'verification.json').read_text())
            assert run['primal_accepted']==verified['primal_accepted'];checked+=1
            raw=verified['raw'];rounded=verified['integer_rounded']
        else:raw={};rounded={}
        records.append({'model':run['model'],'family':run['family'],'solver':run['solver'],'policy':run['policy'],
            'outcome':run['outcome'],'reported_completion':run['reported_completion'],'has_point':run['has_point'],
            'primal_accepted':run['primal_accepted'],'maximum_raw_ratio':raw.get('maximum_row_budget_ratio'),
            'maximum_rounded_ratio':rounded.get('maximum_row_budget_ratio'),
            'max_mass_violation_kg':rounded.get('max_mass_violation_kg'),
            'optimizer_seconds':run.get('optimizer_seconds'),'work':run.get('work'),
            'original_objective':run.get('original_objective'),'error':run.get('error')})
    assert len(records)==55
    csvwrite(out/'verified-runs.csv',records)
    dump(out/'verification-summary.json',{'assigned_arms':len(records),'saved_points_rechecked':checked,
        'accepted_primal_points':sum(r['primal_accepted'] for r in records),
        'optimizer_calls_during_verification':0,'exact_original_row_arithmetic':True,
        'all_arms_retained':True,'scope':'numerical primal budget acceptance only; no independently certified MILP bounds or optima'})
    print('Pilot replay passed',len(records),'arms,',checked,'points')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=('prepare','solve','verify'))
    globals()[parser.parse_args().stage]()
