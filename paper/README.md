# OMS manuscript

**Pre-Export Row Scaling for Generated Mixed-Integer Programs: Accuracy Contracts and
Software Evaluation**, by Mathias Rodríguez Castro, prepared for Optimization Methods and Software.

From the repository root:

```bash
make paper
make research-online-resources
make research-claims
python3 scripts/research/package_oms.py
python3 scripts/research/validate_oms.py
```

The submission PDF is `oms/main_oms.pdf`. `scripts/research/build_oms.py` generates its
source from `main.tex`, including the same abstract and body. `main.pdf` is the journal-neutral
view. Supplementary Material 1 is `supporting-information.pdf`.

The publisher's `interact.cls` and numeric `tfq.bst` are included in `oms/` with download
provenance. The journal-specific reference style and portal requirements still require
confirmation against the current author instructions: that page returned HTTP 403.
See [OMS_NOTES.md](oms/OMS_NOTES.md).

| Path | Contents |
|---|---|
| `main.tex` | Canonical manuscript, results and declarations |
| `oms/` | Current Taylor & Francis source, bibliography, figures and cover letter |
| `supporting-information.tex`, `supporting-information.pdf` | Supplementary Material 1 |
| `sections/implementation.tex` | Procedure, software components and verification responsibilities |
| `tables/`, `figs/research/`, `research-references.bib` | Experimental tables, figures and bibliography |
| `validation/` | Independent numerical-claim verification |
| `submission/oms/` | [Current packages and instructions](submission/oms/README.md) |
| `coap/` | Earlier COAP editorial files, retained as historical material |

`submission/oms/VALIDATION.json` records source-bundle compilation, checksum checks and
audits from a clean extraction of Supplementary Material 2. Its supplement PDF is identical
to the separately supplied Supplementary Material 1.

The numerical data include the archived `v1.2-coap-submission` baseline and the additional
OMS dispatch comparison, stage ablation and physical-budget audit in
`results-revision/research-audit/oms-close-20261013`. The OMS revision is
locally frozen as `v1.3.17-oms-submission` and has no new Zenodo version DOI. The default build does not regenerate the historical
COAP folder. Authorship, funding, competing interests and AI assistance remain stated in
the manuscript. The manuscript is outside the source-code and data licenses.

The activation follow-up is documented in [RESULTADOS.md](../exploration/oms-followup-20261014/RESULTADOS.md). Its 114 nonpilot calls and 20 exact feasible witnesses are supplied in the artifact and checked by `make research-oms-check`; they do not certify global MILP optima.

The current main Table 11 uses `tables/matched-main.tex`, regenerated from the
fully matched six-model comparison by `scripts/research/oms_matched_tables.py`.
The older `activation-summary.tex` remains an archived derived table; the old
measurements remain in supplementary Tables S11–S12. The four standard saved-result
audit/analysis commands are self-contained in Material 2. Reconstructing all
1,530 historical bases or rerunning their stress-sample precision calculation
additionally requires the baseline bulk archive documented in the root README.

Version v1.3.11 adds Supplementary Tables S17–S19: the fixed multi-budget study,
a C++ standalone preparation benchmark, and exact original-Base LP certificates.
Version v1.3.12 promotes the existing 30–100 m3 regime to the abstract, introduction
and main Table 12 (`tables/precision-frontier-main.tex`), without new experiments.
The compact table and full S17 table share `scripts/research/oms_frontier_tables.py`.
The canonical source remains `main.tex`; generated OMS copies must still be rebuilt
with `scripts/research/build_oms.py`.

Version v1.3.13 adds independent batch transfer (S20), matched integer-tolerance
sensitivity and activation-factor replay (S21), and complete-cycle native timings
in S18. `scripts/research/oms_followup_tables.py` generates the three new tables.
The two principal contributions remain unchanged; the abstract is shortened and
its favorable dispatch regime now explicitly states the integer tolerance.

Version v1.3.14 adds the secondary evidence audit in Supplementary Table S22:
model/seed deletion checks and all external control costs. Its solver-free
programs are under `exploration/oms-evidence-audit-20261017/`. The favorable
dispatch work result survives removal of each observed model or seed; external
complete-process time does not improve over L2. No optimizer calls are added.

Version v1.3.15 adds directed matched Base/Base-tight controls to the previously
favorable dispatch sensitivity. The original sensitivity and prior releases remain
unchanged. Main Table 12 includes the unscaled controls; Supplementary Table S23
separates work, verified numerical quality and contemporaneous full-process timing.
The comparison remains within six known models and does not demonstrate additional
primal recovery over Base or general MILP certification.

Version v1.3.16 adds no optimizer calls. Main Table 13 exposes per-model
complete-process timings from the existing interleaved study, and the abstract
identifies paired geometric means explicitly. The complete delivery includes a
reproduction guide and the successful clean-extraction validation report;
Supplementary Material 2 is included in that ZIP. The frozen v1.3.15 remains intact.

Version v1.3.17 corrects the portal helper's outdated no-DOI text check and
explicitly names GM in the condensed conditioning discussion. Existing scientific
records and numerical results are unchanged; the complete package is revalidated.
