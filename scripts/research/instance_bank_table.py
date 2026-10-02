#!/usr/bin/env python3
"""Per-class size and numerical statistics of the dispatch instance bank.

Reads the unscaled Base export of every model of the fixed-basis audit --- the same files the
audit measured --- and reports, per class, the median and range of rows, columns, nonzeros,
integer variables and the width of the coefficient and right-hand-side magnitudes. No optimizer
is called and nothing is re-exported.
"""
import argparse
import csv
import math
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_identifiability_grid import parse

CLASSES = [("simple", "Simple"), ("sgtm", "SG-Ter-Mer"), ("full", "Full")]


def integers(text):
    """Variables the export declares integer or binary."""
    n = 0
    for section in ("Binaries", "binary", "Generals", "general", "Integers"):
        m = re.search(r"(?m)^%s\s*$" % section, text)
        if not m:
            continue
        rest = re.split(r"(?im)^(?:bounds|binaries|binary|generals|general|integers|end)\s*$",
                        text[m.end():])[0]
        n += len(rest.split())
    return n


def stats(path):
    rows, _ = parse(path)
    coef = np.array([abs(v) for r in rows.values() for v in r["terms"].values() if v != 0])
    rhs = np.array([abs(r["rhs"]) for r in rows.values() if r.get("rhs")])
    cols = {c for r in rows.values() for c in r["terms"]}
    return {"rows": len(rows), "cols": len(cols), "nnz": len(coef),
            "ints": integers(path.read_text()),
            "coef_min": float(coef.min()), "coef_max": float(coef.max()),
            "coef_decades": float(math.log10(coef.max() / coef.min())),
            "rhs_decades": float(math.log10(rhs.max() / rhs.min())) if len(rhs) else 0.0}


def sci(x):
    e = int(math.floor(math.log10(abs(x)))) if x else 0
    return rf"$10^{{{e}}}$" if abs(x / 10.0**e - 1) < 5e-2 else rf"${x/10.0**e:.1f}\times10^{{{e}}}$"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path,
                    default=ROOT / "results-revision/research-audit/fixed-basis-final-20260914")
    ap.add_argument("--csv", type=Path,
                    default=ROOT / "results-revision/research-audit/instance-bank.csv")
    ap.add_argument("--out", type=Path, default=ROOT / "paper/tables/instance-bank.tex")
    args = ap.parse_args()

    records = []
    for key, _ in CLASSES:
        for folder in sorted((args.root / "fresh" / key).iterdir()):
            records.append({"class": key, "instance": folder.name} | stats(folder / "Base.lp"))
            print(f"{key} {folder.name} {records[-1]['rows']}x{records[-1]['cols']}", flush=True)
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(records[0])); w.writeheader(); w.writerows(records)

    def cell(v):
        v = np.array(v)
        return (f"{int(np.median(v)):,}" if v.max() == v.min()
                else f"{int(np.median(v)):,} [{int(v.min()):,}, {int(v.max()):,}]")

    lines = [r"\begin{tabular}{lrllll}", r"\toprule",
             r"Class & $n$ & Rows & Columns & Nonzeros & Integer vars \\", r"\midrule"]
    for key, label in CLASSES:
        g = [r for r in records if r["class"] == key]
        lines.append(f"{label} & {len(g)} & " + " & ".join(
            cell([r[k] for r in g]) for k in ("rows", "cols", "nnz", "ints")) + r" \\")
    lines += [r"\midrule",
              r"Class & $n$ & \multicolumn{2}{l}{Coefficient magnitudes} & "
              r"Coef.\ decades & RHS decades \\", r"\midrule"]
    for key, label in CLASSES:
        g = [r for r in records if r["class"] == key]
        lo, hi = min(r["coef_min"] for r in g), max(r["coef_max"] for r in g)
        cd = np.array([r["coef_decades"] for r in g]); rd = np.array([r["rhs_decades"] for r in g])
        lines.append(f"{label} & {len(g)} & \\multicolumn{{2}}{{l}}{{{sci(lo)} to {sci(hi)}}} & "
                     f"{np.median(cd):.1f} [{cd.min():.1f}, {cd.max():.1f}] & "
                     f"{np.median(rd):.1f} [{rd.min():.1f}, {rd.max():.1f}] \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    args.out.write_text("\n".join(lines) + "\n")
    print("wrote", args.out, "and", args.csv, len(records), "models")


if __name__ == "__main__":
    main()
