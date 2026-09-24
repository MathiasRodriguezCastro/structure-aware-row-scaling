#!/usr/bin/env python3
"""Reconstruct final operational evidence without overwriting historical results.

Native Gurobi log summaries recover Work to 0.01 units after the legacy C++
stream-format bug rounded scaled runs to whole units. Timeouts are penalized
only in seconds. Work is a secondary common-completed-pool diagnostic; failure
and residual counts stay on the complete assigned pool. All inference is
exploratory. No solver is run and no external connection is made by this script.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np

VARIANTS = ("base", "matricial_plano", "matricial_plano_l2", "role_hybrid")
LABELS = dict(zip(VARIANTS, ("Base", "Flat-GM", "Flat-L2", "Role-Hybrid")))
WORK = re.compile(r"Explored [^\n]*? in [\d.eE+-]+ seconds \(([\d.eE+-]+) work units\)")
STOPPED = {"TIME_LIMIT", "WORK_LIMIT", "NODE_LIMIT", "INTERRUPTED", "SUBOPTIMAL"}
COMPLETE = {"OPTIMAL", "OPTIMO", "SOLVED", "INTEGER OPTIMAL"}


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def completed(row):
    # Process OK only means the wrapper exited successfully, including timeouts.
    return row.get("status") == "OK" and row.get("status_solver") in COMPLETE


def time_cost(row, timeout):
    value = number(row.get("tiempo_solver_s"))
    return value if completed(row) and value is not None and value >= 0 else 10 * timeout


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def boot_ratio(a, b, rng, draws, geometric=False):
    a, b = np.asarray(a), np.asarray(b)
    index = rng.integers(0, len(a), size=(draws, len(a)))
    if geometric:
        if np.any(a <= 0) or np.any(b <= 0):
            raise ValueError("Geometric analysis requires strictly positive measurements")
        ratios = np.log(a / b)
        estimate = np.exp(ratios.mean())
        resampled = np.exp(ratios[index].mean(axis=1))
    else:
        estimate = a.mean() / b.mean()
        resampled = a[index].mean(axis=1) / b[index].mean(axis=1)
    lo, hi = np.quantile(resampled, [0.025, 0.975])
    return tuple(float(x) for x in (estimate, lo, hi))


def bound_integer_ok(row, tol=1e-6):
    values = [number(row.get(key)) for key in
              ("verif_solver_max_lb", "verif_solver_max_ub", "verif_solver_max_int")]
    return all(x is not None and x <= tol for x in values)


def residual_readings(row):
    """Explicit sensitivity readings, not domain-calibrated acceptance standards."""
    vals = [number(row.get(key)) for key in
            ("verif_solver_max_le", "verif_solver_max_ge", "verif_solver_max_eq")]
    abs_residual = max(vals) if all(x is not None for x in vals) else None
    activity = number(row.get("verif_solver_max_viol_relact"))
    available = number(row.get("verif_solver_missing")) == 0 and abs_residual is not None
    bound_ok = bound_integer_ok(row)
    strict = available and bound_ok and abs_residual <= 1e-6
    # The union below is deliberately a global aggregate sensitivity; it is not
    # equivalent to checking the mixed test separately for each row.
    activity_1e8 = available and bound_ok and activity is not None and activity <= 1e-8
    activity_1e6 = available and bound_ok and activity is not None and activity <= 1e-6
    return abs_residual, activity, available, strict, activity_1e8, activity_1e6


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=root / "results-revision/final-variants")
    parser.add_argument("--output", type=Path, default=root / "results-revision/research-audit/operational")
    parser.add_argument("--timeout", type=float, default=1800.0)
    parser.add_argument("--bootstrap", type=int, default=10000)
    args = parser.parse_args()
    args.source = args.source.resolve()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20260908)
    manifest, reconstructed, summaries, contrasts, identities = [], [], [], [], []
    for source in sorted(args.source.glob("*/resumen.csv")):
        cell = source.parent.name
        manifest.append({"path": str(source.relative_to(root)), "sha256": sha256(source)})
        rows = list(csv.DictReader(source.open()))
        by_instance = {}
        for row in rows:
            instance, variant = row["instancia"], row["variante"]
            if variant not in VARIANTS:
                raise ValueError(f"Unexpected variant {variant}")
            group = by_instance.setdefault(instance, {})
            if variant in group:
                raise ValueError(f"Duplicate assignment: {cell}/{instance}/{variant}")
            group[variant] = row
            filename = f"{Path(instance).stem}_{variant}.log"
            candidates = [source.parent / "logs" / filename,
                          args.output / "cluster-logs" / cell / "logs" / filename]
            log = next((p for p in candidates if p.is_file()), None)
            work = None
            if log is not None:
                matches = WORK.findall(log.read_text(errors="replace"))
                if len(matches) != 1:
                    raise ValueError(f"Expected exactly one MIP Work summary in {log}: {matches}")
                work = float(matches[0])
                manifest.append({"path": str(log.relative_to(root)), "sha256": sha256(log)})
            row["audit_work"] = work
            row["audit_complete"] = completed(row)
            ar, act, available, strict, act8, act6 = residual_readings(row)
            recorded = number(row.get("work_units"))
            reconstructed.append({
                "cell": cell, "instance": instance, "variant": variant,
                "status_solver": row["status_solver"], "completed": row["audit_complete"],
                "solver_seconds": number(row.get("tiempo_solver_s")),
                "par10_seconds": time_cost(row, args.timeout), "work_recorded": recorded,
                "work_native_log": work, "work_native_resolution": 0.01 if work is not None else None,
                "work_rounding_mismatch": work is not None and recorded is not None and abs(work - recorded) > 0.00500001,
                "nodes": number(row.get("nodos_explorados")), "max_absolute_row_residual": ar,
                "max_rhs_normalized_residual": number(row.get("verif_solver_max_viol_rel")),
                "max_activity_normalized_residual": act, "verification_available": available,
                "absolute_1e6_pass": strict, "activity_1e8_pass": act8, "activity_1e6_pass": act6,
                "log": str(log.relative_to(root)) if log else "",
            })
        expected = set(VARIANTS)
        if any(set(group) != expected for group in by_instance.values()):
            raise ValueError(f"Incomplete assigned variant pool in {cell}")
        # Fixed pool, identical across all four methods, for descriptive completed Work.
        work_pool = [group for group in by_instance.values()
                     if all(r["audit_complete"] and r["audit_work"] is not None
                            and r["audit_work"] > 0.005 for r in group.values())]
        for variant in VARIANTS:
            subset = [row for row in reconstructed if row["cell"] == cell and row["variant"] == variant]
            values = [group[variant] for group in by_instance.values()]
            summaries.append({
                "cell": cell, "variant": variant, "n_assigned": len(values),
                "n_completed": sum(r["audit_complete"] for r in values),
                "n_stopped": sum(r["status_solver"] in STOPPED for r in values),
                "n_other_failures": sum(not r["audit_complete"] and r["status_solver"] not in STOPPED for r in values),
                "mean_par10_seconds": float(np.mean([time_cost(r, args.timeout) for r in values])),
                "work_common_completed_n": len(work_pool),
                "recorded_work_zeros": sum(r["work_recorded"] == 0 for r in subset),
                "work_rounding_mismatches": sum(r["work_rounding_mismatch"] for r in subset),
                "max_absolute_row_residual": max(r["max_absolute_row_residual"] for r in subset),
                "max_activity_normalized_residual": max(r["max_activity_normalized_residual"] for r in subset),
                "absolute_1e6_failures": sum(not r["absolute_1e6_pass"] for r in subset),
                "activity_1e8_failures": sum(not r["activity_1e8_pass"] for r in subset),
                "activity_1e6_failures": sum(not r["activity_1e6_pass"] for r in subset),
            })
            if variant == "base":
                continue
            for denominator in ("base", "matricial_plano"):
                if denominator == variant:
                    continue
                a = [time_cost(group[variant], args.timeout) for group in by_instance.values()]
                b = [time_cost(group[denominator], args.timeout) for group in by_instance.values()]
                est, lo, hi = boot_ratio(a, b, rng, args.bootstrap)
                contrasts.append({"cell": cell, "numerator": variant, "denominator": denominator,
                                  "endpoint": "ratio_mean_PAR10_seconds", "n": len(a),
                                  "estimate": est, "ci_low": lo, "ci_high": hi,
                                  "rounding_bound_low": "", "rounding_bound_high": ""})
                a = np.array([g[variant]["audit_work"] for g in work_pool])
                b = np.array([g[denominator]["audit_work"] for g in work_pool])
                if len(a):
                    est, lo, hi = boot_ratio(a, b, rng, args.bootstrap, geometric=True)
                    # Worst-case bounds due solely to rounding each native summary to .01.
                    rounding_lo = np.exp(np.mean(np.log((a - 0.005) / (b + 0.005))))
                    rounding_hi = np.exp(np.mean(np.log((a + 0.005) / (b - 0.005))))
                    contrasts.append({"cell": cell, "numerator": variant, "denominator": denominator,
                                      "endpoint": "geomean_work_ratio_common_completed", "n": len(a),
                                      "estimate": est, "ci_low": lo, "ci_high": hi,
                                      "rounding_bound_low": float(rounding_lo), "rounding_bound_high": float(rounding_hi)})
        pairs = [(g["role_hybrid"], g["matricial_plano"]) for g in by_instance.values()]
        identities.append({"cell": cell, "n": len(pairs),
                           "nodes_equal": sum(a["nodos_explorados"] == b["nodos_explorados"] for a, b in pairs),
                           "recorded_work_equal": sum(a["work_units"] == b["work_units"] for a, b in pairs),
                           "native_work_equal_at_0p01": sum(a["audit_work"] is not None and a["audit_work"] == b["audit_work"] for a, b in pairs)})
    write_csv(args.output / "reconstructed_runs.csv", reconstructed)
    write_csv(args.output / "cell_summary.csv", summaries)
    write_csv(args.output / "paired_contrasts.csv", contrasts)
    write_csv(args.output / "role_flat_identity.csv", identities)
    compact = []
    tex = [r"\begin{tabular}{llrrrr}", r"\toprule",
           r"Class & Gap & Base & Flat-GM & Flat-L2 & Role-Hybrid \\", r"\midrule"]
    for family in ("simple", "sgtm"):
        for tag, gap in (("1pct", "1\\%"), ("01pct", "0.1\\%")):
            cell = f"gurobi_{family}_{tag}"
            selected = {r["variant"]: r for r in summaries if r["cell"] == cell}
            if not selected:
                continue
            row = {"class": "Simple" if family == "simple" else "SG-Ter-Mer",
                   "mipgap_percent": 1 if tag == "1pct" else 0.1, "assigned_per_variant": 15}
            for v in VARIANTS:
                row[f"{v}_par10_seconds"] = selected[v]["mean_par10_seconds"]
                row[f"{v}_completed"] = selected[v]["n_completed"]
            compact.append(row)
            values = [f"{selected[v]['mean_par10_seconds']:.2f} ({selected[v]['n_completed']})" for v in VARIANTS]
            tex.append(" & ".join([row["class"], gap] + values) + r" \\")
    tex += [r"\bottomrule", r"\end{tabular}",
            "% Entries: arithmetic mean PAR10 in seconds (number completed out of 15).",
            "% Time limit: 1800 seconds; every non-completion receives 18000 seconds.",
            "% These are exploratory single-seed, fixed-pool observations, not a superiority test."]
    write_csv(args.output / "main_table_four_cells.csv", compact)
    (args.output / "main_table_four_cells.tex").write_text("\n".join(tex) + "\n")
    (args.output / "input_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    meta = {"bootstrap_draws": args.bootstrap, "bootstrap_seed": 20260908,
            "unit": "instance within each cell; no cross-cell pooling", "timeout_seconds": args.timeout,
            "work_source": "native Gurobi summary; rounded to 0.01 Work units for all variants",
            "work_analysis": "secondary, common all-methods-completed subset; no timeout imputation",
            "primary_endpoint": "arithmetic mean of fixed-pool PAR10 cost in seconds",
            "uncertainty": "exploratory paired percentile bootstrap; not confirmatory or multiplicity-adjusted",
            "residual_sensitivities": "not calibrated physical tolerances and not optimality certificates"}
    (args.output / "analysis_metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
    report = ["# Reconstructed final operational campaign", "",
              "All four variants are retained on the assigned pool (15 instances per cell). Work comes from the native Gurobi log, at 0.01-unit resolution. The historical scaled Work marker was rounded to integers; zero is a rounding artifact, not a zero-cost solve.", "",
              "PAR10 below is the arithmetic mean of solver seconds with 18,000 seconds per non-completion. Work ratios use the same all-variants-completed pool within each cell and are secondary, conditional summaries. The confidence intervals are exploratory paired bootstrap intervals; the small pools and influential timeouts prevent a general superiority or equivalence claim.", "",
              "| Cell | Variant | Completed | PAR10 seconds | Absolute residual max | Activity residual max |", "|---|---|---:|---:|---:|---:|"]
    for r in summaries:
        report.append(f"| {r['cell']} | {LABELS[r['variant']]} | {r['n_completed']}/{r['n_assigned']} | {r['mean_par10_seconds']:.2f} | {r['max_absolute_row_residual']:.3g} | {r['max_activity_normalized_residual']:.3g} |")
    report += ["", "| Cell | Contrast | Common completed n | Work GM ratio [95% CI] | Rounding-only bounds |", "|---|---|---:|---:|---:|"]
    for r in contrasts:
        if r["endpoint"] == "geomean_work_ratio_common_completed" and r["denominator"] == "base":
            report.append(f"| {r['cell']} | {LABELS[r['numerator']]}/Base | {r['n']} | {r['estimate']:.3f} [{r['ci_low']:.3f}, {r['ci_high']:.3f}] | [{r['rounding_bound_low']:.3f}, {r['rounding_bound_high']:.3f}] |")
    report += ["", "The 4.9704 original-scale residual on caso46e (Flat-L2, 1%) belongs to an equality with zero RHS. Its RHS-normalized diagnostic divides by 1; interpreting it as a 497% physical error is invalid. The maximum activity-normalized diagnostic in that run is 1.15e-7. Both scales must be reported until application tolerances are justified.", "",
               "The native Work summaries are still rounded. Equal Work at 0.01 resolution, or equal node counts, is not proof of identical trajectories or matrices. Model-equivalence claims require direct matrix/row-factor comparisons.", ""]
    (args.output / "README.md").write_text("\n".join(report))
    # Compact standalone figures for the paper; generated from the CSV-equivalent arrays.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cellnames = sorted({r["cell"] for r in contrasts})
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
    endpoints = ["ratio_mean_PAR10_seconds", "geomean_work_ratio_common_completed"]
    colors = {"matricial_plano": "#17659b", "matricial_plano_l2": "#bc5227", "role_hybrid": "#348866"}
    offsets = {"matricial_plano": -0.18, "matricial_plano_l2": 0, "role_hybrid": 0.18}
    for ax, endpoint in zip(axes, endpoints):
        for variant in VARIANTS[1:]:
            selected = [r for r in contrasts if r["endpoint"] == endpoint and r["numerator"] == variant and r["denominator"] == "base"]
            ys = [cellnames.index(r["cell"]) + offsets[variant] for r in selected]
            estimates = np.array([r["estimate"] for r in selected])
            lower = estimates - np.array([r["ci_low"] for r in selected])
            upper = np.array([r["ci_high"] for r in selected]) - estimates
            ax.errorbar(estimates, ys, xerr=[lower, upper], fmt="o", color=colors[variant], label=LABELS[variant], capsize=2, markersize=4)
        ax.axvline(1, color="0.4", lw=0.8)
        ax.set_xscale("log")
        ax.grid(axis="x", alpha=0.2)
        ax.set_xlabel("Variant / Base (lower is better)")
    axes[0].set_title("Fixed-pool mean PAR10 (seconds)")
    axes[1].set_title("Work: common completed pool")
    axes[0].set_yticks(range(len(cellnames)), [c.replace("gurobi_", "").replace("_01pct", " / 0.1%").replace("_1pct", " / 1%") for c in cellnames])
    axes[0].invert_yaxis()
    axes[1].legend(loc="best", fontsize=8)
    fig.suptitle("Exploratory paired 95% bootstrap intervals; 15 assigned instances per cell", fontsize=10)
    fig.tight_layout()
    fig.savefig(args.output / "operational_corrected.pdf", bbox_inches="tight")
    fig.savefig(args.output / "operational_corrected.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"Audited {len(reconstructed)} runs; wrote {args.output}")


if __name__ == "__main__":
    main()
