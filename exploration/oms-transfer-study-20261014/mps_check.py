"""Independent literal and domain check for the MPS features in this dataset."""
from fractions import Fraction
import gzip
import hashlib
import json
from pathlib import Path

F=Fraction.from_float


def check(model,sources):
    sources=Path(sources);source=next(v for v in json.loads((sources/'provenance.json').read_text()) if v['name']==model['name'])
    path=sources/(model['name']+'.mps.gz');digest=hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest==source['sha256']==model['source_sha256']
    rows={};columns={};rhs={};integers=set();bound_lines=[];section='';active=False;objective=None;rounded_literals=0
    for line in gzip.decompress(path.read_bytes()).decode('latin1').splitlines():
        if not line.strip() or line.startswith('*'):continue
        t=line.split()
        if not line[0].isspace():
            section=t[0];assert section in ('NAME','ROWS','COLUMNS','RHS','BOUNDS','ENDATA');continue
        if section=='ROWS':
            sense,name=t;assert sense in ('N','E','L','G')
            if sense=='N':assert objective is None;objective=name
            else:rows[name]={'sense':{'E':'=','L':'<','G':'>'}[sense],'terms':{}}
        elif section=='COLUMNS':
            if "'MARKER'" in t:
                assert t[2] in ("'INTORG'","'INTEND'");active=t[2]=="'INTORG'";continue
            assert len(t) in (3,5);name=t[0];columns.setdefault(name,{})
            if active:integers.add(name)
            for j in range(1,len(t),2):
                assert t[j] not in columns[name]
                literal=t[j+1].replace('D','E');value=F(float(literal));rounded_literals+=value!=Fraction(literal)
                columns[name][t[j]]=value
        elif section=='RHS':
            assert len(t) in (3,5)
            for j in range(1,len(t),2):
                assert t[j] not in rhs;literal=t[j+1].replace('D','E');value=F(float(literal));rounded_literals+=value!=Fraction(literal);rhs[t[j]]=value
        elif section=='BOUNDS':bound_lines.append(t)
    assert objective is not None and not rhs.get(objective,0)
    bounds={name:[Fraction(0),Fraction(1) if name in integers else None] for name in columns}
    explicit_upper=set()
    for t in bound_lines:
        if len(t)==4:rounded_literals+=F(float(t[3]))!=Fraction(t[3])
        kind,_,name=t[:3];assert name in bounds and kind in ('FR','UP','LO','LI'),kind
        if kind=='FR':bounds[name]=[None,None];explicit_upper.add(name)
        elif kind=='UP':bounds[name][1]=F(float(t[3]));explicit_upper.add(name)
        elif kind=='LO':bounds[name][0]=F(float(t[3]))
        else:
            integers.add(name);bounds[name][0]=F(float(t[3]))
            if name not in explicit_upper:bounds[name][1]=None
    index={v['name']:i for i,v in enumerate(model['variables'])}
    assert set(index)==set(columns) and set(rows)=={r['name'] for r in model['rows']}
    for name,terms in columns.items():
        v=model['variables'][index[name]]
        assert v['integer']==(name in integers)
        assert F(float(v['cost']))==terms.get(objective,Fraction(0))
        assert [F(float(v[k])) if v[k] is not None else None for k in ('lower','upper')]==bounds[name]
        for row,value in terms.items():
            if row!=objective and value:rows[row]['terms'][str(index[name])]=value
    for r in model['rows']:
        source_row=rows[r['name']]
        assert source_row['sense']==r['sense'] and source_row['terms']=={i:F(float(a)) for i,a in r['terms'].items() if a}
        assert rhs.get(r['name'],Fraction(0))==F(float(r['rhs']))
    return {'name':model['name'],'source_sha256':digest,'variables':len(columns),'rows':len(rows),
            'nonzeros':sum(len(r['terms']) for r in rows.values()),'objective_bounds_domains_checked':True,
            'decimal_literals_rounded_in_binary64':rounded_literals,
            'literal_interpretation':'original decimal literals converted to binary64; not ideal rational decimals'}
