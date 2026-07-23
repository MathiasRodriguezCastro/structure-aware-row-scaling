# CPLEX direct-control batches

## Status of `simple-cplex-1pct`: NOT a paper result

This batch was measured on a local workstation (13th Gen Intel Core i7-13620H,
16 threads), **not** on ClusterUY. The manuscript declares a single computational
environment in `tab:computational-environment` — ClusterUY, partition `ute`, Intel
Xeon Gold 6138 — and every timing result it reports comes from there. Timings taken
on different hardware are not comparable to that campaign and must not be pooled
with it, quoted beside it, or used to claim a cross-solver ordering.

The batch is kept because it did useful work that does not depend on the hardware:

* it validated `scripts/flat_control_cplex.py` end to end against real CPLEX output;
* it exposed two reporting bugs that would each have put a wrong number in the
  paper — a reversed ratio direction (the module computes `log(Flat/SA)` but
  reports `SA/Flat`) and a Benjamini–Hochberg adjustment taken from the
  solver-time p-value while printed beside the total-time effect;
* it established that CPLEX populates `dettime_ticks` but neither `work_units`
  nor the own-incumbent fixed-LP diagnostic, so those endpoints are unavailable
  under CPLEX and the analysis has to report them as such;
* it revealed a build confound: preprocessing is identical C++ in both campaigns
  yet its median is 0.0745 s in the Gurobi batches and 0.0156 s here, a factor of
  4.8, because those batches used the diagnostic build and this one the release
  build. Any cross-campaign comparison has to hold the build fixed as well as the
  hardware.

## What replaces it

`cluster/run_flat_cplex.slurm` runs all six class-by-tolerance cells on ClusterUY
with one build, one machine type and one set of flags. Its output is the batch the
paper may cite. Until those cells land, no cross-solver claim is made in the text.
