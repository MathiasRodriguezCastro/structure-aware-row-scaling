#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analizar_grilla_sintetica.py — análisis reproducible de la grilla sintética.

Lee (SIN modificarlos):
    <results>/metrics.csv
    <results>/summary_by_pattern_severity_variant.csv     (opcional, solo se valida)

y escribe en <results>/analysis/ :
    synthetic_summary_table.csv / .tex
    synthetic_conditioning_reduction.csv      (comparaciones vs Base: Wilcoxon + BH)
    synthetic_objective_feasibility_checks.csv
    figuras paper-ready (.pdf y .png)

Robustez de locale: pandas lee con decimal='.' explícito (los CSV los escribe C++
con punto), así que NO depende de LC_NUMERIC. Aun así se recomienda correr con
`LC_ALL=C` para que cualquier post-proceso shell sea consistente:

    LC_ALL=C python3 synthetic/analisis/analizar_grilla_sintetica.py

Enfoque conceptual (instancias chicas, resuelven en ms): el análisis NO vende
speedup; se enfoca en control del desbalance, recuperación del condicionamiento,
preservación de factibilidad/objetivo y comparación limpia entre variantes.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # backend sin display (paper-ready a archivo)
import matplotlib.pyplot as plt
from scipy.stats import wilcoxon

VARIANT_ORDER = ["Base", "SA-Aug", "SA-Mat", "Ruiz", "Ruiz+Cols"]
PATTERN_ORDER = ["none", "local", "coupling", "mixed"]
S_ORDER = [0, 3, 6]
MIPGAP = 1e-3


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #
def bh_adjust(pvals):
    """Benjamini-Hochberg. Ignora NaN (los devuelve como NaN)."""
    p = np.asarray(pvals, dtype=float)
    out = np.full_like(p, np.nan, dtype=float)
    mask = ~np.isnan(p)
    q = p[mask]
    n = q.size
    if n == 0:
        return out
    order = np.argsort(q)
    ranked = q[order]
    adj = np.empty(n, dtype=float)
    prev = 1.0
    for i in range(n - 1, -1, -1):
        prev = min(prev, ranked[i] * n / (i + 1))
        adj[i] = min(prev, 1.0)
    res = np.empty(n, dtype=float)
    res[order] = adj
    out[mask] = res
    return out


def safe_log10(x):
    x = pd.to_numeric(x, errors="coerce")
    return np.where(x > 0, np.log10(x.where(x > 0)), np.nan)


def median_or_nan(s):
    s = pd.to_numeric(s, errors="coerce").dropna()
    return float(np.median(s)) if len(s) else np.nan


def cat(df, col, order):
    df[col] = pd.Categorical(df[col], categories=order, ordered=True)
    return df


# --------------------------------------------------------------------------- #
# Carga
# --------------------------------------------------------------------------- #
def load_metrics(path: Path) -> pd.DataFrame:
    # decimal='.' fija el separador (independiente del locale del sistema).
    df = pd.read_csv(path, decimal=".", na_values=["NA", "nan", ""], keep_default_na=True)
    num_cols = ["seed", "severity_S", "filas", "cols", "binarias",
                "kappa_antes", "kappa_despues", "rho_antes", "rho_despues",
                "tiempo_preproc_s", "tiempo_solver_s", "wall_time_s", "objetivo",
                "gap", "best_bound",
                "max_original_row_violation", "max_integrality_violation"]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    # is_feasible_original_scale: "true"/"false"/"NA" -> bool / NaN
    fmap = {"true": True, "false": False, "True": True, "False": False}
    df["is_feasible_bool"] = df["is_feasible_original_scale"].map(fmap)

    # Derivadas de condicionamiento (por fila).
    df["log10_kappa_antes"] = safe_log10(df["kappa_antes"])
    df["log10_kappa_despues"] = safe_log10(df["kappa_despues"])
    df["log10_rho_antes"] = safe_log10(df["rho_antes"])
    df["log10_rho_despues"] = safe_log10(df["rho_despues"])
    with np.errstate(divide="ignore", invalid="ignore"):
        df["reduction_factor"] = df["kappa_antes"] / df["kappa_despues"].where(df["kappa_despues"] > 0)
    df["log10_reduction"] = df["log10_kappa_antes"] - df["log10_kappa_despues"]
    return df


# --------------------------------------------------------------------------- #
# 1) Tabla resumen por (pattern, S, variant)
# --------------------------------------------------------------------------- #
def build_summary_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    g = df.groupby(["pattern", "severity_S", "variante"], observed=True)
    for (pat, S, var), sub in g:
        rows.append({
            "pattern": pat, "severity_S": int(S), "variante": var,
            "n": int(len(sub)),
            "n_feasible": int((sub["is_feasible_bool"] == True).sum()),
            "n_status_ok": int((sub["status"] == "ok").sum()),
            "median_kappa_antes": median_or_nan(sub["kappa_antes"]),
            "median_kappa_despues": median_or_nan(sub["kappa_despues"]),
            "median_reduction_factor": median_or_nan(sub["reduction_factor"]),
            "median_log10_reduction": median_or_nan(sub["log10_reduction"]),
            "median_rho_antes": median_or_nan(sub["rho_antes"]),
            "median_rho_despues": median_or_nan(sub["rho_despues"]),
            "median_wall_time_s": median_or_nan(sub["wall_time_s"]),
            "median_tiempo_solver_s": median_or_nan(sub["tiempo_solver_s"]),
            "median_max_original_row_violation": median_or_nan(sub["max_original_row_violation"]),
            "median_max_integrality_violation": median_or_nan(sub["max_integrality_violation"]),
        })
    out = pd.DataFrame(rows)
    out = cat(out, "pattern", PATTERN_ORDER)
    out = cat(out, "variante", VARIANT_ORDER)
    out = out.sort_values(["pattern", "severity_S", "variante"]).reset_index(drop=True)
    return out


def write_latex(summary: pd.DataFrame, path: Path):
    cols = ["pattern", "severity_S", "variante", "n", "n_feasible", "n_status_ok",
            "median_kappa_antes", "median_kappa_despues", "median_log10_reduction",
            "median_rho_despues", "median_tiempo_solver_s",
            "median_max_original_row_violation", "median_max_integrality_violation"]
    tex = summary[cols].copy()

    def f(x):
        if isinstance(x, float):
            if np.isnan(x):
                return "--"
            if x != 0 and (abs(x) >= 1e4 or abs(x) < 1e-3):
                return f"{x:.2e}"
            return f"{x:.3g}"
        return str(x)

    latex = tex.to_latex(index=False, escape=True, float_format=f,
                         caption="Resumen de la grilla sintética por (pattern, S, variante): "
                                 "factibilidad, condicionamiento (mediana de $\\kappa$ antes/después, "
                                 "reducción en $\\log_{10}$), $\\rho$ posterior, tiempos y violaciones máximas.",
                         label="tab:synthetic_summary")
    path.write_text(latex, encoding="utf-8")


# --------------------------------------------------------------------------- #
# 2) Comparaciones vs Base (Wilcoxon + BH)
# --------------------------------------------------------------------------- #
def build_conditioning_reduction(df: pd.DataFrame) -> pd.DataFrame:
    metrics = {
        "log10_kappa_despues": "log10_kappa_despues",
        "log10_rho_despues":   "log10_rho_despues",
    }
    rows = []
    for metric_name, col in metrics.items():
        for pat in PATTERN_ORDER:
            for S in S_ORDER:
                base = df[(df.pattern == pat) & (df.severity_S == S) & (df.variante == "Base")]
                base = base[["instancia", col]].rename(columns={col: "base_val"})
                for var in VARIANT_ORDER:
                    if var == "Base":
                        continue
                    cur = df[(df.pattern == pat) & (df.severity_S == S) & (df.variante == var)]
                    cur = cur[["instancia", col]].rename(columns={col: "var_val"})
                    merged = base.merge(cur, on="instancia", how="inner").dropna()
                    n_pairs = len(merged)
                    diff = merged["var_val"].to_numpy() - merged["base_val"].to_numpy()
                    median_diff = float(np.median(diff)) if n_pairs else np.nan
                    pval = np.nan
                    stat = np.nan
                    if n_pairs >= 1 and np.any(diff != 0):
                        try:
                            stat, pval = wilcoxon(merged["var_val"], merged["base_val"],
                                                  zero_method="wilcox", alternative="two-sided")
                            stat = float(stat)
                            pval = float(pval)
                        except ValueError:
                            stat, pval = np.nan, np.nan
                    rows.append({
                        "metric": metric_name, "pattern": pat, "severity_S": S, "variante": var,
                        "n_pairs": n_pairs,
                        "median_diff_log10_vs_base": median_diff,   # tamaño de efecto simple
                        "wilcoxon_stat": stat, "p_value": pval,
                    })
    out = pd.DataFrame(rows)
    # BH dentro de cada métrica (familia de comparaciones).
    out["p_value_bh"] = np.nan
    for metric_name in metrics:
        m = out["metric"] == metric_name
        out.loc[m, "p_value_bh"] = bh_adjust(out.loc[m, "p_value"].to_numpy())
    out = cat(out, "pattern", PATTERN_ORDER)
    out = cat(out, "variante", VARIANT_ORDER)
    out = out.sort_values(["metric", "pattern", "severity_S", "variante"]).reset_index(drop=True)
    return out


# --------------------------------------------------------------------------- #
# 3) Checks de objetivo / factibilidad
# --------------------------------------------------------------------------- #
def build_checks(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    def spread(o):
        o = pd.to_numeric(o, errors="coerce").dropna()
        if len(o) < 2:
            return 0.0
        den = max(abs(o.max()), 1e-12)
        return float((o.max() - o.min()) / den)

    for pat in PATTERN_ORDER:
        for S in S_ORDER:
            cell = df[(df.pattern == pat) & (df.severity_S == S)]
            if cell.empty:
                continue
            spreads = cell.groupby("instancia", observed=True)["objetivo"].apply(spread)
            rows.append({
                "pattern": pat, "severity_S": S,
                "n_instancias": int(cell["instancia"].nunique()),
                "max_rel_obj_spread": float(spreads.max()) if len(spreads) else np.nan,
                "n_instancias_over_mipgap": int((spreads > MIPGAP).sum()),
                "max_original_row_violation": float(pd.to_numeric(cell["max_original_row_violation"], errors="coerce").max()),
                "max_integrality_violation": float(pd.to_numeric(cell["max_integrality_violation"], errors="coerce").max()),
                "n_infeasible_rows": int((cell["is_feasible_bool"] == False).sum()),
            })
    out = pd.DataFrame(rows)

    # Fila TOTAL global.
    all_spreads = df.groupby("instancia", observed=True)["objetivo"].apply(spread)
    total = {
        "pattern": "TOTAL", "severity_S": -1,
        "n_instancias": int(df["instancia"].nunique()),
        "max_rel_obj_spread": float(all_spreads.max()) if len(all_spreads) else np.nan,
        "n_instancias_over_mipgap": int((all_spreads > MIPGAP).sum()),
        "max_original_row_violation": float(pd.to_numeric(df["max_original_row_violation"], errors="coerce").max()),
        "max_integrality_violation": float(pd.to_numeric(df["max_integrality_violation"], errors="coerce").max()),
        "n_infeasible_rows": int((df["is_feasible_bool"] == False).sum()),
    }
    out = pd.concat([out, pd.DataFrame([total])], ignore_index=True)
    return out


# --------------------------------------------------------------------------- #
# Figuras
# --------------------------------------------------------------------------- #
def _save(fig, stem: Path):
    fig.savefig(str(stem) + ".pdf", bbox_inches="tight")
    fig.savefig(str(stem) + ".png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_box_kappa_despues(df, outdir):
    fig, axes = plt.subplots(len(PATTERN_ORDER), len(S_ORDER),
                             figsize=(12, 12), sharey=True)
    for i, pat in enumerate(PATTERN_ORDER):
        for j, S in enumerate(S_ORDER):
            ax = axes[i][j]
            sub = df[(df.pattern == pat) & (df.severity_S == S)]
            data = [sub[sub.variante == v]["log10_kappa_despues"].dropna().to_numpy()
                    for v in VARIANT_ORDER]
            ax.boxplot(data, tick_labels=VARIANT_ORDER, showfliers=True)
            ax.tick_params(axis="x", rotation=45, labelsize=7)
            if i == 0:
                ax.set_title(f"S = {S}", fontsize=10)
            if j == 0:
                ax.set_ylabel(f"{pat}\n$\\log_{{10}}\\kappa_{{post}}$", fontsize=9)
            ax.grid(True, axis="y", alpha=0.3)
    fig.suptitle("Condicionamiento posterior $\\log_{10}\\kappa_{post}$ por variante "
                 "(filas = pattern, columnas = S)", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    _save(fig, outdir / "fig1_boxplot_log10_kappa_despues")


def fig_bars_reduction(df, outdir):
    fig, axes = plt.subplots(len(PATTERN_ORDER), len(S_ORDER),
                             figsize=(12, 12), sharey=True)
    for i, pat in enumerate(PATTERN_ORDER):
        for j, S in enumerate(S_ORDER):
            ax = axes[i][j]
            sub = df[(df.pattern == pat) & (df.severity_S == S)]
            meds = [median_or_nan(sub[sub.variante == v]["log10_reduction"]) for v in VARIANT_ORDER]
            ax.bar(range(len(VARIANT_ORDER)), meds, color="tab:blue", alpha=0.8)
            ax.set_xticks(range(len(VARIANT_ORDER)))
            ax.set_xticklabels(VARIANT_ORDER, rotation=45, fontsize=7)
            ax.axhline(0, color="k", lw=0.6)
            if i == 0:
                ax.set_title(f"S = {S}", fontsize=10)
            if j == 0:
                ax.set_ylabel(f"{pat}\nmediana $\\Delta\\log_{{10}}\\kappa$", fontsize=9)
            ax.grid(True, axis="y", alpha=0.3)
    fig.suptitle("Reducción mediana de condicionamiento "
                 "$\\log_{10}\\kappa_{pre}-\\log_{10}\\kappa_{post}$ por variante", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    _save(fig, outdir / "fig2_bars_log10_reduction")


def fig_kappa_antes_vs_S(df, outdir):
    fig, ax = plt.subplots(figsize=(7, 5))
    base = df[df.variante == "Base"]
    for pat in PATTERN_ORDER:
        meds = [median_or_nan(base[(base.pattern == pat) & (base.severity_S == S)]["kappa_antes"])
                for S in S_ORDER]
        ax.plot(S_ORDER, meds, marker="o", label=pat)
    ax.set_yscale("log")
    ax.set_xticks(S_ORDER)
    ax.set_xlabel("Severidad S")
    ax.set_ylabel("mediana $\\kappa_{pre}$ (escala log)")
    ax.set_title("$\\kappa_{pre}$ crece con S solo cuando el pattern inyecta desbalance")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(title="pattern")
    fig.tight_layout()
    _save(fig, outdir / "fig3_kappa_antes_vs_S")


def fig_feasibility(df, outdir):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    xlabels = [f"{pat}\nS={S}" for pat in PATTERN_ORDER for S in S_ORDER]
    xs = np.arange(len(xlabels))
    for ax, col, title in [
        (axes[0], "max_original_row_violation", "Máx. violación de fila (escala original)"),
        (axes[1], "max_integrality_violation", "Máx. violación de integralidad"),
    ]:
        vals = []
        for pat in PATTERN_ORDER:
            for S in S_ORDER:
                cell = df[(df.pattern == pat) & (df.severity_S == S)]
                v = pd.to_numeric(cell[col], errors="coerce").max()
                vals.append(max(v, 1e-18))  # piso para log
        ax.bar(xs, vals, color="tab:red", alpha=0.75)
        ax.set_yscale("log")
        ax.axhline(1e-5, color="k", ls="--", lw=0.8, label="tol factibilidad 1e-5")
        ax.set_xticks(xs)
        ax.set_xticklabels(xlabels, rotation=90, fontsize=7)
        ax.set_ylabel(col)
        ax.set_title(title)
        ax.grid(True, axis="y", which="both", alpha=0.3)
        ax.legend(fontsize=8)
    fig.suptitle("Factibilidad en escala original: violaciones máximas por pattern/S", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    _save(fig, outdir / "fig4_feasibility_violations")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    script_dir = Path(__file__).resolve().parent
    default_results = script_dir.parent / "resultados" / "grilla_inicial_gurobi"

    ap = argparse.ArgumentParser(description="Análisis reproducible de la grilla sintética.")
    ap.add_argument("--results-dir", type=Path, default=default_results,
                    help="Carpeta con metrics.csv y summary_by_pattern_severity_variant.csv")
    args = ap.parse_args()

    results = args.results_dir
    metrics_path = results / "metrics.csv"
    if not metrics_path.exists():
        raise SystemExit(f"[error] no se encontró {metrics_path}")

    outdir = results / "analysis"
    outdir.mkdir(parents=True, exist_ok=True)

    df = load_metrics(metrics_path)
    print(f"[info] metrics.csv: {len(df)} filas, {df['instancia'].nunique()} instancias")

    # 1) Tabla resumen
    summary = build_summary_table(df)
    summary.to_csv(outdir / "synthetic_summary_table.csv", index=False)
    write_latex(summary, outdir / "synthetic_summary_table.tex")
    print(f"[ok] synthetic_summary_table.csv/.tex ({len(summary)} grupos)")

    # 2) Comparaciones vs Base
    comp = build_conditioning_reduction(df)
    comp.to_csv(outdir / "synthetic_conditioning_reduction.csv", index=False)
    print(f"[ok] synthetic_conditioning_reduction.csv ({len(comp)} comparaciones)")

    # 3) Checks objetivo/factibilidad
    checks = build_checks(df)
    checks.to_csv(outdir / "synthetic_objective_feasibility_checks.csv", index=False)
    print("[ok] synthetic_objective_feasibility_checks.csv")

    # 4) Figuras
    fig_box_kappa_despues(df, outdir)
    fig_bars_reduction(df, outdir)
    fig_kappa_antes_vs_S(df, outdir)
    fig_feasibility(df, outdir)
    print("[ok] figuras fig1..fig4 (.pdf y .png)")

    # Resumen consola
    tot = checks[checks.pattern == "TOTAL"].iloc[0]
    print("\n==== checks globales ====")
    print(f"  máx spread relativo de objetivo entre variantes : {tot['max_rel_obj_spread']:.3e}")
    print(f"  instancias que superan mipgap={MIPGAP}            : {int(tot['n_instancias_over_mipgap'])}")
    print(f"  máx max_original_row_violation                   : {tot['max_original_row_violation']:.3e}")
    print(f"  máx max_integrality_violation                    : {tot['max_integrality_violation']:.3e}")
    print(f"  filas con is_feasible_original_scale=false        : {int(tot['n_infeasible_rows'])}")
    print(f"\n[done] salidas en {outdir}")


if __name__ == "__main__":
    main()
