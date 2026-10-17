"""Exact selector for redundant integer copies; preserves projected LP/MILP."""
from fractions import Fraction
import math

F=Fraction.from_float
EPS,GAMMA=F(1e-6),F(1e-9)
LOW,HIGH=F(1e-9),F(1e9)


def pow2(k):return Fraction(2)**k


def flog(q):
    k=q.numerator.bit_length()-q.denominator.bit_length()
    return k-int(pow2(k)>q)


def clog(q):
    k=flog(q)
    return k+int(pow2(k)<q)


def factor(row,delta,gamma,lo,hi):
    a=[abs(F(float(x))) for x in row['terms'].values() if x]
    M=F(float(row['M']))
    remaining=delta-M*gamma
    if remaining<=0:return None
    low=max(clog(lo/min(a)),clog(EPS/remaining));high=flog(hi/max(a))
    if low>high:return None
    norm=sum((v*v for v in a),Fraction(0));middle=(-flog(norm))//2
    choices={max(low,min(high,u)) for u in range(middle-1,middle+2)}
    def objective(u):
        q=norm*pow2(2*u)
        return max(q,1/q),-u
    u=min(choices,key=objective);alpha=float(pow2(u))
    if any(F(float(float(x)*alpha))!=F(float(x))*F(alpha) for x in row['terms'].values()):
        return None
    return alpha


def select(rows,delta):
    delta=F(float(delta))
    grouped={}
    for row in rows:grouped.setdefault(row['z'],[]).append(row)
    for t in range(31):
        lo=max(LOW,pow2(-t));hi=min(HIGH,pow2(t));answer={};ok=True
        for z,group in grouped.items():
            found=None
            for k in range(29):
                K=pow2(k);sigma=pow2(flog(hi/K))
                if sigma<lo:continue
                eta=EPS/sigma
                if K*GAMMA+eta+GAMMA>=Fraction(1,2):continue
                effective=(GAMMA+eta)/K
                alphas={r['row']:factor(r,delta,effective,lo,hi) for r in group}
                if all(x is not None for x in alphas.values()):
                    found={'K':int(K),'sigma':float(sigma),'gamma_effective':str(effective),
                           'factors':alphas,'k':k}
                    break
            if found is None:ok=False;break
            answer[z]=found
        if ok:return {'compatible':True,'t':t,'groups':answer,'budget':str(delta)}
    return {'compatible':False,'budget':str(delta),'reason':'no_complete_contract_in_declared_window'}
