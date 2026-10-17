# Matched IF1 control and full workflow timing

Read [RESULTADOS.md](RESULTADOS.md), the [PDF note](workflow-note.pdf) and the
[frozen protocol](PROTOCOL.md). Principal data: twelve complete workflows on the
known instance046, L2/Budget-L2 × IF0/IF1 × seeds 11/23/47. The first twelve-call
pass and its independent validation remain in `first-pass/`; a binding-array copy
in its import checker was corrected before repeating all treatments. Both passes
have identical native endpoints and saved points. Total: 24 MILP calls, no new LPs.

The generator and scaled exports match the historical binary64 files exactly.
The main timing covers a fresh Python process, original C++ input/construction,
selection/export, import, solve, verification and persistence. Construction and
Base serialization form one timed stage. The machine was shared; timing is a
prototype cost measurement, not a general performance claim.

IF1 does not change the six paired outcomes. Budget-L2 reduces the activation
residual substantially at higher work, but retains two refuted lower bounds of
three. This is one retrospective case, with original-unit study budgets, not an
operator standard, a new general algorithm or global optimality certification.

From the root of the expanded artifact, with research dependencies installed:

```bash
OPENBLAS_NUM_THREADS=1 python3 exploration/oms-if1-workflow-20261015/independent_check.py
python3 exploration/oms-if1-workflow-20261015/write_report.py
python3 -m pytest -q exploration/oms-if1-workflow-20261015/test_verification.py
```

These commands read stored points and exact feasible witnesses without optimizing
or requiring a commercial license. HiGHS is used only as a model reader. The
package validator blocks solver calls, commercial optimizer imports and external
processes during numerical replay. It also rebuilds the PDF separately.

`study.py prepare` and `study.py run` document and implement the executed workflow;
they refuse to overwrite frozen designs or run folders. Fresh resolution also
requires the separately built solver-free C++ executable and Gurobi 13.0.2/license.
The source and recorded binary hash are retained; the executable is not distributed.
Exact witness acquisition and generator compilation are offline costs, excluded
from the measured workflow and explicitly declared. No new exact LP was needed.
