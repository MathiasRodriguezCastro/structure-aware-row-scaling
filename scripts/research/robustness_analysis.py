#!/usr/bin/env python3
"""Aggregate the robustness campaign from the per-run records.

Reads every run.json under the campaign root, writes one tidy table, and
reports the endpoints within family x solver x gap: failure-sensitive PAR10 on
the assigned pool, completion and timeout rates, and paired conditional ratios
on the instances completed by all four policies. Seeds and gaps are never
pooled as independent replications.
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "results-revision/solver-robustness"
POLICIES = ["Base", "Flat-GM", "Flat-L2", "Role-Hybrid"]
SOLVERS = ["gurobi", "cplex", "highs"]
FAMILIES = ["Simple", "SG-Ter-Mer", "Full"]
EFFORT = {"gurobi": "work_units", "cplex": "dettime_ticks", "highs": "nodos_explorados"}


def load(root):
    rows = [json.loads(p.read_text()) for p in sorted(root.rglob("run.json"))]
    if not rows:
        raise SystemExit(f"no run.json under {root}")
    d = pd.DataFrame(rows)
    for col in ("cap_s", "gap", "seed", "tiempo_solver_s", "wall_s", "gap_pct", "work_units",
                "dettime_ticks", "nodos_explorados", "iter_simplex", "objetivo_solver",
                "best_bound", "verif_solver_max_viol_relact", "verif_solver_max_int",
                "verif_solver_max_lb", "verif_solver_max_ub", "verif_solver_missing"):
        if col in d:
            d[col] = pd.to_numeric(d[col], errors="coerce")
    d["completed"] = d.outcome.eq("COMPLETED")
    d["censored"] = d.outcome.isin(["TIME_LIMIT", "TIME_LIMIT_NO_SOLUTION", "WRAPPER_TIMEOUT"])
    d["failed"] = ~(d.completed | d.censored)
    d["no_incumbent"] = d.outcome.eq("TIME_LIMIT_NO_SOLUTION")
    # PAR10 cost: measured solver time when completed, ten times the cap otherwise.
    d["par10_s"] = np.where(d.completed, d.tiempo_solver_s.fillna(d.cap_s), 10.0 * d.cap_s)
    d["verified"] = ((d.get("verif_solver_max_viol_relact", pd.Series(np.nan, index=d.index)) <= 1e-6)
                     & (d.get("verif_solver_max_lb", pd.Series(np.nan, index=d.index)) <= 1e-6)
                     & (d.get("verif_solver_max_ub", pd.Series(np.nan, index=d.index)) <= 1e-6)
                     & (d.get("verif_solver_max_int", pd.Series(np.nan, index=d.index)) <= 1e-5)
                     & (d.get("verif_solver_missing", pd.Series(np.nan, index=d.index)) == 0))
    return d


def cells(d):
    out = []
    for (stage, fam, solver, gap, seed), g in d.groupby(["stage", "family", "solver", "gap", "seed"]):
        for policy, gp in g.groupby("policy"):
            done = gp[gp.completed]
            out.append({
                "stage": stage, "family": fam, "solver": solver, "gap": gap, "seed": seed,
                "policy": policy,
                "n": len(gp), "completed": int(gp.completed.sum()), "censored": int(gp.censored.sum()),
                "failed": int(gp.failed.sum()),
                "censored_without_incumbent": int(gp.no_incumbent.sum()),
                "completion_rate": round(float(gp.completed.mean()), 4),
                "par10_mean_s": round(float(gp.par10_s.mean()), 2),
                "median_time_completed_s": round(float(done.tiempo_solver_s.median()), 2) if len(done) else None,
                "median_final_gap_censored_pct": round(float(gp[gp.censored].gap_pct.median()), 4)
                    if gp.censored.any() else None,
                "verified_rate": round(float(gp.verified.mean()), 4),
                # Upper bound on the cost of the policy itself: build + scale + verify.
                "median_nonsolver_overhead_s": round(float((gp.wall_s - gp.tiempo_solver_s).median()), 2)
                    if gp.wall_s.notna().any() else None,
                "infrastructure_failures": int(gp.infrastructure_failure.astype(bool).sum()),
            })
    return pd.DataFrame(out)


def paired(d, seed=None, boot=2000, rng_seed=20260916):
    """Ratios policy/Base on instances completed by every policy, within each cell."""
    rows = []
    sub = d if seed is None else d[d.seed.eq(seed)]
    for (stage, fam, solver, gap, s), g in sub.groupby(["stage", "family", "solver", "gap", "seed"]):
        wide_t = g.pivot_table(index="instance", columns="policy", values="tiempo_solver_s")
        wide_c = g.pivot_table(index="instance", columns="policy", values="completed")
        eff_col = EFFORT[solver]
        wide_e = g.pivot_table(index="instance", columns="policy", values=eff_col) if eff_col in g else None
        pool = wide_c.index[wide_c.reindex(columns=POLICIES).fillna(False).all(axis=1)]
        if len(pool) < 3:
            continue
        rng = np.random.default_rng(rng_seed)
        for policy in POLICIES[1:]:
            for label, wide in (("time", wide_t), ("effort", wide_e)):
                if wide is None or policy not in wide or "Base" not in wide:
                    continue
                r = (wide.loc[pool, policy] / wide.loc[pool, "Base"]).replace([np.inf, -np.inf], np.nan).dropna()
                r = r[r > 0]
                if len(r) < 3:
                    continue
                logs = np.log(r.values)
                idx = rng.integers(0, len(logs), size=(boot, len(logs)))
                gm_boot = np.exp(logs[idx].mean(axis=1))
                rows.append({"stage": stage, "family": fam, "solver": solver, "gap": gap,
                             "seed": s, "policy": policy,
                             "endpoint": label, "n_pairs": len(r),
                             "geometric_mean_ratio": round(float(np.exp(logs.mean())), 4),
                             "median_ratio": round(float(r.median()), 4),
                             "ci_low": round(float(np.quantile(gm_boot, 0.025)), 4),
                             "ci_high": round(float(np.quantile(gm_boot, 0.975)), 4)})
    return pd.DataFrame(rows)


def seed_stability(d):
    """Across-seed dispersion and sign stability of the Flat-GM/Base time ratio."""
    ms = d[d.stage.eq("multiseed") | d.seed.eq(1)]
    rows = []
    for (fam, solver, gap), g in ms.groupby(["family", "solver", "gap"]):
        per_seed = []
        for seed, gs in g.groupby("seed"):
            wide_t = gs.pivot_table(index="instance", columns="policy", values="tiempo_solver_s")
            wide_c = gs.pivot_table(index="instance", columns="policy", values="completed")
            pool = wide_c.index[wide_c.reindex(columns=POLICIES).fillna(False).all(axis=1)]
            if len(pool) < 3 or "Flat-GM" not in wide_t:
                continue
            r = (wide_t.loc[pool, "Flat-GM"] / wide_t.loc[pool, "Base"]).dropna()
            if len(r):
                per_seed.append((int(seed), float(np.exp(np.log(r[r > 0]).mean())), len(r)))
        if len(per_seed) >= 2:
            vals = [v for _, v, _ in per_seed]
            rows.append({"family": fam, "solver": solver, "gap": gap,
                         "seeds": [s for s, _, _ in per_seed], "ratios": [round(v, 4) for v in vals],
                         "min": round(min(vals), 4), "max": round(max(vals), 4),
                         "all_below_one": bool(all(v < 1 for v in vals)),
                         "all_above_one": bool(all(v > 1 for v in vals))})
    return pd.DataFrame(rows)



def audit(d, tables_dir):
    """One row per planned run: every absence is classified, none is silently dropped."""
    planned = []
    for path in sorted(Path(tables_dir).glob("*.csv")):
        planned += list(csv.DictReader(path.open()))
    if not planned:
        raise SystemExit(f"no run tables under {tables_dir}")
    p = pd.DataFrame(planned)[["run_id", "stage", "family", "instance", "policy", "solver", "gap", "seed"]]
    got = d.set_index("run_id")
    p["record"] = p.run_id.isin(got.index)
    p["outcome"] = p.run_id.map(got.outcome) if len(got) else None
    p["infrastructure_failure"] = p.run_id.map(got.infrastructure_failure.astype(bool)) if len(got) else False
    p["status"] = np.where(~p.record, "absent: not yet executed",
                  np.where(p.infrastructure_failure.fillna(False), "present: infrastructure failure",
                           "present: solver outcome"))
    return p


def clustered(d, policies=None):
    """Multi-seed inference with the instance as the resampling unit.

    Seeds of one instance are not independent replications: the per-instance mean of the
    log ratio is the observation, and the bootstrap resamples instances.
    """
    policies = policies or POLICIES[1:]
    ms = d[d.stage.eq("multiseed") | (d.stage.eq("primary") & d.seed.eq(1))]
    rows = []
    for (fam, solver, gap), g in ms.groupby(["family", "solver", "gap"]):
        inst_ms = set(g[g.stage.eq("multiseed")].instance)
        g = g[g.instance.isin(inst_ms)]
        for policy in policies:
            per_instance = []
            for instance, gi in g.groupby("instance"):
                wide_t = gi.pivot_table(index="seed", columns="policy", values="tiempo_solver_s")
                wide_c = gi.pivot_table(index="seed", columns="policy", values="completed")
                if policy not in wide_t or "Base" not in wide_t:
                    continue
                keep = wide_c.reindex(columns=[policy, "Base"]).fillna(False).all(axis=1)
                r = (wide_t.loc[keep, policy] / wide_t.loc[keep, "Base"]).dropna()
                r = r[r > 0]
                if len(r):
                    per_instance.append((instance, float(np.log(r.values).mean()), len(r)))
            if len(per_instance) < 3:
                continue
            vals = np.array([v for _, v, _ in per_instance])
            rng = np.random.default_rng(20260916)
            idx = rng.integers(0, len(vals), size=(4000, len(vals)))
            boot = np.exp(vals[idx].mean(axis=1))
            rows.append({"family": fam, "solver": solver, "gap": gap, "policy": policy,
                         "n_instances": len(vals),
                         "seeds_per_instance_median": float(np.median([n for _, _, n in per_instance])),
                         "geometric_mean_ratio": round(float(np.exp(vals.mean())), 4),
                         "ci_low": round(float(np.quantile(boot, 0.025)), 4),
                         "ci_high": round(float(np.quantile(boot, 0.975)), 4)})
    return pd.DataFrame(rows)



def equivalence(d):
    """Objective agreement across policies on the same instance, against the MIP gap.

    Two policies may stop at different incumbents within the target gap, so the check is
    whether the spread exceeds what the gap allows, not whether it is zero.
    """
    done = d[d.completed & d.objetivo_solver.notna()]
    rows = []
    for (stage, fam, solver, gap, seed, instance), g in done.groupby(
            ["stage", "family", "solver", "gap", "seed", "instance"]):
        obj = g.groupby("policy").objetivo_solver.first()
        if "Base" not in obj or len(obj) < 2:
            continue
        base = obj["Base"]
        scale = max(abs(base), 1.0)
        rel = (obj.drop("Base") - base).abs() / scale
        rows.append({"stage": stage, "family": fam, "solver": solver, "gap": gap, "seed": seed,
                     "instance": instance, "policies": len(obj),
                     "max_rel_objective_gap": float(rel.max()),
                     "worst_policy": str(rel.idxmax()),
                     "above_target_gap": bool(rel.max() > float(gap) + 1e-6)})
    return pd.DataFrame(rows)



def contradictions(d, tol=1e-6):
    """Claims contradicted by a solution that is verified feasible for the same model.

    The dispatch model is a minimization and every returned point is checked against the
    original, unscaled model, so any verified point of any run on that instance is an upper
    bound on its optimum, whatever policy, solver, gap or seed produced it. A run that claims
    optimality within its gap at a worse objective, or reports a dual bound above that point,
    is wrong.
    """
    rows = []
    for (fam, instance), g in d.groupby(["family", "instance"]):
        ok = g[g.verified & g.verif_solver_obj_original.notna()]
        if ok.empty:
            continue
        i = ok.verif_solver_obj_original.idxmin()
        best = float(ok.loc[i, "verif_solver_obj_original"])
        source = f'{ok.loc[i, "solver"]}/{ok.loc[i, "policy"]}/{ok.loc[i, "stage"]}'
        scale = max(abs(best), 1.0)
        for _, r in g.iterrows():
            obj = r.get("verif_solver_obj_original")
            excess = (float(obj) - best) / scale if pd.notna(obj) else None
            bound = r.get("best_bound")
            bound_excess = (float(bound) - best) / scale if pd.notna(bound) else None
            claimed = bool(r.completed) and excess is not None and excess > float(r.gap) + tol
            invalid = bound_excess is not None and bound_excess > tol
            if claimed or invalid:
                rows.append({"stage": r.stage, "family": fam, "solver": r.solver, "gap": r.gap,
                             "seed": r.seed, "instance": instance, "policy": r.policy,
                             "outcome": r.outcome, "objective": obj, "best_known": best,
                             "relative_excess": excess, "best_bound": bound,
                             "bound_relative_excess": bound_excess,
                             "optimality_claim_contradicted": claimed, "dual_bound_invalid": invalid,
                             "best_known_from": source})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=Path, default=BASE / "runs-raw")
    ap.add_argument("--out", type=Path, default=BASE / "analysis")
    ap.add_argument("--tables", type=Path, default=BASE / "runs")
    args = ap.parse_args()
    d = load(args.runs)
    args.out.mkdir(parents=True, exist_ok=True)
    d.to_csv(args.out / "runs.csv", index=False)
    cells(d).to_csv(args.out / "cells.csv", index=False)
    paired(d, seed=1).to_csv(args.out / "paired-primary.csv", index=False)
    paired(d).to_csv(args.out / "paired-all-seeds.csv", index=False)
    seed_stability(d).to_csv(args.out / "seed-stability.csv", index=False)
    clustered(d).to_csv(args.out / "paired-clustered.csv", index=False)
    eq = equivalence(d)
    eq.to_csv(args.out / "objective-equivalence.csv", index=False)
    bad = contradictions(d)
    bad.to_csv(args.out / "contradictions.csv", index=False)
    a = audit(d, args.tables)
    a.to_csv(args.out / "audit.csv", index=False)
    summary = {"runs": len(d), "stages": d.stage.value_counts().to_dict(),
               "outcomes": d.outcome.value_counts().to_dict(),
               "infrastructure_failures": int(d.infrastructure_failure.astype(bool).sum()),
               "solvers": sorted(set(d.solver)), "families": sorted(set(d.family)),
               "contradictions": {"runs_flagged": int(len(bad)),
                   "optimality_claims_contradicted": int(bad.optimality_claim_contradicted.sum()) if len(bad) else 0,
                   "invalid_dual_bounds": int(bad.dual_bound_invalid.sum()) if len(bad) else 0,
                   "by_policy": {k: int(v) for k, v in bad.policy.value_counts().items()} if len(bad) else {}},
               "objective_equivalence": {"instances_compared": int(len(eq)),
                   "above_target_gap": int(eq.above_target_gap.sum()) if len(eq) else 0,
                   "max_rel_objective_gap": float(eq.max_rel_objective_gap.max()) if len(eq) else None},
               "audit": {f"{k[0]}|{k[1]}": int(v)
                         for k, v in a.groupby(["stage", "status"]).size().items()}}
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
