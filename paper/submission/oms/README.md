# OMS local submission package

Target: **Optimization Methods and Software**. Revised 2026-10-18.
Article: **Pre-Export Row Scaling for Generated Mixed-Integer Programs: Accuracy Contracts
and Software Evaluation**.

| File | Intended role |
|---|---|
| `main_oms.pdf` | Manuscript |
| `oms-submission.zip` | Editable manuscript and supplement sources |
| `cover-letter.pdf` | Cover letter |
| `supplementary-material-1.pdf` | Supplementary Material 1: proofs, protocols and reproduction instructions |
| `reproducibility-artifact.zip` | Supplementary Material 2: source code and stored experiment data |
| `oms-delivery.zip` | Complete local package; extract before assigning individual upload roles |

`uploads/UPLOAD_INSTRUCTIONS.md` gives captions for the supplements. Supplementary Material 2
includes the exact separately supplied supplement PDF and all documented license-free audit
inputs. Bulk fixed-basis LP text and bases remain available through the archived baseline.

Build from the repository root:

```bash
make paper
make research-claims research-online-resources
python3 scripts/research/package_oms.py
python3 scripts/research/validate_oms.py
```

`VALIDATION.json` records archive checksums, compilation from extracted sources, regenerated
OMS sources and numerical audits from a clean extraction of the artifact. `SHA256SUMS`
identifies the files generated locally. The package is not a published release and does not
assert that the manuscript has been submitted.
The complete `oms-delivery.zip` includes Supplementary Material 2 and also
`REPRODUCE.md` and `REPRODUCTION-VALIDATION.json`. The latter reports `passed`
only after the clean-extraction checks succeed and identifies the inner archives
by SHA-256. A small PDF-only review ZIP is not the full reproducibility package.

The locally frozen OMS version is `v1.3.17-oms-submission`. `SNAPSHOT.json` records the
historical/new-data distinction, and `OMS_DATA_MANIFEST.json` inventories every new OMS
experiment file and required replay program/input with SHA-256. After validation,
`python3 scripts/research/freeze_oms.py` creates a non-overwriting versioned copy of the
delivery, individual supplements, metadata and validation records.

The earlier experimental baseline is `v1.2-coap-submission`, archived at
https://doi.org/10.5281/zenodo.23145294. The OMS snapshot has no separately published version DOI. [OMS_NOTES.md](../../oms/OMS_NOTES.md) records the adaptation and formatting status.
See the [checklist](SUBMISSION_CHECKLIST.md) before using the journal portal.

The v1.3.3 activation extension adds 114 nonpilot calls and 20 exact native-export feasible witnesses. Three supplementary tables retain numerical controls and preset sensitivity, including negative results. The artifact includes `exploration/oms-followup-20261014`; its checks require no commercial solver or SoPlex installation.

The v1.3.4 editorial revision brings a compact activation comparison into the main
article and retains all detailed controls in Supplementary Material 1. It moves the
older exploratory stored-run discussion to that supplement and reports the local
comparison's six-model demand-inversion-free sensitivity. No solver calls were added.

## Final checks v1.3.5

Table 11 English corrected; Section 7.9 explicitly states the higher presolve-off
solver work and remaining bound discrepancies. Cover letter unchanged. The final
package is checked from clean extractions, including PDF identity across archives
and upload files, manuscript/supplement/metadata version consistency, file inventory
checksums before and after numerical replay, and table regeneration. No new solves.

## Initialization diagnostic v1.3.6

Section 7.3 adds one explanatory paragraph on sensitivity to a common incumbent.
Supplementary Material 1, Table S14 contains the protocol, completion/work results,
offline acquisition costs, and verification limits. The artifact includes the three
known MPS inputs, frozen factors, 36 recorded MILP calls, three exact reference LPs,
15 posthoc pattern LPs and solver-free replay under
`exploration/oms-root-attribution-20261015/`. Two unknown LP outcomes are retained.
The two principal contributions, abstract, introduction and cover letter are unchanged.
No additional solver calls were made during incorporation. v1.3.5 remains frozen.

## Matched IF control and workflow v1.3.7

Section 7.9 adds a short matched IntegralityFocus=1 control. Supplementary
Material 1, Table S15 reports original-unit accuracy, bound/gap discrepancies
and full fresh-process prototype costs. Twelve principal calls and a retained
twelve-call instrumentation pass have identical native endpoints and saved points;
the import checker was made linear in vector access without changing its checks.
Both passes and independent replay are supplied under
`exploration/oms-if1-workflow-20261015/`. This is one known case on a shared machine,
with no new reference LPs or general performance claim. Abstract, introduction,
two contributions and cover letter are unchanged; v1.3.6 remains frozen.

## Editorial reconciliation v1.3.8 — 16 October 2026

No new optimization calls. Main Table 11 and Supplementary Table S12 use the
geometric mean of Budget-L2 Work (4.4847271866, displayed 4.485); Table S15 and
the workflow note use the median (4.9754950464, displayed 4.975). The per-seed
values and native settings match; the explanation is now explicit in all three
documents. `scripts/research/reconcile_oms_work.py` checks the native provenance.
The cover letter is shorter and centers the two methodological/software contributions.
All prior frozen releases and research archives are retained. The author will create
a new-version Zenodo draft and provide its reserved DOI before final deposition.

## Fully matched accuracy/remedy confirmation v1.3.9 — 16 October 2026

Table S16 supplies a six-model, two-presolve, three-seed, four-policy comparison,
with 144 terminal outcomes and one separately retained host-reboot interruption.
Complete construction-to-verification stages, original exports, saved points and
independent replay are supplied under `exploration/oms-matched-accuracy-20261016/`.
The main text adds a brief scope qualification; the cover identifies the known
presolve-off case explicitly. The introduction explains the budget-to-verification
workflow earlier. The abstract and two principal contributions are retained.
All earlier frozen releases and closed research archives remain intact. The DOI
and remote deposition remain deferred at the author's instruction.

## Reproducibility and presentation revision v1.3.10 — 16 October 2026

No new research solver calls. The fully matched 144-call comparison replaces the
old mixed-panel main Table 11; S11–S12 and S15 retain the earlier results and
geometric-mean/median reconciliation. The abstract and conclusions explicitly
localize primal recovery versus L2 to instance046 with presolve disabled. The
two principal contributions are retained. Zero detected bound/gap discrepancies
is not an optimality certificate.

The same independent stress verifier now runs on both the HiGHS/Gurobi archive
and the byte-identical-model CPLEX archive: 5,184 configurations, 432 abstentions,
4,752 historical optimizer calls and 1,152 exact dyadic export checks. S3 now
records recent local campaign hardware/timing scope. S2 calls floating-point upper
endpoints diagnostic estimates and retains rational certification for lower bounds.
The four standard audit/analysis commands are checked from a clean Material 2
extraction. Historical basis reconstruction/precision reruns additionally need
fixed-basis-exports.tar.zst from baseline DOI 10.5281/zenodo.23145294.
Earlier frozen versions and closed research archives are preserved. DOI and
remote deposition remain deferred at the author's request.

The expanded four-command audit caught two omitted stopped-campaign analysis CSVs.
They are now explicitly included and inventoried despite the bulk-directory filter.
The certificate-table generator raises on missing inputs, with two regression tests;
targeted clean replay preserves both historical tables and their counts. This is
a packaging/replay correction, not new solver evidence or exact certification of
the historical numerically screened points.

## Precision–effort revision v1.3.11 — 16 October 2026

A sensitivity fixed before solving adds 330 MILP calls, 30 contractual abstentions
and 31 exact feasible native-export witnesses. Main Section 7.9 reports the bounded
30–100 m3 regime against NF3; Supplementary Table S17 retains all budgets and adverse
outcomes. Tables S18–S19 add an isolated C++ preparation benchmark with identical
exports and exact global-LP reference intervals, without another principal method.
The broader joint row/continuous-column study remains separate from the row-scaling
claims. That revision has 35 manuscript pages, 25 supplement pages and a one-page
cover letter. Older releases and research archives remain frozen. DOI assignment
and public deposition remain deferred.

## Presentation revision v1.3.12 — 16 October 2026

No new research solver calls. The abstract and introduction foreground the existing
30–100 m3 regime under automatic presolve. Compact main Table 12 reports all seven
automatic-presolve budgets, including abstentions and adverse outcomes; S17 retains
the full two-panel sensitivity. Ratios are paired geometric means, and shared-host
complete time excludes compilation and exact-witness acquisition. The introduction,
limitations and root README now distinguish the exact optimum of original Base
instance031 from certificates of native solver outputs. The two principal
contributions and the separate status of joint row/column research are unchanged.
DOI assignment and public deposition remain deferred.

Validated layout: 36 manuscript pages, 25 supplementary pages and a one-page cover
letter. The new compact table is main Table 12.

## Scientific follow-up v1.3.13 — 17 October 2026

176 new MIP calls and eight exact-reference LP attempts are supplied with the
independent checkers, source dependencies, failed construction preflight and
seven unknown refinements. S20 reports the independent batch-scheduling transfer;
S21 delimits integer-tolerance robustness and the activation-factor path. S18
separates preparation speedups from a new complete-cycle ratio of 0.824 with
18 identical numerical endpoints. Matched L2 remains accurate in all 24 external
calls; the study does not establish unique Budget-L2 recovery over that control.
The author confirmed CAP did not support this work. DOI and remote deposit are
still deferred. Historical versions and research archives are preserved.

Validated v1.3.13 layout: 36 manuscript pages, 28 supplementary pages, one cover
page and a four-page separate research note. The rendered abstract has 191 words.

## Evidence revision v1.3.14 — 17 October 2026

No new optimizer calls. The software specification and checked workflow are
foregrounded using established residual-transfer identities. A secondary audit
checks all saved frontier cells and external control costs. Supplementary Table
S22 shows 36/36 favorable dispatch work pairs, model/seed deletion ranges and
external complete-process costs. This is descriptive robustness on known models,
not new external generalization or an explanation of internal solver mechanisms.
The two tested favorable targets are 30 and 100 m3; intermediate budgets were
not tested. Earlier frozen releases remain unchanged; the new DOI stays deferred.

Validated layout: 36 manuscript pages, 29 supplementary pages and one cover page.
The rendered abstract has 193 words; all 39 tables are regenerated from saved data.

## Directed unscaled controls v1.3.15 — 18 October 2026

The previously omitted Base and Base-tight comparisons are added at exactly the
settings and seeds of the favorable dispatch sensitivity: 36 new calls and
36 reused Budget-L2 calls. A conditional, interleaved 54-call confirmation records
complete fresh-process time without mixing it with historical measurements.
No new reference LP is required. Main Table 12 gives the unscaled and scaled
controls together; S23 gives the directed protocol, quality checks and paired
comparisons. Base also meets the numerical budgets: the new result concerns
solver effort, not unique primal recovery or external generalization. The earlier
v1.3.14 delivery and all native scientific records are preserved. The new DOI
remains deferred.

Validated v1.3.15 layout: 36 manuscript pages, 30 supplementary pages, one cover
page and a one-page control note. The abstract has 183 words. The 90 new calls
and all 126 audited points are retained; the current tables are reproducible.

## Editorial closure v1.3.16 — 18 October 2026

No new optimizer calls. Main Table 13 reports all six models' existing
interleaved complete-process times and paired ratios against Base/Base-tight;
the abstract names paired geometric means. The cover letter distinguishes lower
work from preparation overhead on inexpensive models. Optimality limitations,
native scientific records and previously frozen releases are preserved.
The complete delivery now carries the replay guide and validation report next
to both supplements; the new Zenodo version DOI remains deferred.
The layout remains 36 manuscript pages, 30 supplementary pages and one cover
page. Repeated discussion of conditioning diagnostics was consolidated to
accommodate the timing table without extending the article. The abstract is
below 200 words.

## Portal preparation correction v1.3.17 — 18 October 2026

The portal helper now accepts the manuscript's current statement that the local
snapshot has no separate Zenodo DOI, as well as the earlier wording containing
“version DOI”. Its generated form fields, declarations and source extraction
were checked on the frozen v1.3.16 before this revision. The conditioning summary
explicitly names GM scaling. Scientific records and the timing table are unchanged.
Both v1.3.15 and v1.3.16 remain preserved; the definitive delivery uses v1.3.17.
