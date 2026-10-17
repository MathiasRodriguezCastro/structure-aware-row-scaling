#!/usr/bin/env python3
"""Reaggregate historical cross-run discrepancies from numerical screening records.

The strict tier screens original-model relative activity, bounds and integrality
at 1e-9. This is not exact feasibility verification: its discrepancy flags are
numerical diagnostics, distinct from the rational feasible witnesses in the newer
activation studies. Historical column names are retained for traceability.

Neither campaign is a census. The solver-robustness campaign was stopped by decision and the
operational replication covers a fixed 30-instance subset, so these counts describe occurrences
in what was run and are not estimates of how often a solver does this.
"""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = [
    ("Stopped campaign", ROOT / "results-revision/solver-robustness/analysis/contradictions.csv",
     ROOT / "results-revision/solver-robustness/analysis/runs.csv"),
    ("Operational replication",
     ROOT / "results-revision/research-audit/operational-replication/analysis/contradictions.csv",
     ROOT / "results-revision/research-audit/operational-replication/analysis/runs.csv"),
]
POLICIES = ["Base", "Flat-GM", "Flat-L2", "Role-Hybrid"]


def tru(v):
    return str(v).strip().lower() in ("1", "true", "yes")


def summarize(path):
    """Counts under the stored strict numerical screen, not an exact certificate."""
    all_rows = list(csv.DictReader(path.open()))
    rows = [r for r in all_rows if tru(r["dual_bound_invalid_strict"])]
    strong = [r for r in all_rows if tru(r["optimality_claim_contradicted_strict"])]
    return {
        "rows": len(rows), "instances": len({r["instance"] for r in rows}),
        "rows_ordinary_tier": len(all_rows),
        "strong_runs": len(strong), "strong_instances": len({r["instance"] for r in strong}),
        "by_solver": dict(Counter(r["solver"] for r in strong)),
        "by_policy": dict(Counter(r["policy"] for r in strong)),
        "by_policy_all": dict(Counter(r["policy"] for r in rows)),
        "by_solver_all": dict(Counter(r["solver"] for r in rows)),
        "worst_excess": max(((float(r["objective"]) - float(r["best_known_strict"]))
                             / abs(float(r["best_known_strict"]))
                             for r in rows if r.get("best_known_strict") and r["objective"]),
                            default=None),
        "worst_row": max((r for r in rows if r.get("best_known_strict") and r["objective"]),
                         key=lambda r: (float(r["objective"]) - float(r["best_known_strict"]))
                         / abs(float(r["best_known_strict"])), default=None),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "paper/tables/certificate-audit.tex")
    ap.add_argument("--detail", type=Path,
                    default=ROOT / "paper/tables/certificate-audit-detail.tex")
    ap.add_argument("--json", type=Path,
                    default=ROOT / "results-revision/research-audit/certificate-audit.json")
    args = ap.parse_args()

    # Missing saved inputs must fail the audit rather than silently drop a campaign.
    for label,cpath,rpath in SOURCES:
        for path in (cpath,rpath):
            if not path.is_file():raise FileNotFoundError(f'required {label} analysis input missing: {path}')

    out = {}
    main = [r"\begin{tabular}{lrrrr}", r"\toprule",
            r"Campaign & Runs & Dual bound & Certificate & Instances \\",
            r"\midrule"]
    detail = [r"\begin{tabular}{llrrrrrr}", r"\toprule",
              r"Campaign & Level & Runs & Inst. & " + " & ".join(POLICIES) + r" \\",
              r"\midrule"]
    for label, cpath, rpath in SOURCES:
        s = summarize(cpath)
        total = len(list(csv.DictReader(rpath.open())))
        s["campaign_runs"] = total
        out[label] = s
        main.append(f"{label} & {total:,} & {s['rows']} & {s['strong_runs']} & "
                    f"{s['instances']} " + r"\\")
        detail.append(f"{label} & Dual bound & {s['rows']} & {s['instances']} & "
                      + " & ".join(str(s["by_policy_all"].get(p, 0)) for p in POLICIES) + r" \\")
        detail.append(f" & Certificate & {s['strong_runs']} & {s['strong_instances']} & "
                      + " & ".join(str(s["by_policy"].get(p, 0)) for p in POLICIES) + r" \\")
        print(f"{label}:")
        print(f"  runs in the campaign      : {total}")
        print(f"  flagged (bound or worse)  : {s['rows']} runs in {s['instances']} instances")
        print(f"  certificate contradicted  : {s['strong_runs']} runs in {s['strong_instances']} instances")
        print(f"    by solver  : {s['by_solver']}")
        print(f"    by policy  : {s['by_policy']}")
        w = s["worst_row"]
        print(f"  worst excess              : {s['worst_excess']:.4f} "
              f"({w['solver']}/{w['policy']} on {w['instance']}; strict witness named in the article)")
        print()
    for block, path in ((main, args.out), (detail, args.detail)):
        block += [r"\bottomrule", r"\end{tabular}"]
        path.write_text("\n".join(block) + "\n")
    args.json.write_text(json.dumps(out, indent=2) + "\n")
    print("wrote", args.out, args.detail, "and", args.json)


if __name__ == "__main__":
    main()
