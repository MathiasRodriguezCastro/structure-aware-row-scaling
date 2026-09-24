# Final internal review — 9 September 2026

This is an internal automated research audit, not independent external peer review or a guarantee of publication. It records checks actually performed on the revised manuscript and saved evidence.

## Mathematical checks and repairs

- The post-GM block-center collapse follows by reciprocity of each row's extrema. The pooled-extrema proof and its `[1/u,u]` extension use nonzero rows and exclude coefficient filtering/window vetoes. The candidate-factor condition-number bound holds before coupling safeguards. These restrictions appear in the statements and experimental interpretation.
- The stylized coupling transformation multiplies each entire row and RHS by one factor. Earlier coefficientwise division by block scales is superseded and is not used as a proof of row-scaling equivalence.
- The triangular-model optimum follows from the extremal two-by-two SVD block; the zero-coupling case balances the two diagonal blocks. The full proof is in Online Resource 1.
- The residual interval is a conditional exact-arithmetic contract. It does not equate a solver parameter with a proven residual bound. Coefficient spread, residual budget, integer-rounding allowance and representability can independently obstruct the desired contract.
- The dyadic exponent interval includes the factor's own representability and the odd-significand and highest-bit restrictions of every coefficient and RHS. Gradual underflow and finite binary64 input data are explicit hypotheses.
- A concrete near-midpoint issue was found in the implementation: `[1e-100,5e99]` has an exact represented product slightly greater than `1/2`, although floating logarithms produce an apparent midpoint. Exact rational comparison now chooses factor 1 rather than 2. A regression test also distinguishes a genuine tie. All **3,456 saved factor selections**, including **768 dyadic configurations**, were recomputed and are unchanged. See `budget-final/current-source-factor-check.json`; frozen generating-source snapshots are preserved.
- The stale statement that dyadic factors were not used has been removed. The arbitrary-factor implementation promises exact interval admissibility, not exact multiplication or an exactly rounded floating-point minimax optimizer.

## Evidence checks

- Independent enumeration/checker: 96 models; all 3,456 unique configuration keys; 3,168 optimizer calls; 288 justified abstentions; 768 exact dyadic exports. All saved acceptance labels pass the independent reconstruction. The rounded optimum is distinguished from raw-point residual acceptance.
- Exact-optimum counts in all 18 solver/policy cells match the table and text. Budget-GM is 182/192 on HiGHS and 152/192 on Gurobi; Budget-only is 191 and 151. Budget-round verifies 48 and abstains on 144 per solver. No universal advantage is inferred.
- Matrix audit: all 1,080 whole-row checks pass at the declared floating-point tolerance. SA-Mat/Role-Hybrid byte identity is 136/180; SA-Mat/permuted scales is 165/180. Spectral ratios and the 25 independent-rank disagreements match saved results. Literal identity does not rest on rounded spectral values.
- Operational reconstruction: all 240 assigned runs are retained. Six scaled runs time out (one instance, three policies, two gaps); arithmetic mean PAR10 uses seconds on the fixed pool. Secondary Work uses the common completed pool and native 0.01-unit resolution. All 16 reported operational table entries match the generated source table.
- The activity normalization in the supplement was checked against the actual C++ implementation: `max(1,abs(rhs),sum(abs(a_j*x_j)))`. It is not the sum of those three terms. A zero-RHS normalized residual is not interpreted as a physical percentage.
- Twelve factor/verification tests and one native C++ serialization integration test passed. The separate saved-data checker passed; all 1,080 frozen LP checksums passed. Full commands/results are in `final-checks.log`.

## Archive reproduction

An initial clean-extraction test exposed a path-handling defect in the operational analyzer: relative CLI paths were compared directly with an absolute repository root. Both input/output directories are now resolved before provenance paths are recorded. The failed first attempt is retained in `package-validation-first-attempt.log`; the final package check rebuilds the C++ exporter, verifies saved results, regenerates analyses and compiles both PDFs from a new extraction. The final status is recorded in `package-validation.json`.

## Literature and presentation

Prior tolerance scaling, modeling-layer metadata, power-of-two scaling, diagonal preconditioning and exact MIP verification are explicitly credited. The final bibliography updates Hoen–Gleixner to the published CPAIOR 2025 paper (DOI `10.1007/978-3-031-95976-9_3`) and Qu et al. to Operations Research 73(3), 1479–1495 (2025). The IEEE standard metadata was checked against its official page. Primary-source audit links are retained in `literature.md` and the bibliography.

The main paper is a concise methodological contribution, not a superior-scaler claim. The dispatch campaign is a case study, and the adversarial binary experiment cannot estimate industrial failure rates. The two dyadic arms are explicitly post hoc. Intermediate runs with incorrect floating endpoints and older serializers remain available and are labeled superseded.

The main PDF, supplement, code and data form a reviewable submission candidate. Novelty/significance and acceptance remain matters for the author and journal reviewers. The author still needs to review the final assisted work before actual submission. There is no claim that external peer review has occurred.

Final clean-extraction result: all four steps passed—archive contents hashes, the complete solver-free implementation/saved-data check, all three analyses, and compilation of the article and supplement. The delivered code/data are compared with that tested extraction when the final archives are assembled. A subsequent editorial addition records the native historical solver version (Gurobi 13.0.1); the stress experiment remains 13.0.2.
