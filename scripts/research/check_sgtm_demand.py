#!/usr/bin/env python3
"""Count SG-Ter-Mer instances whose local demand exceeds the stated total demand.

The market dispatch reads a local demand series d(t) and a total demand series D(t).
A scenario with d(t) > D(t) in some hour is not a faithful market scenario; the models
remain valid MILPs, so this check reports the defect, it does not repair anything.
"""
import argparse
import json
from pathlib import Path


def series(path):
    """(local demand, total demand) of one instance script; None when absent."""
    lines = [l.strip() for l in path.read_text().split("\n")]
    d = tot = None
    for i, line in enumerate(lines):
        low = line.lower()
        if low.startswith("agregaragente --demandafija"):
            d = [float(v.replace(",", ".")) for v in lines[i + 1].split()]
        elif low.startswith("creardespacho --mercado") and "--condemandatotal" in low:
            k = int(lines[i + 1])
            tot = [float(v.replace(",", ".")) for v in lines[i + 4].split()]
            assert len(lines[i + 2].split()) == len(lines[i + 3].split()) == k
    return d, tot


def scan(paths):
    out = {"n": 0, "with_total": 0, "defective": 0, "instances": {}}
    for path in paths:
        d, tot = series(path)
        out["n"] += 1
        if d is None or tot is None:
            continue
        out["with_total"] += 1
        assert len(d) == len(tot), path
        hours = [t for t, (a, b) in enumerate(zip(d, tot)) if a > b]
        if hours:
            out["defective"] += 1
            out["instances"][path.stem] = {"hours": len(hours),
                                           "max_excess": round(max(d[t] - tot[t] for t in hours), 3)}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path,
                    default=Path("results-revision/solver-robustness/inventory/sgtm-demand-check.json"))
    args = ap.parse_args()
    inv = Path("results-revision/solver-robustness/inventory/raw/pools")
    operational = ["instance001", "instance005", "instance014", "instance022", "instance027",
                   "instance031", "instance042", "instance046", "instance051", "instance058",
                   "instance068", "instance072", "instance077", "instance081", "instance092"]
    hist = Path("data/entradas/entrada-SG-Ter-Mer")
    sets = {
        "operational subset (historical)": [hist / f"{i}.txt" for i in operational],
        "benchmark pool (corrected)": sorted(inv.glob("sgtm/*.txt")),
        "sealed release pool": sorted(inv.glob("sgtm_sealed_release/*.txt")),
        "historical instances": sorted(hist.glob("instance*.txt")),
        "benchmark instance077 (corrected)": [Path("data/benchmark-v1/instance077-corrected/instance077.txt")],
    }
    # A reduced copy of the repository may not carry every pool.
    sets = {name: [q for q in paths if q.exists()] for name, paths in sets.items()}
    result = {name: scan(paths) for name, paths in sets.items() if paths}
    for name, r in result.items():
        if len(r["instances"]) > 20:
            r["instances_note"] = "listing truncated to the first 20 by name"
            r["instances"] = dict(sorted(r["instances"].items())[:20])
        print(f"{name}: {r['defective']}/{r['with_total']} defective of {r['n']} files")
    args.out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
