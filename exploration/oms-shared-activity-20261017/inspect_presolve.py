"""Native representation inspection only: no optimize calls or causal claim."""
from fractions import Fraction
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def main():
    import gurobipy as gp
    design=json.loads((HERE/'pilot/design.json').read_text());target=HERE/'presolve-inspection';target.mkdir(exist_ok=True)
    env=gp.Env(empty=True);env.setParam('OutputFlag',0);env.start();reports=[]
    for policy in ('Shared-budget','SOS-unit','SOS-normalized','SOS-range'):
        call=next(a for a in design['assignments'] if a['name']=='control30-3-2-3' and a['policy']==policy and a['unit_exponent']==0)
        arm=HERE/'pilot/models'/call['name']/call['canonical_arm']
        assert hashlib.sha256((arm/'model.lp').read_bytes()).hexdigest()==call['export_sha256']
        meta=json.loads((arm/'selection.json').read_text());m=gp.read(str(arm/'model.lp'),env=env)
        for k,v in call['parameters'].items():m.setParam(k,v)
        reduced=m.presolve();reduced.write(str(target/(policy+'.mps')))
        orig={v.VarName:v for v in m.getVars()};sos=[];observations=[]
        for ss in reduced.getSOSs():
            _,members,weights=reduced.getSOS(ss)
            sos.append([{'name':v.VarName,'lower':v.LB,'upper':v.UB,
                         'original_lower':orig[v.VarName].LB if v.VarName in orig else None,
                         'original_upper':orig[v.VarName].UB if v.VarName in orig else None} for v in members])
        for link in meta['links']:
            name=f'x{link["y"]:05d}';v=reduced.getVarByName(name)
            row_name=f'r{link["row"]:05d}';c=reduced.getConstrByName(row_name)
            if v is None or c is None:continue
            old=m.getRow(m.getConstrByName(row_name));new=reduced.getRow(c)
            old_terms={old.getVar(j).VarName:old.getCoeff(j) for j in range(old.size())}
            new_terms={new.getVar(j).VarName:new.getCoeff(j) for j in range(new.size())}
            if name not in new_terms or {k:x for k,x in old_terms.items() if k!=name}!={k:x for k,x in new_terms.items() if k!=name}:continue
            if old_terms[name]==new_terms[name]:continue
            observations.append({'row':link['row'],'variable':name,'old_coefficient':old_terms[name],
                                 'new_coefficient':new_terms[name],
                                 'coefficient_ratio':str(Fraction.from_float(new_terms[name])/Fraction.from_float(old_terms[name])),
                                 'old_upper':orig[name].UB,'new_upper':v.UB,
                                 'other_row_coefficients_unchanged':True})
        reports.append({'policy':policy,'export_sha256':call['export_sha256'],'original_sos':m.NumSOS,
                        'presolved_sos':reduced.NumSOS,'variables':reduced.NumVars,'rows':reduced.NumConstrs,
                        'members':sos,'changed_activity_coefficients':observations,'optimizer_calls':0,
                        'causal_interpretation':'Representation observations only. No complete presolve inverse map or causality certificate is inferred.'})
        m.dispose();reduced.dispose()
    env.dispose();(target/'REPORT.json').write_text(json.dumps(reports,indent=2)+'\n')
    print(json.dumps([{'policy':r['policy'],'presolved_sos':r['presolved_sos'],
                       'changed_activity_coefficients':len(r['changed_activity_coefficients'])} for r in reports],indent=2))


if __name__=='__main__':main()
