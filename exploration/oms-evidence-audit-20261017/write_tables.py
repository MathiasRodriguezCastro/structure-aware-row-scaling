"""Compact supplementary tables from the checked secondary evidence audit."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def table(name, columns, header, rows):
    text = [r"\begin{tabular}{" + columns + "}", r"\toprule", header + r"\\",
            r"\midrule", *[" & ".join(row) + r"\\" for row in rows],
            r"\bottomrule", r"\end{tabular}"]
    (ROOT / "paper/tables" / name).write_text("\n".join(text) + "\n")


def main():
    result = json.loads((HERE / "RESULTS.json").read_text())
    rows = []
    for r in result["dispatch_summary"]:
        if r["presolve"] != -1 or r["budget"] not in (30, 100):
            continue
        def interval(group):
            return (f'{r[f"delete_{group}_work_ratio_min"]:.3f}--'
                    f'{r[f"delete_{group}_work_ratio_max"]:.3f}')
        rows.append([str(r["budget"]), f'{r["work_wins"]}/18', f'{r["work_ratio"]:.3f}',
                     interval("instance"), interval("seed"), f'{r["full_time_wins"]}/18'])
    table("frontier-deletions.tex", "rrrrrr",
          r"$\delta_V$ & Work wins & $W/W_{\rm NF3}$ & Omit one model & Omit one seed & Time wins", rows)
    rows = []
    for r in result["external_summary"]:
        if r["scope"] != "all_eight_horizons":
            continue
        rows.append([r["policy"], f'{r["budget_passes"]}/24',
                     f'{r["work_ratio_to_L2"]:.3f}', f'{r["total_seconds_ratio_to_L2"]:.3f}',
                     f'{r["known_bound_checks"]}/24'])
    table("external-cost-controls.tex", "lrrrr",
          r"Policy & Budgets & $W/W_{\rm L2}$ & $T/T_{\rm L2}$ & Known bound checks", rows)


if __name__ == "__main__":
    main()
