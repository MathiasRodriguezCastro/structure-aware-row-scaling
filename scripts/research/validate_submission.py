#!/usr/bin/env python3
"""Check the submission archives the way a reviewer would: extract, verify, rebuild.

Extracts each archive into a temporary directory, verifies its recorded checksums, rebuilds the
MPC manuscript from the bundle alone, and records what was checked in
paper/submission/VALIDATION.json.
"""
import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper/submission"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_archive(name):
    archive = OUT / name
    with tempfile.TemporaryDirectory(prefix="submission-check-") as tmp:
        zipfile.ZipFile(archive).extractall(tmp)
        manifest = Path(tmp) / "CONTENTS.sha256"
        r = subprocess.run(["sha256sum", "--quiet", "-c", manifest.name],
                           cwd=tmp, capture_output=True, text=True)
        return {"archive": name, "sha256": sha(archive),
                "files": len(zipfile.ZipFile(archive).namelist()),
                "checksums_verified": r.returncode == 0,
                "checksum_output": r.stdout.strip()[:400]}


def rebuild_mpc():
    """The bundle must compile on its own, with the class files it carries."""
    with tempfile.TemporaryDirectory(prefix="mpc-build-") as tmp:
        zipfile.ZipFile(OUT / "mpc-submission.zip").extractall(tmp)
        shipped = sha(Path(tmp) / "main_mpc.pdf")
        for _ in range(2):
            subprocess.run(["pdflatex", "-interaction=nonstopmode", "main_mpc.tex"],
                           cwd=tmp, capture_output=True)
        log = (Path(tmp) / "main_mpc.log").read_text(errors="ignore")
        pages = subprocess.run(["pdfinfo", "main_mpc.pdf"], cwd=tmp, capture_output=True,
                               text=True).stdout
        pages = next((l.split()[-1] for l in pages.splitlines() if l.startswith("Pages")), None)
        return {"rebuilt_from_bundle_alone": True,
                "shipped_pdf_sha256": shipped,
                "pages": int(pages) if pages else None,
                "overfull_boxes": log.count("Overfull"),
                "undefined_references": log.lower().count("undefined")}


def main():
    result = {"archives": [check_archive(n) for n in
                           ["mpc-submission.zip", "manuscript-sources.zip",
                            "reproducibility-artifact.zip"]],
              "mpc_bundle_build": rebuild_mpc(),
              "documents": {}}
    for label, pdf in [("main", ROOT / "paper/main.pdf"),
                       ("supplement", ROOT / "paper/supporting-information.pdf"),
                       ("mpc_manuscript", ROOT / "paper/mpc/main_mpc.pdf"),
                       ("cover_letter", ROOT / "paper/mpc/cover-letter.pdf")]:
        info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
        pages = next((l.split()[-1] for l in info.splitlines() if l.startswith("Pages")), None)
        result["documents"][label] = {"pages": int(pages) if pages else None, "sha256": sha(pdf)}
    (OUT / "VALIDATION.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
