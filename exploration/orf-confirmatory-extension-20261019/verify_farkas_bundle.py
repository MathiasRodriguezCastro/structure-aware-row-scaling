#!/usr/bin/env python3
"""Verify the two-row certificates using only Python's standard library."""
import argparse
from collections import defaultdict
from decimal import Decimal
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import re

if not __debug__:
    raise RuntimeError('Run the certificate verifier without Python optimization flags (-O/-OO).')

NUMBER=r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?'
TERM=re.compile('('+NUMBER+r')\s+(\S+)')
SENSE=re.compile(r'(<=|>=|=)\s+('+NUMBER+')')


def read_selected(path,wanted,convert):
    rows={};mode=None;current=None;bounds={}
    for raw in path.read_text().splitlines():
        line=raw.strip();lower=line.lower()
        if lower=='s.t.':mode='rows';continue
        if lower in ['bounds','binary','binaries','generals','end']:
            mode='binary' if lower in ['binary','binaries'] else lower;continue
        if mode=='rows':
            if line.endswith(':'):
                current=line[:-1]
                if current in wanted:rows[current]=dict(terms={},sense=None,rhs=None)
            elif current in wanted:
                term=TERM.fullmatch(line);sense=SENSE.fullmatch(line)
                if term:
                    coefficient,name=term.groups();rows[current]['terms'][name]=convert(coefficient)
                    bounds.setdefault(name,[Q(0),None])
                elif sense:rows[current].update(sense=sense[1],rhs=convert(sense[2]))
                elif line:raise ValueError('Unrecognized selected row line: '+line)
        elif mode=='bounds':
            words=line.split()
            if len(words)==5 and words[1]=='<=' and words[3]=='<=':
                lo,name,hi=words[0],words[2],words[4]
                if name in bounds:bounds[name]=[convert(lo),convert(hi)]
            elif len(words)==2 and words[1].lower()=='free':
                if words[0] in bounds:bounds[words[0]]=[None,None]
            elif len(words)==3:
                left,relation,right=words
                if left in bounds:
                    if relation=='<=':bounds[left][1]=convert(right)
                    elif relation=='>=':bounds[left][0]=convert(right)
                    elif relation=='=':bounds[left]=[convert(right),convert(right)]
                elif right in bounds:
                    if relation=='<=':bounds[right][0]=convert(left)
                    elif relation=='>=':bounds[right][1]=convert(left)
            elif any(name in words for name in bounds):
                raise ValueError('Unrecognized relevant bound: '+line)
        elif mode=='binary':
            for name in line.split():
                if name in bounds:
                    lo,hi=bounds[name]
                    bounds[name]=[max(Q(0),lo) if lo is not None else Q(0),
                        min(Q(1),hi) if hi is not None else Q(1)]
    assert set(rows)==set(wanted) and all(r['sense'] is not None for r in rows.values())
    return rows,bounds


def verify(root):
    report=json.loads((root/'STRUCTURAL_FEASIBILITY_AUDIT.json').read_text());count=0
    for certificate in report['certificates']:
        path=root/'models'/certificate['instance']/'Base.lp'
        assert hashlib.sha256(path.read_bytes()).hexdigest()==certificate['base_sha256']
        rows,bounds=read_selected(path,certificate['row_multipliers'],lambda s:Q.from_float(float(s)))
        lhs=defaultdict(Q);rhs=Q(0)
        for name,value in certificate['row_multipliers'].items():
            weight=Q(value);row=rows[name]
            assert row['sense']=='=' or (row['sense']=='<=' and weight>=0)
            for j,c in row['terms'].items():lhs[j]+=weight*c
            rhs+=weight*row['rhs']
        for bound in certificate['bound_multipliers']:
            name=bound['variable'];weight=Q(bound['positive_multiplier']);assert weight>=0
            if bound['bound']=='lower':
                assert bounds[name][0]==Q(bound['value'])
                lhs[name]-=weight;rhs-=weight*bounds[name][0]
            else:
                assert bound['bound']=='upper' and bounds[name][1]==Q(bound['value'])
                lhs[name]+=weight;rhs+=weight*bounds[name][1]
        assert not any(lhs.values()) and rhs<0 and rhs==Q(certificate['contradiction_rhs_exact'])
        decimal_rows,decimal_bounds=read_selected(path,certificate['row_multipliers'],lambda s:Q(Decimal(s)))
        coefficients=defaultdict(Q);decimal_rhs=Q(0)
        for name,value in certificate['row_multipliers'].items():
            for j,c in decimal_rows[name]['terms'].items():coefficients[j]+=Q(value)*c
            decimal_rhs+=Q(value)*decimal_rows[name]['rhs']
        lower=Q(0)
        for j,c in coefficients.items():
            if c:
                endpoint=decimal_bounds[j][0 if c>0 else 1];assert endpoint is not None
                lower+=c*endpoint
        assert decimal_rhs<lower
        count+=1
        print(certificate['instance']+': verified exact binary64 and written-decimal contradictions')
    assert count==2
    print('Verified 2 certificates; no third-party packages or optimization calls.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',nargs='?',type=Path,default=Path(__file__).resolve().parent)
    verify(parser.parse_args().directory)
