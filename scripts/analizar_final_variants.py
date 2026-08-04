#!/usr/bin/env python3
"""Paired analysis + decision rule for the four final attribution variants.

Reads the per-cell resumen.csv produced by validar_preprocesamiento.py under
results-revision/final-variants/<solver>_<family>_<gaptag>/ and reports, per
(solver, family, gap) and pooled, the paired performance of Flat-GM / Flat-L2 /
Role-Hybrid against Base (and against Flat-GM). Primary metric is solver time with a
PAR10 reading for timeouts; the deterministic metric (Gurobi work units / CPLEX
det-ticks) is reported alongside. Then it applies the decision rule (Cases 1-4).

Usage:
  python3 scripts/analizar_final_variants.py [--root results-revision/final-variants]
                                             [--timeout 1800] [--metric tiempo_solver_s]
"""
import argparse, csv, glob, math, os, statistics as st
from collections import defaultdict
import numpy as np
from scipy import stats

VARIANTS = ["base", "matricial_plano", "matricial_plano_l2", "role_hybrid"]
LABEL = {"base": "Base", "matricial_plano": "Flat-GM",
         "matricial_plano_l2": "Flat-L2", "role_hybrid": "Role-Hybrid"}
SOLVED = {"OPTIMAL", "OK", "OPTIMO", "SOLVED", "INTEGER OPTIMAL", ""}  # status_solver strings that mean solved


def fnum(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def load_cell(path):
    """Return dict[instance][variant] = row(dict)."""
    d = defaultdict(dict)
    with open(path) as fh:
        for r in csv.DictReader(fh):
            d[r["instancia"]][r["variante"]] = r
    return d


def timed_out(row, timeout):
    ss = (row.get("status_solver") or row.get("status") or "").upper()
    if "TIMEOUT" in ss or "TIME_LIMIT" in ss or "ABORT" in ss:
        return True
    t = fnum(row.get("tiempo_solver_s"))
    return t is not None and t >= 0.98 * timeout


def par10(row, metric, timeout):
    if timed_out(row, timeout):
        return 10.0 * timeout
    return fnum(row.get(metric))


def geomean(xs):
    xs = [x for x in xs if x is not None and x > 0]
    return math.exp(sum(math.log(x) for x in xs) / len(xs)) if xs else None


def boot_ci_geomean(ratios, n=5000, seed=0):
    r = np.array([x for x in ratios if x is not None and x > 0])
    if len(r) < 3:
        return (None, None)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(r), size=(n, len(r)))
    gms = np.exp(np.mean(np.log(r[idx]), axis=1))
    return (float(np.percentile(gms, 2.5)), float(np.percentile(gms, 97.5)))


def paired(cell, num, den, metric, timeout):
    """num vs den on PAR10(metric): ratios num/den (<1 => num faster)."""
    ratios, wins, ties, losses = [], 0, 0, 0
    a_raw, b_raw = [], []
    for inst, byv in cell.items():
        if num not in byv or den not in byv:
            continue
        a = par10(byv[num], metric, timeout)
        b = par10(byv[den], metric, timeout)
        if a is None or b is None or b <= 0:
            continue
        a_raw.append(a); b_raw.append(b)
        ratios.append(a / b)
        if a < b * 0.999:   wins += 1
        elif a > b * 1.001: losses += 1
        else:               ties += 1
    med = st.median(ratios) if ratios else None
    gm = geomean(ratios)
    lo, hi = boot_ci_geomean(ratios)
    p = None
    if len(a_raw) >= 6 and any(x != y for x, y in zip(a_raw, b_raw)):
        try:
            p = stats.wilcoxon(a_raw, b_raw, zero_method="wilcox").pvalue
        except ValueError:
            p = None
    return dict(n=len(ratios), median=med, geomean=gm, ci=(lo, hi),
               wins=wins, ties=ties, losses=losses, p=p)


def cell_timeouts(cell, timeout):
    out = {v: 0 for v in VARIANTS}
    for byv in cell.values():
        for v in VARIANTS:
            if v in byv and timed_out(byv[v], timeout):
                out[v] += 1
    return out


def worst_residual(cell):
    out = {v: 0.0 for v in VARIANTS}
    for byv in cell.values():
        for v in VARIANTS:
            if v in byv:
                r = fnum(byv[v].get("verif_solver_max_viol_rel"))
                if r is not None:
                    out[v] = max(out[v], r)
    return out


def fmt(x, d=3):
    return "  n/a" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="results-revision/final-variants")
    ap.add_argument("--timeout", type=float, default=1800.0)
    ap.add_argument("--metric", default="tiempo_solver_s",
                    help="primary per-run metric (tiempo_solver_s | work_units | tiempo_determinista)")
    args = ap.parse_args()

    cells = {}
    for path in sorted(glob.glob(os.path.join(args.root, "*", "resumen.csv"))):
        tag = os.path.basename(os.path.dirname(path))       # e.g. gurobi_simple_1pct
        cells[tag] = load_cell(path)
    if not cells:
        print(f"No resumen.csv under {args.root}/*/"); return

    print(f"# Final-variants paired analysis  (metric={args.metric}, PAR10 timeout={args.timeout:g}s)\n")
    pooled = defaultdict(list)   # (num,den) -> list of ratios pooled across cells (same metric)
    for tag in sorted(cells):
        cell = cells[tag]
        print(f"== cell {tag}  ({len(cell)} instances) ==")
        to = cell_timeouts(cell, args.timeout); res = worst_residual(cell)
        print("   timeouts:   " + "  ".join(f"{LABEL[v]}={to[v]}" for v in VARIANTS))
        print("   max|resid|: " + "  ".join(f"{LABEL[v]}={res[v]:.1e}" for v in VARIANTS))
        for den in ["base", "matricial_plano"]:
            for num in VARIANTS:
                if num == den:
                    continue
                if den == "matricial_plano" and num == "base":
                    continue
                r = paired(cell, num, den, args.metric, args.timeout)
                if r["n"] == 0:
                    continue
                ci = r["ci"]
                print(f"   {LABEL[num]:11s} / {LABEL[den]:8s}: "
                      f"med={fmt(r['median'])} gm={fmt(r['geomean'])} "
                      f"CI[{fmt(ci[0])},{fmt(ci[1])}] "
                      f"W/T/L={r['wins']}/{r['ties']}/{r['losses']} "
                      f"p={fmt(r['p'],4) if r['p'] is not None else ' n/a'}")
                # pool by metric only when metric is deterministic across solvers; here per-solver
                pooled[(num, den, tag.split('_')[0])].append(r)
        print()

    # ---- decision rule ----------------------------------------------------
    print("== DECISION RULE (per the plan) ==")
    print("Reading: a variant 'wins' a cell if its geomean ratio vs Base < 1 with the")
    print("bootstrap CI upper bound < 1 (robust speedup), no new timeouts, residual valid.\n")
    # aggregate: for each variant vs base, count cells where robustly better/worse
    verdict = {}
    for num in ["matricial_plano", "matricial_plano_l2", "role_hybrid"]:
        better = worse = neutral = 0
        for tag, cell in cells.items():
            r = paired(cell, num, "base", args.metric, args.timeout)
            if r["n"] == 0 or r["geomean"] is None:
                continue
            lo, hi = r["ci"]
            if hi is not None and hi < 1.0:      better += 1
            elif lo is not None and lo > 1.0:    worse += 1
            else:                                neutral += 1
        verdict[num] = (better, worse, neutral)
        print(f"  {LABEL[num]:11s} vs Base: robustly-better {better} / worse {worse} / neutral {neutral} cells")
    # Role-Hybrid vs the two flats (for Case 1)
    print()
    for num, den in [("role_hybrid", "matricial_plano"), ("role_hybrid", "matricial_plano_l2")]:
        b = w = nu = 0
        for tag, cell in cells.items():
            r = paired(cell, num, den, args.metric, args.timeout)
            if r["n"] == 0 or r["geomean"] is None:
                continue
            lo, hi = r["ci"]
            if hi is not None and hi < 1.0:   b += 1
            elif lo is not None and lo > 1.0: w += 1
            else:                             nu += 1
        print(f"  {LABEL[num]:11s} vs {LABEL[den]:8s}: better {b} / worse {w} / neutral {nu} cells")


if __name__ == "__main__":
    main()
