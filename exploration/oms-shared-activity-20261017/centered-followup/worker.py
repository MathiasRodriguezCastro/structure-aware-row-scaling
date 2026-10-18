"""One native call, from preserved-model selection through independent delivery."""
import json
import math
from pathlib import Path
import sys
import time

started=time.perf_counter()
import gurobipy as gp
import numpy as np
import campaign
import method
import deliver

index=int(sys.argv[1]);out=Path(sys.argv[2]);design=json.loads((campaign.HERE/'pilot/design.json').read_text())
campaign.check_design(design);call=design['calls'][index]
scope=campaign.HERE/'pilot/models'/call['name']/call['budget_label'];arm=scope/call['policy']
for file,key in (('base.json','base_sha256'),('original.json','original_sha256')):assert campaign.sha(scope/file)==call[key]
base=json.loads((scope/'base.json').read_text());original=json.loads((scope/'original.json').read_text())
selection_started=time.perf_counter();model,meta=method.compile_model(base,call['policy'],campaign.parent)
assert model is not None
campaign.parent.write_lp(out/'model.lp',model,meta)
assert campaign.sha(out/'model.lp')==call['export_sha256']
assert model==json.loads((arm/'model.json').read_text()) and meta==json.loads((arm/'selection.json').read_text())
selection_export_seconds=time.perf_counter()-selection_started
import_started=time.perf_counter();env=gp.Env(empty=True);env.setParam('OutputFlag',0);env.start()
native=gp.read(str(out/'model.lp'),env=env);variables=campaign.parent.import_check(native,model,meta,gp)
import_seconds=time.perf_counter()-import_started
for key,value in {**call['parameters'],'Seed':call['seed'],'OutputFlag':1,'LogToConsole':0,'LogFile':str(out/'solver.log')}.items():native.setParam(key,value)
native.optimize()
record={**call,'solver_version':list(gp.gurobi.version()),'status':native.Status,'has_point':native.SolCount>0,
        'solution_count':native.SolCount,'objective':native.ObjVal if native.SolCount else None,
        'reported_bound':native.ObjBound if math.isfinite(native.ObjBound) else None,'optimality_certified':False,
        'work':native.Work,'runtime':native.Runtime,'nodes':native.NodeCount,
        'selection_export_seconds':selection_export_seconds,'import_check_seconds':import_seconds,
        'sos':native.NumSOS,'variables':native.NumVars,'constraints':native.NumConstrs,'indicators':native.NumGenConstrs}
verification={'has_point':record['has_point'],'original_optimality_certified':False}
if native.SolCount:
    values=np.array([variables[f'x{j:05d}'].X for j in range(len(model['variables']))]);np.savez(out/'point.npz',x=values)
    verification_started=time.perf_counter()
    verification.update(deliver.point(original,model,meta,values,design['reference_objectives'][call['name']]))
    verification['verification_seconds']=time.perf_counter()-verification_started
native.dispose();env.dispose()
record['worker_through_verification_seconds']=time.perf_counter()-started
campaign.dump(out/'verification.json',verification);campaign.dump(out/'run.json',record)
