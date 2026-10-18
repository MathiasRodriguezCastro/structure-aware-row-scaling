"""Pre-solve native-reader audit of every unique numeric export and SOS/indicator."""
import json
from pathlib import Path

import gurobipy as gp
import study

HERE=Path(__file__).resolve().parent


def main():
    assert not (HERE/'pilot/runs').exists()
    design=json.loads((HERE/'pilot/design.json').read_text());env=gp.Env(empty=True)
    env.setParam('OutputFlag',0);env.start();seen=set();count=0
    for call in design['calls']:
        key=call['name'],call['arm']
        if key in seen:continue
        seen.add(key);folder=HERE/'pilot/models'/call['name']/call['arm']
        data=json.loads((folder/'model.json').read_text());meta=json.loads((folder/'selection.json').read_text())
        model=gp.read(str(folder/'model.lp'),env=env);study.import_check(model,data,meta,gp);model.dispose();count+=1
    env.dispose()
    result={'before_first_optimize':True,'native_imports_checked':count,'coefficients_rhs_objective_domains_sos_indicators_checked':True,
            'optimizer_calls':0,'solver_version':list(gp.gurobi.version())}
    study.dump(HERE/'IMPORT_AUDIT.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':main()
