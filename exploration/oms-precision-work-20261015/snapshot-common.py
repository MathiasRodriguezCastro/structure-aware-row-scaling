"""Dyadic selection, physical metadata and exact integer dot products."""
from fractions import Fraction as Q
import gzip
import hashlib
import json
import math
import re

SCENARIOS={'Demanding':(.01,100.),'Reference':(.1,1000.),'Permissive':(1.,10000.)}
GAMMA=1e-9


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):
    b=p.read_bytes();return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)
def dump(p,v):
    b=(json.dumps(v,indent=2,allow_nan=False)+'\n').encode()
    p.write_bytes(gzip.compress(b,mtime=0) if str(p).endswith('.gz') else b)
def pow2(k):return Q(2**k) if k>=0 else Q(1,2**(-k))
def logfloor(q):
    k=q.numerator.bit_length()-q.denominator.bit_length();return k-1 if pow2(k)>q else k


def units(row,variables):
    n=row['name'];a={variables[j]['name']:v for j,v in row['terms']}
    if n.startswith(('gh_total(','gen_menor_demanda(')):
        return 'MW',Q(abs(a['g'+n[n.index('('):]]))
    agent=n.split('_')[0];t=n[n.index('('):] if '(' in n else ''
    if re.fullmatch(r'a\d+_g4h_def\(\d+\)',n):
        return 'MW',Q(abs(a['g'+agent[1:]+t]))
    if re.fullmatch(r'a\d+_salto_grande_tangente_\d+\(\d+\)',n):
        return 'MW',Q(abs(a[agent+'_z4h'+t]))
    if re.fullmatch(r'a\d+_balance\(\d+\)',n):
        values=[Q(abs(c)) for v,c in a.items() if v.startswith(agent+'_v4h(')]
        assert values and len(set(values))==1;return 'm3',values[0]
    if re.fullmatch(r'a\d+_activacion_[1-4]\(\d+\)',n):
        assert row['sense']=='<' and len(a)==2 and a[agent+'_v4h'+t]==-1.
        return 'm3',Q(1)
    return None


def exponent(row,kernel,remaining=None):
    nz=[abs(a) for _,a in row['terms'] if a];m,M=min(nz),max(nz)
    lower=Q(1e-9)/Q(m);upper=Q(1e9)/Q(M)
    if remaining is not None:
        if remaining<=0:return None
        lower=max(lower,Q(1e-6)/remaining)
    kl=logfloor(lower);kl+=pow2(kl)<lower;kh=logfloor(upper)
    for v in nz+[row['rhs']]:
        if not v:continue
        num,den=abs(float(v)).as_integer_ratio()
        odd=(num&-num).bit_length()-1-(den.bit_length()-1)
        kl=max(kl,-1074-odd);kh=min(kh,1023-(math.frexp(abs(v))[1]-1))
    if kl>kh:return None
    if kernel=='gm':
        b=(-logfloor(Q(m)*Q(M))-1)//2
        choices={min(kh,max(kl,b)),min(kh,max(kl,b+1))}
        return min(choices,key=lambda k:(max(pow2(k)*Q(M),1/(pow2(k)*Q(m))),-k))
    proposal=1/math.sqrt(math.fsum(v*v for v in nz)) if kernel=='l2' else M**(-15/16)
    k=math.floor(math.log2(proposal)+.5)
    return min(kh,max(kl,k))


def choose(data,policy):
    variables=data['variables'];ex=[];incompatible=[]
    for row in data['rows']:
        if policy in ('Base','Tight','GCD'):ex.append(0);continue
        remaining=None
        if policy.startswith('Budget-'):
            spec=units(row,variables)
            if spec:
                p,w=SCENARIOS[policy.split('-')[1]]
                reserve=Q(GAMMA)*sum(Q(abs(a)) for j,a in row['terms'] if variables[j]['type']!='C')
                remaining=Q(p if spec[0]=='MW' else w)*spec[1]-reserve
        k=exponent(row,'gm' if policy=='GM' else 'ruiz' if policy=='Ruiz' else 'l2',remaining)
        if k is None:incompatible.append(row['name']);k=0
        ex.append(k)
    return ex,incompatible


def gcd_audit(data):
    eligible=0;changed=[]
    for row in data['rows']:
        if all(data['variables'][j]['type']!='C' and float(a).is_integer() for j,a in row['terms']):
            eligible+=1;g=math.gcd(*(abs(int(a)) for _,a in row['terms']))
            if g!=1 or not float(row['rhs']).is_integer():changed.append(row['name'])
    # The frozen bank has only primitive binary-order rows. Do not silently
    # alias a genuine reformulation on a future different model.
    assert not changed,('implement actual GCD transformation before using another bank',changed)
    return dict(eligible_rows=eligible,changed_rows=0,identical_to_base=True)


def canonical(m):
    variables=m.getVars();A=m.getA().tocsr()
    return dict(sense=m.ModelSense,constant=m.ObjCon or 0.,
        variables=[dict(name=v.VarName,lb=v.LB if math.isfinite(v.LB) else None,
                        ub=v.UB if math.isfinite(v.UB) else None,obj=v.Obj,type=v.VType) for v in variables],
        rows=[dict(name=c.ConstrName,sense=c.Sense,rhs=c.RHS,
                   terms=[[int(j),float(a)] for j,a in zip(A.indices[A.indptr[i]:A.indptr[i+1]],A.data[A.indptr[i]:A.indptr[i+1]])])
              for i,c in enumerate(m.getConstrs())])


def build(data,ex,env):
    import gurobipy as gp
    m=gp.Model(env=env)
    vs=[m.addVar(lb=v['lb'] if v['lb'] is not None else -gp.GRB.INFINITY,
                ub=v['ub'] if v['ub'] is not None else gp.GRB.INFINITY,
                obj=v['obj'],vtype=v['type'],name=v['name']) for v in data['variables']]
    m.ModelSense=data['sense'];m.ObjCon=data['constant'];m.update()
    for r,k in zip(data['rows'],ex):
        expr=gp.LinExpr([math.ldexp(a,k) for _,a in r['terms']],[vs[j] for j,_ in r['terms']])
        m.addLConstr(expr,r['sense'],math.ldexp(r['rhs'],k),r['name'])
    m.update();return m


class ExactData:
    """Align dyadic denominators once; each subsequent dot product uses ints.

    This is exact binary64-data arithmetic, not a floating error bound. No
    claim of novelty: exponent alignment is an elementary exact accumulator.
    """
    def __init__(self,data):
        self.data=data;self.qrows=[];allq=[Q(data['constant']),Q(1e-6)]
        for r in data['rows']:
            spec=units(r,data['variables'])
            budgets=[Q(p if spec[0]=='MW' else w)*spec[1] for p,w in SCENARIOS.values()] if spec else [Q(1e-8)*max(Q(1),abs(Q(r['rhs'])))]
            terms=[(j,Q(a)) for j,a in r['terms']]
            self.qrows.append((r,terms,budgets,bool(spec)))
            allq.extend([Q(r['rhs']),*budgets,*[a for _,a in terms]])
        for v in data['variables']:allq.extend(Q(v[k]) for k in ('lb','ub','obj') if v[k] is not None)
        self.e=max(q.denominator.bit_length()-1 for q in allq)
        def integer(q):
            q=Q(q);return q.numerator<<(self.e-(q.denominator.bit_length()-1))
        self.rows=[(r,[(j,integer(a)) for j,a in terms],integer(r['rhs']),[integer(b) for b in budgets],phy)
                   for r,terms,budgets,phy in self.qrows]
        self.variables=[(v,None if v['lb'] is None else integer(v['lb']),None if v['ub'] is None else integer(v['ub']),integer(v['obj'])) for v in data['variables']]
        self.constant=integer(data['constant']);self.bound_budget=integer(Q(1e-6))

    def check(self,point):
        ratios=[float(x).as_integer_ratio() for x in point]
        ex=max(d.bit_length()-1 for _,d in ratios);xs=[n<<(ex-(d.bit_length()-1)) for n,d in ratios]
        maxint=Q(0)
        for j,(v,_,_,_) in enumerate(self.variables):
            if v['type']!='C':
                z=round(float(point[j]));maxint=max(maxint,abs(Q(float(point[j]))-z));xs[j]=z<<ex
        den=1<<(self.e+ex);physical=[(0,1)]*3;aux=(0,1);maximum=0;worst='';bounds=0
        for r,terms,b,ds,phy in self.rows:
            res=sum(a*xs[j] for j,a in terms)-(b<<ex)
            viol=abs(res) if r['sense']=='=' else max(0,res if r['sense']=='<' else -res)
            if viol>maximum:maximum=viol;worst=r['name']
            for j,d in enumerate(ds):
                target=physical[j] if phy else aux
                if viol*target[1]>target[0]*d:
                    if phy:physical[j]=(viol,d)
                    else:aux=(viol,d)
        for x,(v,lo,hi,_) in zip(xs,self.variables):
            if lo is not None:bounds=max(bounds,(lo<<ex)-(x<<self.e))
            if hi is not None:bounds=max(bounds,(x<<self.e)-(hi<<ex))
        objective=sum(c*x for x,(_,_,_,c) in zip(xs,self.variables))+(self.constant<<ex)
        qs=[Q(n,d<<ex) for n,d in physical];auxq=Q(aux[0],aux[1]<<ex)
        return dict(objective_exact=str(Q(objective,den)),objective=float(Q(objective,den)),
                    physical_ratios_exact=list(map(str,qs)),physical_ratios=list(map(float,qs)),
                    max_auxiliary_budget_ratio_exact=str(auxq),max_auxiliary_budget_ratio=float(auxq),
                    max_original_row_residual=float(Q(maximum,den)),worst_row=worst,
                    max_bound_residual=float(Q(bounds,den)),raw_integrality_residual=float(maxint),
                    auxiliary_pass=auxq<=1,bounds_pass=bounds<=(self.bound_budget<<ex))


def exact_feasibility(data,point):
    q=list(map(Q,point));worst=Q(0)
    for r in data['rows']:
        res=sum(Q(a)*q[j] for j,a in r['terms'])-Q(r['rhs'])
        violation=abs(res) if r['sense']=='=' else max(Q(0),res if r['sense']=='<' else -res)
        worst=max(worst,violation)
    bounds=all((v['lb'] is None or x>=Q(v['lb'])) and (v['ub'] is None or x<=Q(v['ub'])) for v,x in zip(data['variables'],q))
    integers=all(v['type']=='C' or x.denominator==1 for v,x in zip(data['variables'],q))
    cost=Q(data['constant'])+sum(Q(v['obj'])*x for v,x in zip(data['variables'],q))
    return dict(exact_feasible=worst==0 and bounds and integers,objective_exact=str(cost),objective=float(cost),
                max_residual_exact=str(worst),bounds_ok=bounds,integers_ok=integers)
