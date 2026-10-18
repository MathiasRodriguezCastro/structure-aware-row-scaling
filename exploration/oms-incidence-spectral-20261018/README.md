# Bounded spectral extension, separate from OMS

The native-numerics campaign remains the practical priority. This note studies
the actual incidence-block structure without turning local blocks into identities.
It does not claim a new competitive scaling algorithm or bibliographic priority.

Results developed here:

1. The commodity mean/contrast identity holds for **positive** singular values,
   with multiplicities. For general rectangular blocks the usual economy SVD
   requires additional zero bookkeeping; the column-Gram eigenvalue identity is
   unambiguous and includes every zero.
2. For nonzero arbitrary B, C=I, D=dI, d>0, K>=1, the unique best common coupling
   factor is gamma*=sqrt(sigma_min_positive(B)*sigma_max(B)/(K+d^2)). No local
   whitening or rank-completeness assumption on B is needed. A closed positive
   factor interval clips this optimum.
3. If D D^T is bounded between two positive scalar identities, extremal singular
   values give a sufficient comparison bound for heterogeneous capacities.
   Exact rational certificates on the six native R matrices check improvement
   of an admissible common dyadic coupling factor over their unscaled matrices.

These are statements about matrix conditioning, not basis stability, optimization
speed, returned-point accuracy, or optimality of a MIP solution. The uniform-D
examples are controlled mathematical tests, not additional native benchmarks.

Background includes classical optimal diagonal/block scaling, e.g.
[Boyd et al., chapter 3](https://web.stanford.edu/~boyd/lmibook/lmibook.pdf)
and [Optimal Diagonal Preconditioning](https://arxiv.org/abs/2209.00809).
The closed formula has not been established as new by this bounded source check.

Run `OPENBLAS_NUM_THREADS=1 python3 exploration/oms-incidence-spectral-20261018/check.py`
from the repository root. Dependencies: NumPy, SciPy and SymPy 1.14.0. Native R
data are the unchanged archive in `exploration/oms-structure-screen-20261018/sources/R.tgz`.
