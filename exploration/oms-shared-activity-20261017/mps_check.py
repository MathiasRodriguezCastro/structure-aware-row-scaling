"""Independent reader for the actual MPS subset in the two new flow models."""
from fractions import Fraction
import gzip
import hashlib

F=Fraction.from_float


def check(path,model):
    rows={};columns={};rhs={};integer=set();bound_lines=[];section='';mark=False;objective=None
    for line in gzip.decompress(path.read_bytes()).decode('latin1').splitlines():
        if not line.strip() or line.startswith('*'):continue
        parts=line.split()
        if not line[0].isspace():
            section=parts[0];assert section in ('NAME','ROWS','COLUMNS','RHS','BOUNDS','ENDATA');continue
        if section=='ROWS':
            sense,name=parts;assert sense in ('N','E','L','G')
            if sense=='N':assert objective is None;objective=name
            else:rows[name]={'sense':{'E':'=','L':'<','G':'>'}[sense],'terms':{}}
        elif section=='COLUMNS':
            if "'MARKER'" in parts:
                assert parts[2] in ("'INTORG'","'INTEND'");mark=parts[2]=="'INTORG'";continue
            assert len(parts) in (3,5);name=parts[0];columns.setdefault(name,{})
            if mark:integer.add(name)
            for j in range(1,len(parts),2):
                r=parts[j];assert r not in columns[name]
                columns[name][r]=F(float(parts[j+1].replace('D','E')))
        elif section=='RHS':
            for j in range(1,len(parts),2):assert parts[j] not in rhs;rhs[parts[j]]=F(float(parts[j+1].replace('D','E')))
        elif section=='BOUNDS':bound_lines.append(parts)
    assert objective is not None and rhs.get(objective,0)==0
    bounds={n:[Fraction(0),Fraction(1) if n in integer else None] for n in columns}
    for parts in bound_lines:
        kind,_,name=parts[:3];assert kind in ('UP','BV') and name in bounds
        if kind=='BV':integer.add(name);bounds[name]=[Fraction(0),Fraction(1)]
        else:
            value=F(float(parts[3]));assert value>=0
            bounds[name][1]=value
    index={v['name']:j for j,v in enumerate(model['variables'])}
    assert set(index)==set(columns) and set(rows)=={r['name'] for r in model['rows']}
    for name,terms in columns.items():
        v=model['variables'][index[name]]
        assert v['integer']==(name in integer) and F(float(v['cost']))==terms.get(objective,Fraction(0))
        assert [None if v[k] is None else F(float(v[k])) for k in ('lower','upper')]==bounds[name]
        for r,value in terms.items():
            if r!=objective and value:rows[r]['terms'][str(index[name])]=value
    for row in model['rows']:
        expected=rows[row['name']]
        assert expected['sense']==row['sense'] and expected['terms']=={j:F(float(x)) for j,x in row['terms'].items() if x}
        assert rhs.get(row['name'],Fraction(0))==F(float(row['rhs']))
    return {'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'rows':len(rows),'variables':len(columns),
            'coefficient_literals_objective_bounds_and_domains_checked':True}
