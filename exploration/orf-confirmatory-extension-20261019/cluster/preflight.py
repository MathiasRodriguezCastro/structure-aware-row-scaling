#!/usr/bin/env python3
"""Isolated compute-node dependency/license probe; never a benchmark observation."""
import importlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys
import traceback


def main():
    out=Path(sys.argv[1])
    report=dict(hostname=os.uname().nodename,slurm_job=os.environ.get('SLURM_JOB_ID'),
        python=sys.version,modules={},solvers={},benchmark_observation=False,
        concurrency_tested=1,maximum_license_concurrency_unknown=True)
    for name in ['numpy','scipy','highspy','gurobipy','cplex']:
        try:
            m=importlib.import_module(name)
            report['modules'][name]=dict(importable=True,version=getattr(m,'__version__',None))
        except Exception as e:report['modules'][name]=dict(importable=False,error=str(e))
    if report['modules']['gurobipy']['importable']:
        try:
            import gurobipy as gp
            with gp.Env(params={'OutputFlag':0}) as env, gp.Model(env=env) as m:
                m.Params.Threads=1;m.Params.TimeLimit=10
                x=m.addVars(1100,lb=0,ub=1);m.setObjective(gp.quicksum(x.values()),gp.GRB.MAXIMIZE)
                m.optimize()
                report['solvers']['gurobi']=dict(passed=m.Status==2,version=list(gp.gurobi.version()),
                    variables=m.NumVars,objective=m.ObjVal)
        except Exception as e:report['solvers']['gurobi']=dict(passed=False,error=str(e))
    if report['modules']['cplex']['importable']:
        try:
            import cplex
            with cplex.Cplex() as m:
                for fn in [m.set_log_stream,m.set_results_stream,m.set_warning_stream,m.set_error_stream]:fn(None)
                m.parameters.threads.set(1);m.parameters.timelimit.set(10)
                m.variables.add(obj=[1.]*1100,lb=[0.]*1100,ub=[1.]*1100)
                m.objective.set_sense(m.objective.sense.maximize);m.solve()
                report['solvers']['cplex']=dict(passed=m.solution.is_primal_feasible(),version=m.get_version(),
                    variables=m.variables.get_num(),objective=m.solution.get_objective_value())
        except Exception as e:report['solvers']['cplex']=dict(passed=False,error=str(e))
    report['maximum_RSS_KiB']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    report['status']='passed' if all(v['importable'] for v in report['modules'].values()) and len(report['solvers'])==2 and all(v['passed'] for v in report['solvers'].values()) else 'incomplete'
    out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
