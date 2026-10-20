# Scope of the frozen physical contracts

The continuation preserves the original row-to-unit map. A statement that
"all budgets pass" refers to the mapped physical rows, not to a 100 m3 budget
on every row of the dispatch model. Other rows retain the registered relative
backward-error check; variable bounds and integer distances have their own checks.

`MODEL_PREPARATION.json` records the mapped row counts and physical groups for
each model. The frozen implementation protects power identities/demand,
generation definitions, production envelopes, water balances and, when present,
the four named Salto Grande `activacion_[1-4]` rows per period. It does not map
the Río Negro `restriccion_varphi*` families to physical activation budgets.
Those families therefore remain in the separate backward-error check. They
must not be described as covered by the 100 m3 activation contract.

The Simple L2 and Budget-L2 exports are identical under this frozen map. This is
a control for stability and overhead, not evidence of a contract benefit on Río
Negro activation rows. The map is not extended during this registered campaign,
which would change policy representations after the pilot.

Common-reference verification has a broader and stricter role: every original
row, explicit finite written bound and integer domain is checked exactly,
including rows outside the physical-contract map. The scope distinction does
not weaken the reference feasibility certificate. It does limit claims about
which physical residual budgets are enforced on returned floating-point candidates.
