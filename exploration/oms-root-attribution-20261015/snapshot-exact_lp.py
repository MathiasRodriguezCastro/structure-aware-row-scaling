"""Fixed-integer rational LP acquisition and independent primal/dual checking."""
from decimal import Decimal,localcontext
from fractions import Fraction as Q
from pathlib import Path
import subprocess
import time
from common import dump,sha,exact_feasibility


def decimal(q):
    q=Q(q);assert q.denominator&(q.denominator-1)==0
    with localcontext() as ctx:
        ctx.prec=len(str(abs(q.numerator)))+q.denominator.bit_length()+20
        s=format(Decimal(q.numerator)/Decimal(q.denominator),'f')
    assert Q(s)==q;return s


def construct(data,pattern):
    integers={int(j):Q(v) for j,v in pattern.items()}
    assert set(integers)=={j for j,v in enumerate(data['variables']) if v['type']!='C'}
    assert all(z.denominator==1 for z in integers.values())
    indices=[j for j,v in enumerate(data['variables']) if v['type']=='C'];idx={j:i for i,j in enumerate(indices)}
    rows=[]
    for r in data['rows']:
        rhs=Q(r['rhs'])-sum(Q(a)*integers[j] for j,a in r['terms'] if j in integers)
        terms={str(idx[j]):str(Q(a)) for j,a in r['terms'] if j in idx}
        for sign in ([1,-1] if r['sense']=='=' else [1] if r['sense']=='<' else [-1]):
            rows.append(dict(terms={j:str(sign*Q(a)) for j,a in terms.items()},rhs=str(sign*rhs),source=r['name']))
    for j in indices:
        v=data['variables'][j]
        for key,sign in (('lb',-1),('ub',1)):
            if v[key] is not None:rows.append(dict(terms={str(idx[j]):str(sign)},rhs=str(sign*Q(v[key])),source=v['name']+':'+key))
    return dict(cost=[str(Q(data['variables'][j]['obj'])) for j in indices],
                offset=str(Q(data['constant'])+sum(Q(data['variables'][j]['obj'])*z for j,z in integers.items())),
                rows=rows,continuous_indices=indices,integers={str(j):str(z) for j,z in integers.items()})


def export(lp,path):
    def expr(terms):
        return ' '.join(('+' if Q(a)>0 else '-')+' '+decimal(abs(Q(a)))+f' x{int(j):05d}' for j,a in terms.items() if Q(a)) or '0 x00000'
    lines=['Minimize',' obj: '+expr(dict(enumerate(lp['cost']))),'Subject To']
    lines += [f' r{i:05d}: '+expr(r['terms'])+' <= '+decimal(r['rhs']) for i,r in enumerate(lp['rows'])]
    lines += ['Bounds']+[f' x{i:05d} free' for i in range(len(lp['cost']))]+['End']
    path.write_text('\n'.join(lines)+'\n')


def parse(path,header,prefix):
    active=False;found=False;v={}
    if not path.exists():return None
    for line in path.read_text().splitlines():
        if header in line:active=found=True;continue
        if active and (line.startswith('All other') or 'Reduced costs' in line):break
        t=line.split()
        if active and len(t)==2 and t[0].startswith(prefix) and t[0][len(prefix):].isdigit():v[str(int(t[0][len(prefix):]))]=str(Q(t[1]))
    return v if found else None


def verify(lp,primal,dual):
    q=list(map(Q,primal));assert len(q)==len(lp['cost']);pi={int(j):Q(x) for j,x in (dual or {}).items()}
    assert all(0<=j<len(lp['rows']) for j in pi)
    primal_ok=True;reduced=list(map(Q,lp['cost']));lb=Q(lp['offset'])
    for i,r in enumerate(lp['rows']):
        primal_ok &= sum(Q(a)*q[int(j)] for j,a in r['terms'].items())<=Q(r['rhs'])
        p=pi.get(i,Q(0));lb+=p*Q(r['rhs'])
        for j,a in r['terms'].items():reduced[int(j)]-=p*Q(a)
    dual_ok=dual is not None and all(x<=0 for x in pi.values()) and not any(reduced)
    value=Q(lp['offset'])+sum(Q(c)*x for c,x in zip(lp['cost'],q))
    return dict(primal_feasible=bool(primal_ok),dual_feasible=bool(dual_ok),optimum_certified=bool(primal_ok and dual_ok and value==lb),
                primal_value_exact=str(value),dual_value_exact=str(lb))


def acquire(data,pattern,folder,binary,limit=5.):
    folder.mkdir(parents=True,exist_ok=True);start=time.perf_counter();lp=construct(data,pattern)
    dump(folder/'lp.json.gz',lp);export(lp,folder/'fixed.lp')
    result=dict(outcome='unknown',native_lp_called=False,time_limit=limit,solver_seconds=0.,
                pattern={str(j):str(z) for j,z in pattern.items()},solver_sha256=sha(binary))
    for r in lp['rows']:
        if not r['terms'] and Q(r['rhs'])<0:
            result.update(outcome='infeasible_constant_row',contradiction=r,total_seconds=time.perf_counter()-start)
            dump(folder/'result.json',result);return result
    (folder/'exact.set').write_text('int:syncmode = 1\nint:readmode = 1\nint:solvemode = 2\nint:checkmode = 2\nreal:feastol = 0\nreal:opttol = 0\nreal:timelimit = '+str(limit)+'\n')
    args=[str(binary),'--loadset='+str(folder/'exact.set'),'-X='+str(folder/'primal.txt'),'-Y='+str(folder/'dual.txt'),str(folder/'fixed.lp')]
    t=time.perf_counter()
    with (folder/'solver.log').open('w') as f:
        try:p=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,timeout=limit+3);rc=p.returncode
        except subprocess.TimeoutExpired:rc=None
    result.update(native_lp_called=True,returncode=rc,solver_seconds=time.perf_counter()-t)
    primal=parse(folder/'primal.txt','Primal solution (name, value):','x')
    dual=parse(folder/'dual.txt','Dual solution (name, value):','r')
    if primal is not None:
        q=[primal.get(str(j),'0') for j in range(len(lp['cost']))]
        certificate=verify(lp,q,dual);dump(folder/'certificate.json',certificate)
        dump(folder/'primal.json',q);dump(folder/'dual.json',dual)
        if certificate['primal_feasible']:
            index={j:i for i,j in enumerate(lp['continuous_indices'])}
            full=[Q(pattern[str(j)] if str(j) in pattern else pattern[j]) if j not in index else Q(q[index[j]]) for j in range(len(data['variables']))]
            dump(folder/'rational-point.json',list(map(str,full)))
            direct=exact_feasibility(data,full);assert direct['exact_feasible']
            result.update(outcome='optimum_certified' if certificate['optimum_certified'] else 'exact_primal_only',**direct)
    result['total_seconds']=time.perf_counter()-start;dump(folder/'result.json',result);return result
