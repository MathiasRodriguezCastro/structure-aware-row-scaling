"""Strict linear MPS/DEC adapter, independent of optimizer libraries.

Keeps every nonzero, checks marker/default bounds and exact representability of
range endpoints, and rejects unsupported constructs rather than dropping them.
"""
from fractions import Fraction as F
import gzip
import math
from pathlib import Path


def read_mps(path):
    section=None;rowtypes={};columns={};integer=set();rhs={};ranges={};bound_lines=[]
    objective=None;objective_sense=1;in_integer=False;sets={};literal_entries=0;duplicates=0
    allowed={'NAME','ROWS','COLUMNS','RHS','BOUNDS','RANGES','ENDATA','OBJSENSE','OBJNAME'}
    for line in gzip.decompress(Path(path).read_bytes()).decode('latin1').splitlines():
        if not line.strip() or line.startswith('*'):continue
        t=line.split()
        if not line[0].isspace():
            section=t[0]
            if section not in allowed:raise ValueError('unsupported MPS section '+section)
            if section=='OBJSENSE' and len(t)>1:objective_sense=-1 if t[1]=='MAX' else 1
            if section=='OBJNAME' and len(t)>1:objective=t[1]
            continue
        if section=='OBJSENSE':
            assert t[0] in ('MIN','MAX');objective_sense=-1 if t[0]=='MAX' else 1
        elif section=='OBJNAME':objective=t[0]
        elif section=='ROWS':
            assert len(t)==2 and t[0] in ('N','L','G','E') and t[1] not in rowtypes
            rowtypes[t[1]]=t[0]
            if t[0]=='N' and objective is None:objective=t[1]
        elif section=='COLUMNS':
            if any('MARKER' in s for s in t):
                assert t[-1] in ("'INTORG'","'INTEND'")
                in_integer=t[-1]=="'INTORG'";continue
            assert len(t) in (3,5)
            data=columns.setdefault(t[0],{})
            if in_integer:integer.add(t[0])
            for r,v in zip(t[1::2],t[2::2]):
                assert r in rowtypes
                value=float(v.replace('D','E'));assert math.isfinite(value)
                literal_entries+=value!=0
                if r in data:duplicates+=1
                data[r]=data.get(r,0.)+value
        elif section in ('RHS','RANGES'):
            assert len(t) in (3,5)
            sets.setdefault(section,t[0]);assert sets[section]==t[0],'multiple named RHS/range vectors require explicit handling'
            store=rhs if section=='RHS' else ranges
            for r,v in zip(t[1::2],t[2::2]):
                assert r in rowtypes and r not in store
                value=float(v.replace('D','E'));assert math.isfinite(value);store[r]=value
        elif section=='BOUNDS':
            assert len(t) in (3,4)
            sets.setdefault(section,t[1]);assert sets[section]==t[1]
            bound_lines.append(t)
        else:raise ValueError('unexpected data in '+str(section))
    assert objective in rowtypes and rowtypes[objective]=='N' and not in_integer
    if duplicates:raise ValueError('duplicate MPS matrix entries need an explicit exact-summation convention')
    lower={n:0. for n in columns};upper={n:1. if n in integer else None for n in columns}
    for t in bound_lines:
        kind,_,name=t[:3]
        assert name in columns
        value=float(t[3].replace('D','E')) if len(t)==4 else None
        if value is not None:assert math.isfinite(value)
        if kind=='BV':integer.add(name);lower[name]=0.;upper[name]=1.
        elif kind in ('LO','LI'):
            assert value is not None;lower[name]=value
            if kind=='LI':integer.add(name)
        elif kind in ('UP','UI'):
            assert value is not None;upper[name]=value
            if kind=='UI':integer.add(name)
            if value<0 and lower[name]==0:lower[name]=None
        elif kind=='FX':assert value is not None;lower[name]=upper[name]=value
        elif kind=='FR':lower[name]=upper[name]=None
        elif kind=='MI':lower[name]=None
        elif kind=='PL':upper[name]=None
        else:raise ValueError('unsupported MPS bound '+kind)
    names=list(columns);index={n:j for j,n in enumerate(names)}
    rows={n:{} for n,t in rowtypes.items() if t!='N'}
    variables=[]
    for name,values in columns.items():
        variables.append(dict(name=name,lower=lower[name],upper=upper[name],integer=name in integer,
            cost=objective_sense*values.get(objective,0.)))
        for row,value in values.items():
            if row in rows and value!=0:rows[row][str(index[name])]=value
    result=[]
    for name,terms in rows.items():
        typ=rowtypes[name];value=rhs.get(name,0.)
        lo=value if typ in ('E','G') else None;hi=value if typ in ('E','L') else None
        if name in ranges:
            r=ranges[name]
            if typ=='L':lo=F(value)-abs(F(r))
            elif typ=='G':hi=F(value)+abs(F(r))
            elif r>=0:hi=F(value)+F(r)
            else:lo=F(value)+F(r)
            for endpoint in (lo,hi):
                if isinstance(endpoint,F) and F(float(endpoint))!=endpoint:
                    raise ValueError('range endpoint is not exactly representable in binary64: '+name)
            lo=None if lo is None else float(lo);hi=None if hi is None else float(hi)
        if lo is not None and hi is not None and lo==hi:
            sides=[('=',lo)]
        else:sides=[('<',hi)] if lo is None else [('>',lo)] if hi is None else [('>',lo),('<',hi)]
        for sense,endpoint in sides:
            result.append(dict(name=name+(':'+sense if len(sides)==2 else ''),source_name=name,
                               terms=terms,sense=sense,rhs=endpoint))
    return dict(name=Path(path).name.removesuffix('.mps.gz'),variables=variables,rows=result,
        objective_offset=-objective_sense*rhs.get(objective,0.),source_objective_sense=objective_sense,
        original_rows=len(rows),ranged_rows=len(ranges),literal_nonzeros=literal_entries,
        nonzeros=sum(len(r['terms']) for r in result),ignored_free_rows=[n for n,t in rowtypes.items() if t=='N' and n!=objective])


def read_dec(path,model):
    lines=[s.strip() for s in Path(path).read_text().splitlines() if s.strip() and not s.startswith('\\')]
    assert lines[:3]==['PRESOLVED','0','NBLOCKS']
    blocks=int(lines[3]);block=None;owner={}
    for line in lines[4:]:
        if line.startswith('BLOCK '):block=int(line.split()[1]);assert 1<=block<=blocks
        elif line=='MASTERCONSS':block=0
        else:
            assert block is not None and line not in owner
            owner[line]=block
    original={r['source_name'] for r in model['rows']}
    assert set(owner)==original,dict(missing=len(original-set(owner)),extra=len(set(owner)-original))
    support=[set() for _ in model['variables']]
    for row in model['rows']:
        block=owner[row['source_name']]
        if block:
            for j in row['terms']:support[int(j)].add(block)
    private={str(j):next(iter(s)) for j,s in enumerate(support) if len(s)==1}
    genuine=[];master=[]
    for i,row in enumerate(model['rows']):
        if owner[row['source_name']]==0:
            master.append(i)
            if len({private[j] for j in row['terms'] if j in private})>=2:genuine.append(i)
    sizes={block:sum(s=={block} for s in support) for block in set(private.values())}
    return dict(declared_blocks=blocks,local_rows=sum(owner[r['source_name']]!=0 for r in model['rows']),
        master_rows=len(master),genuine_row_coupling_rows=len(genuine),shared_columns=sum(len(s)>1 for s in support),
        master_only_columns=sum(not s for s in support),private_columns=len(private),
        nontrivial_private_blocks=sum(v>=10 for v in sizes.values()),private_block_sizes=sizes,
        full_role_applicable=sum(v>=10 for v in sizes.values())>=2 and bool(genuine),
        coupling_row_indices=genuine,source_row_blocks=owner)
