"""
Verification v4 -- THE DECISIVE TEST.

Same 2-block MIP as v3 (z_LP=30.8 < z_DW=38 = z_MIP). Now implement classical
BENDERS DECOMPOSITION with the binaries y = (y1_0,y2_0,y1_1,y2_1) in the MASTER
and the continuous variables (x_0,x_1,s) in the SUBPROBLEM (LP with y fixed).

We run two master modes:
  (M-LP)  master y RELAXED to [0,1]  -> Benders cuts -> bound it converges to.
  (M-IP)  master y BINARY            -> branch-and-Benders-cut -> z_MIP.

Hypothesis: (M-LP) converges to z_LP = 30.8, NOT z_DW = 38.
            (M-IP) converges to z_MIP = 38 (it solves the MIP, but the cuts
                   are big-M/dual-LP cuts, the master is itself a hard MIP).

Subproblem (y fixed):
   min  CX*(x0+x1) + CF*s
   s.t. x_i <= UBx_i(y) := (XMAX/2)(y1_i+y2_i)        [x_i <= bnd_i]
        x_i <= XMAX
        x0 + x1 + s >= D
        x,s >= 0
The master then carries F*sum(y) + eta, eta >= subproblem value via Benders
optimality cuts. The cover constraint 3y1+3y2>=4 lives in the MASTER feas set.

Benders optimality cut from LP duals:
   Let the subproblem (primal min) have dual multipliers. We solve the LP,
   read duals on the y-dependent constraints, and form the standard cut
       eta >= dualvalue(y) = sum_i mu_i * UBx_i(y) + lambda*D
   (affine in y). We just query gurobi's parametric dual via re-solving and
   taking the dual of constraints whose RHS depends on y.
"""
import numpy as np
import gurobipy as gp
from gurobipy import GRB

XMAX=10.0; D=14.0; CF=1000.0; CX=1.0; F=6.0
C1,C2,RHS=3.0,3.0,4.0
BND_COEF=XMAX/2.0   # x_i <= BND_COEF*(y1_i+y2_i)

# ---- subproblem: y fixed -> LP over (x0,x1,s). Return value + Benders cut data.
def subproblem(yv):
    """yv = (y1_0,y2_0,y1_1,y2_1). Returns (Qval, cut) where
       cut is (const, coef dict over the 4 y-vars) s.t. eta >= const + coef.y."""
    bnd = [BND_COEF*(yv[0]+yv[1]), BND_COEF*(yv[2]+yv[3])]
    m=gp.Model(); m.Params.OutputFlag=0
    x=[m.addVar(lb=0,ub=XMAX,name=f"x{i}") for i in (0,1)]
    s=m.addVar(lb=0,name="s")
    cbnd=[m.addConstr(x[i] <= bnd[i], name=f"cb{i}") for i in (0,1)]
    cdem=m.addConstr(x[0]+x[1]+s >= D, name="dem")
    m.setObjective(CX*(x[0]+x[1]) + CF*s, GRB.MINIMIZE)
    m.optimize()
    Q=m.ObjVal
    # duals: cbnd are <= constraints (mu<=0 in min sense); cdem is >= (lam>=0)
    mu=[cbnd[i].Pi for i in (0,1)]   # dual on x_i<=bnd_i
    lam=cdem.Pi                      # dual on x0+x1+s>=D
    # Benders optimality cut: eta >= lam*D + sum_i mu_i*bnd_i, with bnd_i affine in y.
    # bnd_i = BND_COEF*(y..). expand into y-coefs.
    const = lam*D
    coef={0:0.0,1:0.0,2:0.0,3:0.0}
    coef[0]+=mu[0]*BND_COEF; coef[1]+=mu[0]*BND_COEF
    coef[2]+=mu[1]*BND_COEF; coef[3]+=mu[1]*BND_COEF
    return Q, (const, coef)

# ---- Benders master loop. relax=True -> y in [0,1]; relax=False -> y binary.
def benders(relax, maxit=200, verbose=False):
    m=gp.Model(); m.Params.OutputFlag=0
    vt=GRB.CONTINUOUS if relax else GRB.BINARY
    y=[m.addVar(vtype=vt,lb=0,ub=1,name=f"y{j}") for j in range(4)]
    # cover constraints (master feasibility): 3y1+3y2>=4 per block
    m.addConstr(C1*y[0]+C2*y[1]>=RHS)
    m.addConstr(C1*y[2]+C2*y[3]>=RHS)
    eta=m.addVar(lb=0,name="eta")
    m.setObjective(F*gp.quicksum(y)+eta, GRB.MINIMIZE)
    LB=-1e18
    for it in range(maxit):
        m.optimize()
        LB=m.ObjVal
        yv=[v.X for v in y]
        Q,(const,coef)=subproblem(yv)
        etav=eta.X
        # check cut violation
        rhs_cut = const + sum(coef[j]*yv[j] for j in range(4))
        if verbose:
            print(f"  it{it}: LB={LB:.4f} y={[round(v,3) for v in yv]} eta={etav:.4f} Q={Q:.4f} cutrhs={rhs_cut:.4f}")
        if etav >= rhs_cut - 1e-6:
            # no violated cut -> converged
            return LB, yv, it
        m.addConstr(eta >= const + gp.quicksum(coef[j]*y[j] for j in range(4)))
    return LB, [v.X for v in y], maxit

print("=== Benders, master y RELAXED to [0,1] ===")
lb_lp, y_lp, it_lp = benders(relax=True, verbose=True)
print(f"  --> converged bound = {lb_lp:.6f} in {it_lp} iters, y={[round(v,3) for v in y_lp]}")
print()
print("=== Benders, master y BINARY (branch-and-Benders-cut, single tree via lazy not needed here) ===")
lb_ip, y_ip, it_ip = benders(relax=False, verbose=True)
print(f"  --> converged bound = {lb_ip:.6f} in {it_ip} iters, y={[round(v,3) for v in y_ip]}")
print()
print("=== REFERENCE BOUNDS (from v3) ===")
print(f"  z_LP=30.8   z_DW=38.0   z_MIP=38.0")
print()
print("VERDICT on hypothesis 1:")
print(f"  Benders-LP-master bound = {lb_lp:.4f}  (== z_LP=30.8 ? {abs(lb_lp-30.8)<1e-3};  == z_DW=38 ? {abs(lb_lp-38.0)<1e-3})")
print(f"  Benders-IP-master bound = {lb_ip:.4f}  (== z_MIP=38 ? {abs(lb_ip-38.0)<1e-3})")
