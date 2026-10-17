#!/usr/bin/env python3
"""Post-observation check, one exact feasibility LP; never a new MIP arm."""
from decimal import Decimal,localcontext
from fractions import Fraction as Q
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import time

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
SOPLEX=ROOT/'exploration/oms-followup-20261014/tools/soplex-build/bin/soplex'


def read(p):
    b=Path(p).read_bytes();return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)


def decimal(q):
    q=Q(q);assert q.denominator & (q.denominator-1)==0
    with localcontext() as ctx:
        ctx.prec=len(str(abs(q.numerator)))+q.denominator.bit_length()+20
        result=format(Decimal(q.numerator)/Decimal(q.denominator),'f')
    assert Q(result)==q;return result


def main():
    folder=HERE/'exact-witness';folder.mkdir(exist_ok=True)
    candidates=[]
    for p in (HERE/'runs/discovery').glob('instance001-*.json.gz'):
        if '-diagnostic' in p.name or '-presolved' in p.name:continue
        r=read(p)
        if r['point'] is not None:candidates.append((r['objective'],str(p.relative_to(HERE)),r))
    _,source,run=min(candidates,key=lambda t:(t[0],t[1]))
    data=read(HERE/'inputs/instance001/canonical.json.gz')
    integers={j:Q(round(x)) for j,(x,v) in enumerate(zip(run['point'],data['variables'])) if v['type']!='C'}
    assert all(abs(run['point'][j]-z)<1e-5 for j,z in integers.items())
    continuous=[j for j,v in enumerate(data['variables']) if v['type']=='C'];idx={j:i for i,j in enumerate(continuous)}
    rows=[]
    for r in data['rows']:
        rhs=Q(r['rhs'])-sum(Q(a)*integers[j] for j,a in r['terms'] if j in integers)
        terms={idx[j]:Q(a) for j,a in r['terms'] if j in idx}
        for sign in ([1,-1] if r['sense']=='=' else [1] if r['sense']=='<' else [-1]):
            rows.append(({i:sign*a for i,a in terms.items()},sign*rhs))
    for j in continuous:
        v=data['variables'][j]
        if v['lb'] is not None:rows.append(({idx[j]:Q(-1)},-Q(v['lb'])))
        if v['ub'] is not None:rows.append(({idx[j]:Q(1)},Q(v['ub'])))
    fixed=Q(data['constant'])+sum(Q(data['variables'][j]['obj'])*z for j,z in integers.items())
    rows.append(({idx[j]:Q(data['variables'][j]['obj']) for j in continuous if data['variables'][j]['obj']},-fixed))
    def expr(terms):
        return ' '.join(('+' if a>0 else '-')+' '+decimal(abs(a))+f' x{j:05d}' for j,a in terms.items() if a) or '0 x00000'
    lines=['Minimize',' obj: 0 x00000','Subject To']
    lines += [f' r{i:05d}: '+expr(a)+' <= '+decimal(b) for i,(a,b) in enumerate(rows)]
    lines += ['Bounds']+[f' x{j:05d} free' for j in range(len(continuous))]+['End']
    (folder/'feasibility.lp').write_text('\n'.join(lines)+'\n')
    settings='int:syncmode = 1\nint:readmode = 1\nint:solvemode = 2\nint:checkmode = 2\nreal:feastol = 0\nreal:opttol = 0\nreal:timelimit = 30\n'
    (folder/'exact.set').write_text(settings)
    command=[str(SOPLEX),'--loadset='+str(folder/'exact.set'),'-X='+str(folder/'primal.txt'),str(folder/'feasibility.lp')]
    start=time.perf_counter()
    with (folder/'solver.log').open('w') as f:
        try:p=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,timeout=45);returncode=p.returncode
        except subprocess.TimeoutExpired:returncode=None
    result=dict(stage='post-observation exact feasibility check; excluded from factorial timing',source=source,
                instance='instance001',time_limit=30,watchdog=45,seconds=time.perf_counter()-start,returncode=returncode,
                solver_sha256=hashlib.sha256(SOPLEX.read_bytes()).hexdigest(),outcome='unknown',
                objective_cap=0,claim='A feasible witness only, never a proof of MILP optimality')
    vector={};active=False
    if (folder/'primal.txt').exists():
        for line in (folder/'primal.txt').read_text().splitlines():
            if 'Primal solution (name, value):' in line:active=True;continue
            if active and line.startswith('All other'):break
            t=line.split()
            if active and len(t)==2 and t[0].startswith('x') and t[0][1:].isdigit():vector[int(t[0][1:])]=Q(t[1])
    if vector:
        assert all(i<len(continuous) for i in vector)
        q=[vector.get(i,Q(0)) for i in range(len(continuous))]
        if all(sum(a*q[j] for j,a in row.items())<=rhs for row,rhs in rows):
            full=[integers[j] if j in integers else q[idx[j]] for j in range(len(data['variables']))]
            (folder/'rational-point.json').write_text(json.dumps(list(map(str,full)))+'\n')
            objective=Q(data['constant'])+sum(Q(v['obj'])*x for v,x in zip(data['variables'],full))
            result.update(outcome='exact_feasible',objective_exact=str(objective),objective=float(objective))
    (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
