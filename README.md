# Pre-Export Row Scaling for Generated Mixed-Integer Programs: Mechanism Attribution and Residual-Budget Contracts

**Research status, 24 September 2026: revision complete, consistency audit done.**
The manuscript has been reframed around mechanism attribution and residual-budget contracts.
What changed in this round, and which claims are confirmatory rather than exploratory, is
recorded in [the revision record](paper/research-audit/revision-record-20260924.md).

A pre-registered solver-robustness campaign was prepared and partly run on ClusterUY, then
descoped from this manuscript to keep it about mechanism and guarantees rather than
benchmarking. Its protocol, split, frozen run tables and the 9,057 runs completed before it was
stopped remain in [`results-revision/solver-robustness/`](results-revision/solver-robustness/)
for a separate study; nothing in the paper depends on them.

Research manuscript and reproducibility materials by Mathias Rodríguez Castro.
The current manuscript is **unpublished**. No journal acceptance, submission, or
upload of this revision to an external archive is claimed.

The paper separates what row scaling demonstrably does from what it is credited with. With one
LP basis held fixed, scaling moves the basis condition number by six to eight orders of
magnitude; the apparent block-metadata advantage of an earlier draft turns out to be a
coupling-kernel effect that a control without ownership information reproduces; residual budgets
stated in application units survive consistent row re-emission and determine the admissible row
factors exactly; and what a solver then does with the representation is measured, not assumed.
The results do not establish a universal solver speedup or reliability improvement.

The earlier positive block-attribution claim is superseded. Historical drafts and intermediate
results remain available so the change in interpretation can be audited; the separate
rounding-safety investigation lives in its own
[working note](paper/research-notes/joint-rounding.pdf) and is not part of this manuscript.

## Reproduce the current paper without a solver license

Run commands from the repository root. The recorded environment is Python 3.10.12,
NumPy 2.2.6, SciPy 1.15.3, pandas 2.3.3, matplotlib 3.10.9, and pytest 9.0.3.
The requirements file pins these Python packages; it does not install an optimizer.

```bash
python3 -m venv .venv-research
. .venv-research/bin/activate
python3 -m pip install -r environment/research-requirements.txt
make research-check-python
make research-analysis
make paper
```

`research-check-python` runs the row-factor mathematical/numerical tests, independently
checks the saved binary solutions and enumerated optima, and checks all 1,080 final
LP hashes. It imports neither HiGHS nor Gurobi. It writes an updated
`budget-final/verification.json`; the saved model and solution data are unchanged.
`research-analysis` regenerates the current budget, matrix, and operational summaries,
tables, and vector figures from saved data. `paper` builds `paper/main.pdf` and
`paper/supporting-information.pdf` with pdfLaTeX and BibTeX. A standard TeX Live
installation with the packages listed in [paper/README.md](paper/README.md) suffices;
the current manuscript does not use the historical Wiley class or fonts.

To also check the actual C++ LP serializer, install GNU Make and a C++17 compiler:

```bash
make research-check
```

This builds a solver-free `DummyLp` executable in the isolated `code/build-audit/`
directory, then runs both Python checks and a C++ export integration test. The test
covers small coefficients, the RHS, bounds, and objective values that the old fixed
precision format could lose. `code/build/` is not used for this target. A first build
takes longer than the Python-only check.

## Which data support the current manuscript?

| Location under `results-revision/research-audit/` | Role |
|---|---|
| `identifiability-final/` | Authoritative matrix audit: 180 generated instances, six policies, 1,080 LP exports using the corrected round-trip serializer; named comparisons, whole-row checks, spectra at a common reference rank, and hashes. |
| `budget-final/` | Authoritative binary stress experiment: 96 models, nine policies, two solvers and two presolve settings; 3,456 planned configurations, including 288 abstentions and 3,168 optimizer calls. Models, factors, returned points, protocol and source snapshots are retained. |
| `operational/` | Authoritative reconstruction of 240 historical dispatch runs, with recovered native logs, input hashes, fixed-pool PAR10, conditional completed-run Work summaries, and residual diagnostics. These are reconstructed observations, not new optimizer runs. |
| `budget-pilot/`, `budget-confirmatory/`, `budget-confirmatory-v2/` | Earlier stress runs, retained for provenance. The initial endpoint implementation and later correction give different results; these folders must not be substituted for `budget-final/`. |
| `identifiability-confirmatory/` | Earlier matrix export with the old serializer; retained to expose the effect of representation changes. |

`budget-final/protocol.json` records versions, seeds, settings, methods and source
hashes. The independent checker verifies the complete Cartesian configuration grid,
all 96 enumerated optima and stored acceptance labels, 768 exact dyadic exports, and
288 justified abstentions. Its current saved-data SHA-256 is
`f0cfa86aa97e60dcca6985dd66b235883ecabafb1fe1f4de40a3b70b39840aa2`
for `budget-final/runs.csv`.

The stress models deliberately approach integer feasibility boundaries and do not
estimate failure rates or runtime on industrial MILPs. A verified binary optimum uses
the paper's declared independent acceptance rule. Abstention is counted separately
from a solve. The dispatch data have no corresponding exact optimality certificate
or application-calibrated residual budgets.

The original paper sources and PDFs are preserved in
`paper/research-audit/baseline-20260908/`; superseded documentation is in its `docs/`
subdirectory. Earlier attribution controls are in
`results-revision/attribution-controls/`. Existing `results/`, `results-revision/`
campaigns, synthetic outputs, old figures, and the original `paper/references.bib`
are historical material unless explicitly referenced by the current manuscript.

## Optional fresh experiments

These commands generate new experiments; they are not needed to verify the saved
results or build the paper. Targets reject an existing output directory, so choose
a new path for each rerun. The rerun defaults are separate from the authoritative data.

The matrix grid uses `DummyLp` and performs **no optimization**:

```bash
make research-grid
# Equivalent, after make audit-build:
python3 scripts/audit_identifiability_grid.py \
    --exe code/build-audit/SistemaElectrico \
    --out results-revision/research-audit/reruns/identifiability-manual \
    --seeds 10 --seed-base 20260909 --roundtrip-export
```

The binary experiment uses the Python solver APIs. The complete recorded protocol
uses HiGHS 1.15.1 and Gurobi 13.0.2; the latter requires a suitable license:

```bash
python3 -m pip install highspy==1.15.1 gurobipy==13.0.2
make research-budget
python3 scripts/research/verify_saved_experiment.py \
    --root results-revision/research-audit/reruns/budget
```

There are up to 3,168 solver calls with a ten-second limit per call in the full run.
To run only the license-free HiGHS arm:

```bash
python3 -m pip install highspy==1.15.1
make research-budget BUDGET_SOLVERS=highs \
    BUDGET_OUT=results-revision/research-audit/reruns/budget-highs
python3 scripts/research/verify_saved_experiment.py \
    --root results-revision/research-audit/reruns/budget-highs
```

A HiGHS-only run has half the planned configurations. The current paper table/plot
script expects both solvers; do not replace the complete paper data with that subset.
For a complete rerun, analyze into a separate output location:

```bash
python3 scripts/research/analyze_budget_experiment.py \
    --root results-revision/research-audit/reruns/budget \
    --figures results-revision/research-audit/reruns/budget/figures \
    --tables results-revision/research-audit/reruns/budget/tables
```

Solver outputs can depend on the versions and platform. Frozen sources identify the
reported implementation; rerunning the current code is a reproduction attempt, not
a promise of identical trajectories or wall times. The matrix analysis script reads
`identifiability-final/` explicitly; a fresh grid produces its own comparison CSVs
and hashes without replacing the manuscript's chosen data.

The original commercial-solver dispatch campaigns and cluster templates remain in
`cluster/`, `environment/solver-notes.md`, and the historical documentation. They are
longer, separate experiments, not dependencies of any current verification target.
`make help` lists current and historical targets. `make analysis-n0` and
`make synthetic-mini` reproduce earlier analyses, not the current paper.

## Repository map and licensing

- `paper/`: current manuscript, supplement, bibliography, generated figures/tables,
  and research audits.
- `scripts/research/`: budget construction, experiment, analysis and independent checker.
- `scripts/audit_identifiability_grid.py`: direct named LP and row-scaling audit.
- `scripts/audit_operational_evidence.py`: reconstruction from saved dispatch records.
- `tests/`: mathematical/numerical checks and C++ serializer integration.
- `code/`: C++ model generator, row preprocessing and retained solver interfaces.
- `data/`, `results/`, `results-revision/`: instances and current/historical evidence.

Code is MIT-licensed ([LICENSE](LICENSE)); data and aggregate results use CC BY 4.0
([DATA_LICENSE.md](DATA_LICENSE.md)). The manuscript is not covered by those licenses;
all rights are reserved pending an explicit manuscript license. It is an unpublished
research draft, not an accepted or submitted-version article.

The pre-existing archive identifier
[10.5281/zenodo.20648950](https://doi.org/10.5281/zenodo.20648950) belongs to the project's
archive history. It does not establish that this local revision has been deposited.
See [CITATION.cff](CITATION.cff) for the current local citation metadata; there is no
journal article DOI for this manuscript.
