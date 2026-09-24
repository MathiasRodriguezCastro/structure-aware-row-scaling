# Current research revision. The default target only lists available commands.
.DEFAULT_GOAL := help
PYTHON ?= python3
AUDIT_ROOT := results-revision/research-audit
GRID_OUT ?= $(AUDIT_ROOT)/reruns/identifiability
BUDGET_OUT ?= $(AUDIT_ROOT)/reruns/budget
BUDGET_SOLVERS ?= highs gurobi
FIXED_BASIS_ROOT := $(AUDIT_ROOT)/fixed-basis-final-20260914
FIXED_BASIS_OUT ?= $(AUDIT_ROOT)/reruns/fixed-basis

.PHONY: help paper audit-build research-check-python research-check research-analysis \
        research-budget-analysis research-matrix-analysis research-operational-analysis \
        research-fixed-basis-analysis research-fixed-basis-check research-fixed-basis \
        research-fixed-basis-precision \
        research-grid research-budget analysis-n0 synthetic-mini sanity-check \
        research-rounding-check research-rounding-analysis rounding-note

help:
	@echo "Active rounding-safety investigation (not submission-ready):"
	@echo "  make research-rounding-check    - exact certificates, witnesses and math tests"
	@echo "  make research-rounding-analysis - verify the lattice control and draw comparison"
	@echo "  make rounding-note              - build the active working-note PDF"
	@echo "Current paper (no optimizer license required):"
	@echo "  make research-check-python  - mathematical tests, saved binary audit, LP hashes"
	@echo "  make research-check         - also build and test the C++ LP serializer"
	@echo "  make research-analysis      - regenerate current tables, figures and summaries"
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

rounding-note:
	pdflatex -interaction=nonstopmode -halt-on-error -output-directory=paper/research-notes paper/research-notes/joint-rounding.tex
	pdflatex -interaction=nonstopmode -halt-on-error -output-directory=paper/research-notes paper/research-notes/joint-rounding.tex

audit-build:
	$(MAKE) -C code BUILD_DIR=build-audit USE_GUROBI=0 USE_CPLEX=0 USE_CBC=0 USE_HEXALY=0

research-check-python:
	$(PYTHON) -m pytest -q tests/test_budget_scaling.py
	$(PYTHON) scripts/research/verify_saved_experiment.py --root $(AUDIT_ROOT)/budget-final
	cd $(AUDIT_ROOT)/identifiability-final && sha256sum --quiet -c checksums.sha256

research-check: audit-build research-check-python
	$(PYTHON) -m pytest -q tests/test_export_roundtrip.py

research-analysis: research-budget-analysis research-matrix-analysis research-operational-analysis \
                   research-fixed-basis-analysis

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
	$(PYTHON) scripts/research/analyze_budget_experiment.py --root $(AUDIT_ROOT)/budget-final

research-matrix-analysis:
	$(PYTHON) scripts/research/analyze_identifiability.py

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
