from pathlib import Path
import json,time
import gurobipy as gp
out=Path(__file__).resolve().parent
root=out.parents[3]
source=root/'results-revision/research-audit/fixed-basis-final-20260914/fresh'
env=gp.Env(params={"OutputFlag":0})
records=[]
for cls,instance in [("simple","caso01a"),("sgtm","instance001"),("sgtm","instance077")]:
 for policy in ["Base","Flat-GM"]:
  model=gp.read(str(source/cls/instance/(policy+".lp")),env=env)
  model.setParam("OutputFlag",1); model.setParam("LogToConsole",0)
  model.setParam("LogFile",str(out/(instance+"-"+policy+".log")))
  for k,v in {"Threads":4,"Seed":42,"TimeLimit":60,"MIPGap":.01}.items(): model.setParam(k,v)
  t=time.perf_counter();model.optimize();elapsed=time.perf_counter()-t
  row={"class":cls,"instance":instance,"policy":policy,"status":model.Status,"solutions":model.SolCount,"work":model.Work,"runtime":model.Runtime,"elapsed":elapsed,"gap":model.MIPGap if model.SolCount else None}
  records.append(row); (out/"results.json").write_text(json.dumps(records,indent=2)+"\n")
  print(row,flush=True);model.dispose()
env.dispose()
