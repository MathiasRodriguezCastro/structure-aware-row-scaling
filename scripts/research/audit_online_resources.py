#!/usr/bin/env python3
"""Mechanical audit of the two Online Resources before submission.

Checks, from the sources and the rendered PDFs rather than by reading them:
  1. every "Online Resource 1, Table Sx" of the article exists in the supplement and carries
     that number;
  2. every numbered table of the supplement is pointed at from the article;
  3. every value the article quotes next to such a pointer appears in that table;
  4. every path the two documents name exists in the repository;
  5. the supplement carries the article title, the journal, the author, the affiliation and the
     contact address, and the artifact identifies itself as Online Resource 2.
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
    "S7": ["161", "153", "140", "192", "191", "182", "167", "141", "151", "152", "156", "150",
           "48"],
    "S8": ["10"],
    "S9": ["77", "27", "25", "9", "20", "6", "4"],
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

    cited = sorted(set(re.findall(r"Table~(S\d+)", main_src)), key=lambda s: int(s[1:]))
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
    # enclosure width and how closely the certified bounds agree with the estimates. Check them
    # against the stored data, which is stronger than matching the table text.
    width, agree = derived_s2_values()
    for value, claim, name in ((width, "6\\times10^{-3}", "enclosure width"),
                               (agree, "2.1\\times10^{-5}", "bound/estimate agreement")):
        quoted = float(re.sub(r"\\times10\^\{(-?\d+)\}", r"e\1", claim))
        ok = value <= quoted * 1.05 and value >= quoted * 0.5
        print(f"[3] S2 derived {name}: data {value:.3e}, article says {quoted:.1e} "
              + ("--- consistent" if ok else "--- INCONSISTENT"))
        if not ok:
            failures.append(f"article quotes {quoted:.1e} for the {name}; data give {value:.3e}")
        if claim.replace("\\times10^{", "").replace("}", "") and claim not in MAIN.read_text():
            failures.append(f"article no longer states {claim} for the {name}")

    required = ["Pre-Export Row Scaling", "Mathematical Programming Computation",
                "Rodr\\'iguez Castro", "Universidad de la Rep\\'ublica", "mathiasr@fing.edu.uy",
                "Online Resource 1"]
    missing = [r for r in required if r not in si_src]
    print(f"[5] supplement front matter: {len(required) - len(missing)}/{len(required)} present"
          + (f" --- MISSING {missing}" if missing else ""))
    if missing:
        failures.append(f"supplement front matter missing {missing}")
    readme = (ROOT / "README.md").read_text()
    for r in ("Online Resource 2", "mathiasr@fing.edu.uy", "Universidad de la Rep\u00fablica"):
        if r not in readme:
            failures.append(f"README does not identify itself: missing {r!r}")
    print("[5] the artifact identifies itself as Online Resource 2"
          if "Online Resource 2" in readme else "[5] FAILED")

    if failures:
        print("\nFAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
