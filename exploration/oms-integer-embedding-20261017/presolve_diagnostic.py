"""Post-pilot diagnostic: compare actual presolved matrices and domains."""
import hashlib
import json
from pathlib import Path

import gurobipy as gp

HERE=Path(__file__).resolve().parent


def main():
    env=gp.Env(empty=True);env.setParam('OutputFlag',0);env.start();report=[]
    for name,budget in [('control30-3-2-3','1e-04'),('neos-3421095-cinca','1e-04'),('neos-3421095-cinca','1e-08')]:
        arms=[]
        for policy in ('Integer-copy','Continuous-copy'):
            folder=HERE/'pilot/models'/name/(policy+'-'+budget)
            meta=json.loads((folder/'selection.json').read_text());model=gp.read(str(folder/'model.lp'),env=env)
            for key,value in {'IntFeasTol':1e-9,'FeasibilityTol':1e-6,'Presolve':-1,'Threads':4,'PreSOS1BigM':0}.items():
                model.setParam(key,value)
            reduced=model.presolve();variables=reduced.getVars();names={v.VarName for v in variables}
            columns=[(v.VarName,v.VType,v.LB,v.UB,v.Obj) for v in variables];rows=[]
            for constraint in reduced.getConstrs():
                a=reduced.getRow(constraint)
                rows.append((constraint.ConstrName,constraint.Sense,constraint.RHS,
                             sorted((a.getVar(j).VarName,a.getCoeff(j)) for j in range(a.size()))))
            payload={'columns':sorted(columns),'rows':sorted(rows),'objective_constant':reduced.ObjCon,'model_sense':reduced.ModelSense}
            arms.append({'policy':policy,'variables':reduced.NumVars,'integer_variables':reduced.NumIntVars,
                         'rows':reduced.NumConstrs,'binary_variables':reduced.NumBinVars,'original_copy_count':len(meta['copies']),
                         'copy_variables_retained':sum(f'x{c["q"]:05d}' in names for c in meta['copies']),
                         'canonical_presolved_sha256':hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()})
            reduced.dispose();model.dispose()
        report.append({'name':name,'budget':budget,'arms':arms,
                       'identical_presolved_matrix_and_domains':arms[0]['canonical_presolved_sha256']==arms[1]['canonical_presolved_sha256']})
    env.dispose()
    result={'post_pilot_mechanism_diagnostic':True,'presolve_calls':6,'optimize_calls':0,'cases':report}
    (HERE/'PRESOLVE_DIAGNOSTIC.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
