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


def shift_range(x):
    n,d=abs(float(x)).as_integer_ratio();trail=(n&-n).bit_length()-1
    return -1074-(trail-(d.bit_length()-1)),1023-(n.bit_length()-d.bit_length())


def row_radius_interval(g,epsilon=1e-6,gamma_sos=1e-5,tau=1e-6):
    """Necessary and sufficient integer interval for one exact dyadic link."""
    values=[abs(F(float(v))) for v in g['g'].values() if v]
    if not values:raise ValueError('nonconstant continuous activity required')
    M=F(float(g['M']));delta=F(float(g['delta']));eps=F(epsilon)
    T=max(F(gamma_sos),F(tau));slo,shi=shift_range(float(M))
    A=min(1023,flog(HIGH/max(values)),*(shift_range(float(v))[1] for v in values))
    C=max(-1074,clog(LOW/min(values)),*(shift_range(float(v))[0] for v in values))
    B=min(flog(HIGH/M),shi);D=max(clog(LOW/M),slo)
    P=eps*pow2(-A);Q=eps*pow2(-B);MT=M*T
    certificate={'row':g['row'],'A':A,'B':B,'C':C,'D':D,'P':str(P),'Q':str(Q),
                 'MT':str(MT),'delta':str(delta),'M_shift_range':[slo,shi]}
    if A<C or B<D or delta<=P:
        return {**certificate,'compatible':False,'reason':'row_window_or_precision_floor'}
    low=max(-1074,-shi,C-B,clog(MT/(delta-P)),clog((Q+MT)/delta))
    high=min(1023,flog(CAP),-slo,A-D)
    return {**certificate,'compatible':low<=high,'lower_r':low,'upper_r':high,
            'reason':'integer_interval' if low<=high else 'empty_integer_interval'}


def select_shared(group,epsilon=1e-6,gamma_sos=1e-5,tau=1e-6):
    certificates=[row_radius_interval(g,epsilon,gamma_sos,tau) for g in group]
    if not all(c['compatible'] for c in certificates):
        return {'compatible':False,'reason':'row_radius_incompatible','certificates':certificates}
    low=max(c['lower_r'] for c in certificates);high=min(c['upper_r'] for c in certificates)
    if low>high:
        return {'compatible':False,'reason':'shared_radius_intersection_empty','lower_r':low,
                'upper_r':high,'certificates':certificates}
    R=pow2(low);T=max(F(gamma_sos),F(tau));decisions=[]
    for g in group:
        h=exact(F(float(g['M']))/R)
        assert h is not None
        alpha=factor([*g['g'].values(),-h],delta=F(float(g['delta'])),reserve=F(h)*T,epsilon=epsilon)
        assert alpha is not None
        decisions.append({'row':g['row'],'h':h,'alpha':alpha,
                          'bound':str(F(epsilon)/F(alpha)+F(h)*T)})
    return {'compatible':True,'radius':float(R),'r':low,'decisions':decisions,
            'lower_r':low,'upper_r':high,'certificates':certificates}


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
