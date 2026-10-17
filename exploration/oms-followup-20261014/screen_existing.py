#!/usr/bin/env python3
"""Bounded, solver-free follow-up; never writes to the OMS manuscript or release.

Read the saved contracts and six already selected stage-check models. Quantify
conditional precision headroom and inspect integer rounding of stored points.
Whole-model floating-point diagnostics are not feasibility certificates.
"""
import csv
from fractions import Fraction
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys
import re
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DATA = ROOT / "results-revision/research-audit/oms-close-20261013"
sys.path.insert(0, str(ROOT / "scripts/research"))
import oms_dispatch_validation as campaign
from audit_identifiability_grid import parse
from check_sgtm_demand import scan


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    inputs = {DATA / "factor-contracts.csv.gz", DATA / "design.json"}
    groups = {}
    records = 0
    decisions_changed = 0
    with gzip.open(DATA / "factor-contracts.csv.gz", "rt") as stream:
        for row in csv.DictReader(stream):
            records += 1
            decisions_changed += row["decision"] != "unchanged"
            if row["scenario"] != "Demanding":
                continue
            key = row["policy"], row["unit"]
            group = groups.setdefault(key, {
                "policy": key[0], "unit": key[1], "rows": 0,
                "physical_budget": float(row["physical_budget"]),
                "minimum_conditional_headroom": math.inf,
                "maximum_conditional_residual_physical": 0.0,
                "limiting_instance": "", "limiting_row": "",
            })
            alpha = float(row["proposed"])
            conversion = float(row["units_per_physical"])
            epsilon = float(row["epsilon_exported"])
            budget = float(row["physical_budget"])
            assert min(alpha, conversion, epsilon, budget) > 0
            residual_bound = epsilon / (alpha * conversion)
            headroom = budget / residual_bound
            group["rows"] += 1
            if headroom < group["minimum_conditional_headroom"]:
                group.update(minimum_conditional_headroom=headroom,
                             limiting_instance=row["instance"],
                             limiting_row=row["row_name"])
            group["maximum_conditional_residual_physical"] = max(
                group["maximum_conditional_residual_physical"], residual_bound)
    assert records == 1710720 and decisions_changed == 0
    headroom_rows = [groups[key] for key in sorted(groups)]
    write_csv(HERE / "conditional-headroom.csv", headroom_rows)

    design = json.loads((DATA / "design.json").read_text())
    selected = [item for item in design["instances"] if item["ablation"]]
    assert len(selected) == 6
    demand_paths = [ROOT / item["input"] for item in selected if item["class"] == "sgtm"]
    demand_check = scan(demand_paths)
    inputs.update(demand_paths)
    assert demand_check["with_total"] == 3
    observations, support_rows, activation_rows, witnesses = [], [], [], []
    with tempfile.TemporaryDirectory(prefix="oms-followup-") as temp:
        path = Path(temp) / "Base.lp"
        for item in selected:
            cls, instance = item["class"], item["instance"]
            base_path = DATA / "exports" / cls / instance / "Base.lp.gz"
            inputs.add(base_path)
            path.write_bytes(gzip.decompress(base_path.read_bytes()))
            _, lp, matrix = campaign.afb.read_lp(path)
            rows, _ = parse(path)
            indices = [i for i, kind in enumerate(lp.integrality_)
                       if str(kind) != "HighsVarType.kContinuous"]
            integer_names = {lp.col_names_[i] for i in indices}
            physical = [name for name, row in rows.items()
                        if campaign.physical_spec(name, row["terms"]) is not None]
            physical_with_integers = sum(bool(set(rows[name]["terms"]) & integer_names)
                                         for name in physical)
            # This identity justifies reusing the exact raw-point physical audit:
            # changing only integer coordinates cannot change these activities.
            assert physical_with_integers == 0
            support_rows.append({"class": cls, "instance": instance,
                                 "integer_variables": len(indices),
                                 "physical_rows": len(physical),
                                 "physical_rows_with_integer_terms": physical_with_integers})
            row_lower, row_upper = np.array(lp.row_lower_), np.array(lp.row_upper_)
            col_lower, col_upper = np.array(lp.col_lower_), np.array(lp.col_upper_)
            storage_bounds = {name: (float(lo), float(hi))
                              for name, lo, hi in zip(lp.col_names_, col_lower, col_upper)}
            activations = {name: row for name, row in rows.items()
                           if re.fullmatch(r"a\d+_activacion_[1-4]\(\d+\)", name)}

            def diagnostics(point):
                activity = matrix @ point
                violation = np.maximum(np.maximum(row_lower - activity,
                                                  activity - row_upper), 0)
                normalized = violation / np.maximum(1, abs(matrix) @ abs(point))
                bound = np.maximum(np.maximum(col_lower - point, point - col_upper), 0)
                winner = int(np.argmax(normalized))
                return float(normalized[winner]), lp.row_names_[winner], float(bound.max())

            for policy in (*campaign.POLICIES, *campaign.ABLATION):
                solution_path = DATA / "runs" / cls / instance / (policy + "-solution.npz")
                inputs.add(solution_path)
                with np.load(solution_path, allow_pickle=False) as saved:
                    values = dict(zip(saved["names"].tolist(), saved["x"].tolist()))
                x = np.array([values[name] for name in lp.col_names_])
                rounded = x.copy()
                rounded[indices] = np.rint(x[indices])
                assert np.array_equal(rounded[np.setdiff1d(np.arange(len(x)), indices)],
                                      x[np.setdiff1d(np.arange(len(x)), indices)])
                raw, raw_row, raw_bound = diagnostics(x)
                new, new_row, new_bound = diagnostics(rounded)
                integer_change = float(np.max(abs(rounded[indices] - x[indices]))) if indices else 0.0
                assert integer_change <= design["solver"]["parameters"]["IntFeasTol"]
                observations.append({"class": cls, "instance": instance, "policy": policy,
                    "max_integer_coordinate_change": integer_change,
                    "raw_max_activity_normalized_violation": raw,
                    "rounded_max_activity_normalized_violation": new,
                    "raw_limiting_row": raw_row, "rounded_limiting_row": new_row,
                    "raw_max_bound_violation": raw_bound,
                    "rounded_max_bound_violation": new_bound,
                    "physical_activities_unchanged_by_support": True})
                if activations:
                    rounded_values = dict(zip(lp.col_names_, rounded.tolist()))
                    raw_max = rounded_max = Fraction(0)
                    winner = None
                    for name, row in activations.items():
                        raw_violation = campaign.exact_violation(row["terms"], row["rhs"], values, row["sense"])
                        rounded_violation = campaign.exact_violation(row["terms"], row["rhs"], rounded_values, row["sense"])
                        raw_max = max(raw_max, raw_violation)
                        if rounded_violation > rounded_max:
                            rounded_max = rounded_violation
                            winner = name
                    activation_rows.append({"class": cls, "instance": instance, "policy": policy,
                        "rows": len(activations), "unit": "m3",
                        "raw_max_exact_binary64_data_violation": float(raw_max),
                        "rounded_max_exact_binary64_data_violation": float(rounded_max),
                        "rounded_limiting_row": winner or "",
                        "budget_assigned_to_activation_rows": False})
                    if winner:
                        row = activations[winner]
                        assert row["sense"] == "<=" and len(row["terms"]) == 2
                        binary = next(name for name in row["terms"] if name in integer_names)
                        storage = next(name for name in row["terms"] if name not in integer_names)
                        f = Fraction.from_float
                        m = f(float(row["terms"][binary]))
                        assert float(row["terms"][storage]) == -1 and m > 0
                        threshold = m - f(float(row["rhs"]))
                        low, high = storage_bounds[storage]
                        assert math.isfinite(low) and math.isfinite(high)
                        min_valid_m = max(Fraction(0), threshold - f(low))
                        witnesses.append({"class": cls, "instance": instance, "policy": policy,
                            "row": winner, "binary_variable": binary, "storage_variable": storage,
                            "unit": "m3", "binary_raw": values[binary],
                            "binary_rounded": rounded_values[binary], "storage": values[storage],
                            "M_binary64": float(m), "rhs_binary64": float(row["rhs"]),
                            "threshold_from_exact_binary64_difference": str(threshold),
                            "rounded_violation_exact_fraction": str(rounded_max),
                            "rounded_violation_m3": float(rounded_max),
                            "worst_case_rounding_reserve_at_declared_IntFeasTol_m3": float(m * f(design["solver"]["parameters"]["IntFeasTol"])),
                            "storage_lower_bound_m3": low,
                            "minimum_M_valid_for_this_implication_using_lower_bound_m3": float(min_valid_m),
                            "worst_case_reserve_with_minimum_M_m3": float(min_valid_m * f(design["solver"]["parameters"]["IntFeasTol"])),
                            "demand_inversion_detected": instance in demand_check["instances"],
                            "scope": "auxiliary activation row, outside the published physical-budget scope; no operational budget assigned"})
            print("screened", cls, instance, "without optimization", flush=True)
    assert len(observations) == 36
    write_csv(HERE / "integer-support.csv", support_rows)
    write_csv(HERE / "rounded-point-diagnostics.csv", observations)
    write_csv(HERE / "activation-row-diagnostics.csv", activation_rows)
    (HERE / "activation-witnesses.json").write_text(json.dumps(witnesses, indent=2, allow_nan=False) + "\n")
    summary = {
        "date": "2026-10-14", "optimization_calls": 0,
        "contract_records_read": records, "changed_decisions": decisions_changed,
        "demanding_contract_records": sum(row["rows"] for row in headroom_rows),
        "minimum_conditional_headroom": min(row["minimum_conditional_headroom"] for row in headroom_rows),
        "rounding_models": len(selected), "rounding_points": len(observations),
        "physical_rows_per_model_summed": sum(row["physical_rows"] for row in support_rows),
        "physical_rows_with_integer_terms": sum(row["physical_rows_with_integer_terms"] for row in support_rows),
        "maximum_integer_coordinate_change": max(row["max_integer_coordinate_change"] for row in observations),
        "raw_max_activity_normalized_violation": max(row["raw_max_activity_normalized_violation"] for row in observations),
        "rounded_max_activity_normalized_violation": max(row["rounded_max_activity_normalized_violation"] for row in observations),
        "physical_rounding_effect": "exactly zero by row support on these six models",
        "auxiliary_activation_points_checked": len(activation_rows),
        "auxiliary_activation_rounded_positive_witnesses": len(witnesses),
        "auxiliary_activation_max_rounded_violation_m3": max(row["rounded_max_exact_binary64_data_violation"] for row in activation_rows),
        "selected_sgtm_demand_check": demand_check,
        "scope": "headroom is conditional on exported residual; whole-model diagnostics use binary64 arithmetic; no exact feasibility or optimality certification",
        "decision": "No budget-active case identified in the published physical scope. A rounding issue in auxiliary volume-activation rows merits a separate check of budget meaning and existing remedies; retain the closed OMS release.",
    }
    (HERE / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    inputs.add(Path(__file__))
    inputs.update({ROOT / "scripts/research/oms_dispatch_validation.py",
                   ROOT / "scripts/research/audit_fixed_basis.py",
                   ROOT / "scripts/audit_identifiability_grid.py",
                   ROOT / "scripts/research/check_sgtm_demand.py",
                   ROOT / "code/SystemController/Agentes/Generacion/Generadores/SaltoGrande/SaltoGrande.cpp"})
    manifest = {"inputs": {str(path.relative_to(ROOT)): sha(path) for path in sorted(inputs)},
                "outputs": {name: sha(HERE / name) for name in (
                    "conditional-headroom.csv", "integer-support.csv",
                    "rounded-point-diagnostics.csv", "activation-row-diagnostics.csv",
                    "activation-witnesses.json", "summary.json")}}
    (HERE / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
