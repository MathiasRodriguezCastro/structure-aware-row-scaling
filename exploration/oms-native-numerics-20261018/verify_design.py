"""License-free structural replay and independent finite-grid selector audit."""
from fractions import Fraction as F
import gzip
import json
import math

from factors import row_spec,select
from fetch import HERE,dump,sha
from native import read_mps,read_dec


def brute(row,variables,delta,rounded):
    a=list(row['terms'].values())
    if not a:return 1.
    minimum=min(map(abs,a));maximum=max(map(abs,a));norm=sum((F(x)**2 for x in a),F(0))
    E=F(1e-9)*sum((abs(F(c)) for j,c in row['terms'].items() if variables[int(j)]['integer']),F(0)) if rounded else F(0)
    valid=[]
    # All native selected factors fit this checked grid; extreme formal cases are separate.
    for k in range(-100,101):
        factor=F(2)**k
        if factor*F(minimum)<F(1e-9) or factor*F(maximum)>F(1e9):continue
        if delta is not None and F(1e-6)/factor+E>F(delta):continue
        if not all(F(float(float(factor)*v))==factor*F(v) for v in [*a,row['rhs']]):continue
        q=factor*factor*norm;valid.append((max(q,1/q),-k,float(factor)))
    return min(valid)[2] if valid else None


def main():
    ledger=json.loads((HERE/'sources/manifest.json').read_text())
    for r in ledger:assert sha((HERE/'sources'/r['file']).read_bytes())==r['sha256']
    retained=json.loads((HERE/'contracts.retention.json').read_text())
    assert sha(gzip.decompress((HERE/'contracts.csv.gz').read_bytes()))==retained['original_csv_sha256']
    selection=json.loads((HERE/'selection.json').read_text());b=json.loads((HERE/'stage-b-design.json').read_text())
    assert sha((HERE/'PROTOCOL.md').read_bytes())==selection['protocol_sha256']==b['protocol_sha256']
    assert sha((HERE/'selection.json').read_bytes())==b['selection_sha256']
    checked=0;models=0
    for entry in selection['selected']:
        name=entry['name'];model=read_mps(HERE/'sources'/(name+'.mps.gz'))
        with gzip.open(HERE/'models'/name/'original.json.gz','rt') as stream:saved=json.load(stream)
        assert all(saved[k]==v for k,v in model.items())
        dec=read_dec(HERE/'sources'/(name+'.dec'),model)
        stored=json.loads((HERE/'models'/name/'structure.json').read_text())
        assert json.loads(json.dumps(dec))==stored
        rows=model['rows']
        choices=set(range(min(8,len(rows))))
        choices.add(max(range(len(rows)),key=lambda i:max(map(abs,rows[i]['terms'].values()),default=0)))
        for i in choices:
            row=rows[i];spec=row_spec(row,model['variables'])
            assert select(spec)['factor']==brute(row,model['variables'],None,True)
            checked+=1
            for delta in (.1,.001,.00001,.0000001):
                for rounded in (True,False):
                    assert select(spec,delta,rounded)['factor']==brute(row,model['variables'],delta,rounded)
                    checked+=1
        models+=1
    # These exact IEEE boundary cases must abstain instead of under/overflowing an export.
    for row in [dict(terms={'0':math.ldexp(1.,-1074)},rhs=0.),
                dict(terms={'0':1e308},rhs=1e-320)]:
        assert select(row_spec(row,[dict(integer=False)]))['factor'] is None
        checked+=1
    result=dict(source_models_verified=models,finite_grid_decisions_checked=checked,
        original_decompositions_replayed=True,optimizer_calls=0)
    dump(HERE/'verification-design.json',result);print(result)


if __name__=='__main__':main()
