# High-level reproduction targets. See README.md for the N0–N3 levels.
.PHONY: help paper analysis-n0 synthetic-mini sanity-check clean

help:
	@echo "Targets:"
	@echo "  make paper           - build the manuscript PDF (paper/main.pdf)"
	@echo "  make analysis-n0     - rebuild all tables/figures from results/*/resumen.csv (no solver)"
	@echo "  make synthetic-mini  - build (Cbc, license-free) + run the synthetic mini benchmark"
	@echo "  make sanity-check    - pre-release sanity scan (paths/secrets/LSTM-DW)"
	@echo "  make clean           - remove build/analysis/LaTeX artifacts"

paper:
	$(MAKE) -C paper

analysis-n0:
	bash scripts/run_analysis_n0.sh

# Always builds a license-free binary (Cbc only) into its own build dir
# (code/build-cbc/), so this target never depends on — nor overwrites — a
# preexisting Gurobi/CPLEX build under code/build/.
synthetic-mini:
	$(MAKE) -C code BUILD_DIR=build-cbc USE_GUROBI=0 USE_CPLEX=0 USE_CBC=1 USE_HEXALY=0
	cd code && ./build-cbc/SistemaElectrico < ../data/synthetic/validacion_mini_cbc.txt
	@echo "Synthetic-mini metrics under code/synthetic/resultados/valid/"

sanity-check:
	bash scripts/check_release_sanity.sh

clean:
	-$(MAKE) -C code clean
	-$(MAKE) -C code BUILD_DIR=build-cbc clean
	-$(MAKE) -C paper clean
	rm -rf results-analysis code/synthetic/resultados
