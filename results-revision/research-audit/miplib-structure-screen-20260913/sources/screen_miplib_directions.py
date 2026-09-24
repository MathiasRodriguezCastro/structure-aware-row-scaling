#!/usr/bin/env python3
"""Applicability screen on a selection frozen before reading model coefficients.

No optimization is performed. The model is the binary64 matrix read from MPS;
the number of nonzero source entries is checked against the reader to detect
dropped entries. This is a small descriptive screen, not a benchmark claim.
"""
import argparse,csv,gzip,hashlib,json,math,time
from pathlib import Path
import highspy
import numpy as np
from scipy.sparse import csc_matrix,csr_matrix
from integer_direction_compression import canonical_integer_row,compress_row,single_coefficient_control


def source_matrix_entries(path):
    section=None;objectives=set();count=0;minimum=math.inf
    with gzip.open(path,'rt') as stream:
        for line in stream:
            fields=line.split()
            if not fields or fields[0].startswith('*'):continue
            if fields[0] in ['NAME','ROWS','COLUMNS','RHS','BOUNDS','RANGES','ENDATA'] and len(fields)<=2:
                section=fields[0];continue
            if section=='ROWS' and fields[0]=='N':objectives.add(fields[1])
            if section!='COLUMNS' or any('MARKER' in t for t in fields):continue
            assert len(fields) in [3,5],fields
            for row,value in zip(fields[1::2],fields[2::2]):
                numeric=float(value.replace('D','E'))
                if row not in objectives and numeric!=0:count+=1;minimum=min(minimum,abs(numeric))
    return count,minimum


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);args=ap.parse_args()
    design=json.loads((args.root/'design.json').read_text());results=[];certificates={}
    for item in design['selected']:
        name=item['Instance'];path=args.root/'models'/(name+'.mps.gz')
        entries,min_value=source_matrix_entries(path)
        h=highspy.Highs();h.setOptionValue('output_flag',False);h.setOptionValue('small_matrix_value',1e-12)
        status=h.readModel(str(path));assert status==highspy.HighsStatus.kOk
        lp=h.getLp();assert all(t==highspy.HighsVarType.kInteger for t in lp.integrality_)
        assert min(lp.col_lower_)>=0 and max(lp.col_upper_)<=1
        matrix=lp.a_matrix_
        if matrix.format_==highspy.MatrixFormat.kColwise:
            A=csc_matrix((matrix.value_,matrix.index_,matrix.start_),shape=(lp.num_row_,lp.num_col_)).tocsr()
        else:A=csr_matrix((matrix.value_,matrix.index_,matrix.start_),shape=(lp.num_row_,lp.num_col_))
        assert entries==A.nnz,(name,entries,A.nnz,'reader may have changed source entries')
        counts=dict(instance=name,variables=lp.num_col_,constraints=lp.num_row_,nnz=A.nnz,
                    inequality_sides=0,already_integer_gap_safe=0,wide_sides_skipped=0,
                    exact_direction_attempts=0,direction_reduced=0,extra_over_single_coefficient=0,
                    nonrepresentable_replacements=0,minimum_source_coefficient=min_value,
                    source_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        start=time.perf_counter()
        for i in range(lp.num_row_):
            values=A.data[A.indptr[i]:A.indptr[i+1]]
            for sign,rhs in [(1,lp.row_upper_[i]),(-1,-lp.row_lower_[i])]:
                if not math.isfinite(rhs):continue
                counts['inequality_sides']+=1;a=sign*values
                # An exact integer sum this far below the threshold makes a
                # rational reconstruction pass unnecessary; RHS flooring alone
                # gives the unit-gap guarantee on all binary centers.
                if np.all(a==np.rint(a)) and np.abs(a).sum()<=999998:
                    counts['already_integer_gap_safe']+=1;continue
                if len(a)>design['max_row_support']:
                    counts['wide_sides_skipped']+=1;continue
                ar,br,_=canonical_integer_row(a,rhs)
                if sum(map(abs,ar))<=999998:
                    counts['already_integer_gap_safe']+=1;continue
                counts['exact_direction_attempts']+=1
                proof=compress_row(a,rhs);original_score=max([abs(br),*map(abs,ar),1])
                if not proof['steps']:continue
                counts['direction_reduced']+=1
                sr,sb=single_coefficient_control(a,rhs)
                simple_score=max([abs(sb),*map(abs,sr),1]);new_score=max([abs(proof['b']),*map(abs,proof['a']),1])
                if 2*new_score<simple_score:counts['extra_over_single_coefficient']+=1
                from fractions import Fraction as F
                try:representable=all(F(float(v))==v for v in [*proof['a'],proof['b']])
                except OverflowError:representable=False
                if not representable:counts['nonrepresentable_replacements']+=1
                certificates[name+f'_row{i}_sign{sign}']=dict(proof=proof,original_score=str(original_score),
                       simple_score=str(simple_score),new_score=str(new_score),representable=representable)
        counts['screen_seconds']=time.perf_counter()-start;results.append(counts)
        print(json.dumps(counts),flush=True)
        with (args.root/'screen-progress.jsonl').open('a') as stream:stream.write(json.dumps(counts)+'\n')
    with (args.root/'screen.csv').open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(results[0]));writer.writeheader();writer.writerows(results)
    (args.root/'screen-certificates.json').write_text(json.dumps(certificates,indent=2)+'\n')
    (args.root/'screen-source.sha256').write_text(hashlib.sha256(Path(__file__).read_bytes()).hexdigest()+'\n')


if __name__=='__main__':main()
