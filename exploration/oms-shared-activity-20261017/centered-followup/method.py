"""Precision-constrained centering of shared or individual SOS activities."""
from fractions import Fraction
import importlib.util
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import activity as a

F=Fraction.from_float


def center(group,low=-1000,high=1000):
    q=[F(float(g['M']))**2/sum((F(float(c))**2 for c in g['g'].values()),Fraction(0)) for g in group]
    qmin,qmax=min(q),max(q);middle=a.flog(qmin*qmax)//4
    candidates={min(high,max(low,r)) for r in (middle,middle+1)}
    def objective(r):return max(qmax*a.pow2(-2*r),a.pow2(2*r)/qmin),r
    r=min(candidates,key=objective)
    return r,{'qmin':str(qmin),'qmax':str(qmax),'objective':str(objective(r)[0])}


def radius(group,policy,epsilon,gamma):
    if policy=='Unconstrained-shared':
        r,score=center(group);return {'compatible':True,'r':r,'radius':float(a.pow2(r)),'score':score}
    feasible=a.select_shared(group,epsilon,gamma)
    if not feasible['compatible']:return feasible
    if policy=='Minimum-shared':return feasible
    r,score=center(group,feasible['lower_r'],feasible['upper_r'])
    R=a.pow2(r);decisions=[]
    for g in group:
        h=a.exact(F(float(g['M']))/R)
        assert h is not None
        alpha=a.factor([*g['g'].values(),-h],delta=F(float(g['delta'])),
                       reserve=F(h)*max(F(gamma),F(1e-6)),epsilon=epsilon)
        assert alpha is not None
        decisions.append({'row':g['row'],'h':h,'alpha':alpha,
                          'bound':str(F(epsilon)/F(alpha)+F(h)*max(F(gamma),F(1e-6)))})
    return {**feasible,'r':r,'radius':float(R),'score':score,'decisions':decisions}


def compile_model(base,policy,parent):
    import collections
    import copy
    epsilon,gamma=(1e-9,1e-9) if policy in ('Tight-coefficient-SOS','Tight-raw') else (1e-6,1e-5)
    gates,groups=parent.target_groups(base);byrow={g['row']:g for g in gates}
    selected={g['row']:g for block in groups.values() for g in block}
    model=copy.deepcopy(base)
    meta={'policy':policy,'epsilon':epsilon,'gamma':gamma,'selected_rows':sorted(selected),
          'original_variables':len(base['variables']),'original_rows':len(base['rows']),
          'factors':[],'sos':[],'links':[],'indicators':[],'groups':[],'unit_exponent':0,'all_gate_rows':list(byrow)}
    for i,row in enumerate(model['rows']):
        reserve=F(gamma)*F(float(byrow[i]['M'])) if i in byrow and i not in selected and policy!='Tight-raw' else Fraction(0)
        alpha=a.factor(list(row['terms'].values()),row['rhs'],delta=None if i in selected and policy!='Tight-raw' else F(float(row['budget'])),
                       reserve=reserve,epsilon=epsilon)
        if alpha is None:return None,{'compatible':False,'reason':'initial_row_contract','row':i}
        meta['factors'].append(alpha)
    if policy=='Tight-raw':return model,meta
    complement={}
    def variable(name,upper):
        j=len(model['variables']);model['variables'].append({'name':name,'cost':0.,'lower':0.,'upper':upper,'integer':False,'bound_budget':1e-6});return j
    def comp(z):
        if z not in complement:
            w=variable(f'complement_{z}',1.);idx=len(model['rows'])
            model['rows'].append({'name':f'complement_{z}','terms':{str(w):1.,str(z):1.},'rhs':1.,'sense':'=','budget':1e-6,'unit':'auxiliary'})
            meta['factors'].append(1.);complement[z]=(w,idx)
        return complement[z]
    for z,block in groups.items():
        if policy=='Indicator-budget':
            for g in block:
                i=g['row'];alpha=a.factor(list(g['g'].values()),delta=F(float(g['delta'])),epsilon=epsilon)
                if alpha is None:return None,{'compatible':False,'reason':'indicator_factor','row':i}
                model['rows'][i]={'name':f'cap_{i}','terms':g['g'],'rhs':g['M'],'sense':'<','budget':g['delta'],'unit':'auxiliary'}
                meta['factors'][i]=alpha;meta['indicators'].append({'row':i,'z':z,'terms':g['g'],'alpha':alpha,'M':g['M'],'rhs':0.})
            continue
        chunks=[[g] for g in block] if policy in ('Coefficient-SOS','Tight-coefficient-SOS','Centered-individual') else [block]
        for chunk in chunks:
            if policy in ('Coefficient-SOS','Tight-coefficient-SOS'):
                g=chunk[0];mean=sum((abs(F(float(c))) for c in g['g'].values()),Fraction(0))/len(g['g'])
                e=a.flog(mean);choices=(a.pow2(e),a.pow2(e+1))
                h=min(choices,key=lambda q:(max(q/mean,mean/q),q));R=a.exact(F(float(g['M']))/h)
                if R is None or R>float(a.CAP):return None,{'compatible':False,'reason':'coefficient_scale_representation','row':g['row']}
                dec={'r':None,'radius':R,'coefficient_h':float(h)}
            else:
                dec=radius(chunk,policy,epsilon,gamma)
                if not dec['compatible']:return None,dec
                R=dec['radius']
            y=variable(f'activity_{chunk[0]["row"]}',R);w,c=comp(z)
            meta['sos'].append({'z':z,'y':y,'w':w,'complement_row':c,'radius':R})
            meta['groups'].append({'z':z,'rows':[g['row'] for g in chunk],**dec})
            for g in chunk:
                h=a.exact(F(float(g['M']))/F(float(R)))
                if h is None:return None,{'compatible':False,'reason':'link_representation','row':g['row']}
                constrained=policy in ('Centered-individual','Centered-shared','Minimum-shared')
                alpha=a.factor([*g['g'].values(),-h],delta=F(float(g['delta'])) if constrained else None,
                               reserve=F(h)*max(F(gamma),F(1e-6)),epsilon=epsilon)
                if alpha is None:return None,{'compatible':False,'reason':'link_factor','row':g['row']}
                i=g['row'];model['rows'][i]={'name':f'activity_link_{i}','terms':{**g['g'],str(y):-h},'rhs':0.,'sense':'<','budget':g['delta'],'unit':'auxiliary'}
                meta['factors'][i]=alpha;meta['links'].append({'row':i,'z':z,'y':y,'w':w,'complement_row':c,'M':g['M'],
                      'h':h,'radius':R,'sign':g['sign'],'bound':str(F(epsilon)/F(alpha)+F(h)*max(F(gamma),F(1e-6)))})
    return model,meta
