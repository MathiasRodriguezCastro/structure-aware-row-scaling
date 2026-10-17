#!/usr/bin/env python3
"""Construct and independently check an exact feasible MILP dispatch witness.

Fix saved binary states, substitute them, and solve the remaining LP exactly.
The LP coefficients are exact decimal expansions of original binary64 data.
The checker uses Fraction against every ORIGINAL row, bound and integer domain.
This proves feasibility and a primal objective value, never MILP optimality.
"""
import argparse
import csv
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts/research'))
import audit_fixed_basis as afb
from audit_identifiability_grid import parse
F=Fraction.from_float


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')


def decimal(q):
    assert q.denominator & (q.denominator-1)==0
    with localcontext() as ctx:
        ctx.prec=max(100,len(str(abs(q.numerator)))+q.denominator.bit_length()+5)
        value=Decimal(q.numerator)/Decimal(q.denominator)
    assert Fraction(value)==q
    # Keep the exact rational input independent of any exponent parser. In
    # SoPlex 8.1.0 the decimal-reader exponent path multiplies by pow(10,mult);
    # plain decimal expansion avoids that path. Fraction is the final authority.
    return format(value,'f')


def prepare(out,model,solution):
    out.mkdir(parents=True,exist_ok=True)
    rows,_=parse(model);_,lp,_=afb.read_lp(model)
    with np.load(solution,allow_pickle=False) as saved:
        point=dict(zip(saved['names'].tolist(),saved['x'].tolist()))
    integers={name:int(round(point[name])) for name,kind in zip(lp.col_names_,lp.integrality_)
              if str(kind)!='HighsVarType.kContinuous'}
    continuous=[name for name in lp.col_names_ if name not in integers]
    aliases={name:f'x{i}' for i,name in enumerate(continuous)}
    costs={name:F(float(cost)) for name,cost in zip(lp.col_names_,lp.col_cost_)}
    lines=['Minimize\n obj:\n']
    for name in continuous:
        if costs[name]:lines.append(f'  {"+" if costs[name]>=0 else ""}{decimal(costs[name])} {aliases[name]}\n')
    lines.append('Subject To\n');kept=0;skipped=[]
    for name,row in rows.items():
        rhs=F(float(row['rhs']))-sum((F(float(a))*integers[n] for n,a in row['terms'].items() if n in integers),Fraction(0))
        terms={n:F(float(a)) for n,a in row['terms'].items() if n not in integers and a}
        if not terms:
            assert (rhs>=0 if row['sense']=='<=' else rhs<=0 if row['sense']=='>=' else rhs==0),name
            skipped.append(name);continue
        lines.append(f' r{kept}:\n');kept+=1
        for n,a in terms.items():lines.append(f'  {"+" if a>=0 else ""}{decimal(a)} {aliases[n]}\n')
        lines.append(f'  {row["sense"]} {decimal(rhs)}\n')
    lines.append('Bounds\n')
    for name,low,high in zip(lp.col_names_,lp.col_lower_,lp.col_upper_):
        if name in integers:continue
        alias=aliases[name]
        if math.isinf(low) and math.isinf(high):lines.append(f' {alias} free\n')
        elif math.isinf(low):lines.extend((f' {alias} free\n',f' {alias} <= {decimal(F(float(high)))}\n'))
        elif math.isinf(high):lines.append(f' {alias} >= {decimal(F(float(low)))}\n')
        else:lines.append(f' {decimal(F(float(low)))} <= {alias} <= {decimal(F(float(high)))}\n')
    lines.append('End\n')
    (out/'fixed-original-binary64.lp').write_text(''.join(lines))
    dump(out/'mapping.json',{'original_model':str(model.relative_to(ROOT)),
        'original_model_sha256':sha(model),'saved_solution':str(solution.relative_to(ROOT)),
        'saved_solution_sha256':sha(solution),'integers':integers,'aliases':aliases,
        'omitted_constant_rows':skipped,'lp_rows':kept,'lp_columns':len(continuous),
        'definition':'each original LP decimal coefficient is first interpreted as binary64; the exact rational value of that binary64 number defines the certified model',
        'fixed_lp_sha256':sha(out/'fixed-original-binary64.lp')})
    print('Exact witness LP prepared',kept,'rows',len(continuous),'columns',flush=True)


def solve(out,binary):
    settings=out/'exact.set'
    settings.write_text('int:syncmode = 1\nint:readmode = 1\nint:solvemode = 2\nint:checkmode = 2\nreal:feastol = 0\nreal:opttol = 0\nreal:timelimit = 120\n')
    command=[str(binary),'--loadset='+str(settings),'-X='+str(out/'rational-solution.txt'),str(out/'fixed-original-binary64.lp')]
    with (out/'soplex.log').open('w') as log:
        result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    dump(out/'solver-provenance.json',{'command':command,'returncode':result.returncode,
        'binary_sha256':sha(binary),'source_release':'SoPlex v8.1.0',
        'source_url':'https://github.com/scipopt/soplex/releases/tag/v8.1.0',
        'fixed_lp_sha256':sha(out/'fixed-original-binary64.lp'),'settings_sha256':sha(settings)})
    assert result.returncode==0
    print('Exact LP solve returned; independent checking follows',flush=True)


def check(out):
    meta=json.loads((out/'mapping.json').read_text())
    model=ROOT/meta['original_model'];assert sha(model)==meta['original_model_sha256']
    rows,_=parse(model);_,lp,_=afb.read_lp(model)
    values={n:Fraction(v) for n,v in meta['integers'].items()}
    aliases={alias:name for name,alias in meta['aliases'].items()}
    values.update({name:Fraction(0) for name in aliases.values()})
    text=(out/'rational-solution.txt').read_text();assert 'Primal solution (name, value):' in text
    for line in text.splitlines():
        parts=line.split()
        if len(parts)==2 and parts[0] in aliases:values[aliases[parts[0]]]=Fraction(parts[1])
    assert set(values)==set(lp.col_names_)
    worst=Fraction(0)
    for name,row in rows.items():
        residual=sum((F(float(a))*values[n] for n,a in row['terms'].items()),Fraction(0))-F(float(row['rhs']))
        violation=abs(residual) if row['sense']=='=' else max(Fraction(0),residual if row['sense']=='<=' else -residual)
        assert violation==0,(name,str(violation))
        worst=max(worst,violation)
    for name,low,high,kind in zip(lp.col_names_,lp.col_lower_,lp.col_upper_,lp.integrality_):
        if math.isfinite(low):assert values[name]>=F(float(low)),name
        if math.isfinite(high):assert values[name]<=F(float(high)),name
        if str(kind)!='HighsVarType.kContinuous':assert values[name].denominator==1,name
    objective=sum((F(float(cost))*values[name] for name,cost in zip(lp.col_names_,lp.col_cost_)),F(float(lp.offset_)))
    dump(out/'exact-witness.json',{n:str(v) for n,v in values.items()})
    result={'original_rows_checked':len(rows),'variables_checked':len(values),'integer_variables_checked':len(meta['integers']),
        'exact_original_row_violations':0,'exact_bound_violations':0,'exact_integrality_violations':0,
        'objective_exact_fraction':str(objective),'objective_float_for_display':float(objective),
        'witness_sha256':sha(out/'exact-witness.json'),'original_model_sha256':sha(model),
        'scope':'exact feasible point and primal upper bound of original binary64-data MILP; not a global optimality certificate'}
    dump(out/'independent-certificate.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='objective_exact_fraction'},indent=2),flush=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=('prepare','solve','check'))
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--model',type=Path);ap.add_argument('--solution',type=Path)
    ap.add_argument('--soplex',type=Path);args=ap.parse_args();out=args.out.resolve()
    if args.stage=='prepare':prepare(out,args.model.resolve(),args.solution.resolve())
    elif args.stage=='solve':solve(out,args.soplex.resolve())
    else:check(out)


if __name__=='__main__':main()
