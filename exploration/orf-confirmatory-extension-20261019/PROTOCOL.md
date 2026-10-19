# Confirmatory extension: registered preparation and data admission

19 October 2026. Scientific parent: `v1.5.0-orf-submission`, commit `2fbb5f14`.
The supplied plan initially referred to v1.4.2; both frozen submissions remain
unchanged. This branch is separate from the submission. No new outcome is added
to the paper without a subsequent scientific assessment.

## Data gate and the user's clarification

The user identified the large Simple bank and the SG-Ter-Mer/Full banks on
ClusterUY. First inventory those exact directories and their provenance. New
filenames, recombinations or cyclic shifts do not establish new observed
operational data. Distinguish generated scenarios, observed origins, previously
solved Base models and models previously used to develop scaling policies.
The existing 500-per-family pools are recombinations of historical components;
the large Simple generator additionally rotates hydrology and demand cyclically.
The large shifted bank is reserved for a separately labelled sensitivity, not
silently treated as a collection of independent observed episodes.

The available generated pools can support a confirmatory comparison conditional
on that finite generated population. This is a narrower claim than the requested
40 new observed operational datasets. Preserve this distinction in every report.
No assertion of statistical independence follows from distinct content hashes.

The provisional generated-population allocation is 14 Simple, 13 SG-Ter-Mer,
13 Full confirmatory parents, and a disjoint pilot of 3, 3 and 2 parents. Select
by a fixed salted hash of bank/family/relative filename, independent of solver
outcomes. Reserve eight pilot parents *in addition to* 40 confirmatory parents:
otherwise excluding the pilot leaves only 32 and cannot produce 3,840 calls.
Audit all candidate input hashes, original integer domains and demand coherence
before any pilot optimization. The SG-Ter-Mer pool must be the corrected version.
Exclude duplicates of the archived contract-development inputs by cleaned content,
not basename. Record shared component ancestry and all known previous solver and
policy exposure rather than claiming blindness. The earlier, discontinued
`solver-robustness-v1` campaign also applied noncontract Flat-GM, Flat-L2 and
Role-Hybrid policies to this bank. A partial archived configuration table documents
nonBase exposure for 17 of the selected 48 parents (3 pilot, 14 confirmation).
Absence from that partial table does not establish no exposure. Retain the fixed
selection; this is a registered extension under new contracts/settings and nested
horizons, not a validation on data wholly unseen by scaling research. No previous
policy outcome is used to select or replace a parent. `PRIOR_POLICY_EXPOSURE.json`
records this amendment before any new-model reference or comparative run.

## Policies and primary estimand

Freeze Base, GM, L2, Ruiz-R4, Budget-L2 and Export-Budget-L2 implementation
dependencies by SHA-256. Historical numerical constants stay fixed. Primary
policies are Base, L2, Budget-L2 and an explicitly solver-specific L2 numerical
control. Gurobi uses NumericFocus=3. CPLEX uses numerical emphasis=1, labelled
L2-NumEmphasis; it is not called NumericFocus or asserted equivalent to it.
The common contract is 100 m3 activation/water and 0.01 MW power, with exported
residual hypothesis 1e-6 and integer distance 1e-9. Unknown row units remain
outside the physical audit and are checked separately by backward error.
Unsupported generator row families or selector errors fail the preparation gate;
they do not justify silently changing a frozen policy.

Primary comparison: Budget-L2/L2, separately by solver. Four nested horizons
24/72/168/360 hours, three new solver seeds (401, 457, 503), four threads,
requested native MIP gap 0.001 and relative candidate-quality target 0.001.
The reference is an independently verified feasible witness acquired before
comparative runs by a common, separately costed procedure, never an assumed
MILP optimum. Reference acquisition failures remain explicit and are not used
to select easier parents. A gap-0.01 sensitivity is secondary, with its own costs.
Pilot starts with one seed; 8 x 4 x 4 x 2 = 256 planned assignments. Pilot can
set operational resource limits, never select the most favorable policy.
The 40-parent confirmation contains 3,840 planned assignments if all data and
reference gates pass; abstentions and setup failures remain outcomes.

## Timing, censoring and verification

Save all callback candidate vectors, final points, native logs, exact exports,
parameters, hardware and solver versions. Check actual imported matrix/RHS,
objective, bounds and domains. Compare representational equivalence in exact
arithmetic before serialization; separately quantify actual binary64 export
errors instead of asserting exact proportionality for arbitrary factors.

Retain the previous strict criterion: physical budgets at raw and rounded
points, integer distance <=1e-9, exact bounds at the rounded point and remaining
rows' relative backward error <=1e-6. The quality threshold uses the independently
verified reference cost. Tiny bound violations and any post hoc projection are
reported separately, rather than silently changing the primary endpoint.
Primal acceptance never validates a branch-and-bound lower bound.

Capture retrospective discovery and actual *postsolve* verified availability
separately. Unless a tested online verifier is implemented and registered before
the pilot, do not label retrospective callbacks as online certified stopping.
Primary PAR2 assigns an unattained target twice the declared solve limit plus
measured preparation; successful targets use actual verified availability.
Report success counts, common-success times, all-assignment PAR2, preparation,
total time and work/censoring separately. Gurobi work and CPLEX ticks are never
pooled numerically. Keep all errors, timeouts, missing references and abstentions.

Bootstrap whole parent blocks, retaining all nested horizons and seeds. Report
strata by solver, horizon and model class. Distinct parents can share historical
components; parent resampling does not eliminate that population limitation.
Use 100,000 fixed-seed resamples and marginal percentile 95% intervals on log
ratios. An interval containing one is not evidence of equivalence. No practical
equivalence claim is registered in this protocol.

## Stage gates and complementary studies

0. Verify the frozen parent's clean-extraction audit and current file hashes.
1. Inventory remote pools; select 48 parents; audit four-horizon generation and
   all primary representations without solving. Nested prefixes keep original
   initial states, hourly units and decimal values. Full models keep the same
   mathematical Bellman continuation function across horizons. This convention
   defines a dimension sensitivity, not a date-recalibrated operational forecast;
   neither the terminal curve nor initial states are cyclically shifted.
2. Attempt common feasible references, then run the 256-assignment resource pilot
   only after the data/representation and environment gates. A failed reference
   does not remove a pilot model: quality remains unknown, not a target miss, and
   the pilot still profiles resources. No confirmatory quality comparison is
   permitted without its reference. Record measured RSS and CPU hardware.
3. Freeze time/memory/concurrency from the pilot and available license capacity;
   then permit the confirmatory array. Never run optimizers or compression on login.
4. Independently replay all points, failures, witnesses and grouped summaries.

Main confirmation and a separately specified batch-scheduling transfer study
take priority over multiplying auxiliary runs. Fixed-basis conditioning must
reuse one named basis across representations. Mechanism, 480 exactly enumerated
12-binary stress instances, active/inactive coupling ablations and selector
boundary checks retain their own prespecified designs and solver-call accounting.
Do not launch 25,920 stress configurations before resolving the main data gate.

Transfers use port 10022 without remote compression. All significant processing,
including inventories of large directories, environment installation, decompression
and license probes, runs through sbatch on compute nodes. No email notifications
are enabled. Isolated releases never overwrite an existing cluster checkout.

## Technical setup accounting

The initial compute environment has Gurobi 13.0.2 but lacks highspy and the CPLEX
Python API. It also has no pip. The initial failed installation and logs are
retained. Locked CPython 3.11 wheels are downloaded locally; their outer and
internal RECORD hashes are checked during extraction on a compute node into an
isolated directory. CPLEX uses the existing full native 22.1.2 library, not a
silently substituted Community solver. Probes are not benchmark observations.
Two tiny local MIPs test native import, callbacks and the solver-specific
numerical controls before freezing the pilot runner; they are counted separately.

The 1,100-variable initial Gurobi probe did not exceed its restricted-license
size limit. The first reference array revealed that the clean container had
not inherited the explicit full-license file setting. That array and its
unstarted dependent pilot were cancelled; no comparative pilot ran. Preserve
the entire first acquisition attempt, including its valid small-model witnesses,
under `infrastructure-attempts/limited-license-6068550/`. Explicitly pass the
existing license file through Singularity's environment (never its credentials).
A fresh compute-node probe with 2,501 variables must pass for both solvers before
the retry. Repeat the same 32-reference schedule under the corrected environment;
retain and cost all initial attempts separately. There is no replacement of
parents, outcomes or policies. The 256 comparative assignments and their ordering
remain unchanged. `LICENSE_ENVIRONMENT_AMENDMENT.json` records this intervention.
