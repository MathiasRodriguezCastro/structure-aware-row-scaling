#!/usr/bin/env python3
"""Analyze three frozen direction-compression campaigns without solver calls.

The independent checker must have completed first.  This script binds its
summary to the retained inputs by SHA-256 and checks design completeness; it
does not replace the independent mathematical/solution verifier.
"""

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REPO = Path(__file__).resolve().parents[2]
CAMPAIGNS = {
    "original-100": ("original", 96, 72, 25),
    "multilevel-200": ("multilevel", 336, 80, 25),
    "rounded-all-200": ("multilevel", 48, 80, 25),
}
ORDER = ["Base", "GCD-floor", "Single-coefficient", "Dyadic-GM",
         "Rounded-direction", "Rational-direction", "Rounded-all",
         "Oracle-direction"]
LABELS = {
    "Base": "Original", "GCD-floor": "GCD / RHS flooring",
    "Single-coefficient": "Single-coefficient control", "Dyadic-GM": "Dyadic GM",
    "Rounded-direction": "Rounded, sparse grid", "Rational-direction": "Rational direction",
    "Rounded-all": "Rounded, all q = 1,...,32*", "Oracle-direction": "Known-direction oracle",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_campaign(root, name):
    family, expected, ncols, nrows = CAMPAIGNS[name]
    folder = root / ("direction-compression-" + name)
    # Read verification before using any experimental outcome.
    verification = json.loads((folder / "independent-verification.json").read_text())
    assert verification["configurations"] == expected
    assert verification["models"] == 12
    assert sha256(folder / "runs.csv") == verification["runs_sha256"]
    design = json.loads((folder / "design.json").read_text())
    for source, digest in design["sources"].items():
        assert sha256(folder / ("source-" + source)) == digest, (name, source)
    d = pd.read_csv(folder / "runs.csv", dtype={"status": str})
    assert len(d) == expected
    for field in ["rounded_feasible", "rounded_optimal", "presolve"]:
        assert d[field].notna().all() and set(d[field]).issubset({False, True})
        d[field] = d[field].astype(bool)
    assert not (d.rounded_optimal & ~d.rounded_feasible).any()
    keys = ["M", "seed", "method", "solver", "presolve"]
    assert not d.duplicated(keys).any()
    assert set(d.method) == set(design["methods"])
    expected_keys = {(item["M"], item["seed"], method, solver, presolve)
                     for item in design["models"] for method in design["methods"]
                     for solver in ("gurobi", "highs") for presolve in (False, True)}
    assert set(d[keys].itertuples(index=False, name=None)) == expected_keys
    assert (d.rows == nrows).all()
    assert design["blocks"] * design["local_size"] == ncols
    assert design["blocks"] * design["local_rows"] + 1 == nrows
    original_models = {}
    for filename, digest in verification["model_sha256"].items():
        path = folder / filename
        assert sha256(path) == digest
        with np.load(path) as model:
            assert model["A"].shape == (nrows, ncols)
            original_models[path.stem] = {key: model[key].copy() for key in model.files}
    assert len(original_models) == 12
    summary = d.groupby(["solver", "method"]).agg(
        n=("status", "size"), feasible=("rounded_feasible", "sum"),
        optimal=("rounded_optimal", "sum"))
    observed = {f"{solver}/{method}": {k: int(v) for k, v in row.items()}
                for (solver, method), row in summary.iterrows()}
    assert observed == verification["summary"]
    d["campaign"] = name
    d["family"] = family
    d["posthoc_control"] = name == "rounded-all-200"
    d["solver_reported_optimal"] = ((d.solver == "highs") & (d.status == "kOptimal")) | (
        (d.solver == "gurobi") & (d.status == "2"))
    d["within_integrality_tolerance"] = d.integer_error <= design["eta"]
    # Missing means that the integer-row certificate was not applicable/reported.
    # It is not a proof that the corresponding model is unsafe.
    assert set(d.all_rows_gap_safe.dropna()).issubset({False, True})
    d["gap_certificate_reported"] = d.all_rows_gap_safe.eq(True)
    d["prep_plus_optimize_seconds"] = d.prep_seconds + d.solver_seconds
    d["source_rows"] = nrows
    d["source_variables"] = ncols
    for (M, seed, method), group in d.groupby(["M", "seed", "method"]):
        # Preprocessing occurred once and was copied into four solver records.
        for field in ["prep_seconds", "rows", "nnz", "max_coefficient"]:
            assert group[field].nunique(dropna=False) == 1, (name, M, seed, method, field)
        d.loc[group.index, "source_max_coefficient"] = float(
            np.max(np.abs(original_models[f"M{M}_s{seed}"]["A"])))
    provenance = {
        "family": family, "configurations": expected, "models": 12,
        "source_variables": ncols, "source_rows": nrows,
        "verification": verification,
        "verification_file_sha256": sha256(folder / "independent-verification.json"),
        "design_sha256": sha256(folder / "design.json"),
        "certificates_sha256": sha256(folder / "certificates.json"),
    }
    return d, provenance, original_models


def outcomes(d, keys):
    return d.groupby(keys, sort=False).agg(
        configurations=("status", "size"),
        solver_reported_optimal=("solver_reported_optimal", "sum"),
        exactly_feasible_after_rounding=("rounded_feasible", "sum"),
        exactly_optimal_after_rounding=("rounded_optimal", "sum"),
        within_integrality_tolerance=("within_integrality_tolerance", "sum"),
        integer_gap_certificate_reported=("gap_certificate_reported", "sum"),
    ).reset_index()


def timing(d, keys):
    return d.groupby(keys, sort=False).agg(
        configurations=("status", "size"),
        median_optimize_seconds=("solver_seconds", "median"),
        q25_optimize_seconds=("solver_seconds", lambda x: x.quantile(.25)),
        q75_optimize_seconds=("solver_seconds", lambda x: x.quantile(.75)),
        min_optimize_seconds=("solver_seconds", "min"),
        max_optimize_seconds=("solver_seconds", "max"),
        median_prep_plus_optimize_seconds=("prep_plus_optimize_seconds", "median"),
    ).reset_index()


def markdown_table(headers, records):
    return "\n".join(["| " + " | ".join(headers) + " |",
                      "| " + " | ".join(["---"] * len(headers)) + " |"] +
                     ["| " + " | ".join(map(str, row)) + " |" for row in records])


def figure(d, path):
    plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42, "ps.fonttype": 42,
                         "axes.titlesize": 10, "axes.labelsize": 9})
    fig, axes = plt.subplots(2, 3, figsize=(11.1, 6.7), sharex=True, sharey=True)
    y = np.arange(len(ORDER))
    sub = d[d.family == "multilevel"]
    for i, solver in enumerate(["gurobi", "highs"]):
        for j, M in enumerate([10**3, 10**6, 10**9]):
            ax = axes[i, j]
            group = sub[(sub.solver == solver) & (sub.M == M)].groupby("method").agg(
                n=("status", "size"), good=("rounded_feasible", "sum"),
                opt=("rounded_optimal", "sum")).reindex(ORDER)
            assert (group.n == 8).all()
            ax.barh(y, group.opt, height=.68, color="#245775", label="Exact optimum")
            ax.barh(y, group.good-group.opt, left=group.opt, height=.68,
                    color="#a8cadb", label="Feasible, suboptimal")
            ax.barh(y, group.n-group.good, left=group.good, height=.68,
                    color="#e1b5a4", label="Infeasible after rounding")
            for k, count in enumerate(group.opt):
                ax.text(8.19, k, f"{count}/8", va="center", fontsize=8)
            ax.set(yticks=y, yticklabels=[LABELS[m] for m in ORDER],
                   xlim=(0, 9), xticks=[0, 2, 4, 6, 8],
                   title=f"{dict(gurobi='Gurobi', highs='HiGHS')[solver]}, $M=10^{{{int(np.log10(M))}}}$")
            ax.grid(axis="x", color="white", linewidth=.7)
            ax.set_axisbelow(False)
            ax.spines[["top", "right", "left"]].set_visible(False)
            ax.tick_params(axis="y", length=0)
            if i == 1:
                ax.set_xlabel("Solver configurations")
    axes[0, 0].invert_yaxis()
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(.61, .043),
               ncol=3, frameon=False, fontsize=8)
    fig.text(.335, .018, "Eight configurations = four seeds × two presolve settings.  * Added after inspecting the sparse-grid results.",
             ha="left", fontsize=8)
    fig.tight_layout(rect=(0, .09, 1, 1))
    fig.savefig(path / "outcomes-by-scale.pdf", bbox_inches="tight", metadata={"CreationDate": None})
    fig.savefig(path / "outcomes-by-scale.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def write_report(d, prep, summary, destination):
    mult = summary[summary.family == "multilevel"].set_index(["method", "solver"])
    records = []
    for method in ORDER:
        vals = [mult.loc[(method, solver)] for solver in ["gurobi", "highs"]]
        records.append([LABELS[method], *[
            f"{int(v.exactly_optimal_after_rounding)}/{int(v.exactly_feasible_after_rounding)}/24"
            for v in vals], f"{sum(int(v.exactly_optimal_after_rounding) for v in vals)}/48"])
    result_table = markdown_table(["Method", "Gurobi: optimal / feasible / total",
                                   "HiGHS: optimal / feasible / total", "Combined exact optima"], records)
    timing_records = []
    for method in ORDER:
        p = prep[(prep.family == "multilevel") & (prep.method == method)].prep_seconds
        g = d[(d.family == "multilevel") & (d.method == method)]
        timing_records.append([LABELS[method], f"{1e3*p.median():.3f}", *[
            f"{1e3*g[g.solver == solver].solver_seconds.median():.3f}"
            for solver in ["gurobi", "highs"]]])
    timing_table = markdown_table(["Method", "Median preprocessing (ms; 12 models)",
                                   "Median Gurobi optimize (ms; 24 calls)",
                                   "Median HiGHS optimize (ms; 24 calls)"], timing_records)
    coefficient_records = []
    for method in ORDER:
        coefficient_records.append([LABELS[method], *[
            f"{prep[(prep.family == 'multilevel') & (prep.method == method) & (prep.M == M)].max_coefficient.max():.6g}"
            for M in [10**3, 10**6, 10**9]]])
    coefficient_table = markdown_table(["Method", "Max |A|, M = 10³", "Max |A|, M = 10⁶",
                                        "Max |A|, M = 10⁹"], coefficient_records)
    original = d[d.family == "original"]
    original_text = "; ".join(
        f"{LABELS[method]} {int(g.rounded_optimal.sum())}/{len(g)} exact optima"
        for method, g in original.groupby("method", sort=False))
    text = f"""# Integer-direction compression: frozen exploratory evidence

Generated by `scripts/research/analyze_direction_compression.py`; no solver calls are made by this analysis.

## Main finding and comparison boundary

On the new multilevel family, both matrix-only rational direction recovery and the stronger simple rounded-direction search return the exact optimum in all 48 solver configurations. The original model, GCD/RHS flooring, and the implemented single-coefficient control each return 39/48 exact optima. This supports investigating direction-based coefficient compression for these constructed inputs. It does **not** establish an advantage of rational approximation over a simple direction search, novelty of coefficient compression, or general solver acceleration.

The original rounded search tested only q in {{1, 2, 3, 4, 8, 16, 32}}. Its 41/48 result was inspected before adding the all-q control (q = 1,...,32), which obtains 48/48 on the same retained models. The sparse grid omits q = 5 and is an insufficient basis for claiming superiority of rational direction recovery. The follow-up is **post hoc**, not an independent holdout. Its complete results are included, without replacing the original campaign.

## Counted experiments

There are 480 completed solver configurations across three campaigns, representing **24 distinct input models** in two constructed families. The all-q follow-up reuses the same 12 multilevel inputs; exact array equality is checked by this script. Seeds and coefficient scales within each family share generator structure, and each model is evaluated with both solvers and both presolve settings. These are paired configurations, not 480 independent random instances. No hypothesis test or confidence interval treating them as independent samples is reported.

- `direction-compression-original-100`: 12 models × 2 methods × 2 solvers × 2 presolve settings = 96. Twelve blocks of six binary variables, two local rows per block and one resource row: 72 binary variables, 25 rows. M is 10⁶, 10⁹ or 10¹²; seeds 100–103. These inputs were already used in the preceding guard investigation and are not a fresh validation set for this direction.
- `direction-compression-multilevel-200`: 12 models × 7 methods × 2 solvers × 2 presolve settings = 336. Eight blocks of ten binary variables, three local rows per block and one resource row: 80 binary variables, 25 rows. M is 10³, 10⁶ or 10⁹; seeds 200–203. Each local row has its own signed leading direction; the generator does not plant an opposite pair forcing a single shared aggregate equality.
- `direction-compression-rounded-all-200`: the same 12 multilevel models × 1 additional method × 2 solvers × 2 presolve settings = 48.

All 480 calls returned a native optimal status (`2` for Gurobi, `kOptimal` for HiGHS). There are no abstentions or observed time limits in these three campaigns. Native status is not the acceptance criterion: overall, {int(d.rounded_feasible.sum())}/480 returned vectors round to exactly feasible points and {int(d.rounded_optimal.sum())}/480 to exact optima. All 480 vectors lie within the configured integrality tolerance of their nearest integer vector. Feasibility and optimality below are checked against the original integer data and independently computed dynamic-programming optima. The maximum distance from the nearest integer is recorded separately in the CSV tables.

## Exact outcomes on the multilevel family

{result_table}

`outcomes-by-scale.pdf` and `.png` separate each M and solver; each panel contains eight configurations per method, and the numbers beside each bar give exact optima out of eight. `outcomes-by-scale-and-solver.csv` retains those exact counts, and `outcomes-by-presolve.csv` further separates presolve. At M = 10⁹ the original model gives 7/8 exact optima with Gurobi and 0/8 with HiGHS; rational and all-q compression give 8/8 with either solver. The lower coefficient scales are not omitted.

On the original family: {original_text}. Both preserve all 25 rows and 72 variables, and reduce the maximum exported coefficient to at most {original.max_coefficient.max():g} (the source maximum over these models is {original.source_max_coefficient.max():.6g}). This campaign does not rerun the earlier 49-row known-generator decomposition; its success and timings belong to the separately archived guard comparison, so no new paired runtime comparison to it is claimed here.

## Coefficients and timing

The following are maximum absolute matrix coefficients over four models at each scale, in each method's own exported representation. Absolute coefficient size alone is not a scale-invariant quality measure: dyadic row scaling makes coefficients small without guaranteeing exact rounded feasibility.

{coefficient_table}

Direction methods stop reducing a row once its canonical integer representation satisfies the configured unit-gap rounding bound. Consequently the M = 10³ inputs can retain larger coefficients than the compressed higher-M inputs; this is intentional early stopping, not a transcription error. The precise sufficient condition used by the certificate is ε + η ||a||₁ < 1 for integral a and integral right-hand side, with ε = η = 10⁻⁶. A missing certificate flag means the checker was not applied/reported for that exported representation; it is not a proof of unsafety.

{timing_table}

Preprocessing is measured once per model and method; its copied value in four solver records is deduplicated before computing preprocessing summaries. Solve timing covers only `h.run()` or `m.optimize()`, excluding model construction, child-process startup, solver imports and Gurobi environment startup. `prep_plus_optimize_seconds` is therefore only the sum of the two measured components, **not end-to-end elapsed time**. Solver summaries include every completed call, including those with an incorrect exact outcome. Comparisons are descriptive; a quick incorrect answer is not a successful baseline solve. Timings are single observations on tiny models, without randomized method order or repeated timing trials. The stronger all-q method was run in a later campaign. No speedup claim is made.

## Controls, provenance and unresolved limitations

The single-coefficient control is the implemented binary saturation/slack-reduction rule with complementation and GCD/RHS flooring. It is not a complete reproduction of commercial presolve or all known coefficient-reduction algorithms. The oracle uses the planted direction and scale; the two matrix-only strategies and the all-q control do not read that metadata. The experiments do not compare against lattice reduction, full Frank–Tardos compression, PaPILO, or a complete historical coefficient-reduction implementation. The three designs archive source snapshots and settings but do not archive solver version strings or machine metadata; these are not reconstructed from the current environment.

Each independent verifier checked original model optima, local integer equivalence, the coupling row, and all reported exact outcome flags. Its compression proof checks are distinct from the analysis here. Before producing a table, this script checks the verifier's run/model hashes, all retained source hashes, design coverage and consistency with the verifier's summary. `provenance.json` records the identities of the input and verification artifacts. The certificate files are hashed by this analysis; the older independent-verification JSON does not itself bind the certificate file with a recorded hash. This report therefore relies on the retained verifier result plus the current certificate identity, not a cryptographically signed audit.

These families contain small bounded integer leading directions by construction. The exact equivalence checks enumerate local states only for validation and ground truth; the preprocessor does not use that enumeration. Positive results remain exploratory until independently motivated models and stronger established reduction controls establish practical scope. The mathematical connection between tolerance safety and a better integer representation is worth pursuing, while publication readiness and priority remain unresolved.

## Reproduce the analysis

From the repository root:

```sh
python3 scripts/research/analyze_direction_compression.py
```

The three campaign directories and their completed `independent-verification.json` files must be present. Outputs are rebuilt under `paper/research-audit/direction-comparison-20260913/`; frozen solver data are read only.
"""
    (destination / "report.md").write_text(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO / "results-revision/research-audit")
    parser.add_argument("--out", type=Path, default=REPO / "paper/research-audit/direction-comparison-20260913")
    args = parser.parse_args()
    frames, provenance, models = [], {}, {}
    for name in CAMPAIGNS:
        frame, checked, raw = read_campaign(args.root, name)
        frames.append(frame)
        provenance[name] = checked
        models[name] = raw
    # The post-hoc dense-grid run must really reuse the original multilevel data.
    assert set(models["multilevel-200"]) == set(models["rounded-all-200"])
    for name, original in models["multilevel-200"].items():
        rerun = models["rounded-all-200"][name]
        assert set(original) == set(rerun)
        assert all(np.array_equal(value, rerun[key]) for key, value in original.items())
    d = pd.concat(frames, ignore_index=True)
    assert len(d) == 480 and not d.duplicated(["family", "M", "seed", "method", "solver", "presolve"]).any()
    assert d.solver_reported_optimal.all()
    args.out.mkdir(parents=True, exist_ok=True)
    d.drop(columns="x").to_csv(args.out / "all-verified-outcomes.csv", index=False)
    summary = outcomes(d, ["family", "method", "solver"])
    summary.to_csv(args.out / "outcomes-by-method-and-solver.csv", index=False)
    outcomes(d, ["family", "M", "method", "solver"]).to_csv(
        args.out / "outcomes-by-scale-and-solver.csv", index=False)
    outcomes(d, ["family", "M", "method", "solver", "presolve"]).to_csv(
        args.out / "outcomes-by-presolve.csv", index=False)
    timing(d, ["family", "method", "solver"]).to_csv(args.out / "solver-timing.csv", index=False)
    timing(d, ["family", "M", "method", "solver"]).to_csv(
        args.out / "solver-timing-by-scale.csv", index=False)
    fields = ["family", "campaign", "M", "seed", "method", "posthoc_control", "prep_seconds",
              "source_variables", "source_rows", "rows", "nnz", "source_max_coefficient", "max_coefficient"]
    prep = d.drop_duplicates(["family", "M", "seed", "method"])[fields]
    assert len(prep) == 120
    prep.to_csv(args.out / "preprocessing-per-model.csv", index=False)
    prep.groupby(["family", "method"], sort=False).agg(
        models=("prep_seconds", "size"), median_prep_seconds=("prep_seconds", "median"),
        q25_prep_seconds=("prep_seconds", lambda x: x.quantile(.25)),
        q75_prep_seconds=("prep_seconds", lambda x: x.quantile(.75)),
        min_prep_seconds=("prep_seconds", "min"), max_prep_seconds=("prep_seconds", "max"),
    ).to_csv(args.out / "preprocessing-timing.csv")
    prep.groupby(["family", "M", "method"], sort=False).agg(
        models=("prep_seconds", "size"), median_prep_seconds=("prep_seconds", "median"),
        source_max_coefficient=("source_max_coefficient", "max"),
        max_exported_coefficient=("max_coefficient", "max"),
        median_exported_coefficient=("max_coefficient", "median"),
        min_rows=("rows", "min"), max_rows=("rows", "max"),
        min_nnz=("nnz", "min"), max_nnz=("nnz", "max"),
    ).to_csv(args.out / "coefficients-and-preprocessing-by-scale.csv")
    figure(d, args.out)
    write_report(d, prep, summary, args.out)
    provenance["analysis"] = {"script_sha256": sha256(Path(__file__)),
                              "total_configurations": len(d), "unique_input_models": 24,
                              "unique_model_method_preprocessings": len(prep),
                              "reused_multilevel_models_array_checked": 12,
                              "solver_calls_made_by_analysis": 0}
    (args.out / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(summary.to_string(index=False))
    print(f"Wrote analysis artifacts to {args.out}")


if __name__ == "__main__":
    main()
