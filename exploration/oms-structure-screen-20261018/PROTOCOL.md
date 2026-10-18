# Structural screening before solver outcomes

Registered 2026-10-18. This exploration is separate from the frozen OMS submission.
No optimization outcomes are used to choose instances.

## Questions

1. Do native, independently supplied block-angular MIPs activate the coupling stage?
2. Do explicit accuracy budgets change its factors, and are their intervals feasible?
3. Does a conditioning advantage survive a specified equilibration surrogate?
4. Only then: is there a verified computational advantage over strong controls?

The residual-transfer contracts do not require block structure. The triangular spectral
proposition does require identity local blocks and an identity aggregate block. Network
incidence blocks do not satisfy those assumptions, and row scaling cannot supply them.

## Sources and selection, fixed before solving

- CommaLAB R fixed-charge multicommodity design: the lexicographically first file in
  each of the first six size classes R01,...,R06. Preserve native demands, costs and
  capacities; no artificial unit perturbations and no demand-based removal of arcs.
- CommaLAB Gunluk capacity expansion: inventory all native files; choose the first
  two files in each of the three published groups (six models), without outcome data.
- SIPLIB SSLP: inspect the native first-/second-stage incidence. Do not call shared
  first-stage columns genuine coupling rows between distinct recourse blocks. Do not
  silently introduce variable copies or nonanticipativity rows.

The two network collections have different formulations and provenance; they do not
establish generalization across two application domains. Retain source archives and hashes.

## Screening

Record local block and linking row counts, column ownership, coefficient range,
row-norm range, local/coupling factor changes, coefficient vetoes, and compatibility.
Use the final kernel definitions: Base; local-GM/coupling-L2 Role-Hybrid; Flat-L2;
coefficient-only row-Ruiz with four half-steps. Identity band [1/2,2] and coefficient
window [1e-9,1e9]. RHS is scaled but excluded from kernel norms.

Accuracy study goals are absolute original-flow-unit budgets 1e-3, 1e-5 and 1e-7,
not operational standards. Exported residual hypothesis epsilon=1e-6; hypothetical
integer rounding allowance uses eta=1e-9 and is kept separate from observed residuals.
Report raw-point and integer-rounded-point checks separately. An incompatible sufficient
contract is an abstention, not evidence of instance infeasibility.

Compute numerical condition measures before and after a declared power-of-two
row/column equilibration surrogate. Do not describe it as observation of proprietary
solver scaling or as a theorem about solver bases. Preserve redundant conservation
rows in exported optimization models. State any diagnostic-only row reduction explicitly.

## Bounded solver pilot (only after screening)

Gurobi 13.0.2; sequential calls; 4 threads; seed 223; Presolve=-1; ScaleFlag=-1;
MIPGap=0.01; WorkLimit=0.25; TimeLimit=10 seconds. Common IntFeasTol=1e-9.
Policies: Base, Ruiz-R4, Flat-L2, Role-Hybrid, Budget-L2 at 1e-5 if compatible,
Flat-L2 with FeasibilityTol=1e-9, Flat-L2 with NumericFocus=3, and Coupling-only.
FeasibilityTol=1e-6 unless tightened. No incumbent is called an optimum without a
certificate, and no low work figure counts as a benefit without verified delivered quality.
The pilot is exploratory; a promising outcome requires a separately registered replication.

Stop each line if its structural mechanism is absent or if all policies already attain
the goals with no distinctive benefit. Keep rejected models and negative outcomes.
Do not change the manuscript for an improvement confined to matrix diagnostics.
