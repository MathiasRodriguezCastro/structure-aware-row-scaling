# Prior-art reassessment of the rounding-safety direction

Status: ongoing research, not an assertion of priority. Sources below were checked against publisher or author/institutional pages on 13 September 2026. The independent reviewer identified the overlaps; the root investigator retrieved the primary sources after that review was interrupted by an account usage limit.

## Direct overlaps that restrict the claims

- **Finite multiplier geometry.** Althoff, Stursberg and Buss, *Computing Reachable Sets of Hybrid Systems Using a Combination of Zonotopes and Polytopes*, Theorem 7, give a facet-normal enumeration using subsets of box-image generators. [Author/institutional manuscript](https://mediatum.ub.tum.de/doc/1287515/document.pdf). The finite family in our note is an application of this classical geometry together with the nonnegative multiplier orthant. Neither the two-row breakpoints nor the fixed-row-count arrangement should be sold as a new general polyhedral enumeration algorithm.

- **Numerically scaled certificates.** Coey, Lubin and Vielma, *Outer approximation with conic certificates for mixed-integer convex problems*, Mathematical Programming Computation 12 (2020), 249–293, Sections 3.2 and 6.3.3, explicitly treat certificate-cut scaling under positive feasibility tolerances. [Author PDF](https://juan-pablo-vielma.github.io/publications/Outer-Approximation-With-Conic.pdf), [DOI](https://doi.org/10.1007/s12532-020-00178-3). Certificate-based tolerance scaling by itself is already established.

- **Local table encodings and cuts.** Bierlee, Piessens, Guns and Stuckey, *Table Constraints for Integer Programming*, CP 2026, article 6, published 13 July 2026, compare table encodings and lazy cut generation, including an MDD flow encoding and cut shrinking/lifting. [Publisher paper and metadata](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.CP.2026.6). A proposed compiler based on local feasible binary tables must distinguish its numerical acceptance criterion from these existing encodings and cut constructions. A claim of introducing table-based strengthening for ILP would be false.

- **Automatic local tabulation.** Akgün et al., *TabID: Automatic Identification and Tabulation of Subproblems in Constraint Models*, JAIR 82 (2025), 1999–2056, automates the selection and tabulation of promising subproblems and evaluates multiple CP/SAT solvers. [Institutional record and published PDF](https://research-repository.st-andrews.ac.uk/handle/10023/31802). Generator-local compilation or selective tabulation alone cannot establish novelty.

- **Feasible rounding.** Neumann, Stein and Sudermann-Merx's granularity/inner-parallel-set program constructs points that admit feasible rounding. [Bounds on the Objective Value of Feasible Roundings](https://link.springer.com/article/10.1007/s10013-020-00393-4). Our current question instead quantifies over *all* near-binary points in a tolerance-expanded relaxation. That is a scope distinction, not evidence of priority; the earlier papers and references still need a precise theorem-by-theorem comparison.

## Boolean minimization interpretation

The following is our mathematical identification, not a finding attributed to the preceding sources. Let U be the unsafe binary centers, F the feasible centers, and D the remaining centers already excluded by the numerical contract. Selecting forbidden partial assignments is two-level Boolean minimization with U as the ON-set, F as the OFF-set, and D as the don't-care set. Prime implicants and set-cover selection are classical. A plausible distinct ingredient is the certified construction of U and D from the exported numerical contract, not the minimization machinery itself. A primary textbook/paper citation for this exact incompletely specified Boolean-function terminology remains to be added.

## What survives as a research question

The exact characterization of row-scaling remediability and the coNP-completeness result for universal near-binary acceptance have not yet been matched to a prior theorem in this search. This is **not** proof that they are new. The weighted residual threshold offers an exact quantitative diagnostic computable from the classical finite multiplier family. The remaining publication question is whether these results, with a convincing application or an additional substantive algorithmic theorem, support a focused contribution.

The synthetic balanced-direction experiment admits a direct small-coefficient integer reformulation. That mandatory control may remove the practical motivation for the partial-clause compiler on this family. Negative results must remain in the eventual account; generating more examples from the same family does not fix this limitation.
