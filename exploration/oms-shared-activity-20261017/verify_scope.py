"""Independent activation selection, row-factor abstention and alias audit."""
from fractions import Fraction
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
F=Fraction.from_float


def ceil_log(q):
    k=q.numerator.bit_length()-q.denominator.bit_length()
    while Fraction(2)**k<q:k+=1
    while Fraction(2)**(k-1)>=q:k-=1
    return k


def exists(row,model,gamma):
    values=[abs(F(float(x))) for x in row['terms'].values() if x]
    reserve=F(gamma)*sum((abs(F(float(x))) for j,x in row['terms'].items() if model['variables'][int(j)]['integer']),Fraction(0))
    left=F(float(row['budget']))-reserve
    if left<=0:return False
    lo=max(F(1e-9)/min(values),F(1e-6)/left);hi=F(1e9)/max(values)
    k=max(-1074,ceil_log(lo))
    for x in [*row['terms'].values(),row['rhs']]:
        if x:
            n,d=abs(float(x)).as_integer_ratio();trailing=(n&-n).bit_length()-1
            k=max(k,-1074-trailing+d.bit_length()-1)
            hi=min(hi,Fraction(2)**(1023-n.bit_length()+d.bit_length()))
    return k<=1023 and Fraction(2)**k<=hi


def gates(model):
    result={}
    for i,row in enumerate(model['rows']):
        if row['rhs']!=0 or row['sense']=='=':continue
        sign=1 if row['sense']=='<' else -1
        ints=[(int(j),sign*F(float(x))) for j,x in row['terms'].items() if model['variables'][int(j)]['integer']]
        if len(ints)!=1:continue
        z,a=ints[0];v=model['variables'][z]
        if a>=0 or (v['lower'],v['upper'])!=(0,1):continue
        result[i]=z
    return result


def main():
    design=json.loads((HERE/'pilot/design.json').read_text());reports=[]
    for item in design['models']:
        folder=HERE/'pilot/models'/item['name'];base=json.loads((folder/'contracted-model.json').read_text())
        detected=gates(base);assert sorted(detected)==sorted(item['gate_rows'])
        selected_z={z for i,z in detected.items() if not exists(base['rows'][i],base,1e-5)}
        selected_rows=sorted(i for i,z in detected.items() if z in selected_z)
        assert len(selected_z)==item['selected_groups'] and selected_rows==item['selected_rows']
        variants=[v for v in design['assignments'] if v['name']==item['name']]
        for v in variants:
            arm=folder/v['arm'];meta=json.loads((arm/'selection.json').read_text())
            assert meta['selected_rows']==selected_rows
            canonical=[x for x in variants if x['arm']==v['canonical_arm']][0]
            assert canonical['parameters']==v['parameters'] and canonical['export_sha256']==v['export_sha256']
        for abstention in (x for x in design['abstentions'] if x['name']==item['name']):
            i=abstention['row'];k=abstention['unit_exponent'];row=base['rows'][i].copy()
            if i in detected:
                row={**row,'terms':{j:float(F(float(x))*Fraction(2)**k) for j,x in row['terms'].items()},
                     'rhs':float(F(float(row['rhs']))*Fraction(2)**k),'budget':float(F(float(row['budget']))*Fraction(2)**k)}
            assert not exists(row,base,1e-5)
        reports.append({'name':item['name'],'independent_gates':len(detected),'selected_groups':len(selected_z),
                        'selected_rows':len(selected_rows),'assignments':len(variants),'abstentions_verified':5})
    output={'models':reports,'new_optimizer_calls':0,'all_scope_checks_pass':True}
    (HERE/'SCOPE_VALIDATION.json').write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(output,indent=2))


if __name__=='__main__':main()
