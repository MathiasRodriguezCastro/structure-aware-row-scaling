"""Check every saved interval certificate field independently of the selector."""
from fractions import Fraction
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('independent_contract_audit',HERE/'verify.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
F=Fraction.from_float


def check(meta,source):
    links={g['row']:g for g in meta['links']};count=0
    for group in meta['groups']:
        for saved in group.get('certificates',[]):
            i=saved['row'];g=links[i];row=source[i];sign=1 if row['sense']=='<' else -1
            terms={j:float(sign*c) for j,c in row['terms'].items() if int(j)!=g['z']}
            M=F(float(g['M']));delta=row['budget']
            result=audit.interval(terms,M,delta);assert result is not None
            low,high,A,B,C,D=result
            assert saved['compatible'] and saved['reason']=='integer_interval'
            assert (saved['A'],saved['B'],saved['C'],saved['D'])==(A,B,C,D)
            assert (saved['lower_r'],saved['upper_r'])==(low,high)
            assert Fraction(saved['P'])==F(meta['epsilon'])*Fraction(2)**(-A)
            assert Fraction(saved['Q'])==F(meta['epsilon'])*Fraction(2)**(-B)
            assert Fraction(saved['MT'])==M*max(F(meta['gamma']),F(1e-6))
            assert Fraction(saved['delta'])==delta
            assert saved['M_shift_range']==list(audit.shifts(float(M)));count+=1
    return count


def main():
    primary=json.loads((HERE/'pilot/design.json').read_text());pcount=0;fcount=0
    models={}
    for item in primary['models']:
        models[item['name']]=json.loads((HERE/'pilot/models'/item['name']/'contracted-model.json').read_text())
    for call in primary['assignments']:
        arm=HERE/'pilot/models'/call['name']/call['arm'];meta=json.loads((arm/'selection.json').read_text())
        rows=audit.scaled_source(models[call['name']],set(meta['all_gate_rows']),call['unit_exponent'])
        pcount+=check(meta,rows)
    follow=HERE/'centered-followup';design=json.loads((follow/'pilot/design.json').read_text())
    for call in design['variants']:
        scope=follow/'pilot/models'/call['name']/call['budget_label'];meta=json.loads((scope/call['policy']/'selection.json').read_text())
        base=json.loads((scope/'base.json').read_text());rows=audit.scaled_source(base,set(),0)
        fcount+=check(meta,rows)
    result={'primary_row_interval_certificates':pcount,'followup_row_interval_certificates':fcount,
            'certificate_fields_recomputed_without_selector':True,'new_optimizer_calls':0}
    (HERE/'CERTIFICATE_VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
