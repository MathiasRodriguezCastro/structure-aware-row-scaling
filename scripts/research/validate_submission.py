#!/usr/bin/env python3
"""Check the submission archives the way a reviewer would: extract, verify, rebuild.

Extracts each archive into a temporary directory, verifies its recorded checksums, rebuilds the
COAP manuscript from the bundle alone, and records what was checked in
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


def audit_artifact():
    """Check the included supplement and run the documented audit from the ZIP alone."""
    with tempfile.TemporaryDirectory(prefix="artifact-audit-") as tmp:
        with zipfile.ZipFile(OUT / "reproducibility-artifact.zip") as archive:
            archive.extractall(tmp)
        root = Path(tmp)
        supplement = root / "paper/supporting-information.pdf"
        if not supplement.is_file() or sha(supplement) != sha(ROOT / "paper/supporting-information.pdf"):
            raise SystemExit("Online Resource 2 is missing the exact Online Resource 1 PDF")
        audit = subprocess.run(["make", "research-online-resources"], cwd=tmp,
                               capture_output=True, text=True)
        if audit.returncode:
            raise SystemExit("Extracted artifact audit failed:\n" + audit.stdout + audit.stderr)
        # README links to files in this artifact must resolve inside the extracted archive.
        import re
        missing = []
        for rel in ("README.md", "paper/README.md", "paper/submission/README.md"):
            readme = root / rel
            for target in re.findall(r"\]\(([^)]+)\)", readme.read_text()):
                if "://" in target or target.startswith("#"):
                    continue
                target = target.split("#", 1)[0]
                if not (readme.parent / target).exists():
                    missing.append(rel + " -> " + target)
        if missing:
            raise SystemExit("Artifact README links do not resolve: " + ", ".join(missing))
        return {"online_resource_1_included": True, "supplement_pdf_sha256": sha(supplement),
                "research_online_resources_passed": True, "readme_relative_links_verified": True,
                "audit_output": audit.stdout.strip()}


def rebuild_coap():
    """The bundle must compile on its own, with the class files it carries."""
    with tempfile.TemporaryDirectory(prefix="coap-build-") as tmp:
        zipfile.ZipFile(OUT / "coap-submission.zip").extractall(tmp)
        shipped = sha(Path(tmp) / "main_coap.pdf")
        for _ in range(2):
            subprocess.run(["pdflatex", "-halt-on-error", "-interaction=nonstopmode", "main_coap.tex"],
                           cwd=tmp, capture_output=True, check=True)
        for _ in range(2):
            subprocess.run(["pdflatex", "-halt-on-error", "-interaction=nonstopmode", "supporting-information.tex"], cwd=tmp, capture_output=True, check=True)
        log = (Path(tmp) / "main_coap.log").read_text(errors="ignore")
        pages = subprocess.run(["pdfinfo", "main_coap.pdf"], cwd=tmp, capture_output=True,
                               text=True).stdout
        pages = next((l.split()[-1] for l in pages.splitlines() if l.startswith("Pages")), None)
        return {"rebuilt_from_bundle_alone": True,
                "shipped_pdf_sha256": shipped,
                "pages": int(pages) if pages else None,
                "overfull_boxes": log.count("Overfull"),
                "undefined_references": log.lower().count("undefined")}


def main():
    result = {"archives": [check_archive(n) for n in
                           ["coap-submission.zip",
                            "reproducibility-artifact.zip"]],
              "coap_bundle_build": rebuild_coap(),
              "artifact_audit": audit_artifact(),
              "documents": {}}
    for label, pdf in [
                       ("supplement", ROOT / "paper/supporting-information.pdf"),
                       ("coap_manuscript", ROOT / "paper/coap/main_coap.pdf"),
                       ("cover_letter", ROOT / "paper/coap/cover-letter.pdf")]:
        info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
        pages = next((l.split()[-1] for l in info.splitlines() if l.startswith("Pages")), None)
        result["documents"][label] = {"pages": int(pages) if pages else None, "sha256": sha(pdf)}
    (OUT / "VALIDATION.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if not all(a["checksums_verified"] for a in result["archives"]):
        raise SystemExit("Archive checksum verification failed")
    if result["coap_bundle_build"]["undefined_references"] or result["coap_bundle_build"]["overfull_boxes"]:
        raise SystemExit("Bundle build has unresolved references or overfull boxes")


if __name__ == "__main__":
    main()
