#!/usr/bin/env python3
"""Exceed restricted solver model sizes; never print license credentials."""
import json
import os
from pathlib import Path
import sys


def main():
    import gurobipy as gp
    import cplex
    report=dict(hostname=os.uname().nodename,slurm_job=os.environ.get('SLURM_JOB_ID'),
        explicit_Gurobi_license_file_set=bool(os.environ.get('GRB_LICENSE_FILE')),
        variables=2501,technical_LP_calls=2,benchmark_observations=0,solvers={})
    try:
        with gp.Env(params={'OutputFlag':0}) as env,gp.Model(env=env) as m:
            m.Params.Threads=1;m.Params.TimeLimit=10
            x=m.addVars(2501,lb=0,ub=1)
            m.setObjective(gp.quicksum(x.values()),gp.GRB.MAXIMIZE);m.optimize()
            assert m.Status==2 and m.ObjVal==2501
            report['solvers']['gurobi']=dict(passed=True,version=list(gp.gurobi.version()))
    except Exception as e:
        report['solvers']['gurobi']=dict(passed=False,error_type=type(e).__name__)
    try:
        with cplex.Cplex() as m:
            for fn in [m.set_log_stream,m.set_results_stream,m.set_warning_stream,m.set_error_stream]:fn(None)
            m.parameters.threads.set(1);m.parameters.timelimit.set(10)
            m.variables.add(obj=[1.]*2501,lb=[0.]*2501,ub=[1.]*2501)
            m.objective.set_sense(m.objective.sense.maximize);m.solve()
            assert m.solution.is_primal_feasible() and m.solution.get_objective_value()==2501
            report['solvers']['cplex']=dict(passed=True,version=m.get_version())
    except Exception as e:
        report['solvers']['cplex']=dict(passed=False,error_type=type(e).__name__)
    report['status']='passed' if len(report['solvers'])==2 and all(v['passed'] for v in report['solvers'].values()) else 'failed'
    Path(sys.argv[1]).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)
    if report['status']!='passed':raise SystemExit(1)


if __name__=='__main__':main()
