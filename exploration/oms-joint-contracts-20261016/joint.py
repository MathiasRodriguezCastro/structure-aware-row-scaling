"""Integer difference constraints for exact dyadic mixed-integer model scaling.

Nodes: anchor, row exponent u_i, negative column exponent w_j=-v_j.
An edge (a,b,c) means p_b-p_a <= c. All arithmetic after construction is integer.
"""
from collections import deque
from fractions import Fraction
import math

F=Fraction.from_float
def power(k):return Fraction(2**k) if k>=0 else Fraction(1,2**(-k))
def floorlog(q):
    if q<=0:raise ValueError('positive rational required')
    k=q.numerator.bit_length()-q.denominator.bit_length()
    return k-int(power(k)>q)
def ceillog(q):
    k=floorlog(q);return k+int(power(k)<q)
def shift_range(x):
    """Necessary/sufficient k for nonzero x*2^k exactly finite binary64."""
    if not math.isfinite(x) or not x:raise ValueError('nonzero finite input required')
    n,d=abs(x).as_integer_ratio();trailing=(n&-n).bit_length()-1
    low=-1074-(trailing-(d.bit_length()-1))
    high=1023-(n.bit_length()-1-(d.bit_length()-1))
    return low,high

class Graph:
    def __init__(self,labels):self.labels=labels;self.edges=[]
    def edge(self,a,b,c,label):self.edges.append([a,b,int(c),label])
    def box(self,node,low,high,label):
        self.edge(0,node,high,label+' upper');self.edge(node,0,-low,label+' lower')
    def interval(self,a,b,low,high,label):
        self.edge(a,b,high,label+' upper');self.edge(b,a,-low,label+' lower')
    def check(self,result):
        if 'potential' in result:
            p=result['potential'];assert len(p)==len(self.labels) and p[0]==0
            assert all(isinstance(v,int) for v in p)
            assert all(p[b]-p[a]<=c for a,b,c,_ in self.edges)
        else:
            ids=result['negative_cycle'];assert ids
            edges=[self.edges[i] for i in ids]
            assert all(edges[i][1]==edges[(i+1)%len(edges)][0] for i in range(len(edges)))
            assert sum(e[2] for e in edges)<0
        return True
    def solve(self):
        n=len(self.labels);adj=[[] for _ in range(n)]
        for i,(a,b,c,_) in enumerate(self.edges):adj[a].append(i)
        d=[0]*n;pred=[None]*n;queue=deque(range(n));queued=[True]*n
        relaxations=0
        def cycle(node):
            seen={};path=[]
            while node not in seen and pred[node] is not None:
                seen[node]=len(path);i=pred[node];path.append(i);node=self.edges[i][0]
                if len(path)>n:raise AssertionError('predecessor walk exceeds nodes')
            if node in seen:
                ids=list(reversed(path[seen[node]:]))
                if sum(self.edges[i][2] for i in ids)<0:return ids
            return None
        while queue:
            a=queue.popleft();queued[a]=False
            for i in adj[a]:
                _,b,c,_=self.edges[i]
                if d[b]>d[a]+c:
                    d[b]=d[a]+c;pred[b]=i;relaxations+=1
                    # Checking predecessor cycles is only a speed optimization;
                    # a returned cycle is always checked by integer summation.
                    if b==a or relaxations%256==0:
                        ids=cycle(b)
                        if ids is not None:
                            r={'negative_cycle':ids,'relaxations':relaxations};self.check(r);return r
                    if not queued[b]:queue.append(b);queued[b]=True
        p=[v-d[0] for v in d];r={'potential':p,'relaxations':relaxations};self.check(r);return r

def construct(model,t,columns=True,window=(1e-9,1e9),epsilon=1e-6,backend_cap=1e19):
    """model holds rows, columns, costs, bounds, integer set, and delta/E maps."""
    rows=model['rows'];names=model['columns'];labels=['anchor']+['row:'+n for n in rows]+['col:'+n for n in names]
    graph=Graph(labels);ri={n:i+1 for i,n in enumerate(rows)};ci={n:len(rows)+i+1 for i,n in enumerate(names)}
    for n,i in ri.items():
        graph.box(i,-1074,1023,'row factor '+n)
        row=rows[n]
        if n in model['delta']:
            remainder=model['delta'][n]-model['E'].get(n,Fraction(0))
            if remainder<=0:graph.edge(0,0,-1,'rounding reserve exhausts budget '+n)
            else:graph.edge(i,0,-ceillog(F(epsilon)/remainder),'accuracy '+n)
        rhs=float(row['rhs'])
        if rhs:
            lo,hi=shift_range(rhs);hi=min(hi,floorlog(F(backend_cap)/F(abs(rhs))))
            graph.box(i,lo,hi,'rhs exact/backend '+n)
        for col,value in row['terms'].items():
            a=float(value)
            if not a:continue
            lo,hi=shift_range(a)
            lo=max(lo,ceillog(F(window[0])/F(abs(a))),-t-floorlog(F(abs(a))))
            hi=min(hi,floorlog(F(window[1])/F(abs(a))),t-ceillog(F(abs(a))))
            # u_i-w_j = u_i+v_j
            graph.interval(ci[col],i,lo,hi,'coefficient '+n+' / '+col)
    for n,i in ci.items():
        # w=-v; representability of factor s=2^v.
        graph.box(i,-1023,1074,'column factor '+n)
        if not columns or n in model['integers']:graph.box(i,0,0,'fixed integer/control column '+n)
        cost=float(model['costs'][n])
        if cost:
            lo,hi=shift_range(cost);graph.box(i,-hi,-lo,'objective exact '+n)
        for label,b in zip(['lower','upper'],model['bounds'][n]):
            if not math.isfinite(b) or b==0:continue
            lo,hi=shift_range(b);hi=min(hi,floorlog(F(backend_cap)/F(abs(b))))
            graph.box(i,lo,hi,'bound exact/backend '+n+' '+label)
    return graph

def minimize(model,columns=True):
    high=40;g=construct(model,high,columns);r=g.solve()
    if 'negative_cycle' in r:return {'feasible':False,'graph':g,'result':r,'t':high}
    lo=-1;best=(g,r)
    while high-lo>1:
        mid=(lo+high)//2;g=construct(model,mid,columns);r=g.solve()
        if 'potential' in r:high=mid;best=(g,r)
        else:lo=mid
    g,r=best;lower=None
    if high:
        lowerg=construct(model,high-1,columns);lower=lowerg.solve();assert 'negative_cycle' in lower
        lower={'graph':{'labels':lowerg.labels,'edges':lowerg.edges},'result':lower}
    return {'feasible':True,'t':high,'graph':g,'result':r,'lower_certificate':lower}

def exponents(model,result):
    assert result['feasible'];p=dict(zip(result['graph'].labels,result['result']['potential']))
    return {n:p['row:'+n] for n in model['rows']},{n:-p['col:'+n] for n in model['columns']}
