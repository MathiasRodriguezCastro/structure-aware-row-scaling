# Hidden integer structure: prior-art and experiment audit

Research note, 13 September 2026. Primary-source search for the proposed pivot from row scaling to automatic extraction of integer balances from ill-scaled local blocks. This is a research assessment, not a claim of novelty or submission readiness.

## Decision

The winning control **already exploits matrix structure**. For rows `Mv+u` and `-Mv+w`, bounded residual activities force the integer quantity `v*z` to zero. Removing the dominant term then exposes small coefficients. Thus the negative experiment does not establish that structure is unhelpful; it establishes that the earlier rounding-guard compiler missed the most useful structure in its own test family.

Recovering a short integer direction from the numerical matrix is a sensible next experiment. It is **not, by itself, a new mathematical idea**. Decomposable knapsack problems, parallel approximation, coefficient reduction, rational presolve, and certified presolve all have substantial primary literature. A credible contribution would need a specific algorithmic or theoretical advance over that combination, plus evidence beyond the manufactured two-row family.

## Closest established work

| Work and primary source | What is already established | Consequence for our claims |
|---|---|---|
| Aardal and Lenstra, *Hard Equality Constrained Integer Knapsacks*, Mathematics of Operations Research 29(3), 724–738 (2004), [publisher](https://pubsonline.informs.org/doi/10.1287/moor.1040.0099), [author-submitted record](https://optimization-online.org/2002/11/561/) | Coefficients with decomposable arithmetic structure can defeat ordinary branch-and-bound and become easy after a lattice reformulation. | Large coefficients encoding a simple integer relation are an established mechanism, not an original example family. |
| Krishnamoorthy and Pataki, *Column basis reduction and decomposable knapsack problems*, Discrete Optimization (2009), DOI [10.1016/j.disopt.2009.01.003](https://doi.org/10.1016/j.disopt.2009.01.003), [author preprint](https://arxiv.org/abs/0807.1317), [full text](https://arxiv.org/pdf/0807.1317) | Explicitly studies `a=pM+r`, produces a unimodular rangespace reformulation, and analyzes branching in the short direction `p`. It connects short transformed columns with easy integer branching. | Neither the decomposition nor lattice-based preconditioning can be claimed as new. Include an extraction/reformulation comparator, not only scaling and GCD. |
| Pataki and Tural, *Parallel Approximation and Integer Programming Reformulation*, [author-submitted report](https://optimization-online.org/2007/12/1861/), [full text](https://optimization-online.org/wp-content/uploads/2007/12/1861.pdf), [arXiv](https://arxiv.org/abs/0807.3355) | Extracts a near-parallel integer vector without an assumed decomposition. Section 3.2 explains extraction from LLL transformation matrices; Section 4.2 discusses approximation by several integer vectors. The integer width bounds lead to branching directions. | “We do not know M or v” is insufficient as the novelty distinction. A rank-greater-than-one extension alone is also insufficient. |
| Huyer and Neumaier, *Integral Approximation of Rays and Verification of Feasibility*, Reliable Computing 10, 195–207 (2004), [publisher](https://link.springer.com/article/10.1023/B:REOM.0000032108.23609.bc) | Computes integer vectors close to given rays and uses approximate information to recover exact rational relations and verify LP feasibility or redundancy. | Heuristic numerical discovery followed by exact rational verification is an established design. |
| Bradley, Hammer and Wolsey, *Coefficient reduction for inequalities in 0–1 variables*, Mathematical Programming 7, 263–282 (1974), [author institution](https://dial.uclouvain.be/pr/boreal/object/boreal%3A85271), [author institution full text](https://calhoun.nps.edu/server/api/core/bitstreams/fea8b2bc-5e88-47c7-893a-5c0beceb6a12/content) | Characterizes inequalities with identical binary feasible points and constructs representations with smaller coefficients. | Reducing coefficient size while preserving the binary feasible set is an old objective; truth-table enumeration is a control, not a contribution. |
| Frank and Tardos, *An application of simultaneous diophantine approximation in combinatorial optimization*, Combinatorica 7, 49–65 (1987), [publisher](https://link.springer.com/article/10.1007/BF02579200) | Uses simultaneous Diophantine approximation to replace numerical weights with smaller integral weights while preserving relevant optimization decisions. The full coefficient-compression theorem should be consulted before any general existence claim. | Do not claim the first magnitude-independent coefficient compression theorem. The publisher abstract was verified; its detailed theorem has not been rederived in this audit. |
| Dietrich, Escudero and Chance, *Efficient reformulation for 0–1 programs—methods and computational results*, Discrete Applied Mathematics 42, 147–175 (1993), [publisher](https://doi.org/10.1016/0166-218X(93)90044-O) | Generalizes coefficient reduction and lifting, explicitly including pairs of knapsack constraints and several recognizable model structures. | Pairwise integer-equivalent strengthening needs a comparison to this older reformulation tradition. Only publisher abstract/metadata were accessible here. |

## Modern presolve and certification are also close

Achterberg, Bixby, Gu, Rothberg and Weninger, *Presolve Reductions in Mixed Integer Programming*, IJOC 32(2), 473–506, [published paper](https://pubsonline.informs.org/doi/10.1287/ijoc.2018.0857), [2016 full report hosted by Gurobi](https://support.gurobi.com/hc/article_attachments/37616707559057):

- Section 3.4 describes rational GCD/Euclidean reduction and integer RHS tightening.
- Section 5.2 uses “nearly parallel” for rows that become **exactly proportional after singleton columns are removed**. This differs from two dense normals with small angular separation.
- Section 5.3 replaces a row using a known equality and discusses numerical risk from large aggregation multipliers. The reported implementation avoids absolute multipliers above 1000.
- Section 5.4 obtains activity bounds from other rows and from selected local blocks before bound/coefficient strengthening.

These observations motivate testing whether an exact local certificate can safely justify a large cancellation that floating presolve avoids. They do not establish a gap in current commercial solver implementations. The report concerns Gurobi 6.5, not a verified description of all algorithms in Gurobi 13.

Gleixner, Gottwald and Hoen, *PaPILO: A Parallel Presolving Library for Integer and Linear Optimization with Multiprecision Support*, IJOC 35(6), 1329–1341 (2023), [publisher](https://pubsonline.informs.org/doi/10.1287/ijoc.2022.0171), [official source](https://github.com/scipopt/papilo): solver-independent presolve with multiprecision/rational arithmetic already exists. A rational PaPILO comparison is more informative than asserting that commercial floating presolve is the only competing approach.

Hoen, Oertel, Gleixner and Nordström, *Certifying MIP-Based Presolve Reductions for 0–1 Integer Linear Programs*, CPAIOR 2024, [author full text](https://jakobnordstrom.se/docs/publications/CertifyingMIP-BasedPresolveReductions_CPAIOR.pdf), [author preprint](https://arxiv.org/abs/2401.09277): VeriPB certificates already verify a broad range of presolve transformations. Our certificate format should be justified by simplicity or supported numerical guarantees; “certified presolve” alone cannot be advertised as new.

The [official VIPR project](https://github.com/scipopt/vipr) verifies MIP result certificates in exact rational arithmetic. A new ad hoc JSON checker is useful experimentally but is weaker evidence of broad compatibility than expressing transformations in an established proof language.

## Exact mechanism to implement without generator metadata

The following is an elementary derivation for our research design, not a proposed novelty claim.

Let `x=(z,y)` satisfy finite bounds `l <= x <= u`, with integer `z`. Propose an integer vector `p` supported only on integer variables, and extend it with zeros on continuous variables. For any original row `a*x <= b`, select a nonzero rational `gamma` and define the exact residual `r=a-gamma*p`. Define the box activity lower bound

```
L_box(r) = sum_j min(r_j*l_j, r_j*u_j).
```

Every feasible point satisfies

```
gamma*(p*x) <= b - L_box(r).
```

A positive `gamma` supplies an upper bound for `p*x`; a negative one supplies a lower bound after reversing the inequality. Collect the strongest lower and upper bounds from available rows and ordinary variable bounds. If their integer roundings agree,

```
ceil(lower_bound) = floor(upper_bound) = t,
```

then all mixed-integer feasible points satisfy `p*z=t`. If the integer interval is empty, the model is infeasible. If it contains several integers, no equality may be inferred, although the direction can still support branching or a disjunction.

Once the equality is proved, replace any row by

```
(a-gamma*p)*x <= b-gamma*t
```

while retaining `p*z=t`. This preserves the mixed-integer feasible set exactly, with the same variables and objective. Unlike a column basis transformation, it does not change binary variable semantics or automatically densify their bounds. It generally changes the LP relaxation through the inferred integer equality.

The certificate needs only the exact input coefficients/bounds, integer `p`, rational `gamma`, exact residuals, activity bounds, and `t`. It does not need the hidden generator scale `M`, its original `v`, or a claim that these latent parameters are identifiable. A wrong guessed direction is harmless when the exact certificate fails and the algorithm abstains.

For the existing family, use the positive and negative dominant rows. Their bounded residuals produce `-1 < v*z < 1`, hence `v*z=0`. An automatic extractor should reproduce this result before more elaborate clauses are added.

### Candidate discovery versus acceptance

Cheap discovery can use normalized coefficient ratios and bounded-denominator reconstruction; LLL or Huyer–Neumaier-style ray approximation supplies a stronger comparator/fallback. Neither method should round away the residual in the correctness proof. Certify using the rational values represented by the actual exported binary64 input. A separate original-rational-data experiment is possible, but it must be labeled as having additional information.

Choose cancellation multipliers by minimizing residual coefficient size on the certified equality space. If multiple equalities are inferred sequentially, record dependency order. If they are inferred together, use a proof that does not assume one unproved equality to establish another.

An equality `p*z=t` with small integer `p` has a useful tolerance margin: a rounded point that violates it differs by at least one. If a solver output is within `eta_j` of its integer rounding and its equality residual is at most `epsilon`, then

```
epsilon + sum_j |p_j|*eta_j < 1
```

is enough to force the rounded equality. After coefficient reduction, apply the same lattice-gap check to all small integer rows. This is a conditional rounded-feasibility guarantee, not a certification of the solver's optimality bound.

## Plausible contribution, and what would falsify it

A defensible working question is:

> Can a sparse local presolver recover and certify short integer balances from numerically difficult inequality blocks, then remove their dominant components without changing variables, cheaply enough to improve the reliability and total solve time of general MIP solvers?

This is a hypothesis. Potential value lies in the **specific sparse extraction algorithm, exact export certificate, applicability conditions, and measured coverage**, not in LLL, integer width, GCD, or Farkas reasoning individually. A theorem should delimit a recoverable family and its complexity, including binary encoding length. A runtime depending exponentially on local block size needs to be stated honestly.

The present two-row family is only a unit/control experiment: the known-structure baseline solves all its held-out instances. Matching that baseline automatically is progress but not evidence of a publishable advance. It would become more credible if the method worked on heterogeneous signed blocks with independent row reemissions, nonzero target balances, mixed continuous residuals, missing row pairs, and partially recoverable multidimensional structure.

Avoid manufacturing only models whose answer was planted specifically for the proposed extractor. Include negatives with angular similarity but no valid integer equality, and models near the dominance threshold where the only valid action is abstention or an integer interval. Include real or established public benchmark models and report how often useful structure occurs. No useful detection outside the bespoke family would sharply limit the paper's scope.

Required controls include original solver presolve, scaling, GCD/coefficient strengthening, the known-structure oracle, simple ratio reconstruction, an established lattice extraction method, rational PaPILO if available, and stronger local formulations where affordable. Separate extraction time, certificate verification time, exported model size, solver time, exact feasibility, and independently known optimality. Keep failed detection, abstention and solver failures in the denominators.

## Search limits and open checks

The search verified primary author/publisher sources and accessible full sections where identified above. It is not an exhaustive novelty review. In particular, the precise relationship to older paired-knapsack coefficient reduction, practical simultaneous-approximation implementations, and recent rational presolve needs more detailed comparison before a novelty statement.

The interpretation above is that a useful engineering/theory contribution remains possible, but “infer v without M and check it exactly” is already covered in spirit by several existing lines of work. Any manuscript should foreground the concrete improvement that survives the comparator experiments.
