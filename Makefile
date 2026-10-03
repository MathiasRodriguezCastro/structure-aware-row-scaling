# Current research revision. The default target only lists available commands.
.DEFAULT_GOAL := help
PYTHON ?= python3
AUDIT_ROOT := results-revision/research-audit
GRID_OUT ?= $(AUDIT_ROOT)/reruns/identifiability
BUDGET_OUT ?= $(AUDIT_ROOT)/reruns/budget
BUDGET_SOLVERS ?= highs gurobi
FIXED_BASIS_ROOT := $(AUDIT_ROOT)/fixed-basis-final-20260914
FIXED_BASIS_OUT ?= $(AUDIT_ROOT)/reruns/fixed-basis
APP_BUDGET_DIR := $(AUDIT_ROOT)/application-budgets
APP_BUDGET_LP ?= $(APP_BUDGET_DIR)/caso46e-dummylp.lp.gz
APP_BUDGET_INSTANCE := data/entradas/entrada-modelo-simple/caso46e.txt

.PHONY: help paper audit-build research-check-python research-check research-analysis \
        research-budget-analysis research-matrix-analysis research-operational-analysis \
        research-fixed-basis-analysis research-fixed-basis-check research-fixed-basis \
        research-fixed-basis-precision research-application-budgets \
        research-application-export research-online-resources research-bridge \
        research-certificate-audit research-stage-ablation \
        research-grid research-budget analysis-n0 synthetic-mini sanity-check \
        research-rounding-check research-rounding-analysis \
        research-robustness-analysis

help:
	@echo "Active rounding-safety investigation (not submission-ready):"
	@echo "  make research-rounding-check    - exact certificates, witnesses and math tests"
	@echo "  make research-rounding-analysis - verify the lattice control and draw comparison"
	@echo "Current paper (no optimizer license required):"
	@echo "  make research-check-python  - mathematical tests, saved binary audit, LP hashes"
	@echo "  make research-check         - also build and test the C++ LP serializer"
	@echo "  make research-analysis      - regenerate current tables, figures and summaries"
	@echo "  make research-application-budgets - declared-budget table and its delta sweep"
	@echo "  make research-application-export  - re-export that model and compare byte by byte"
	@echo "  make research-online-resources    - audit the two Online Resources before submitting"
	@echo "  make research-bridge              - what a solver-style scaling leaves of the audit"
	@echo "  make research-certificate-audit   - solver claims contradicted by a verified point"
	@echo "  make research-stage-ablation      - historical local/coupling stage ablation"
	@echo "  make paper                  - build main and supplement PDFs with pdfLaTeX"
	@echo "  make audit-build            - isolated solver-free C++ build in code/build-audit"
	@echo "Optional fresh experiments (new output directories only):"
	@echo "  make research-fixed-basis-check - rebuild all fixed-basis matrices from LP text"
	@echo "  make research-grid          - generate/audit 1080 LPs; no optimization"
	@echo "  make research-fixed-basis   - rerun the 306-model fixed-basis audit (HiGHS)"
	@echo "  make research-budget        - rerun nine-arm stress protocol; HiGHS and Gurobi"
	@echo "    BUDGET_SOLVERS=highs       - select only the license-free HiGHS arm"
	@echo "    GRID_OUT=... BUDGET_OUT=...- choose separate rerun output paths"
	@echo "Historical targets: analysis-n0, synthetic-mini (Cbc), sanity-check"

paper:
	$(MAKE) -C paper

research-rounding-check:
	OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 $(PYTHON) -m pytest -q tests/test_joint_rounding_certificate.py tests/test_finite_safety_geometry.py tests/test_single_row_safety.py tests/test_certified_guards.py
	$(PYTHON) scripts/research/verify_guard_experiment.py --root $(AUDIT_ROOT)/guards-holdout-100-isolated
	$(PYTHON) scripts/research/verify_intrinsic_witnesses.py --root $(AUDIT_ROOT)/guards-holdout-100-isolated --out $(AUDIT_ROOT)/guards-holdout-100-isolated/intrinsic-witnesses.json

research-rounding-analysis:
	$(PYTHON) scripts/research/analyze_guard_holdout.py --root $(AUDIT_ROOT)/guards-holdout-100-isolated --control $(AUDIT_ROOT)/guards-lattice-control-100 --out paper/research-audit/guards-comparison-20260913


audit-build:
	$(MAKE) -C code BUILD_DIR=build-audit USE_GUROBI=0 USE_CPLEX=0 USE_CBC=0 USE_HEXALY=0

research-check-python:
	$(PYTHON) -m pytest -q tests/test_budget_scaling.py tests/test_robustness_analysis.py
	$(PYTHON) scripts/research/verify_saved_experiment.py --root $(AUDIT_ROOT)/budget-final
	cd $(AUDIT_ROOT)/identifiability-final && sha256sum --quiet -c checksums.sha256

research-check: audit-build research-check-python
	$(PYTHON) -m pytest -q tests/test_export_roundtrip.py

research-analysis: research-budget-analysis research-matrix-analysis research-operational-analysis \
                   research-fixed-basis-analysis research-application-budgets \
                   research-certificate-audit research-stage-ablation

# Aggregates of the solver-robustness campaign; the raw per-run records are not in the repository.
research-robustness-analysis:
	$(PYTHON) scripts/research/robustness_analysis.py || true
	$(PYTHON) scripts/research/robustness_tables.py

research-fixed-basis-analysis:
	$(PYTHON) scripts/research/analyze_fixed_basis.py --root $(FIXED_BASIS_ROOT)

research-fixed-basis-check:
	OPENBLAS_NUM_THREADS=1 $(PYTHON) scripts/research/verify_fixed_basis.py $(FIXED_BASIS_ROOT)

# Recomputes the stored precision check into a new directory (refuses to overwrite).
research-fixed-basis-precision:
	OPENBLAS_NUM_THREADS=1 $(PYTHON) scripts/research/verify_fixed_basis_precision.py --root $(FIXED_BASIS_ROOT) \
		--out $(AUDIT_ROOT)/reruns/fixed-basis-precision

research-fixed-basis: audit-build
	@test ! -e "$(FIXED_BASIS_OUT)" || { echo "Output already exists; choose a new FIXED_BASIS_OUT."; exit 1; }
	OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 $(PYTHON) scripts/research/fixed_basis_campaign.py --out "$(FIXED_BASIS_OUT)" --workers 6

research-budget-analysis:
	$(PYTHON) scripts/research/analyze_budget_experiment.py --root $(AUDIT_ROOT)/budget-final \
	    --extra-root $(AUDIT_ROOT)/budget-final-cplex \
	    --extra-classical-root $(AUDIT_ROOT)/exploration-lattice-cplex

research-matrix-analysis:
	$(PYTHON) scripts/research/analyze_identifiability.py

# Runs whose reported bound or completion certificate a verified point contradicts.
research-certificate-audit:
	$(PYTHON) scripts/research/certificate_audit.py

# Where the earlier structured rules' solver-time gain sat, from the stored ablation runs.
research-stage-ablation:
	$(PYTHON) scripts/research/stage_ablation_table.py

# Rescales every basis of the fixed-basis audit the way a solver would and recomputes kappa_1,
# plus the constructed check that such a scaling does not undo a pre-export row scaling.
BRIDGE_OUT ?= $(AUDIT_ROOT)/solver-scaling-bridge/bridge.csv
research-bridge:
	OPENBLAS_NUM_THREADS=1 $(PYTHON) scripts/research/solver_scaling_bridge.py --out $(BRIDGE_OUT)
	$(PYTHON) scripts/research/analyze_solver_scaling_bridge.py --csv $(BRIDGE_OUT)
	OPENBLAS_NUM_THREADS=1 $(PYTHON) scripts/research/equilibration_kernel_check.py

# Pre-submission audit of Online Resource 1 and 2; see the script for what it checks.
research-online-resources:
	$(PYTHON) scripts/research/audit_online_resources.py

# The declared residual contract on one dispatch model, and how far the budgets can be
# tightened before a kernel stops being admissible. Reads the stored LP; no solver.
research-application-budgets:
	$(PYTHON) scripts/research/application_budgets.py --lp $(APP_BUDGET_LP) \
	    --budgets $(APP_BUDGET_DIR)/declared-budgets.json --out $(APP_BUDGET_DIR)/caso46e.csv
	$(PYTHON) scripts/research/application_budget_sensitivity.py --lp $(APP_BUDGET_LP) \
	    --budgets $(APP_BUDGET_DIR)/declared-budgets.json --exponents -16 2 \
	    --out $(APP_BUDGET_DIR)/caso46e-sensitivity.csv
	$(PYTHON) scripts/research/application_budget_table.py
	$(PYTHON) scripts/research/application_budget_sensitivity_table.py

# Re-exports that LP from the instance with the solver-free build and checks it against the
# stored copy, so the input of the table above is traceable to the generator.
research-application-export: audit-build
	sed '/^configurarSolver/,$$d' $(APP_BUDGET_INSTANCE) > $(APP_BUDGET_DIR)/.export.in
	printf 'configurarSolver --DummyLp --timeout 60 --mipgap 0.01\ngrabar $(APP_BUDGET_DIR)/.export.lp --noConstante\nsalir\n' >> $(APP_BUDGET_DIR)/.export.in
	code/build-audit/SistemaElectrico < $(APP_BUDGET_DIR)/.export.in > /dev/null
	gzip -dc $(APP_BUDGET_LP) | cmp - $(APP_BUDGET_DIR)/.export.lp \
	    && echo "re-export matches $(APP_BUDGET_LP)"
	rm -f $(APP_BUDGET_DIR)/.export.in $(APP_BUDGET_DIR)/.export.lp

research-operational-analysis:
	$(PYTHON) scripts/audit_operational_evidence.py --source results-revision/final-variants --output $(AUDIT_ROOT)/operational --timeout 1800 --bootstrap 10000
	cp $(AUDIT_ROOT)/operational/main_table_four_cells.tex paper/tables/operational-results.tex

# Refuse to overwrite either a frozen dataset or an earlier rerun.
research-grid: audit-build
	@test ! -e "$(GRID_OUT)" || { echo "Output already exists; choose a new GRID_OUT."; exit 1; }
	$(PYTHON) scripts/audit_identifiability_grid.py --exe code/build-audit/SistemaElectrico --out "$(GRID_OUT)" --seeds 10 --seed-base 20260909 --roundtrip-export

research-budget:
	@test ! -e "$(BUDGET_OUT)" || { echo "Output already exists; choose a new BUDGET_OUT."; exit 1; }
	$(PYTHON) scripts/research/residual_budget_experiment.py --out "$(BUDGET_OUT)" --seeds 8 --start-seed 100 --solvers $(BUDGET_SOLVERS)

# Retained historical workflows; these do not reproduce the revised manuscript.
analysis-n0:
	bash scripts/run_analysis_n0.sh

synthetic-mini:
	$(MAKE) -C code BUILD_DIR=build-cbc USE_GUROBI=0 USE_CPLEX=0 USE_CBC=1 USE_HEXALY=0
	cd code && ./build-cbc/SistemaElectrico < ../data/synthetic/validacion_mini_cbc.txt
	@echo "Historical synthetic-mini metrics under code/synthetic/resultados/valid/"

sanity-check:
	bash scripts/check_release_sanity.sh
