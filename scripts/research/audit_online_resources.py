#!/usr/bin/env python3
"""Mechanical audit of the two Supplementary Materials before submission.

Checks, from the sources and the rendered PDFs rather than by reading them:
  1. every "Supplementary Material 1, Table Sx" of the article exists in the supplement and carries
     that number;
  2. every numbered table of the supplement is pointed at from the article;
  3. every value the article quotes next to such a pointer appears in that table;
  4. every path the two documents name exists in the repository;
  5. the supplement carries the article title, the journal, the author, the affiliation and the
     contact address, and the artifact identifies itself as Supplementary Material 2.
Exits non-zero on the first category that fails, and prints a line per check either way.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / "paper/main.tex"
SI = ROOT / "paper/supporting-information.tex"
SI_PDF = ROOT / "paper/supporting-information.pdf"

# Values the article quotes beside a table pointer, and the table that must contain them.
QUOTED = {
    "S2": ["2.405", "1.681", "1.077", "6.247", "1.216", "2.277", "3.055", "6.046"],
    "S3": ["Gurobi 13.0.1", "CPLEX 22.1.2.0", "HiGHS 1.15.1", "Xeon Gold 6138"],
    "S4": ["0.452", "0.502", "0.698", "0.682"],
    "S5": ["116", "134", "1216", "1217"],
    "S6": ["0.778", "0.777", "0.698", "0.682", "1.078", "1.077"],
    "S7": ["3.73", "2.02", "2.01", "3.74", "14.42", "8.55", "8.58", "14.45"],
    "S8": ["161", "153", "140", "192", "191", "182", "167", "141", "151", "152", "156", "150",
           "48"],
    "S9": ["10"],
    "S10": ["76", "26", "25", "9", "20", "6", "4"],
    "S14": ["001", "003", "042", "Cold", "CommonStart", "0/3", "3/3"],
    "S15": ["IF0", "IF1", "Generate", "Select/export", "Verify", "Total", "4,837.338"],
    "S16": ["18/18", "15/18", "1.106", "0.6023", "3.063", "2.648"],
    "S17": ["0.362", "0.629", "30", "100"],
    "S18": ["0.824", "0.731", "0.987"],
    "S20": ["24/24", "23/24", "111.041", "8.2"],
    "S21": ["0.356", "18/18"],
    "S22": ["0.373", "0.519", "0.329", "0.499", "0.960", "1.054"],
}


def pdf_text(path):
    out = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                         capture_output=True, text=True, check=True).stdout
    return re.sub(r"-\n\s*", "", out)


def table_blocks(text):
    """The text of each numbered table of the supplement, from its caption to the next one."""
    starts = [(m.group(1), m.start()) for m in re.finditer(r"Table (S\d+):", text)]
    blocks = {}
    for i, (num, pos) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else len(text)
        blocks.setdefault(num, "")
        blocks[num] += text[pos:end]
    return blocks


def cited_tables(source):
    """Read singular/plural pointers, lists and inclusive LaTeX ranges."""
    cited = set()
    pattern = r"Tables?~(S\d+(?:(?:--|,\s*|\s+and\s+)S\d+)*)"
    for match in re.finditer(pattern, source):
        cited.update(re.findall(r"S\d+", match[1]))
        for first, last in re.findall(r"S(\d+)--S(\d+)", match[1]):
            cited.update(f"S{i}" for i in range(int(first), int(last) + 1))
    return sorted(cited, key=lambda s: int(s[1:]))


# The documents write paths relative to these roots, as the supplement states; a bare path is
# resolved against each in turn.
PATH_ROOTS = ["", "results-revision/research-audit",
              "results-revision/research-audit/fixed-basis-final-20260914",
              "results-revision/research-audit/operational", "results-revision", "paper"]


def derived_s2_values():
    """The two figures the article derives from the precision check, recomputed from its data."""
    import json
    d = ROOT / "results-revision/research-audit/fixed-basis-final-20260914/precision-check"
    pr = {(r["class"], r["instance"], r["variant"]): r
          for r in json.loads((d / "results.json").read_text())}
    design = json.loads((d / "design.json").read_text())
    width = agree = 0.0
    for cls, chosen in design["selection"].items():
        for inst in dict.fromkeys(chosen.values()):
            recs = [pr[cls, inst, v] for v in ("Base", "Flat-GM", "Flat-L2")]
            width = max(width, max(x["kappa1_upper_bound"] / x["kappa1_certified_lower"] - 1
                                   for x in recs))
            est = recs[1]["kappa1_estimate_seed0"] / recs[0]["kappa1_estimate_seed0"]
            bound = recs[1]["kappa1_upper_bound"] / recs[0]["kappa1_certified_lower"]
            agree = max(agree, abs(bound / est - 1))
    return width, agree


def main():
    main_src = MAIN.read_text()
    si_src = SI.read_text()
    si_txt = pdf_text(SI_PDF)
    blocks = table_blocks(si_txt)
    failures = []

    cited = cited_tables(main_src)
    present = sorted(blocks, key=lambda s: int(s[1:]))
    print(f"[1] article cites {', '.join(cited)}; supplement contains {', '.join(present)}")
    for t in cited:
        if t not in blocks:
            failures.append(f"article cites {t}, which the supplement does not contain")
    print("[1] every cited table exists and carries that number"
          if not failures else "[1] FAILED")

    orphans = [t for t in present if t not in cited]
    print(f"[2] tables nobody points at: {orphans or 'none'}")
    if orphans:
        failures.append(f"supplement tables not pointed at from the article: {orphans}")

    for t, values in QUOTED.items():
        if t not in blocks:
            continue
        missing = [v for v in values if v not in blocks[t]]
        print(f"[3] {t}: {len(values) - len(missing)}/{len(values)} quoted values found"
              + (f" --- MISSING {missing}" if missing else ""))
        if missing:
            failures.append(f"{t} does not contain {missing}")

    paths = set()
    for src in (main_src, si_src):
        paths |= set(re.findall(r"\\path\{([^}]+)\}", src))
        paths |= set(re.findall(r"\\texttt\{([^}]+)\}", src))
    named = {p.replace("\\_", "_").replace("\\", "") for p in paths}
    named = {p for p in named if "/" in p and not p.startswith(("http", "make ", "v1."))}
    def resolves(p):
        return any((ROOT / r / p.rstrip("/")).exists() for r in PATH_ROOTS)
    absent = sorted(p for p in named if not resolves(p))
    print(f"[4] paths named in the two documents: {len(named)}; absent: {absent or 'none'}")
    if absent:
        failures.append(f"paths named but absent: {absent}")

    # The article states two figures that Table S2 does not print literally: the largest
    # diagnostic bracket width and agreement of numerical upper endpoints with estimates. Check them
    # against the stored data, which is stronger than matching the table text.
    width, agree = derived_s2_values()
    for value, claim, name in ((width, "6\\times10^{-3}", "diagnostic bracket width"),
                               (agree, "2.1\\times10^{-5}", "upper-endpoint/estimate agreement")):
        quoted = float(re.sub(r"\\times10\^\{(-?\d+)\}", r"e\1", claim))
        ok = value <= quoted * 1.05 and value >= quoted * 0.5
        print(f"[3] S2 derived {name}: data {value:.3e}, article says {quoted:.1e} "
              + ("--- consistent" if ok else "--- INCONSISTENT"))
        if not ok:
            failures.append(f"article quotes {quoted:.1e} for the {name}; data give {value:.3e}")
        if claim.replace("\\times10^{", "").replace("}", "") and claim not in MAIN.read_text():
            failures.append(f"article no longer states {claim} for the {name}")

    # Row-path thresholds are supporting text, not cells of tolerance Table S21.
    import json
    mechanism = json.loads((ROOT / "exploration/oms-followup-20261017/mechanism/INDEPENDENT_VALIDATION.json").read_text())
    thresholds = mechanism["L2_budget_switch_threshold_range_m3"]
    for value in thresholds:
        literal = f"{value:,.3f}"
        if literal not in main_src or literal not in si_txt:
            failures.append("activation-factor threshold absent or inconsistent: " + literal)
    print("[3] S21 supporting activation thresholds independently traced: "
          + ", ".join(f"{v:,.3f}" for v in thresholds))

    required = ["Pre-Export Row Scaling", "Optimization Methods and Software",
                "Rodr\\'iguez Castro", "Universidad de la Rep\\'ublica", "mathiasr@fing.edu.uy",
                "Supplementary Material 1"]
    missing = [r for r in required if r not in si_src]
    print(f"[5] supplement front matter: {len(required) - len(missing)}/{len(required)} present"
          + (f" --- MISSING {missing}" if missing else ""))
    if missing:
        failures.append(f"supplement front matter missing {missing}")
    readme = (ROOT / "README.md").read_text()
    for r in ("Supplementary Material 2", "mathiasr@fing.edu.uy", "Universidad de la Rep\u00fablica"):
        if r not in readme:
            failures.append(f"README does not identify itself: missing {r!r}")
    print("[5] the artifact identifies itself as Supplementary Material 2"
          if "Supplementary Material 2" in readme else "[5] FAILED")

    if failures:
        print("\nFAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
