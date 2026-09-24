"""Hard wall-clock isolation for exploratory calls that may exceed native limits."""
import multiprocessing as mp
import time
import numpy as np


def _worker(conn,solver,A,b,c,presolve,tolerance,seed):
    try:
        from residual_budget_experiment import solve_highs,solve_gurobi
        if solver=='highs':result=solve_highs(A,b,c,presolve,tolerance,seed)
        else:
            import gurobipy as gp
            env=gp.Env(empty=True);env.setParam('OutputFlag',0);env.start()
            try:result=solve_gurobi(A,b,c,presolve,tolerance,seed,env)
            finally:env.dispose()
        status,x,wall,nodes=result
        conn.send((status,None if x is None else x.tolist(),wall,nodes))
    except BaseException as err:
        conn.send(('EXCEPTION_'+type(err).__name__,None,0.,0))
    finally:conn.close()


def isolated_solve(solver,A,b,c,presolve,tolerance,seed,external_limit=25.):
    ctx=mp.get_context('spawn');parent,child=ctx.Pipe(duplex=False)
    p=ctx.Process(target=_worker,args=(child,solver,A,b,c,presolve,tolerance,seed))
    tic=time.perf_counter();p.start();child.close()
    if parent.poll(external_limit):
        try:status,x,wall,nodes=parent.recv()
        except EOFError:status,x,wall,nodes='WORKER_EXIT',None,time.perf_counter()-tic,0
    else:status,x,wall,nodes='EXTERNAL_LIMIT',None,time.perf_counter()-tic,0
    p.join(timeout=.5)
    if p.is_alive():p.terminate();p.join(timeout=1.)
    if p.is_alive():p.kill();p.join(timeout=1.)
    parent.close()
    return status,None if x is None else np.asarray(x),wall,nodes
