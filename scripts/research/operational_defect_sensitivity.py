#!/usr/bin/env python3
"""Does the SG-Ter-Mer result survive dropping the scenario-defective instances?

Recomputes the paired work ratio and PAR10 of the reconstruction on all 15 instances of the
class and on the 6 whose total demand never falls below local demand. Reads only the frozen
reconstruction; no solver is called.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
POLICY = {"base": "Base", "matricial_plano": "Flat-GM", "matricial_plano_l2": "Flat-L2",
          "role_hybrid": "Role-Hybrid"}


def defective(instances, folder):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from check_sgtm_demand import series
    out = set()
    for name in instances:
        d, tot = series(folder / name)
        if d and tot and any(a > b for a, b in zip(d, tot)):
            out.add(name)
    return out


def cell_table(d, pool):
    g = d[d.instance.isin(pool)].copy()
    g["policy"] = g.variant.map(POLICY)
    # Same measure and pool as the headline numbers: the native log value, on the instances
    # every policy completed with a work reading above the log resolution.
    wide_w = g.pivot_table(index="instance", columns="policy", values="work_native_log")
    wide_c = g.pivot_table(index="instance", columns="policy", values="completed")
    usable = wide_c.fillna(False).all(axis=1) & (wide_w > 0.005).all(axis=1) & wide_w.notna().all(axis=1)
    common = wide_c.index[usable]
    rows = []
    for policy in ["Flat-GM", "Flat-L2", "Role-Hybrid"]:
        r = (wide_w.loc[common, policy] / wide_w.loc[common, "Base"]).replace([np.inf], np.nan).dropna()
        r = r[r > 0]
        rows.append({"policy": policy, "instances": len(pool), "common_completed": len(common),
                     "work_geometric_ratio": round(float(np.exp(np.log(r).mean())), 4) if len(r) else None})
    par10 = g.groupby("policy").par10_seconds.mean().round(2).to_dict()
    return rows, par10


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=Path,
                    default=ROOT / "results-revision/research-audit/operational/reconstructed_runs.csv")
    ap.add_argument("--instances", type=Path, default=ROOT / "data/entradas/entrada-SG-Ter-Mer")
    ap.add_argument("--tex", type=Path, default=ROOT / "paper/tables/defect-sensitivity.tex")
    ap.add_argument("--out", type=Path,
                    default=ROOT / "results-revision/research-audit/operational/defect-sensitivity.json")
    args = ap.parse_args()
    d = pd.read_csv(args.runs)
    result = {}
    for cell in sorted(c for c in d.cell.unique() if "sgtm" in c):
        sub = d[d.cell.eq(cell)]
        pool = sorted(sub.instance.unique())
        bad = defective(pool, args.instances)
        clean = [i for i in pool if i not in bad]
        rows_all, par_all = cell_table(sub, pool)
        rows_clean, par_clean = cell_table(sub, clean)
        result[cell] = {"defective": sorted(bad), "defect_free": clean,
                        "all": {"ratios": rows_all, "mean_par10_s": par_all},
                        "defect_free_only": {"ratios": rows_clean, "mean_par10_s": par_clean}}
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    if args.tex:
        gap = {"gurobi_sgtm_1pct": r"1\%", "gurobi_sgtm_01pct": r"0.1\%"}
        lines = [r"\begin{tabular}{llrrrr}", r"\toprule",
                 r"& & \multicolumn{2}{c}{Work ratio vs Base} & \multicolumn{2}{c}{Mean PAR10 (s)} \\",
                 r"Gap & Policy & All 15 & Defect-free 6 & All 15 & Defect-free 6 \\", r"\midrule"]
        for cell in ["gurobi_sgtm_1pct", "gurobi_sgtm_01pct"]:
            r = result[cell]
            lines.append(f"{gap[cell]} & Base & --- & --- & "
                         f"{r['all']['mean_par10_s']['Base']:.1f} & "
                         f"{r['defect_free_only']['mean_par10_s']['Base']:.1f} \\\\")
            for a_row, b_row in zip(r["all"]["ratios"], r["defect_free_only"]["ratios"]):
                pol = a_row["policy"]
                lines.append(f" & {pol} & {a_row['work_geometric_ratio']:.3f} & "
                             f"{b_row['work_geometric_ratio']:.3f} & "
                             f"{r['all']['mean_par10_s'][pol]:.1f} & "
                             f"{r['defect_free_only']['mean_par10_s'][pol]:.1f} \\\\")
            if cell != "gurobi_sgtm_01pct":
                lines.append(r"\addlinespace")
        lines += [r"\bottomrule", r"\end{tabular}"]
        args.tex.write_text("\n".join(lines) + "\n")
        print("wrote", args.tex)
    for cell, r in result.items():
        print(cell, f"({len(r['defect_free'])} defect-free of {len(r['defect_free'])+len(r['defective'])})")
        for a, b in zip(r["all"]["ratios"], r["defect_free_only"]["ratios"]):
            print(f"  {a['policy']:12s} all {a['work_geometric_ratio']} (n={a['common_completed']})"
                  f"   defect-free {b['work_geometric_ratio']} (n={b['common_completed']})")
        print("  PAR10 all       ", r["all"]["mean_par10_s"])
        print("  PAR10 defect-free", r["defect_free_only"]["mean_par10_s"])


if __name__ == "__main__":
    main()
