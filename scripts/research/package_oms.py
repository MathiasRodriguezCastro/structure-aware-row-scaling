#!/usr/bin/env python3
"""Prepare local OMS sources, reproducibility artifact and separate upload copies."""
import hashlib
from pathlib import Path
import shutil
import zipfile

import package_submission as shared
from oms_snapshot import write_metadata, followup_files, incumbent_files, workflow_files, matched_files, strengthening_files, HISTORICAL_REPLAY_INPUTS, VERSION, REVISION_DATE

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper/submission/oms"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    paper, oms = ROOT / "paper", ROOT / "paper/oms"
    files = {}
    for folder in (oms, paper):
        if folder == oms:
            names = ["main_oms.tex", "main_oms.bbl", "main_oms.pdf", "interact.cls", "tfq.bst",
                     "research-references.bib", "abstract.txt", "TEMPLATE_PROVENANCE.md"]
        else:
            names = ["supporting-information.tex", "supporting-information.pdf"]
        paths = [folder / n for n in names]
        paths += list((folder / "sections").glob("*.tex"))
        paths += list((folder / "tables").glob("*.tex"))
        paths += list((folder / "figs/research").glob("*.pdf"))
        for path in paths:
            content = path.read_bytes()
            name = path.relative_to(folder).as_posix()
            if name in files and files[name] != content:
                raise SystemExit("Source copy has drifted: " + name)
            files[name] = content
    with zipfile.ZipFile(OUT / "oms-submission.zip", "w", zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for name, content in sorted(files.items()):
            archive.writestr(name, content)
        archive.writestr("CONTENTS.sha256", "".join(
            f"{hashlib.sha256(c).hexdigest()}  {n}\n" for n, c in sorted(files.items())))
    return len(files)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest, snapshot = write_metadata()
    shared.OUT = OUT
    shared.EXCLUDED.clear()
    artifact = [Path(p) for p in (
        "README.md", "Makefile", "LICENSE", "DATA_LICENSE.md", "CITATION.cff", ".zenodo.json",
        "artifacts/README.md", "paper/main.tex", "paper/main.bbl", "paper/Makefile", "paper/README.md",
        "paper/research-references.bib", "paper/supporting-information.tex",
        "paper/supporting-information.pdf", "paper/submission/oms/README.md",
        "paper/submission/oms/SUBMISSION_CHECKLIST.md", "paper/submission/oms/SNAPSHOT.json",
        "paper/submission/oms/OMS_DATA_MANIFEST.json", "artifacts/baseline-metadata/CITATION-v1.2-coap-submission.cff",
        "artifacts/baseline-metadata/zenodo-v1.2-coap-submission.json", "paper/submission/data-deposit/MANIFEST.json",
        "paper/submission/data-deposit/SHA256SUMS")]
    for folder, suffixes in (
        ("paper/sections", {".tex"}), ("paper/tables", {".tex"}),
        ("paper/figs/research", {".pdf"}),
        ("paper/oms", {".tex", ".bib", ".bbl", ".cls", ".bst", ".md", ".pdf", ".txt"}),
        ("environment", {".txt", ".md"}), ("scripts", {".py", ".sh"}),
        ("tests", {".py", ".cpp"}), ("code", {".cpp", ".c", ".h", ".hpp", ".mk", ".md"}),
        ("data", None), ("results-revision/research-audit", None),
        ("results-revision/attribution-controls", None), ("results-revision/fixed-basis", None),
        ("results-revision/r5-ablation", None), ("paper/validation", {".md", ".json", ".csv"}),
        ("results-revision/spectral-heterogeneous", {".csv"}),
    ):
        artifact += list(shared.collect(folder, suffixes))
    artifact += [p.relative_to(ROOT) for p in
                 (ROOT / "results-revision/final-variants").glob("*/resumen.csv")]
    artifact += list(followup_files())
    artifact += list(incumbent_files())
    artifact += list(workflow_files())
    artifact += list(matched_files())
    artifact += list(strengthening_files())
    # The bulk historical directory is excluded; these compact analysis inputs are required.
    artifact += [Path(p) for p in HISTORICAL_REPLAY_INPUTS]
    supplied = {p.as_posix() for p in artifact}
    missing = [item["path"] for item in manifest["files"] if item["path"] not in supplied]
    assert not missing, "New OMS data excluded from artifact: " + str(missing)
    count = shared.archive("reproducibility-artifact.zip", artifact)
    source_count = sources()
    uploads = OUT / "uploads"
    uploads.mkdir(exist_ok=True)
    files = {
        "main_oms.pdf": ROOT / "paper/oms/main_oms.pdf",
        "oms-submission.zip": OUT / "oms-submission.zip",
        "cover-letter.pdf": ROOT / "paper/oms/cover-letter.pdf",
        "supplementary-material-1.pdf": ROOT / "paper/supporting-information.pdf",
        "reproducibility-artifact.zip": OUT / "reproducibility-artifact.zip",
    }
    for name, origin in files.items():
        shutil.copy2(origin, uploads / name)
    (uploads / "SHA256SUMS").write_text("".join(f"{sha(uploads/n)}  {n}\n" for n in files))
    (uploads / "UPLOAD_INSTRUCTIONS.md").write_text(f"""# OMS separate upload files

Extract oms-delivery.zip before assigning individual files in the submission portal.

Article: Pre-Export Row Scaling for Generated Mixed-Integer Programs: Accuracy Contracts and Software Evaluation
Author: Mathias Rodríguez Castro, Facultad de Ingeniería, Universidad de la República, Montevideo, Uruguay
Contact: mathiasr@fing.edu.uy

| File | Intended role |
|---|---|
| main_oms.pdf | Manuscript |
| oms-submission.zip | Editable LaTeX sources |
| cover-letter.pdf | Cover letter |
| supplementary-material-1.pdf | Supplementary Material 1 |
| reproducibility-artifact.zip | Supplementary Material 2 |

Suggested supplementary captions:

Supplementary Material 1: Supplementary proofs, fixed-basis audit protocols and complete
ranges, operational reconstruction details, arithmetic checks and reproduction instructions.

Supplementary Material 2: C++ model generator and scaling code, Python residual-budget
selector, stored experiment data, analysis and independent verification scripts. Includes
the exact Supplementary Material 1 PDF. Bulk fixed-basis LP text and bases are supplied by
the archived experimental baseline, https://doi.org/10.5281/zenodo.23145294.

Select the corresponding file categories in the portal. Confirm current instructions and
supplement size limits at https://www.tandfonline.com/action/authorSubmission?journalCode=goms20&page=instructions.
That page returned HTTP 403 during preparation. This is the locally frozen OMS snapshot
{VERSION}, revised {REVISION_DATE}, not a published Zenodo release. The earlier DOI
does not identify the new Ruiz, stage-check or physical-budget experiments. The artifact
includes SNAPSHOT.json and OMS_DATA_MANIFEST.json with every new-data file checksum.
""")
    with zipfile.ZipFile(OUT / "oms-delivery.zip", "w", zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for name in (*files, "UPLOAD_INSTRUCTIONS.md", "SHA256SUMS"):
            archive.write(uploads / name, name)
    paths = [*files.values(), OUT / "oms-delivery.zip"]
    (OUT / "SHA256SUMS").write_text("".join(
        f"{sha(p)}  {p.relative_to(ROOT)}\n" for p in paths))
    print(f"Prepared OMS sources ({source_count} files), artifact ({count} files) and delivery in {OUT}")


if __name__ == "__main__":
    main()
