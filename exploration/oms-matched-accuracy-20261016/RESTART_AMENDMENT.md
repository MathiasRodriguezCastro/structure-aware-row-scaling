# External restart amendment — 16 October 2026

The host rebooted at 11:42:09 local time. The 37th completed call had been
persisted at 11:41:25. Assignment 38 (instance001, auto presolve, seed 11,
L2-tight) had entered optimization but has no terminal result or saved point.
Neither runner nor worker survived. Its entire partial output and the 37-call
parent record are preserved under interrupted-attempt/, with hashes recorded
in RESTART_AMENDMENT.json. No native outcome is imputed from partial logs.

Before resuming, repeat this same interrupted assignment once and then continue
the unchanged fixed order. Keep the 37 completed results. Models, native
parameters, time limits, endpoints and frozen sources remain unchanged. This
produces 144 completed terminal comparisons and 145 total native attempts,
including one explicitly recorded external interruption. The interrupted attempt
is retained as a failed delivery, separately from solver-induced failures; it is
not an independent completed replicate. No attempt is silently discarded.

Wall timings span a reboot and differing shared-machine load; they describe
measured prototype calls and cannot support a hardware performance claim. Native
Work and within-configuration paired outcomes remain the main effort evidence.
No result-dependent treatment, parameter selection or new experiment is added.
