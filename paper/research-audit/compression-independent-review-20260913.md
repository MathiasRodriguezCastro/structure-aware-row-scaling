# Independent review of integer-direction compression

13 September 2026. Scope: `integer_direction_compression.py`, its six unit
tests, and `hidden-structure-math-20260913.md`. No solver experiments were run.
This review checks mathematical validity and implementation boundaries, not
priority or publication readiness.

## Mathematical result: valid under exact integer arithmetic

Let `a,b,v,alpha,l,u` be integral, `alpha>0`, and `l<=u`. Set
`e=a-alpha*v`, `L=min_box e'z`, `U=max_box e'z`,
`k=floor((b-L)/alpha)`, and `tau=b-alpha*k`. Then
`L<=tau<=L+alpha-1`. Under `alpha>=U-tau`, the original row is:

* always satisfied at integer aggregate levels `v'z<=k-1`;
* equivalent to `e'z<=tau` at `v'z=k`;
* always violated at integer levels `v'z>=k+1`.

The first assertion follows from `alpha*(v'z-k)+e'z<=-alpha+U<=tau`.
The last follows from `alpha*(v'z-k)+e'z>=alpha+L>tau`.
These statements do not require the aggregate levels to be attainable.

If `tau>=U`, replacement by `v'z<=k` is consequently exact on the bounded
integer domain. Otherwise
`beta=max(U-tau,tau-L+1)` is an integer satisfying `1<=beta<=alpha`.
Repeating the same three-level argument proves equivalence of
`(beta*v+e)'z<=beta*k+tau`. Equality in `alpha>=U-tau` and
`beta>=U-tau` is permitted; the upper excluded level needs the strict
inequalities `alpha>tau-L` and `beta>tau-L`. The implementation has these
boundaries right when its operands are Python integers.

Clearing coefficient denominators, dividing the integer coefficient vector by
its positive GCD, and flooring the correspondingly scaled RHS is exact for
integer variables, including negative RHS and all-zero rows. Positive exact
rational row rescaling therefore gives the same canonical row. This does not
license RHS flooring for general mixed continuous rows.

## Confirmed implementation defect: accepted floating bounds break exactness

At the reviewed revision, `compress_row` checks that each bound has an integer
value but does not convert it to a Python integer. Consequently integer-valued
floating bounds pass validation and introduce floating activity bounds and
division into the purportedly exact certificate.

Reproduction with exact integer matrix input:

```python
M = 10**18
a, b = [M+1, 2*M+1], M
compress_row(a, b, lo=[0, 0], hi=[1.0, 1.0])
# Returned row: [0, 1] <= 0
```

The returned row admits `(1,0)`, which violates the original row by one.
Using `hi=[1,1]` instead returns `[1,1]<=0`, correctly excluding this point.
NumPy integer bounds also need conversion to Python integers to avoid fixed
width overflow. The appropriate repair is to validate finite integral values,
then convert all bounds to Python `int` before any arithmetic.

The completed experimental campaigns use default Python integer binary bounds
and were independently checked on all local assignments. This defect does not
invalidate those campaign results; it invalidates a broader exactness claim
for all inputs presently accepted by the public function.

Related input validation should be tightened at the same boundary:

* Require coefficient, direction, and bound vectors to have matching lengths;
  current `zip` operations otherwise silently discard entries.
* `compression_step` advertises an integer scale but only tests `alpha>0`.
  Reject nonintegral scales, and normalize supported integral scalar types.
  The public step also needs either validated integral `a,b,l,u` or an explicit
  internal-only precondition. For example, scale `1/2` on row `[1]<=0` triggers
  the `beta<=alpha` assertion instead of an input validation error.

No code was changed as part of this independent review.

## Limits that should remain explicit

Coefficient compression is integer equivalent, but its continuous relaxation
need not dominate the original one. On `[0,1]^2`, the accepted step

```
4*x + 2*y <= 3  ->  3*x + y <= 2
```

uses `v=(1,1)`, `alpha=3`, `e=(1,-1)`, and `beta=2`.
Point `(3/4,0)` satisfies only the original row; `(2/5,4/5)` satisfies only
the replacement. Thus claims of automatic LP strengthening would be false.

The integer-gap stopping test is sufficient for the stated common row and
coordinate tolerance, conditional on the model's acceptance contract. It
neither certifies a solver's optimality bound nor establishes that its actual
internal tolerance behavior obeys that contract.

The recovery argument in the mathematics note is sound. A largest observed
pivot is justified under `abs(alpha)>2*E`, since different absolute integer
entries differ by at least one. The stronger displayed rational-recovery
condition implies this separation. A cap available in the implementation must
satisfy the recovery inequality; a hypothetical cap `Q=B` need not belong to
the implemented sparse cap grid. Exact certification remains valid even when
the heuristic does not recover the generating direction.

Permutation-independent candidate enumeration does not imply identical final
output under all column permutations: ties are finally broken lexicographically
on the coefficient vector. Equivalence is preserved, but later greedy passes
and heuristic success can differ. Exact invariance should be claimed for
positive exact row rescaling, not blanket equivariance of every output.

## Checks performed

The existing six tests passed. An additional independent exhaustive check
enumerated two-dimensional integer rows in `[-3,3]^2`, RHS in `[-4,4]`,
directions in `[-2,2]^2`, and scales `1,...,4`, on integer box
`[-1,1] x [0,2]`. All 1,746 accepted steps preserved every integer assignment.
The floating-bound counterexample and the two LP non-dominance witnesses were
also reproduced directly.

## Follow-up: implementation repair verified

The root agent repaired the reported arithmetic and vector-length defects.
The re-reviewed reducer has SHA-256
`d46c6691ee74a30c9163cdccd50f4eba6d362320ec7efe460667ede380c97212`.
`exact_integer` now converts accepted integral floating, Fraction, and NumPy
values to Python integers before certificate arithmetic. `compression_step`
normalizes every scalar and vector entry and checks matching dimensions,
ordered bounds, and a positive integer scale. `compress_row` normalizes its
bounds and checks dimensions before discovery. Its matrix coefficients and RHS
still correctly enter through rational canonicalization.

All seven updated tests passed independently, including the previously failing
`10**18` example with floating and NumPy bounds. The earlier defect finding
above is historical and is resolved in this reviewed revision. No change to
the mathematics is needed.

## Follow-up: dense-grid recovery and magnitude-independent coefficients

The proposed sufficient bounds are correct with the following precise scope:
`v` is a nonzero primitive integer vector, `alpha` is a positive integer,
`a=alpha*v+e` is integral, `B=||v||_infinity`, and `E` is a nonnegative integer
upper bound on `||e||_infinity`. The domain in the coefficient bound is binary.

If `alpha>4*E+E/B`, it also exceeds `2*E`. Every index with maximum observed
`|a_p|` must then have `|v_p|=B`: a coordinate of true absolute value at most
`B-1` has observed magnitude at most `alpha*(B-1)+E`, whereas a coordinate of
true magnitude `B` has observed magnitude at least `alpha*B-E`.

For such a pivot,

```
| B*a_j/a_p - sign(v_p)*v_j |
  <= 2*B*E / (alpha*B-E) < 1/2.
```

Hence ordinary nearest-integer rounding at grid value `q=B` recovers `v` up
to sign, without a rational-approximation algorithm. The dense grid
`q=1,...,Q`, `Q>=B`, includes this candidate. Primitivity ensures the subsequent
GCD normalization retains `v`; without it, it retains the primitive direction.
The strict inequality removes rounding-tie conventions from the argument.

All nonzero-coordinate ratios `a_j/v_j` lie in
`[alpha-E,alpha+E]`. Thus every weighted-median minimizer, and its floor and
ceiling, lies in the same interval, since both endpoints are integers. Every
positive median-scale candidate `alpha_prime` satisfies
`|alpha_prime-alpha|<=E`. The new residual therefore obeys

```
||a-alpha_prime*v||_infinity <= E*(B+1) = E_star.
```

If `alpha-E>=n*E_star`, then `alpha_prime>=n*E_star` and the binary residual
activity range is at most `n*E_star`. The core compression condition consequently
holds for every integer RHS. In the non-aggregate branch, integrality and
`L<=tau<U` imply

```
beta=max(U-tau,tau-L+1) <= U-L <= n*E_star.
```

The output coefficient norm is consequently at most
`E_star*(n*B+1)`. The aggregate-bound branch has norm `B`; together this gives
`max(B,E_star*(n*B+1))`, independent of `alpha`. This includes `E=0`, when
the aggregate branch suffices. Subsequent coefficient GCD normalization cannot
increase this coefficient bound.

These statements concern candidate recovery and the core transformation on the
stated integral representation. They do not prove that the deployed heuristic
will run despite its tolerance stopping rule, accept the candidate through its
factor-two score filter, or obtain an RHS bound independent of `alpha` for
arbitrary RHS. Applying the guarantee after a different canonical normalization
requires checking its assumptions for that normalized representation. For
nonintegral `alpha` or nonintegral error bound, the integer-endpoint median
argument needs adjustment (a safe additive rounding allowance is one).

## Follow-up: primitive LP non-dominance example

The earlier `[4,2]` example is a valid core step but has a coefficient GCD that
the public row routine first removes. A cleaner example for the paper is

```
5*x + 2*y <= 3  ->  4*x + y <= 2,   0<=x,y<=1.
```

Take `v=(1,1)`, `alpha=3`, `e=(2,-1)`, `L=-1`, `U=2`, `k=1`,
`tau=0`, and `beta=2`. Both input and output coefficient vectors are primitive,
so canonicalization changes neither row. The exact point `(3/5,0)` satisfies
only the original row; `(1/4,1)` satisfies only the replacement. This is a
statement about the core theorem, not about selection by the deployment
heuristic with its tolerance and factor-two filters. It was reproduced with
the repaired `compression_step`.
