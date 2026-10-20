# Confirmatory execution after the resource/reference freeze

20 October 2026. Authorization: continue the pending 3,840 comparative runs.
Scientific parent, original generator, selected parents, four horizons, scaling
implementations, budget mapping and submission files remain unchanged. This
document implements `PROTOCOL.md` after `CONFIRMATION_PREREQUISITES_FROZEN.json`.

## Fixed design and resources

40 generated parents, four horizons (24/72/168/360), three seeds (401/457/503),
two solvers and four policies produce 3,840 distinct assignments. Exactly 24
belong to the independently infeasible Full/106/168-hour diagnostic; retain all
of them but exclude their nonexistent primal-quality endpoint. The other 3,816
use the 159 already acquired exact feasible references, common to all policies.
They are not assumed MILP optima. No reference is reacquired from policy outcomes.

480 blocks keep the eight solver/policy assignments of each model/seed in one
compute allocation. A fixed pseudorandom order (seed 2026102017) permutes both
blocks and their assignments. No runtime or outcome determines their order.
The first block is submitted separately as part of these same 3,840 assignments;
its successful execution and replay release the remaining 479 blocks. This is
an infrastructure gate, independent of which policies attain the primal target.
One block and one native MIP process run at a time. Each uses four solver
threads, 8 GiB, one BLAS thread and the fixed Haswell kernel. The serial block
replay uses no optimizer. No heavy processing runs on login; transfer port is
10022, without compression. Mail notifications remain disabled.

All four policies share the frozen cap within each family/horizon/solver.
Defaults are 60 s, with Full/360/CPLEX=120 s, SG/360/Gurobi=120 s and
Full/360/Gurobi=300 s. The last stratum did not attain the operational 80%
Base-stop target and keeps explicit censoring. Native requested gap is 0.001;
native primal and integer tolerances stay 1e-6 and 1e-9. Gurobi's numerical
control is L2-NF3; CPLEX's is L2-NumEmphasis. These controls are not asserted
equivalent. Scaling and presolve retain the pilot's automatic native settings.

Each fresh process regenerates the unmodified Base and checks its frozen hash,
selects and exports the frozen row policy, verifies the export hash, checks
native import and saves every incumbent/final vector, native log and parameter
record. The execution wrapper measures the complete process separately from
the solve and the postsolve verified-availability clock. The queue, environment
installation, resource calibration and common-reference acquisition are separate.

## Accuracy, quality and failure accounting

Acceptance uses the original mapped physical budgets (0.01 MW, 100 m3), raw and
integer-rounded points, integer distance <=1e-9, exact rounded bounds and the
remaining rows' relative backward error <=1e-6. Keep every explicitly written
finite bound, including values a native reader treats as an infinity sentinel.
This implements the written-bound interpretation already verified at reference
closure; it changes no benchmark, row factor or physical mapping. In particular,
unmapped Rio Negro activation rows do not acquire a 100 m3 physical contract.

The common cost target is C_ref + binary64(0.001)*max(1,abs(C_ref)), evaluated
exactly from the original coefficients and rounded integer coordinates.
Primary comparison is Budget-L2/L2 separately by solver. Its primary endpoint
is postsolve verified availability with PAR2: successful targets use their
measured verified-availability time; unattained targets use twice the declared
solve cap plus measured preparation. This is retrospective postsolve verification,
not online certified stopping. Store discovery time separately.

Independent replay recomputes all costs and quality decisions from saved vectors;
eligible and final candidates receive complete residual/domain audits. It checks
the first acceptable index, reference hashes and exact feasibility, exported
reference feasibility and conditional bound-contradiction flags. Actual timing
measurements are checked for order, not invented by replay. Acceptance does not
validate branch-and-bound bounds or certify optimality.

Retain abstentions, native time limits, errors and every original assignment.
There are no automatic retries, overwritten attempts, changed seeds or easier
replacement models. Process the remaining jobs of an allocation after an
individual failure and report its exit code. A block whose replay fails remains
unverified. An error without a valid measured preparation time has unavailable
PAR2, not an imputed value. Do not publish the primary comparison from a partial
or failed campaign: final policy analysis requires all 480 replay reports to
pass. Intermediate monitoring reports operational completion and failures only.

## Analysis and automatic closure

Report paired geometric means for PAR2, complete-process time and native work,
success counts and conditional common-success verified-availability times.
Native work remains censored and is not a same-quality or optimality comparison;
Gurobi work and CPLEX ticks are never pooled. Report zero/unavailable denominators
instead of adding arbitrary shifts. Secondary comparisons use Base and each
solver's numerical control. Family and horizon strata are explicit.

For the primary Budget-L2/L2 comparison, use 100,000 whole-parent bootstrap
resamples with fixed seed 2026102021 and deterministic solver/stratum offsets.
Keep all horizons, seeds and the common diagnostic mask of a selected parent
together. Resampled means retain the original observation weights through sums
and counts; the diagnostic parent's shorter eligible block is not filled in.
Give marginal percentile 95% intervals on log ratios and paired success-rate
differences. Common-success intervals condition on that observed subset and
report its denominator. Parents with no common-success pair remain in the
resampling frame; replicas with zero usable pairs are counted as undefined.
No equivalence or simultaneous-coverage claim is made.

Simple L2 and Budget-L2 representations are identical under the frozen map;
their timing differences measure overhead/stability, not a benefit of changing
factors. Parents are historical-component recombinations, with documented prior
policy exposure. The bootstrap does not make them new independent observed data.

After the array, consolidate all identities and block replays, analyze only a
fully verified campaign, and seal all raw artifacts on a compute node. Frozen
source hashes and immediate Slurm receipts prevent accidental duplicate launch.
The gate first repeats saved-candidate arithmetic checks, the complete reference
closure and two 2,501-variable continuous license probes (two technical LP calls,
zero extra MIPs, excluded from benchmark observations). No scientific conclusion
is incorporated into the manuscript automatically.
