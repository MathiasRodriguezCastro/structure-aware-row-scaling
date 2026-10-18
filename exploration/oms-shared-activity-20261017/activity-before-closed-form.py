"""Budget-constrained normalized activity blocks, exact binary64 exports."""
from fractions import Fraction
import math

F=Fraction.from_float
LOW,HIGH,CAP=F(1e-9),F(1e9),F(1e19)


def pow2(k):return Fraction(2)**k


def flog(q):
    if q<=0:raise ValueError('positive value required')
    k=q.numerator.bit_length()-q.denominator.bit_length()
    return k-int(pow2(k)>q)


def clog(q):
    k=flog(q);return k+int(pow2(k)<q)


def exact(q):
    try:x=float(q)
    except OverflowError:return None
    return x if math.isfinite(x) and F(x)==q else None


def factor(terms,rhs=0.,delta=None,reserve=Fraction(0),epsilon=1e-6):
    a=[abs(F(float(x))) for x in terms if x]
    if not a:raise ValueError('constant rows are not supported')
    lo,hi=clog(LOW/min(a)),flog(HIGH/max(a))
    if delta is not None:
        remaining=delta-reserve
        if remaining<=0:return None
        lo=max(lo,clog(F(float(epsilon))/remaining))
    for x in [*terms,rhs]:
        if not x:continue
        n,d=abs(float(x)).as_integer_ratio();trail=(n&-n).bit_length()-1
        lo=max(lo,-1074-(trail-(d.bit_length()-1)));hi=min(hi,1023-(n.bit_length()-d.bit_length()))
    lo,hi=max(-1074,lo),min(1023,hi)
    if lo>hi:return None
    norm=sum((x*x for x in a),Fraction(0));mid=(-flog(norm))//2
    candidates={min(hi,max(lo,k)) for k in range(mid-1,mid+2)}
    def objective(k):
        q=norm*pow2(2*k);return max(q,1/q),-k
    alpha=float(pow2(min(candidates,key=objective)))
    assert all(exact(F(float(x))*F(alpha)) is not None for x in [*terms,rhs])
    return alpha


def gates(model):
    result=[]
    for i,row in enumerate(model['rows']):
        if row['rhs'] or row['sense']=='=':continue
        sign=1 if row['sense']=='<' else -1
        ints=[(int(j),sign*F(float(a))) for j,a in row['terms'].items() if model['variables'][int(j)]['integer']]
        if len(ints)!=1:continue
        z,a=ints[0];v=model['variables'][z]
        if a>=0 or (v['lower'],v['upper'])!=(0.,1.):continue
        result.append({'row':i,'z':z,'sign':sign,'M':float(-a),'delta':row['budget'],
                       'g':{j:sign*c for j,c in row['terms'].items() if int(j)!=z}})
    return result


def select_shared(group,epsilon=1e-6,gamma_sos=1e-5,tau=1e-6):
    T=max(F(gamma_sos),F(tau))
    threshold=max(F(float(g['M']))*T/F(float(g['delta'])) for g in group)
    first=max(-1074,flog(threshold))
    last=min(1023,flog(CAP))
    for r in range(first,last+1):
        R=pow2(r);decisions=[]
        for g in group:
            h=exact(F(float(g['M']))/R)
            if h is None:break
            alpha=factor([*g['g'].values(),-h],delta=F(float(g['delta'])),reserve=F(h)*T,epsilon=epsilon)
            if alpha is None:break
            decisions.append({'row':g['row'],'h':h,'alpha':alpha,
                              'bound':str(F(epsilon)/F(alpha)+F(h)*T)})
        if len(decisions)==len(group):
            return {'compatible':True,'radius':float(R),'r':r,'decisions':decisions}
    return {'compatible':False,'reason':'no_shared_radius_within_declared_window'}


def select_individual(g,epsilon=1e-6,gamma_sos=1e-5,tau=1e-6):
    T=max(F(gamma_sos),F(tau));delta=F(float(g['delta']));M=F(float(g['M']))
    for v in range(min(1023,flog(delta/T)),max(-1074,clog(M/CAP))-1,-1):
        h=pow2(v);upper=exact(M/h)
        if upper is None:continue
        alpha=factor([*g['g'].values(),-float(h)],delta=delta,reserve=h*T,epsilon=epsilon)
        if alpha is not None:
            return {'compatible':True,'h':float(h),'radius':upper,'alpha':alpha,
                    'bound':str(F(epsilon)/F(alpha)+h*T)}
    return {'compatible':False,'reason':'no_individual_activity_scale'}
