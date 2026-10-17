#!/usr/bin/env python3
"""Fixed-integer LP repair with exact original-model and delivery checks.

LP statuses are diagnostic only. A rational certificate is accepted only after
all original binary64 rows/bounds/domains pass a separate Fraction calculation.
Binary64 delivery is checked independently and may fail even for an exact witness.
"""
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PILOT=ROOT/'exploration/oms-generalization-20261014'
sys.path.insert(0,str(PILOT))
from generalization_study import verify_point

F=Fraction.from_float
SOPLEX=ROOT/'exploration/oms-followup-20261014/tools/soplex-build/bin/soplex'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path,obj):Path(path).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')


def plain(q):
    assert q.denominator & (q.denominator-1)==0
    with localcontext() as ctx:
        ctx.prec=max(100,len(str(abs(q.numerator)))+q.denominator.bit_length()+5)
        d=Decimal(q.numerator)/Decimal(q.denominator)
    assert Fraction(d)==q
    return format(d,'f')


def exact_check(model,point):
    assert len(point)==len(model['variables'])
    values=[Fraction(x) for x in point];violations=[]
    for j,row in enumerate(model['rows']):
        signed=sum((F(float(c))*values[int(i)] for i,c in row['terms'].items()),Fraction(0))-F(float(row['rhs']))
        violation=abs(signed) if row['sense']=='=' else max(Fraction(0),signed if row['sense']=='<' else -signed)
        if violation:violations.append((j,str(violation)))
    bad_bounds=[];bad_domains=[]
    for j,(x,v) in enumerate(zip(values,model['variables'])):
        if v['lower'] is not None and x<F(float(v['lower'])):bad_bounds.append(j)
        if v['upper'] is not None and x>F(float(v['upper'])):bad_bounds.append(j)
        if v['integer'] and x.denominator!=1:bad_domains.append(j)
    objective=sum((F(float(v['cost']))*x for x,v in zip(values,model['variables'])),Fraction(0))
    return {'exact_feasible':not violations and not bad_bounds and not bad_domains,
        'row_violations':violations,'bound_violations':bad_bounds,'integer_domain_violations':bad_domains,
        'rows_checked':len(model['rows']),'variables_checked':len(values),
        'objective_exact':str(objective),'objective_for_display':float(objective),
        'scope':'exact feasible point of original binary64 model; no MILP optimality certificate'}


def delivery_check(model,point):
    try:binary64=[float(Fraction(x)) for x in point]
    except (OverflowError,ValueError):return {'primal_accepted':False,'reason':'nonfinite_delivery'},None
    if not all(math.isfinite(x) for x in binary64):return {'primal_accepted':False,'reason':'nonfinite_delivery'},None
    result=verify_point(model,binary64)
    bad=[]
    for j,(x,v) in enumerate(zip(binary64,model['variables'])):
        if v['integer']:
            q=F(x)
            if q.denominator!=1 or v['lower'] is not None and q<F(float(v['lower'])) or v['upper'] is not None and q>F(float(v['upper'])):bad.append(j)
    result['exact_integer_domain_failures']=bad
    result['primal_accepted']=result['primal_accepted'] and not bad
    return result,binary64


def fixed_subproblem(model,point):
    assert len(point)==len(model['variables']) and all(math.isfinite(float(x)) for x in point)
    integers={str(j):int(round(float(x))) for j,(x,v) in enumerate(zip(point,model['variables'])) if v['integer']}
    for i,x in integers.items():
        v=model['variables'][int(i)]
        if v['lower'] is not None and x<F(float(v['lower'])) or v['upper'] is not None and x>F(float(v['upper'])):
            return {'failure':'fixed_integer_outside_exact_domain','variable':i,'value':x,'integers':integers}
    continuous=[j for j,v in enumerate(model['variables']) if not v['integer']]
    rows=[];omitted=[]
    for j,row in enumerate(model['rows']):
        rhs=F(float(row['rhs']))-sum((F(float(c))*integers[i] for i,c in row['terms'].items() if i in integers),Fraction(0))
        terms={i:F(float(c)) for i,c in row['terms'].items() if i not in integers and c}
        if not terms:
            valid=rhs==0 if row['sense']=='=' else rhs>=0 if row['sense']=='<' else rhs<=0
            if not valid:return {'failure':'fixed_integer_contradicts_constant_row','row':j,'rhs_exact':str(rhs),'integers':integers}
            omitted.append(j);continue
        rows.append({'row':j,'terms':terms,'rhs':rhs,'sense':row['sense']})
    return {'integers':integers,'continuous':continuous,'rows':rows,'omitted_rows':omitted}


def write_fixed_lp(path,model,fixed,rational):
    number=plain if rational else lambda q:format(float(q),'.17g')
    def expression(terms):
        return ' '.join(f'{"+" if c>=0 else "-"} {number(abs(c))} y{int(i)}' for i,c in terms.items() if c)
    costs={str(j):F(float(model['variables'][j]['cost'])) for j in fixed['continuous']}
    objective=expression(costs) or ('+ 0 y'+str(fixed['continuous'][0]))
    lines=['Minimize',' obj: '+objective,'Subject To']
    for row in fixed['rows']:
        sense={'<':'<=','>':'>=','=':'='}[row['sense']]
        lines.append(f' r{row["row"]}: {expression(row["terms"])} {sense} {number(row["rhs"])}')
    lines.append('Bounds')
    for j in fixed['continuous']:
        v=model['variables'][j];lo=v['lower'];hi=v['upper'];name='y'+str(j)
        if lo is None and hi is None:lines.append(f' {name} free')
        elif lo is None:lines.extend([f' {name} free',f' {name} <= {number(F(float(hi)))}'])
        elif hi is None:lines.append(f' {name} >= {number(F(float(lo)))}')
        else:lines.append(f' {number(F(float(lo)))} <= {name} <= {number(F(float(hi)))}')
    lines.append('End');Path(path).write_text('\n'.join(lines)+'\n')


def unary_delivery_obstructions(model,fixed):
    """Necessary binary64 feasibility certificates for single-variable equalities."""
    certificates=[]
    if 'failure' in fixed:return certificates
    for row in fixed['rows']:
        if row['sense']!='=' or len(row['terms'])!=1:continue
        name,a=next(iter(row['terms'].items()));q=row['rhs']/a
        try:nearest=float(q)
        except OverflowError:continue
        if not math.isfinite(nearest) or F(nearest)==q:continue
        below,above=(nearest,math.nextafter(nearest,math.inf)) if F(nearest)<q else (math.nextafter(nearest,-math.inf),nearest)
        if not math.isfinite(below) or not math.isfinite(above):continue
        errors=[abs(a*F(x)-row['rhs']) for x in (below,above)]
        budget=F(float(model['rows'][row['row']]['budget']))
        if min(errors)>budget:
            certificates.append({'row':row['row'],'continuous_variable':name,
                'coefficient_exact':str(a),'fixed_rhs_exact':str(row['rhs']),
                'required_rational_value':str(q),'lower_neighbor_hex':below.hex(),'upper_neighbor_hex':above.hex(),
                'minimum_binary64_residual':str(min(errors)),'budget_exact':str(budget),
                'scope':'no binary64 assignment with these fixed integers can satisfy this original row budget'})
    return certificates


def repair(model,point,out,mode='floating',limit=2.):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);started=time.perf_counter()
    fixed=fixed_subproblem(model,point)
    result={'mode':mode,'time_limit_seconds':limit,'delivered':False,'exact_feasible':False}
    if 'failure' in fixed:
        dump(out/'fixed-assignment-obstruction.json',fixed)
        result.update(outcome=fixed['failure'],total_seconds=time.perf_counter()-started)
        dump(out/'repair.json',result);return result,None
    dump(out/'mapping.json',{'integers':fixed['integers'],'continuous':fixed['continuous'],
        'omitted_rows':fixed['omitted_rows'],'original_model_digest':hashlib.sha256(json.dumps(model,sort_keys=True).encode()).hexdigest()})
    obstructions=unary_delivery_obstructions(model,fixed)
    dump(out/'binary64-delivery-obstructions.json',obstructions)
    result['unary_delivery_obstructions']=len(obstructions)
    lp=out/'fixed.lp';write_fixed_lp(lp,model,fixed,mode=='exact')
    result['lp_sha256']=sha(lp);result['preparation_seconds']=time.perf_counter()-started
    values=[Fraction(0)]*len(model['variables'])
    for i,x in fixed['integers'].items():values[int(i)]=Fraction(x)
    candidate=False;solve_started=time.perf_counter()
    if mode=='floating':
        import highspy
        h=highspy.Highs();h.setOptionValue('log_to_console',False);h.setOptionValue('log_file',str(out/'solver.log'))
        for key,value in {'threads':4,'presolve':'on','time_limit':float(limit),
                          'primal_feasibility_tolerance':1e-9,'dual_feasibility_tolerance':1e-9}.items():
            assert h.setOptionValue(key,value)==highspy.HighsStatus.kOk
        status=h.readModel(str(lp))
        if status!=highspy.HighsStatus.kError:
            h.run();solution=h.getSolution()
            result['reported_lp_status']=h.modelStatusToString(h.getModelStatus())
            if solution.value_valid:
                for name,x in zip(h.getLp().col_names_,solution.col_value):values[int(name[1:])]=F(float(x))
                candidate=True
        else:result['reported_lp_status']='import error'
        result['solver_version']=h.version();h.clear()
    elif mode=='exact':
        settings=out/'exact.set'
        settings.write_text('int:syncmode = 1\nint:readmode = 1\nint:solvemode = 2\nint:checkmode = 2\nreal:feastol = 0\nreal:opttol = 0\nreal:timelimit = '+format(float(limit),'.17g')+'\n')
        command=[str(SOPLEX),'--loadset='+str(settings),'-X='+str(out/'rational-solution.txt'),str(lp)]
        with (out/'solver.log').open('w') as stream:
            try:process=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=max(1.,limit+2.))
            except subprocess.TimeoutExpired:process=None;result['reported_lp_status']='external timeout'
        result['returncode']=process.returncode if process is not None else None
        result['solver_binary_sha256']=sha(SOPLEX)
        path=out/'rational-solution.txt'
        if path.exists():
            text=path.read_text();active=False
            for line in text.splitlines():
                if 'Primal solution (name, value):' in line:active=True;candidate=True;continue
                if active and ('All other entries' in line or 'Dual solution' in line):break
                parts=line.split()
                if active and len(parts)==2 and parts[0].startswith('y') and parts[0][1:].isdigit():
                    values[int(parts[0][1:])]=Fraction(parts[1])
        result['solver_version']='SoPlex 8.1.0, GMP 6.2.1'
    else:raise ValueError('Unknown repair mode')
    result['solver_seconds']=time.perf_counter()-solve_started
    check_started=time.perf_counter()
    if candidate:
        check=exact_check(model,values);delivery,binary64=delivery_check(model,values)
        dump(out/'rational-point.json',[str(x) for x in values]);dump(out/'exact-check.json',check)
        dump(out/'delivery-check.json',delivery)
        result.update(exact_feasible=check['exact_feasible'],delivered=delivery['primal_accepted'],
            exact_objective=check['objective_exact'],objective=check['objective_for_display'],
            maximum_delivery_ratio=delivery.get('integer_rounded',{}).get('maximum_row_budget_ratio'))
        if delivery['primal_accepted']:
            with (out/'delivered.npz').open('wb') as stream:np.savez_compressed(stream,x=np.array(binary64))
    else:binary64=None
    result['verification_seconds']=time.perf_counter()-check_started
    result['total_seconds']=time.perf_counter()-started
    result['outcome']='verified_delivery' if result['delivered'] else 'no_verified_delivery'
    dump(out/'repair.json',result)
    return result,binary64 if result['delivered'] else None


def calibrate():
    folder=HERE/'development-repair';folder.mkdir(exist_ok=True)
    model=json.loads((PILOT/'pilot/models/control30-3-2-3/original-model.json').read_text())
    source=PILOT/'pilot/runs/control30-3-2-3/gurobi-Base/solution.npz'
    with np.load(source,allow_pickle=False) as data:point=data['x']
    results=[]
    for mode,limit in (('floating',2.),('exact',10.)):
        result,_=repair(model,point,folder/mode,mode,limit);results.append(result)
        print(mode,result,flush=True)
    dump(folder/'summary.json',{'source_point_sha256':sha(source),'stage':'development only; excluded from prospectively assessed outcomes','results':results})


if __name__=='__main__':calibrate()
