# Hidden integer aggregates from dominant row directions

Working mathematics, 13 September 2026. This is a proposed research direction,
not a novelty or submission-readiness claim. All statements concern bounded
integer variables; extension to mixed continuous blocks requires additional care.

## Exact certificate independent of discovery

Let `P_Z = {z in Z^n : l <= z <= u, Az <= b}`, with finite integer bounds and
exact rational matrix data. Propose any nonzero primitive integer vector `v`.
For every selected row choose any rational number `alpha_i` and define
`e_i = a_i - alpha_i v` exactly. Set

```
m_i = sum_j min(e_ij*l_j, e_ij*u_j).
```

For every `z in P_Z`,

```
alpha_i v'z <= b_i - m_i.
```

Consequently a positive `alpha_i` certifies the integer upper bound
`U_i = floor((b_i-m_i)/alpha_i)`, while a negative `alpha_i` certifies the
integer lower bound `L_i = ceil((b_i-m_i)/alpha_i)`. Rows with zero `alpha_i`
give no bound on this aggregate. Intersect these with the natural bounds
`L_box = sum min(v_j*l_j,v_j*u_j)` and
`U_box = sum max(v_j*l_j,v_j*u_j)`. Denote the resulting interval by `[L,U]`.

These are sufficient bounds, not necessarily the tightest feasible aggregate
range. Incorrect heuristic discovery cannot invalidate them: the residuals and
inequalities are independently checkable using rational arithmetic.

* `L > U` proves integer infeasibility.
* `L = U = k` proves the hidden equality `v'z = k`.
* Otherwise the interval is a certified domain for an aggregate variable.

## Exact singleton reformulation

If the equality is certified, replace selected rows by

```
v'z = k,
e_i'z <= b_i - alpha_i*k.
```

Keep all other rows, bounds, objectives and variable types. This preserves the
integer feasible set in the original variables: original integer points satisfy
the inferred equality and hence each residual row; conversely, summing the
equality times `alpha_i` and the residual row reconstructs the original row.
The new continuous relaxation can be strictly smaller. It is an integer-valid
reformulation, not positive row scaling or an LP-equivalent operation.

If `A` is integral and `alpha_i` integral, residual coefficients remain integral
and RHS can be floored exactly. This is useful for avoiding large coefficient
denominators. Primitive normalization of `v` removes avoidable divisibility;
if a nonprimitive vector is retained then `v'z` belongs to a known lattice and
the bounds should be rounded to that lattice rather than merely to integers.

## Why the generator magnitude is unnecessary

For the generated pair `a_1 = Mv+u`, `a_2=-Mv+w`, the existing baseline uses the
metadata `M` to recover `v,u,w`. The certificate above only needs a proposed
integer direction `v`. Any nearby scales `alpha_1`, `alpha_2` that produce
sufficiently small residuals work. Once `v'z=0` is certified, the terms
`alpha_i v'z` vanish identically. There is no need to recover the original
decomposition or to know the true `M`.

For example, if `l=0,u=1`, `alpha_1>0`, `alpha_2<0`, and

```
alpha_1 + sum_j min(e_1j,0) > b_1,
-alpha_2 + sum_j min(e_2j,0) > b_2,
```

then `v'z >= 1` and `v'z <= -1` are impossible, respectively. The certified
equality is `v'z=0`. The first two displayed interval formulas generalize this
special case to asymmetric magnitudes, nonzero integer aggregate levels,
general bounded integer domains and more than two rows.

## Candidate discovery and scale selection

Discovery should be separated from proof. Normalize each row by a deterministic
large pivot and approximate its coordinate ratios by small-denominator
rationals; clear denominators and divide by the coordinate GCD. Rows near the
same projective direction provide corroboration. Pairing must be insensitive to
row order and should allow opposite signs and unequal magnitudes.

An approximate candidate is acceptable only after the exact interval test. A
denominator or coordinate cap is needed to stop arbitrary rational rows being
encoded as enormous exact integer vectors. Such a cap is a discovery heuristic,
not a mathematical assumption for validity.

For a fixed `v`, a natural scale minimizes the residual activity range

```
R(alpha) = sum_j |a_ij-alpha*v_j| * (u_j-l_j).
```

Ignoring the constant terms with `v_j=0`, its minimizers are weighted medians of
the ratios `a_ij/v_j`, weighted by `|v_j|*(u_j-l_j)`. These can be computed and
compared exactly. If integral scales are desired, evaluate the floor and ceiling
of a weighted-median minimizer. This criterion reduces coefficient activity;
it does not necessarily maximize the aggregate-bound certificate margin.

### A quantified recovery condition

Suppose a row has an unknown representation `a=alpha*v+e`, with primitive
integer `v`, `B=||v||_inf`, `||e||_inf <= E`, and `|alpha|*B>E`. Choose a pivot
`p` with `|v_p|=B`. Then

```
|a_j/a_p - v_j/v_p|
 = |e_j*v_p-e_p*v_j| / (|v_p|*|alpha*v_p+e_p|)
 <= 2E / (|alpha|*B-E).
```

For a denominator cap `Q >= B`, if the last quantity is strictly smaller than
`1/(2Q^2)`, each reduced rational `v_j/v_p` is the unique nearest rational with
denominator at most `Q`. Indeed, two distinct such rationals differ by at least
`1/Q^2`. Clearing denominators and taking a coordinate GCD therefore recovers
`v` up to sign. A sufficient condition with `Q=B` is
`|alpha| > 4EB + E/B`. This bound is conservative.

The pivot used by an implementation must be justified or tried among candidates:
largest observed `|a_p|` need not correspond to largest `|v_p|` without a
separation condition. Trying every pivot is sufficient for this recovery
statement, and trying a few largest entries is a heuristic. The unknown cap
can be swept over a prescribed finite grid; successful exact certificates are
valid even outside this sufficient recovery regime. Increasing the denominator
cap indefinitely can make approximate recovery worse by fitting the residuals.

### Strongest certificate from one row and one aggregate threshold

To certify `v'z <= k`, it suffices to exclude the continuous box slice
`v'x >= k+1`. For any `alpha >= 0`, define

```
F_k(alpha) = alpha*(k+1)
            + sum_j min((a_j-alpha*v_j)*l_j,
                        (a_j-alpha*v_j)*u_j).
```

If `F_k(alpha)>b`, every integer point with `v'z>=k+1` violates the row.
The best such lower bound equals

```
max_{alpha>=0} F_k(alpha)
 = min {a'x : l<=x<=u, v'x>=k+1},
```

whenever the slice is nonempty. This is ordinary LP strong duality for the
single aggregate constraint. The maximum can be found at `alpha=0` or a
nonnegative breakpoint `a_j/v_j` (`v_j != 0`), apart from a constant unbounded
tail whose value is attained at its endpoint. If the slice is empty the box
alone excludes it. Thus, for a proposed `v`, exact certificate-scale optimization
needs only linearly many candidate scales per threshold; sorting breakpoints
supports faster batched evaluation. Negative aggregate thresholds follow by
replacing `v` by `-v`.

This is stronger than choosing the residual-minimizing scale and then taking
the induced integer bound. It remains a single-row bound: joint use of several
rows can be stronger. A rational feasible dual solution for an LP maximizing
`v'x` over all original rows and bounds can also certify an aggregate upper
bound, but that invokes a more expensive and less structurally specialized
procedure. Neither LP duality nor this fractional-knapsack calculation is a
novelty claim.

### Invariances and exact data

Under positive exact row multiplication by `s`, projective ratios are unchanged;
choosing `alpha_new=s*alpha` gives `e_new=s*e` and exactly the same certified
aggregate bound. Thus the mathematics tolerates arbitrary unequal positive
scales on the rows. Restricting the fitted scales to integers does not itself
preserve this invariance unless rows are first put in a canonical integral
normalization. Discovery should compare invariant ratio-based candidates and
certification should use the actual exact rational input data.

An arbitrary floating multiplication followed by rounding is not an exact row
reemission. It can alter the integer feasible set before our method sees it.
Robustness experiments should either use exact representable factors, or state
that the rounded data define a new input model and check that model exactly.
Permutation of rows only changes search order; permutation of columns should
permute the discovered direction (up to a chosen sign convention). A pivot
tie-break based on column position can change heuristic success under a column
permutation, so including all tied largest pivots is a useful guard.

## Nonsingleton ranges

### Single-row compression without fixing the aggregate

Let `a,b,v,alpha,l,u` be integral, `alpha>0`, and `a=alpha*v+e`.
Write `L=min_box e'z`, `U=max_box e'z`, `k=floor((b-L)/alpha)`, and
`tau=b-alpha*k`. Then `L<=tau<L+alpha`. If `alpha>=U-tau`, the original
integer row has exactly three regimes:

* `v'z<=k-1`: always satisfied, because `alpha*(v'z-k)+e'z<=-alpha+U<=tau`.
* `v'z=k`: satisfied exactly when `e'z<=tau`.
* `v'z>=k+1`: always violated, because `alpha*(v'z-k)+e'z>=alpha+L>tau`.

If `tau>=U`, this is precisely the aggregate bound `v'z<=k`.
Otherwise set `beta=max(U-tau,tau-L+1)`. Integrality implies
`1<=beta<=alpha` and `beta<=U-L`. Replacing the row by
`(beta*v+e)'z<=beta*k+tau` preserves all integer points in the box: the same
three regimes apply, including the strict exclusion above `k`. This needs
neither an opposing row nor a unique aggregate value. The implemented reducer
uses only matrix entries and finite integer bounds; enumeration is confined
to independent validation. Clearing rational coefficient denominators and
dividing by their GCD, then flooring the scaled RHS, is a valid preliminary
operation on pure integer rows.

This is an elementary structured coefficient reduction, with substantial older
precedents; deriving this formula does not establish publication novelty. It
preserves the number and meaning of variables and uses one replacement row.
The continuous relaxations can be incomparable. The exact-arithmetic certificate
and exact binary64 representability check must both pass before export.

For example, `M*z1+(M+1)*z2<=M` is equivalent over binary points to
`z1+2*z2<=1`. The original exact feasible point `(0,M/(M+1))` rounds to the
infeasible point `(0,1)` whenever the rounding radius is at least `1/(M+1)`.
Every positive row scaling retains this obstruction. The replacement satisfies
the conditional unit-gap guarantee whenever `epsilon+3*eta<1`.

### A strengthening variant (derived, not computationally evaluated)

In the nontrivial case `tau<U`, add `v'z<=k` and take `beta=U-tau` in the
replacement row. All original integer points satisfy these two rows, and
conversely they imply the original row even continuously: writing `t=v'x-k`,
the original residual is the replacement residual plus `(alpha-beta)*t<=0`.
This variant therefore strengthens the original box relaxation. It uses an
extra row and is not the formulation evaluated in the saved experiments.

### Simple rounded-grid recovery and coefficient bounds

Suppose `a=alpha*v+e` is an integral decomposition on a binary box, with
`alpha>0`, primitive `v`, `B=||v||_inf>=1`, and `E=||e||_inf`.
If `alpha>4E+E/B`, every largest observed coefficient has a pivot with
`|v_p|=B` (since `alpha>2E`). Moreover,

```
|B*a_j/a_p - B*v_j/v_p| <= 2BE/(alpha*B-E) < 1/2.
```

Consequently rounding `B*a/a_p` recovers `v` up to sign. A simple grid of all
integer multipliers `1,...,Q`, with `Q>=B`, contains this candidate. Sparse
power-of-two grids need not contain it. Rational approximation is therefore
not essential to this recovery guarantee or to the experimental improvement.

Every weighted-median fitted scale lies within `E` of `alpha`, as do its
integer floor and ceiling, because `alpha,E` are integral. Thus the new
residual is bounded coordinatewise by `E_star=E*(B+1)`. If in addition
`alpha-E>=n*E_star`, each such positive fitted scale dominates its residual
activity range, so the compression condition holds for every integer RHS.
The resulting coefficient bound is

```
||a_new||_inf <= max(B,E_star*(n*B+1)),
```

independent of the original dominant magnitude. This is a guarantee for the
candidate certificate; the implementation additionally skips already unit-gap
safe rows and requires a factor-two score reduction. The grid's `Q` dependence
is a numerical-parameter dependence, not polynomial time in `log Q`. For fixed
`Q`, candidate generation and certification use polynomially many exact
arithmetic operations in the sparse row length and input bit length.

For any integral replacement `(c,d)`, a returned point `x` with integer rounding
`z`, `||x-z||_inf<=eta`, and `c'x-d<=epsilon` has `c'z<=d` whenever
`epsilon+eta*||c||_1<1`. This follows from the integral violation gap and does
not certify the solver's dual bound. Applying the displayed coefficient bound
gives a sufficient contract independent of `alpha` on this structured family.
General magnitude-independent weight compression is already classical
(Frank--Tardos); the bound here only describes this restricted decomposition.

Introduce a bounded integer `y=v'z`, `L <= y <= U`, and write

```
e_i'z + alpha_i*y <= b_i.
```

This is an exact extended formulation even for arbitrary continuous `y` when
the equality `y=v'z` is retained, because `z` is integral. Declaring `y` integer
nevertheless exposes a branching object with a small certified domain. It
concentrates the large coefficients into one column but does not eliminate them
and is not automatically numerically better.

If the range is small, disaggregate over its integer values. For binary `z`, let
`delta_k` be binary, `sum_k delta_k=1`, and introduce nonnegative continuous
`z^k` with `z=sum_k z^k`, `0<=z^k<=delta_k`, `v'z^k=k*delta_k`, and

```
e_i'z^k <= (b_i-alpha_i*k)*delta_k.
```

Keeping `z` binary makes this exact: the chosen branch has `z^k=z` and all
others zero. A continuous relaxation gives the disjunctive hull of the branch
polyhedra, which can strengthen the original relaxation. However, RHS values
`b_i-alpha_i*k` can remain large away from a central branch. Size is linear in
`U-L+1`; this is classical disjunctive reformulation, not a novelty claim.

## Current boundaries

This direction can recover structure unavailable to magnitude-only row scaling,
but success on generated nearparallel pairs alone does not establish novelty or
practical value. It must be compared against general solver presolve, GCD/RHS
strengthening, coefficient reduction, aggregate detection, and the existing
generator-aware reconstruction. Harder tests need perturbed row ratios,
unknown row groups, nonzero aggregate levels, general bounds, higher-rank
dominant structure and models that do not have a hidden singleton aggregate.

Do not infer that reduced coefficient range certifies solver optimality or even
that the transformed floating model implements every exact rational row. Export
rounding requires its own equivalence or safe-rounding argument, and returned
integer assignments must still be checked in the original model.
