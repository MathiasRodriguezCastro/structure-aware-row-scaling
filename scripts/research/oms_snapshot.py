"""Version and complete new-data inventory for the frozen local OMS snapshot."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper/submission/oms"
VERSION = "v1.3.15-oms-submission"
REVISION_DATE = "2026-10-18"
NEW_DATA = Path("results-revision/research-audit/oms-close-20261013")
BASELINE = {"version": "v1.2-coap-submission", "version_doi": "10.5281/zenodo.23145294",
            "concept_doi": "10.5281/zenodo.20648949"}
REPLAY_PROGRAMS = ["scripts/research/verify_oms_dispatch.py",
    "scripts/research/verify_oms_conditioning.py", "scripts/research/oms_dispatch_validation.py",
    "scripts/research/oms_dispatch_tables.py", "scripts/research/audit_fixed_basis.py",
    "scripts/research/solver_scaling_bridge.py", "scripts/research/budget_scaling.py",
    "scripts/audit_identifiability_grid.py", "scripts/validar_preprocesamiento.py",
    "environment/research-requirements.txt", "Makefile", "code/Makefile",
    "scripts/research/oms_incumbent_tables.py", "scripts/research/oms_workflow_tables.py",
    "scripts/research/reconcile_oms_work.py", "paper/validation/oms-work-reconciliation.json",
    "scripts/research/oms_matched_tables.py", "scripts/research/verify_stress_coverage.py",
    "paper/validation/oms-stress-coverage.json", "paper/validation/oms-certificate-replay-fix.json",
    "scripts/research/oms_frontier_tables.py", "scripts/research/oms_followup_tables.py",
    "scripts/research/oms_base_tables.py"]
INCUMBENT = Path("exploration/oms-root-attribution-20261015")
WORKFLOW = Path("exploration/oms-if1-workflow-20261015")
MATCHED = Path("exploration/oms-matched-accuracy-20261016")
FOLLOWUP = Path("exploration/oms-followup-20261014")
HISTORICAL_REPLAY_INPUTS = [
    "results-revision/solver-robustness/analysis/contradictions.csv",
    "results-revision/solver-robustness/analysis/runs.csv"]
FOLLOWUP_DIRS = {"confirmation-bank", "confirmation-mechanism", "presolve-off-followup",
    "presolve-off-global-tight", "sensitivity-reference", "sensitivity-permissive",
    "pilot-activation", "saved-full-audit", "exact-witnesses", "exact-witness-reference"}
FOLLOWUP_ROOT_FILES = {"activation_study.py", "exact_dispatch_witness.py",
    "make_exact_witnesses.py", "measure_factor_cost.py", "prepare_activation_sensitivity.py",
    "verify_and_summarize.py", "write_paper_tables.py", "EXPERIMENT_PROTOCOL.md",
    "RESULTADOS.md", "README.md", "gate-rounding-certificate.json", "verified-runs.csv",
    "verified-summary.csv", "independent-study-verification.json", "factor-cost-runs.csv",
    "factor-cost-summary.csv"}


def followup_files():
    """Only final study inputs/results; no tool builds or rejected draft witnesses."""
    for path in (ROOT / FOLLOWUP).rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        local = path.relative_to(ROOT / FOLLOWUP)
        if local.parts[0] in FOLLOWUP_DIRS or local.as_posix() in FOLLOWUP_ROOT_FILES:
            yield path.relative_to(ROOT)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def incumbent_files():
    """Expanded diagnostic inputs and certificates; omit duplicate closed ZIP/build files."""
    yield Path('exploration/OMS_RESEARCH_FILTER.md')
    excluded={"root-attribution-artifact.zip", "package-validation.log", "package-replay.log",
        "pdf-build.log", "root-attribution-note.log", "MANIFEST.json"}
    for path in (ROOT/INCUMBENT).rglob('*'):
        if path.is_file() and not any(s in path.parts for s in ('__pycache__','.pytest_cache')) and path.name not in excluded and path.suffix not in ('.aux','.out'):
            yield path.relative_to(ROOT)


def workflow_files():
    """Full measured IF control, including the retained instrumentation pass."""
    excluded={'if1-workflow-artifact.zip','MANIFEST.json','package-validation.log',
        'package-replay.log','pdf-build.log','workflow-note.log','independent-check.log'}
    for path in (ROOT/WORKFLOW).rglob('*'):
        if path.is_file() and path.name not in excluded and path.suffix not in ('.aux','.out') and not any(s in path.parts for s in ('__pycache__','.pytest_cache')):
            yield path.relative_to(ROOT)


def matched_files():
    """All terminal calls and the interrupted attempt, without duplicate closed ZIP."""
    excluded={'matched-accuracy-artifact.zip','MANIFEST.json','package-replay.log',
        'pdf-build.log','matched-accuracy-note.log','independent-check.log'}
    for path in (ROOT/MATCHED).rglob('*'):
        if path.is_file() and path.name not in excluded and path.suffix not in ('.aux','.out','.pyc') and '__pycache__' not in path.parts:
            yield path.relative_to(ROOT)


def strengthening_files():
    """New paper evidence; keep the broader joint-scaling study separate."""
    for study in ('oms-frontier-20261016','oms-native-selector-20261016'):
        for p in (ROOT/'exploration'/study).rglob('*'):
            if p.is_file() and not any(x in p.parts for x in ('__pycache__','.pytest_cache')) and p.suffix not in ('.o','.d','.pyc','.zip','.aux','.out'):
                yield p.relative_to(ROOT)
    folder=ROOT/'exploration/oms-global-lp-20261016'
    names={'PROTOCOL.md','study.py','independent_check.py','design.json','results.json',
        'VALIDATION.json','verified-intervals.csv','RESULTADOS.md','README.md','campaign.log','validation.log'}
    for p in folder.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and (p.relative_to(folder).parts[0].startswith('instance') or p.name in names):
            yield p.relative_to(ROOT)
    # These are original-Base witnesses, not the broader joint algorithm's runs.
    witness=ROOT/'exploration/oms-joint-contracts-20261016'
    yield (witness/'base-witness-index.json').relative_to(ROOT)
    for p in (witness/'base-witnesses').rglob('*'):
        if p.is_file():yield p.relative_to(ROOT)
    # Pin every source/input required by the new numerical reader-only checks.
    for study in ('oms-frontier-20261016','oms-native-selector-20261016','oms-global-lp-20261016'):
        d=json.loads((ROOT/'exploration'/study/'design.json').read_text())
        for rel in d['dependencies']:yield Path(rel)
    # Bounded independent-family, tolerance, factor-path and full-cycle follow-up.
    folder=ROOT/'exploration/oms-followup-20261017'
    for p in folder.rglob('*'):
        if p.is_file() and not any(x in p.parts for x in ('__pycache__','.pytest_cache')) and p.suffix not in ('.pyc','.aux','.out','.zip'):
            yield p.relative_to(ROOT)
    source=ROOT/'exploration/oms-generalization-20261014'
    for name in ('generalization_study.py','independent_check.py','RESULTADOS.md','README.md','PILOT_PROTOCOL.md'):
        yield (source/name).relative_to(ROOT)
    for p in (source/'sources/STN-Scheduler').rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.aux','.out'):
            yield p.relative_to(ROOT)
    for name in ('external','tolerance','native-cycle'):
        d=json.loads((folder/name/'design.json').read_text())
        for rel in d['dependencies']:yield Path(rel)
    # Secondary audit: all saved outcomes, no new optimizer calls.
    for p in (ROOT/'exploration/oms-evidence-audit-20261017').rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.aux','.out','.zip'):
            yield p.relative_to(ROOT)
    # Directed unscaled controls and conditional, interleaved complete-cycle confirmation.
    for p in (ROOT/'exploration/oms-base-control-20261018').rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.aux','.out','.zip'):
            yield p.relative_to(ROOT)


def write_metadata():
    design = json.loads((ROOT / NEW_DATA / "design.json").read_text())
    verified = json.loads((ROOT / NEW_DATA / "independent-verification.json").read_text())
    conditioning = json.loads((ROOT / NEW_DATA / "conditioning-verification.json").read_text())
    files = {}
    for path in (ROOT / NEW_DATA).rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            files[path.relative_to(ROOT).as_posix()] = "new OMS experiment data and provenance"
    for rel in REPLAY_PROGRAMS:
        files[rel] = "replay or export program/configuration"
    for rel in HISTORICAL_REPLAY_INPUTS:
        files[rel] = "stored historical numerical-screening input required to regenerate certificate tables"
    for rel in followup_files():
        files[rel.as_posix()] = "activation follow-up input, result, exact witness or replay program"
    for rel in incumbent_files():
        files[rel.as_posix()] = "common-incumbent diagnostic input, native result, exact certificate or replay program"
    for rel in workflow_files():
        files[rel.as_posix()] = "matched IF control and complete workflow measurement; both passes and replay"
    for rel in matched_files():
        files[rel.as_posix()] = "six-model matched accuracy/remedy comparison; every terminal call and retained external interruption"
    for rel in strengthening_files():
        files[rel.as_posix()] = "prespecified multi-budget study, native-selector integration, or exact global-LP reference verification"
    for item in design["inputs"]:
        files[item["path"]] = "original operational input"
        assert sha(ROOT / item["path"]) == item["sha256"]
    inventory = [{"path": rel, "role": role, "bytes": (ROOT / rel).stat().st_size,
                  "sha256": sha(ROOT / rel)} for rel, role in sorted(files.items())]
    manifest = {"version": VERSION, "revision_date": REVISION_DATE,
                "scope": "complete new OMS experiment files and required replay programs/inputs",
                "new_experiment_root": NEW_DATA.as_posix(), "files": inventory,
                "additional_new_experiment_root": FOLLOWUP.as_posix(),
                "incumbent_diagnostic_root": INCUMBENT.as_posix(),
                "workflow_control_root": WORKFLOW.as_posix(),
                "matched_accuracy_root": MATCHED.as_posix(),
                "file_count": len(inventory), "replay_requires_baseline_bulk_archive": False,
                "replay_command": "make research-oms-check"}
    (OUT / "OMS_DATA_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    snapshot = {"version": VERSION, "revision_date": REVISION_DATE,
                "status": "locally frozen submission snapshot, not a published Zenodo release",
                "version_doi": None, "published": False, "submission_performed": False,
                "previous_local_snapshot": "v1.3.14-oms-submission",
                "editorial_revision": "Add the omitted matched unscaled controls to the favorable dispatch experiment: 36 Base/Base-tight calls and a conditional 54-call interleaved complete-cycle confirmation. Retain the historical sensitivity and all adverse outcomes. Distinguish effort at verified precision from additional primal recovery or general MILP certification.",
                "unscaled_control": {
                    "root": "exploration/oms-base-control-20261018",
                    "known_models": 6, "seeds": [59,71,89],
                    "directed_base_calls": 36, "reused_budget_calls": 36,
                    "interleaved_confirmation_calls": 54, "new_lp_calls": 0,
                    "replay": "make research-oms-check", "table": "S23",
                    "interpretation": "within-family effort comparison at matched verified primal budgets and candidate-cost quality; no additional recovery over Base, no independent-family validation or global MILP optimality certificate"},
                "work_reconciliation": {"geometric_mean": 4.484727186569008,
                    "median": 4.97549504639489, "same_per_seed_work": True,
                    "proof": "paper/validation/oms-work-reconciliation.json"},
                "historical_baseline": BASELINE,
                "historical_data_reused": ["306-model fixed-basis audit", "1,080-export matrix audit",
                    "240-run operational reconstruction and two 240-run sensitivities",
                    "4,752-call enumerated stress experiment", "exploratory stored-run discrepancy audit"],
                "new_oms_data": {"root": NEW_DATA.as_posix(), "comparison_models": 30,
                    "comparison_assigned_runs": 120, "complementary_stage_models": 6,
                    "additional_stage_assigned_runs": 12,
                    "stored_runs_and_exports": verified["exports_and_runs"],
                    "physical_rows_per_comparison_policy": 129600, "precision_scenarios": 3,
                    "all_factor_contract_records": verified["contract_decisions"],
                    "named_conditioning_bases": conditioning["named_bases_rebuilt_from_text"],
                    "parameters": design["solver"],
                    "interpretation": "stage check has an inactive coupling stage; physical contracts do not change factors"},
                "new_data_manifest": "paper/submission/oms/OMS_DATA_MANIFEST.json",
                "activation_followup": {
                    "root": FOLLOWUP.as_posix(), "models": 6,
                    "principal_calls": 72, "mechanism_calls": 27,
                    "fresh_seed_comparison_calls": 9, "preset_sensitivity_calls": 6,
                    "nonpilot_calls": 114, "separate_pilot_calls": 8,
                    "exact_native_export_witnesses": 20,
                    "replay": "python3 exploration/oms-followup-20261014/verify_and_summarize.py",
                    "interpretation": "study numerical precision goals extended to activation thresholds; benefits depend on target and configuration; feasible witnesses expose unsupported bounds, not global optima"},
                "new_data_manifest_sha256": sha(OUT / "OMS_DATA_MANIFEST.json"),
                "incumbent_diagnostic": {"root": INCUMBENT.as_posix(), "known_models": 3,
                    "seeds": [503,509,521], "native_mip_calls": 36,
                    "reference_lp_calls": 3, "posthoc_pattern_lp_calls": 15,
                    "exact_reference_optima": 3, "final_pattern_exact_optima": 13,
                    "final_pattern_unknown": 2, "loaded_common_starts": 18,
                    "table": "S14", "case_selection": "retrospective; one application family",
                    "replay": "python3 exploration/oms-root-attribution-20261015/independent_check.py",
                    "interpretation": "initialization sensitivity of an auxiliary MPS/power-of-two bank, not causal identification of one solver component or of the historical LP campaign"},
                "supplement_1": "paper/supporting-information.pdf",
                "matched_if_workflow": {"root": WORKFLOW.as_posix(),
                    "known_models": 1, "seeds": [11,23,47], "principal_mip_calls": 12,
                    "first_pass_mip_calls": 12, "total_new_mip_calls": 24, "new_lp_calls": 0,
                    "borrowed_exact_native_export_witnesses": 2, "table": "S15",
                    "replay": "python3 exploration/oms-if1-workflow-20261015/independent_check.py",
                    "interpretation": "IF1 leaves all six paired endpoints unchanged; full fresh-process prototype timings on a shared machine; neither new generality nor global optimality"},
                "matched_accuracy": {"root": MATCHED.as_posix(),"known_models":6,
                    "seeds":[11,23,47],"presolve":[-1,0],
                    "policies":["L2","Budget-L2","L2-tight","L2-NF3"],
                    "terminal_comparisons":144,"native_attempts":145,
                    "externally_interrupted_attempts_retained":1,"new_lp_calls":0,
                    "borrowed_exact_native_export_witnesses":12,"table":"S16",
                    "replay":"python3 exploration/oms-matched-accuracy-20261016/independent_check.py",
                    "interpretation":"within-family retrospective confirmation; terminal budget delivery and bound/gap refutations kept separate; no external generalization or global optimality"},
                "precision_frontier": {"root":"exploration/oms-frontier-20261016","assignments":360,
                    "native_MIP_calls":330,"abstentions":30,"exact_native_export_witness_LPs":31,
                    "seeds":[59,71,89],"common_integer_tolerance":1e-9,"volume_budgets":[10,30,100,300,1000,3000,10000],
                    "prespecified_regime_found":True,"automatic_presolve_qualified_models_30_and_100":6,"table":"S17","main_table":"12"},
                "native_selector": {"root":"exploration/oms-native-selector-20261016","timed_preparations":336,
                    "preflight_preparations":48,"exactly_equal_model_pairs":12,"new_optimizer_calls":0,
                    "table":"S18","interpretation":"standalone preparation cost; no extrapolation to full-solve speedup"},
                "global_LP_references": {"root":"exploration/oms-global-lp-20261016","unfixed_global_LP_calls":6,
                    "additional_Base_integer_witness_LPs":6,"one_percent_certified_reference_models":["instance005","instance022","instance031"],
                    "exact_MILP_optimum_certified_reference_models":["instance031"],"table":"S19",
                    "interpretation":"original-Base reference intervals, not certificates of all native floating-export results"},
                "followup_20261017": {"root":"exploration/oms-followup-20261017",
                    "new_MIP_calls":176,"new_exact_LP_attempts":8,"new_contractual_abstentions":18,
                    "external_models":8,"known_external_anchor_models":2,"new_external_horizons":6,
                    "external_comparison_calls":96,"external_reference_calls":8,
                    "external_primal_passes":{"L2":24,"Budget-L2":24,"L2-tight":24,"L2-NF3":23},
                    "external_exact_feasible_references":1,"external_exact_refinement_unknown":7,
                    "external_unknown_bound_checks":84,"external_table":"S20",
                    "tolerance_new_MIP_calls":36,"tolerance_borrowed_low_gamma_calls":54,
                    "tolerance_table":"S21","zero_bound_flag_regime_robust_across_two_gammas":False,
                    "native_cycle_calls":36,"native_cycle_equal_points_work_and_endpoints_pairs":18,
                    "native_cycle_cpp_to_python_full_time_ratio":0.8241102465391204,"native_cycle_table":"S18",
                    "activation_factors_independently_checked":53280,"unchanged_other_rows_checked":319680,
                    "internal_solver_mechanism_identified":False,
                    "preoptimization_external_order_failure_retained":True,"adverse_results_rerun":False},
                "secondary_evidence_audit": {"root":"exploration/oms-evidence-audit-20261017",
                    "table":"S22","new_optimizer_calls":0,"dispatch_pairs_checked":222,
                    "all_budget_presolve_cells_retained":14,"raw_external_calls_checked":96,
                    "favorable_dispatch_pairwise_work_wins":36,
                    "omitting_any_model_or_seed_retains_work_advantage":True,
                    "analysis_is_posthoc":True,"internal_solver_cause_identified":False,
                    "external_computational_superiority_established":False},
                "supplement_2": "reproducibility-artifact.zip",
                "licensing": {"code": "MIT", "data": "CC BY 4.0",
                              "manuscript": "outside code/data licenses"},
                "full_historical_basis_rebuild": "requires the baseline's separate fixed-basis-exports.tar.zst"}
    (OUT / "SNAPSHOT.json").write_text(json.dumps(snapshot, indent=2) + "\n")
    return manifest, snapshot


def verify_manifest(folder):
    """Prove every inventoried file is actually supplied and byte-identical."""
    folder = Path(folder)
    manifest_path = folder / "paper/submission/oms/OMS_DATA_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    snapshot = json.loads((folder / "paper/submission/oms/SNAPSHOT.json").read_text())
    assert manifest["version"] == snapshot["version"] == VERSION
    assert snapshot["version_doi"] is None and not snapshot["published"]
    assert sha(manifest_path) == snapshot["new_data_manifest_sha256"]
    for item in manifest["files"]:
        path = folder / item["path"]
        assert path.is_file() and path.stat().st_size == item["bytes"], item["path"]
        assert sha(path) == item["sha256"], item["path"]
    return {"version": VERSION, "inventoried_files_verified": len(manifest["files"]),
            "complete_new_oms_data_supplied": True, "baseline_bulk_not_needed_for_new_replay": True}
