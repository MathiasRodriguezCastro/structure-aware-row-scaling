#!/usr/bin/env python3
"""Tables and summary statistics for the fixed-basis conditioning audit."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

CLASSES = [("simple", "Simple"), ("sgtm", "SG-Ter-Mer"), ("full", "Full")]
SCALED = ["Flat-GM", "Flat-L2", "Role-Hybrid", "SA-Mat"]


def sci(x, digits=1):
    if 0.1 <= x < 100:
        return f"{x:.2f}"
    e = int(math.floor(math.log10(x)))
    m = x / 10**e
    if round(m, digits) >= 10:
        m, e = m / 10, e + 1
    return f"${m:.{digits}f}\\times10^{{{e}}}$"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("results-revision/research-audit/fixed-basis-final-20260914"))
    ap.add_argument("--tables", type=Path, default=Path("paper/tables"))
    args = ap.parse_args()
    d = pd.read_csv(args.root / "fresh-results.csv")
    attempts = pd.read_csv(args.root / "attempts.csv")
    d["kappa"] = d.kappa1_seed0
    wide = d.pivot_table(index=["class", "instance"], columns="variant", values="kappa")
    sha = d.pivot_table(index=["class", "instance"], columns="variant", values="basis_sha256", aggfunc="first")
    out = {"attempts": attempts.status.value_counts().to_dict(), "classes": {}}
    main_rows = {"Base": [], **{v: [] for v in SCALED}}
    header = []
    si_lines = [r"\begin{tabular}{llrrrrr}", r"\toprule",
                r"Class & Policy & $n$ & Median ratio & Minimum & Maximum & Improved \\", r"\midrule"]
    for cls, label in CLASSES:
        w = wide.loc[cls].dropna()
        n = len(w)
        info = {"n": n, "median_base_kappa1": float(w.Base.median()),
                "min_base_kappa1": float(w.Base.min()), "max_base_kappa1": float(w.Base.max())}
        cells = []
        for v in SCALED:
            r = w[v] / w.Base
            info[v] = {"median_ratio": float(r.median()), "min_ratio": float(r.min()),
                       "max_ratio": float(r.max()), "improved": int((r < 1).sum()),
                       "median_kappa1": float(w[v].median()), "max_kappa1": float(w[v].max()),
                       "median_log10_ratio": float(np.log10(r).median())}
            cells.append(f"{sci(r.median())} ({int((r < 1).sum())})")
            si_lines.append(f"{label} & {v} & {n} & {sci(r.median())} & {sci(r.min())} & "
                            f"{sci(r.max())} & {int((r < 1).sum())} \\\\")
        s = sha.loc[cls].loc[w.index]
        info["identical_basis_matrices"] = {
            f"{a} = {b}": int((s[a] == s[b]).sum())
            for a, b in [("SA-Mat", "Role-Hybrid"), ("SA-Mat", "Flat-GM"), ("Role-Hybrid", "Flat-GM"),
                         ("Flat-GM", "Flat-L2")]}
        info["max_scaled_kappa1"] = float(w[SCALED].max().max())
        info["min_orders_of_magnitude_improvement"] = float(-np.log10((w[SCALED].max(axis=1) / w.Base)).max())
        sub = d[d["class"].eq(cls)]
        info["max_estimator_spread"] = float(sub.estimator_max_min.max())
        info["max_lu_backward_error"] = float(sub.lu_componentwise_backward_error.max())
        info["max_row_scaling_relative_error"] = float(max(sub.max_coefficient_rel_error.max(), sub.max_rhs_rel_error.max()))
        out["classes"][label] = info
        header.append(f"{label} ($n={n}$)")
        main_rows["Base"].append(sci(w.Base.median()))
        for v, c in zip(SCALED, cells):
            main_rows[v].append(c)
        si_lines.append(r"\addlinespace")
    si_lines[-1:] = [r"\bottomrule", r"\end{tabular}"]
    main_lines = [r"\begin{tabular}{lrrr}", r"\toprule", "Policy & " + " & ".join(header) + r" \\",
                  r"\midrule", r"Base, median $\kappa_1$ & " + " & ".join(main_rows["Base"]) + r" \\",
                  r"\addlinespace"]
    main_lines += [f"{v} & " + " & ".join(main_rows[v]) + r" \\" for v in SCALED]
    main_lines += [r"\bottomrule", r"\end{tabular}"]
    precision = args.root / "precision-check" / "results.json"
    if precision.exists():
        pr = {(r["class"], r["instance"], r["variant"]): r for r in json.loads(precision.read_text())}
        design = json.loads((args.root / "precision-check" / "design.json").read_text())
        labels = dict(CLASSES)
        lines = [r"\begin{tabular}{llrrrr}", r"\toprule",
                 r"Class & Model & Base $\kappa_1\ge$ & Enclosure width & Flat-GM/Base estimate & Upper bound \\",
                 r"\midrule"]
        summary = []
        for cls, chosen in design["selection"].items():
            for inst in dict.fromkeys(chosen.values()):
                recs = [pr[cls, inst, v] for v in ("Base", "Flat-GM", "Flat-L2")]
                width = max(x["kappa1_upper_bound"] / x["kappa1_certified_lower"] - 1 for x in recs)
                est = recs[1]["kappa1_estimate_seed0"] / recs[0]["kappa1_estimate_seed0"]
                bound = recs[1]["kappa1_upper_bound"] / recs[0]["kappa1_certified_lower"]
                summary.append({"class": cls, "instance": inst, "enclosure_width": width,
                                "ratio_estimate": est, "ratio_upper_bound": bound,
                                "estimates_inside_enclosure": sum(x["kappa1_certified_lower"] <= x["kappa1_estimate_seed0"]
                                                                 <= x["kappa1_upper_bound"] for x in recs)})
                lines.append(f"{labels[cls]} & {Path(inst).stem} & {sci(recs[0]['kappa1_certified_lower'])} & "
                             f"{sci(width)} & {sci(est, 3)} & {sci(bound, 3)} \\\\")
        lines += [r"\bottomrule", r"\end{tabular}"]
        (args.tables / "fixed-basis-precision.tex").write_text("\n".join(lines) + "\n")
        out["precision_check"] = summary
    verification = args.root / "independent-verification.json"
    if verification.exists():
        v = json.loads(verification.read_text())
        out["independent_verification"] = {k: v[k] for k in v if k != "checks"}
    args.tables.mkdir(parents=True, exist_ok=True)
    (args.tables / "fixed-basis.tex").write_text("\n".join(main_lines) + "\n")
    (args.tables / "fixed-basis-si.tex").write_text("\n".join(si_lines) + "\n")
    (args.root / "analysis.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
