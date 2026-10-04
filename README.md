# Pre-Export Row Scaling in Generated Mixed-Integer Programs: Mechanism Attribution and Residual-Budget Contracts

Manuscript and reproducibility artifact prepared for **Computational Optimization and
Applications (COAP)**. Author: Mathias Rodríguez Castro, Facultad de Ingeniería,
Universidad de la República, Montevideo, Uruguay; mathiasr@fing.edu.uy;
ORCID [0009-0002-7235-7677](https://orcid.org/0009-0002-7235-7677).

The manuscript develops mechanism attribution for pre-export row scaling and residual-budget
contracts in original application units. Its numerical and operational findings are verified
against stored data; they do not establish a universal solver speedup or reliability improvement.
Journal submission, acceptance and publication are not claimed.

## Manuscript and supplements

| File | Purpose |
|---|---|
| `paper/coap/main_coap.pdf` | Manuscript for COAP |
| `paper/submission/coap-submission.zip` | Editable LaTeX sources, class/style files, figures and bibliography |
| `paper/coap/cover-letter.pdf` | Cover letter |
| `paper/submission/editorial-manager/ESM_1.pdf` | Online Resource 1: supplementary proofs, protocols and reproduction instructions |
| `paper/submission/editorial-manager/ESM_2.zip` | Online Resource 2: source code, stored data, analysis and verification scripts |
| `paper/submission/coap-delivery.zip` | Complete set of separately uploaded files and instructions |

Upload the manuscript, source ZIP, cover letter and two ESM files separately in Editorial
Manager. Online Resource 2 includes `paper/supporting-information.pdf`, byte-identical to
Online Resource 1. See the [submission checklist](paper/submission/SUBMISSION_CHECKLIST.md).

The current release is
[`v1.2-coap-submission`](https://github.com/MathiasRodriguezCastro/structure-aware-row-scaling/releases/tag/v1.2-coap-submission).
The repository is archived under the Zenodo concept DOI
[10.5281/zenodo.20648949](https://doi.org/10.5281/zenodo.20648949).
[CITATION.cff](CITATION.cff) gives the citation metadata. Earlier repository states remain
available through Git history and tagged releases.

## Reproduce and verify

Run commands from the repository root. The recorded environment is CPython 3.10.12,
NumPy 2.2.6, SciPy 1.15.3, pandas 2.3.3, matplotlib 3.10.9 and pytest 9.0.3.
The requirements pin analysis dependencies; optimizer packages are optional.

```bash
sudo apt install python3-venv build-essential texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended
python3 -m venv .venv-research
. .venv-research/bin/activate
python3 -m pip install -r environment/research-requirements.txt
make research-check-python
make research-claims
make paper
make research-online-resources
python3 scripts/research/package_submission.py
python3 scripts/research/validate_submission.py
```

`research-check-python` tests the row-factor implementation, independently verifies saved
binary solutions and optima, and checks all 1,080 matrix-export hashes. `research-claims`
independently enumerates the stored binary models, verifies solver acceptance labels,
checks native operational logs and audits the matrix comparisons. Neither imports an optimizer.
`make research-check` also builds the C++ LP exporter and verifies its decimal serialization.

`make research-analysis` regenerates the current tables, figures and summaries from stored data.
`make paper` compiles the canonical manuscript, COAP version and supplement with pdfLaTeX and
BibTeX. [paper/README.md](paper/README.md) maps the manuscript sources.

`validate_submission.py` extracts the archives, verifies their checksums, recompiles the
manuscript and supplement, verifies the exact Online Resource 1 copy in Online Resource 2,
checks relative README links and runs the documented audits from the extracted artifact.
Results are saved in `paper/submission/VALIDATION.json`.

## Stored experiment data

The authoritative datasets are under `results-revision/research-audit/`:

| Directory | Evidence |
|---|---|
| `fixed-basis-final-20260914/` | Fixed-basis audit of 306 dispatch models under five policies, with 1,530 bases and an independent precision check |
| `identifiability-final/` | 180 generated instances, six policies and 1,080 matrix exports; named comparisons, spectra and hashes |
| `budget-final/`, `budget-final-cplex/` | Identical 96 stored binary models under three solvers, nine policies and two presolve settings: 5,184 planned configurations and 4,752 optimizer calls |
| `exploration-lattice/`, `exploration-lattice-cplex/` | Integer-aware GCD controls with exact-enumeration verification |
| `operational/` | Reconstruction of 240 dispatch runs, with native logs, input hashes, completed-run work comparisons and fixed-pool PAR10 |
| `operational-replication/` | Two matched 240-run sensitivity campaigns using a second seed and a second solver |
| `application-budgets/` | Declared residual budgets for 4,320 interpretable rows of one dispatch model, its exported LP and a budget-sensitivity sweep |

Protocols retain versions, seeds, settings and source hashes. Recorded results and source
snapshots are frozen. Intermediate datasets needed to interpret the experiments retain their
provenance; the supplement identifies which comparisons are exploratory.

The root directories `results/` and `results-revision/` also retain dispatch aggregates and
controls used by the current audits. The input instances are under `data/`.
The binary stress models approach integer feasibility boundaries and do not estimate
industrial failure rates. Dispatch instances do not have corresponding exact optimality
certificates or application-calibrated residual budgets.

## Bulk inputs

Online Resource 2 carries the stored summaries, analysis inputs and native logs used by the
verification commands above. The bulk fixed-basis LP text and bases are distributed separately
as `fixed-basis-exports.tar.zst`: 337 MB compressed, 5.18 GB uncompressed in 11,585 files.
Their manifest and checksum are in `paper/submission/data-deposit/`; the archive is attached
to the current release. See [artifacts/README.md](artifacts/README.md).

Only `make research-fixed-basis-check`, which reconstructs all 1,530 bases from LP text,
requires that archive extracted over the repository. `make research-fixed-basis-precision`
recomputes the certified rational bounds into a new output directory. These are verification
calculations, not optimizer runs.

## Optional fresh experiments

Fresh experiment targets require new output directories and retain the stored evidence:

```bash
make research-grid GRID_OUT=results-revision/research-audit/reruns/grid
make research-budget BUDGET_SOLVERS=highs BUDGET_OUT=results-revision/research-audit/reruns/budget-highs
```

The matrix grid uses the solver-free C++ exporter. A HiGHS-only binary run requires `highspy`
and covers one solver arm; it does not replace the three-solver manuscript data. The Gurobi
and CPLEX arms require their respective packages and licenses. The supplement gives the full
recorded protocols. Solver trajectories and wall times can depend on versions and platforms.

## Layout and licensing

| Path | Contents |
|---|---|
| `paper/` | Current manuscript, supplement, cover letter, bibliography, tables and figures |
| `scripts/` | Experiment, analysis, packaging and independent verification tools |
| `tests/` | Row-factor mathematics and C++ export integration checks |
| `code/` | C++ generator and row-scaling implementation |
| `data/`, `results/`, `results-revision/` | Instances, stored observations and provenance |
| `environment/` | Recorded dependencies and solver environment |

Code is MIT-licensed ([LICENSE](LICENSE)); data and aggregate results use CC BY 4.0
([DATA_LICENSE.md](DATA_LICENSE.md)). The manuscript is outside those licenses.
