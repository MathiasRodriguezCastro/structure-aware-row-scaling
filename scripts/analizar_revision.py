#!/usr/bin/env python3
"""Analysis for the peer-review revision experiments (R1 / R3 / R5).

Reads the resumen.csv files produced by validar_preprocesamiento.py and reports,
for every variant present, the same field-standard metrics used in the paper:
  * sgm  : shifted geometric mean of solver time (s=1 s), over solved runs;
  * PAR10: timeout-penalized mean solver time (timeout counts as 10x time limit);
  * paired speedup vs base (median of t_base/t_var over matched solved pairs);
  * Cliff's delta of the paired comparison (negative => variant faster);
  * n     : matched solved pairs (or solved runs for sgm/PAR10).

It does NOT use the hardcoded variant/group whitelists of analisis_tesis_preproc.py,
so the ablation slugs (estructurado_solo_local, ...) and arbitrary sweep folders work.

Usage:
  # R5 (one folder, all variants vs base):
  analizar_revision.py r5 --dir results-revision/r5-ablation/simple-gurobi-1pct

  # R1 (compare base across internal-scaling settings vs the aware variants):
  analizar_revision.py r1 --root results-revision/r1-internal-scaling/simple-gurobi-1pct

  # R3 (one estructurado run per sweep point, each its own folder):
  analizar_revision.py r3 --root results-revision/r3-hyperparam/simple-gurobi-1pct
"""
import argparse, csv, math, glob, os, sys
from pathlib import Path

TIMELIMIT = 3600.0  # solver --timeout used in the campaign


def load(resumen: Path):
    """Return {variant: [ {inst, t, ok, timeout} ]} from a resumen.csv."""
    out = {}
    with open(resumen) as f:
        for r in csv.DictReader(f):
            v = r.get("variante", "")
            inst = r.get("instancia", "")
            st = (r.get("status") or "").upper()
            ts = r.get("tiempo_solver_s", "")
            try:
                t = float(ts)
            except (TypeError, ValueError):
                t = None
            ok = (st == "OK") and (t is not None)
            timeout = ok and t >= 0.99 * TIMELIMIT
            out.setdefault(v, []).append(dict(inst=inst, t=t, ok=ok, timeout=timeout))
    return out


def sgm(xs, s=1.0):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    return math.exp(sum(math.log(x + s) for x in xs) / len(xs)) - s


def par10(runs):
    """Mean solver time with TIMEOUTS penalized at 10x the limit.
    Pure errors (non-timeout) are excluded, matching the paper's convention
    (timeout-aware scoring, not data-loss penalization)."""
    vals = []
    for r in runs:
        if r["timeout"]:
            vals.append(10.0 * TIMELIMIT)
        elif r["ok"]:
            vals.append(r["t"])
        # else: error -> excluded
    return sum(vals) / len(vals) if vals else None


def cliffs_delta(a, b):
    """delta over paired (a_i vs b_i): negative => a tends smaller (faster)."""
    n = len(a)
    if n == 0:
        return None
    gt = sum(1 for x, y in zip(a, b) if x > y)
    lt = sum(1 for x, y in zip(a, b) if x < y)
    return (gt - lt) / n


def paired_vs_base(runs_v, runs_base):
    by_b = {r["inst"]: r for r in runs_base}
    tv, tb = [], []
    for r in runs_v:
        b = by_b.get(r["inst"])
        if b and r["ok"] and b["ok"] and not (r["timeout"] and b["timeout"]):
            tv.append(r["t"]); tb.append(b["t"])
    if not tv:
        return None
    speedups = sorted(tb_i / tv_i for tv_i, tb_i in zip(tv, tb) if tv_i > 0)
    med = speedups[len(speedups) // 2] if speedups else None
    return dict(n=len(tv), speedup_med=med, cliff=cliffs_delta(tv, tb))


def stat_row(runs, base_runs=None):
    solved = [r["t"] for r in runs if r["ok"]]
    row = dict(
        n_ok=sum(1 for r in runs if r["ok"]),
        n_to=sum(1 for r in runs if r["timeout"]),
        sgm=sgm(solved), par10=par10(runs),
    )
    if base_runs is not None:
        p = paired_vs_base(runs, base_runs)
        if p:
            row.update(pair_n=p["n"], speedup=p["speedup_med"], cliff=p["cliff"])
    return row


def fmt(x, d=3):
    if x is None:
        return "--"
    if isinstance(x, float):
        return f"{x:.{d}f}"
    return str(x)


def print_table(title, header, rows):
    print(f"\n## {title}")
    widths = [max(len(str(h)), *(len(str(r[i])) for r in rows)) if rows else len(str(h))
              for i, h in enumerate(header)]
    line = "  ".join(str(h).ljust(widths[i]) for i, h in enumerate(header))
    print(line); print("  ".join("-" * w for w in widths))
    for r in rows:
        print("  ".join(str(c).ljust(widths[i]) for i, c in enumerate(r)))


def analyze_folder(resumen, title):
    data = load(resumen)
    base = data.get("base", [])
    order = ["base"] + sorted(v for v in data if v != "base")
    rows = []
    for v in order:
        s = stat_row(data[v], None if v == "base" else base)
        rows.append([v, s["n_ok"], s["n_to"], fmt(s["sgm"]), fmt(s["par10"], 2),
                     fmt(s.get("speedup")), fmt(s.get("cliff"))])
    print_table(title, ["variante", "n_ok", "n_to", "sgm_tsol", "PAR10", "speedup_vs_base", "cliff_d"], rows)
    return data


def cmd_r5(args):
    analyze_folder(Path(args.dir) / "resumen.csv", f"R5 ablation — {args.dir}")


def cmd_r3(args):
    # each subfolder = one sweep point; report estructurado vs base per point
    root = Path(args.root)
    rows = []
    for sub in sorted(p for p in root.iterdir() if (p / "resumen.csv").exists()):
        data = load(sub / "resumen.csv")
        base = data.get("base", [])
        for v in (x for x in data if x != "base"):
            s = stat_row(data[v], base)
            rows.append([sub.name, v, s["n_ok"], fmt(s["sgm"]), fmt(s["par10"], 2),
                         fmt(s.get("speedup")), fmt(s.get("cliff"))])
    print_table(f"R3 sensitivity — {args.root}",
                ["punto", "variante", "n_ok", "sgm_tsol", "PAR10", "speedup_vs_base", "cliff_d"], rows)


def cmd_r1(args):
    # aware-default/ has base + aware variants; base-* folders each add base under a setting.
    root = Path(args.root)
    rows = []
    aware = root / "aware-default"
    base_runs = []
    if (aware / "resumen.csv").exists():
        data = load(aware / "resumen.csv")
        base_runs = data.get("base", [])
        for v in ["base"] + sorted(x for x in data if x != "base"):
            s = stat_row(data[v], None if v == "base" else base_runs)
            rows.append([f"default/{v}", s["n_ok"], s["n_to"], fmt(s["sgm"]),
                         fmt(s["par10"], 2), fmt(s.get("speedup")), fmt(s.get("cliff"))])
    # internal-scaling settings: each folder's 'base' vs the default base
    for sub in sorted(p for p in root.iterdir() if p.name.startswith("base-") and (p / "resumen.csv").exists()):
        d = load(sub / "resumen.csv")
        b = d.get("base", [])
        s = stat_row(b, base_runs)
        rows.append([sub.name, s["n_ok"], s["n_to"], fmt(s["sgm"]),
                     fmt(s["par10"], 2), fmt(s.get("speedup")), fmt(s.get("cliff"))])
    print_table(f"R1 internal-scaling baseline — {args.root}\n"
                f"(speedup/cliff are vs the DEFAULT-scaling base; compare base-scaleflag* against default/estructurado*)",
                ["fila", "n_ok", "n_to", "sgm_tsol", "PAR10", "speedup_vs_defbase", "cliff_d"], rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p5 = sub.add_parser("r5"); p5.add_argument("--dir", required=True); p5.set_defaults(fn=cmd_r5)
    p3 = sub.add_parser("r3"); p3.add_argument("--root", required=True); p3.set_defaults(fn=cmd_r3)
    p1 = sub.add_parser("r1"); p1.add_argument("--root", required=True); p1.set_defaults(fn=cmd_r1)
    ap.add_argument("--timelimit", type=float, default=None)
    args = ap.parse_args()
    if args.timelimit:
        global TIMELIMIT
        TIMELIMIT = args.timelimit
    args.fn(args)


if __name__ == "__main__":
    main()
