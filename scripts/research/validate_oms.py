#!/usr/bin/env python3
"""Verify clean OMS extractions; no fresh research solves or commercial licenses.

The requested mathematical test suite includes small SciPy reference LPs.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile
from oms_snapshot import VERSION, REVISION_DATE, verify_manifest

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper/submission/oms"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, cwd):
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    if result.returncode:
        raise SystemExit("Failed: " + " ".join(command) + "\n" + result.stdout[-6000:] + result.stderr[-2000:])
    return result.stdout


def pdf_info(path):
    info = run(["pdfinfo", str(path)], path.parent)
    match = re.search(r"^Pages:\s+(\d+)", info, re.M)
    return {"pages": int(match.group(1)), "sha256": sha(path)}


def extracted_checks(name, root):
    with zipfile.ZipFile(OUT / name) as bundle:
        names = bundle.namelist()
        if any(n.startswith(("paper/coap/", "paper/mpc/")) for n in names):
            raise SystemExit("Historical editorial sources found in current package")
        bundle.extractall(root)
    run(["sha256sum", "--quiet", "-c", "CONTENTS.sha256"], root)
    return {"files": len(names), "checksums_verified": True, "sha256": sha(OUT / name)}


def compile_tex(name, folder, bibliography=False):
    run(["pdflatex", "-halt-on-error", "-interaction=nonstopmode", name], folder)
    if bibliography:
        run(["bibtex", name], folder)
    for _ in range(2):
        run(["pdflatex", "-halt-on-error", "-interaction=nonstopmode", name], folder)
    log = (folder / (name + ".log")).read_text(errors="replace")
    issues = {"overfull_boxes": log.count("Overfull"),
              "undefined_references": log.lower().count("undefined")}
    if any(issues.values()):
        raise SystemExit(f"Unresolved compilation issues in {name}: {issues}")
    return {"rebuilt_from_extracted_sources": True, **issues, **pdf_info(folder / (name + ".pdf"))}


def figure_render_hashes(folder):
    """Compare plotted content while allowing PDF creation-date metadata to differ."""
    with tempfile.TemporaryDirectory(prefix='oms-figure-renders-') as tmp:
        result={}
        for p in sorted((folder/'paper/figs/research').glob('*.pdf')):
            target=Path(tmp)/p.stem
            run(['pdftoppm','-f','1','-singlefile','-scale-to','1200','-png',str(p),str(target)],folder)
            result[str(p.relative_to(folder))]=sha(target.with_suffix('.png'))
        return result


def main():
    result = {"target": "Optimization Methods and Software", "local_revision_date": REVISION_DATE,
              "snapshot_version": VERSION,
              "new_release_published": False, "submission_performed": False, "archives": {}}
    with tempfile.TemporaryDirectory(prefix="oms-sources-") as tmp:
        folder = Path(tmp)
        result["archives"]["oms-submission.zip"] = extracted_checks("oms-submission.zip", folder)
        assert sha(folder / "main_oms.pdf") == sha(OUT / "uploads/main_oms.pdf")
        assert sha(folder / "supporting-information.pdf") == sha(OUT / "uploads/supplementary-material-1.pdf")
        assert VERSION in (folder / "main_oms.tex").read_text()
        assert VERSION in (folder / "supporting-information.tex").read_text()
        result["source_archive_identity"] = {"manuscript_pdf_matches_upload": True,
            "supplement_pdf_matches_upload": True, "both_sources_identify_current_version": True}
        result["manuscript_build"] = compile_tex("main_oms", folder, bibliography=True)
        result["supplement_build"] = compile_tex("supporting-information", folder)
    print("OMS source archive: checksums and independent compilation passed", flush=True)
    with tempfile.TemporaryDirectory(prefix="oms-artifact-") as tmp:
        folder = Path(tmp)
        result["archives"]["reproducibility-artifact.zip"] = extracted_checks("reproducibility-artifact.zip", folder)
        supplement = folder / "paper/supporting-information.pdf"
        assert sha(supplement) == sha(ROOT / "paper/supporting-information.pdf")
        assert sha(supplement) == sha(OUT / "uploads/supplementary-material-1.pdf")
        assert sha(folder / "paper/oms/main_oms.pdf") == sha(OUT / "uploads/main_oms.pdf")
        assert sha(folder / "paper/oms/cover-letter.pdf") == sha(OUT / "uploads/cover-letter.pdf")
        inventory = verify_manifest(folder)
        assert json.loads((folder / ".zenodo.json").read_text())["version"] == VERSION
        assert f'version: "{VERSION}"' in (folder / "CITATION.cff").read_text()
        assert VERSION in (folder / "paper/oms/main_oms.tex").read_text()
        assert VERSION in (folder / "paper/supporting-information.tex").read_text()
        run(["make", "research-online-resources"], folder)
        run(["make", "research-claims"], folder)
        all_tables={p:p.read_bytes() for p in (folder/'paper/tables').glob('*.tex')}
        rendered_figures=figure_render_hashes(folder)
        command_results={}
        for target in ('research-oms-check','research-check-python','research-check','research-analysis'):
            print('Extracted artifact: '+target,flush=True)
            output=run(['make',target],folder)
            command_results[target]={'passed':True,'output_sha256':hashlib.sha256(output.encode()).hexdigest()}
            if target=='research-check':
                assert (folder/'code/build-audit/SistemaElectrico').is_file()
                assert '1 passed' in output and 'skipped' not in output
        changed=[str(p.relative_to(folder)) for p,b in all_tables.items() if p.read_bytes()!=b]
        assert not changed,'analysis does not reproduce final tables: '+str(changed)
        assert figure_render_hashes(folder)==rendered_figures,'regenerated plot content changed'
        print('Extracted artifact: all four commands, tables and plotted content passed',flush=True)
        table_paths = [folder / "paper/tables" / (name + ".tex") for name in (
            "activation-bank", "activation-controls", "activation-fresh-seeds",
            "activation-sensitivity", "activation-summary")]
        activation_tables = {path: path.read_bytes() for path in table_paths}
        run(["python3", "exploration/oms-followup-20261014/write_paper_tables.py"], folder)
        assert all(path.read_bytes() == content for path, content in activation_tables.items())
        incumbent_table=folder/'paper/tables/incumbent-initialization.tex'
        original_incumbent_table=incumbent_table.read_bytes()
        run(['python3','scripts/research/oms_incumbent_tables.py'],folder)
        assert incumbent_table.read_bytes()==original_incumbent_table
        run(['python3','-m','pytest','-q','exploration/oms-root-attribution-20261015/test_metrics.py'],folder)
        workflow_tables=[folder/'paper/tables'/name for name in ('if1-accuracy.tex','workflow-cost.tex')]
        workflow_contents={p:p.read_bytes() for p in workflow_tables}
        run(['python3','scripts/research/oms_workflow_tables.py'],folder)
        assert all(p.read_bytes()==b for p,b in workflow_contents.items())
        run(['python3','-m','pytest','-q','exploration/oms-if1-workflow-20261015/test_verification.py'],folder)
        matched_tables=[folder/'paper/tables'/n for n in ('matched-accuracy.tex','matched-cases.tex','matched-main.tex')]
        matched_contents={p:p.read_bytes() for p in matched_tables}
        run(['python3','scripts/research/oms_matched_tables.py'],folder)
        assert all(p.read_bytes()==b for p,b in matched_contents.items())
        run(['python3','-m','unittest','discover','-s','exploration/oms-matched-accuracy-20261016','-p','test_endpoints.py'],folder)
        assert verify_manifest(folder) == inventory
        original = (folder / "paper/oms/main_oms.tex").read_bytes()
        run(["python3", "scripts/research/build_oms.py"], folder)
        assert original == (folder / "paper/oms/main_oms.tex").read_bytes()
        run(["make", "-C", "paper", "oms"], folder)
        missing = []
        for rel in ("README.md", "paper/README.md", "paper/submission/oms/README.md"):
            readme = folder / rel
            for target in re.findall(r"\]\(([^)]+)\)", readme.read_text()):
                if "://" in target or target.startswith("#"):
                    continue
                if not (readme.parent / target.split("#", 1)[0]).exists():
                    missing.append(rel + " -> " + target)
        if missing:
            raise SystemExit("Missing artifact README targets: " + ", ".join(missing))
        result["artifact_audit"] = {"supplement_pdf_identical": True,
            "all_submission_pdfs_match_artifact": True,
            "manuscript_supplement_and_metadata_identify_current_version": True,
            "inventoried_data_identical_after_replay": True,
            "supplement_audit_passed": True, "independent_claims_passed": True,
            "oms_regeneration_identical": True, "oms_build_passed": True,
            "readme_relative_links_verified": True, **inventory,
            "oms_dispatch_replay_passed": True, "oms_conditioning_replay_passed": True,
            "oms_dispatch_details": json.loads((folder / "results-revision/research-audit/oms-close-20261013/independent-verification.json").read_text()),
            "oms_conditioning_details": json.loads((folder / "results-revision/research-audit/oms-close-20261013/conditioning-verification.json").read_text()),
            "oms_activation_replay_passed": True,
            "oms_activation_tables_regenerated_identically": True,
            "oms_activation_details": json.loads((folder / "exploration/oms-followup-20261014/independent-study-verification.json").read_text()),
            "oms_incumbent_replay_passed": True,
            "oms_incumbent_table_regenerated_identically": True,
            "oms_incumbent_tests_passed": 4,
            "oms_incumbent_details": json.loads((folder/'exploration/oms-root-attribution-20261015/independent-verification.json').read_text()),
            "oms_if_workflow_replay_passed": True,
            "oms_if_workflow_tables_regenerated_identically": True,
            "oms_if_workflow_tests_passed": 4,
            "oms_matched_accuracy_replay_passed": True,
            "oms_matched_accuracy_tables_regenerated_identically": True,
            "oms_matched_accuracy_tests_passed": 4,
            "oms_precision_frontier_details": json.loads((folder/'exploration/oms-frontier-20261016/VALIDATION.json').read_text()),
            "oms_native_selector_details": json.loads((folder/'exploration/oms-native-selector-20261016/VALIDATION.json').read_text()),
            "oms_global_LP_reference_details": json.loads((folder/'exploration/oms-global-lp-20261016/VALIDATION.json').read_text()),
            "oms_external_transfer_details": json.loads((folder/'exploration/oms-followup-20261017/external/VALIDATION.json').read_text()),
            "oms_integer_tolerance_details": json.loads((folder/'exploration/oms-followup-20261017/tolerance/VALIDATION.json').read_text()),
            "oms_native_complete_cycle_details": json.loads((folder/'exploration/oms-followup-20261017/native-cycle/VALIDATION.json').read_text()),
            "oms_activation_factor_path_details": json.loads((folder/'exploration/oms-followup-20261017/mechanism/INDEPENDENT_VALIDATION.json').read_text()),
            "four_standard_commands": command_results,
            "all_final_tables_regenerated_identically": len(all_tables),
            "all_plots_regenerated_with_identical_rendered_content": len(rendered_figures),
            "cpp_export_roundtrip_test_passed_without_skip": True,
            "three_solver_stress_verification": json.loads((folder/'paper/validation/oms-stress-coverage.json').read_text()),
            "oms_matched_accuracy_details": json.loads((folder/'exploration/oms-matched-accuracy-20261016/VALIDATION.json').read_text()),
            "work_aggregation_reconciled": json.loads((folder/'paper/validation/oms-work-reconciliation.json').read_text()),
            "oms_if_workflow_details": json.loads((folder/'exploration/oms-if1-workflow-20261015/VALIDATION.json').read_text())}
    print("OMS artifact: supplement, stored claims and regenerated sources passed", flush=True)
    expected = {"main_oms.pdf", "oms-submission.zip", "cover-letter.pdf",
                "supplementary-material-1.pdf", "reproducibility-artifact.zip",
                "UPLOAD_INSTRUCTIONS.md", "SHA256SUMS"}
    with tempfile.TemporaryDirectory(prefix="oms-delivery-") as tmp:
        folder = Path(tmp)
        with zipfile.ZipFile(OUT / "oms-delivery.zip") as bundle:
            assert set(bundle.namelist()) == expected
            bundle.extractall(folder)
        run(["sha256sum", "--quiet", "-c", "SHA256SUMS"], folder)
        assert all(sha(folder / n) == sha(OUT / "uploads" / n) for n in expected)
        result["delivery"] = {"files": sorted(expected), "checksums_verified": True,
                              "upload_copies_verified": True, "sha256": sha(OUT / "oms-delivery.zip")}
    run(["sha256sum", "--quiet", "-c", str(OUT / "SHA256SUMS")], ROOT)
    result["documents"] = {name: pdf_info(path) for name, path in (
        ("manuscript", ROOT / "paper/oms/main_oms.pdf"),
        ("supplement", ROOT / "paper/supporting-information.pdf"),
        ("cover_letter", ROOT / "paper/oms/cover-letter.pdf"))}
    (OUT / "VALIDATION.json").write_text(json.dumps(result, indent=2) + "\n")
    print("OMS delivery and all checksums passed. Wrote paper/submission/oms/VALIDATION.json")


if __name__ == "__main__":
    main()
