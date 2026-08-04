# Length-revision move log

Baseline: commit `108d35e` (main 55 pp, SI 21 pp). After this pass: **main 52 pp, SI 23 pp**,
both compile with 0 undefined references. Marked-changes version: `paper/main_diff.pdf`
(latexdiff vs the baseline; deletions struck through, additions underlined).

The arc is preserved: motivation → theory (Props 1–3 + attribution) → SA-Mat as the recommended
method → non-identifying operational evidence → positive synthetic evidence → bounded conclusion.
Guardrails untouched: Props 1–3 and the attribution proposition; §4.3 (SA-Mat); `tab:reliability`
(original-scale verification); `tab:spectral-audit`, `tab:metadata-grid`, the stylized model;
`tab:flat-control` (kept in the body with a single main reading); "Restoring exhaustive coverage".

## Moved to the Supporting Information (new "Section S5. Relocated results tables")
Nothing deleted; every moved table is referenced from the body by its new number.

| Table | Was | Now | Body reference updated to |
|-------|-----|-----|---------------------------|
| Gurobi efficiency, 0.1 % MIPGap | body `tab:robust-gurobi-01pct-mipgap` | **Table S14** | "Table S14 (SI)" pointer |
| CPLEX efficiency, 0.1 % MIPGap  | body `tab:robust-cplex-01pct-mipgap`  | **Table S15** | "Table S15 (SI)" pointer |
| Internal-scaling comparison (§6.6) | body `tab:internal-scaling` | **Table S16** | intro pointer + split the compound `\cref` in Limitations |

SI preamble additions required by the moved tables: `siunitx` (+ the main's `\sisetup`) and the
`\methodBase/\methodRuiz/\methodRuizCols/\AvgGap` macros. SI contents paragraph in the main text
updated to "sixteen tables" and to announce Sections S3–S5.

## Compressed in place (no numbers changed that alter a conclusion)
| Location | Cut | Note |
|----------|-----|------|
| §4.2 Augmented scaling (SA-Aug) | ~30 lines | all defining equations kept; the surrogate/grid exposition condensed. SA-Aug now reads as the exploratory variant, shorter than §4.3 (recommended). |
| §6.7 reliability discussion | ~10 lines | per-cell PAR10 detail deferred to Table S9; the reversal conclusion kept. |
| §6.7 cached-metadata "cross-protocol counterfactual" | ~14 lines | kept the descriptive-only verdict and the single retained contrast. |
| §6.7 build-invariance audit | ~23 lines | kept 1204/1224 byte-identical + the last-place-float explanation; withdrew the transfer-factor prose. |
| §7 Discussion "second objection" | ~16 lines | the three sub-questions (kernel / coverage / solver) condensed; they restated §6. |

## Deleted outright
None. All detail was moved or condensed, not removed.

## Still open to reach the ~45 pp target (recommended as a careful continuation)
Reaching 45 needs the deeper back-matter work, which is delicate because it touches the arc:
- move `tab:flat-cached`, `tab:flat-absolute` (2–4 body references each) to Section S5;
- move `tab:computational-environment`, `tab:gurobi-conditioning-correlations`;
- dedup the repeated "non-identifying / noise-floor / coupling-inactive / neither-uniformly-superior"
  sentences across intro, discussion, limitations and conclusion to one intro + one conclusion mention;
- condense the Discussion (§7) and Limitations/Conclusion overlap (~340 lines with heavy repetition).

These were left for a focused voice pass so the continuous arc is checked after each cut rather
than risking it in bulk.
