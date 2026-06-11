# =============================================================================
# Build for the cleaned reproducibility platform (monolithic MIP + preprocessing).
#
# Solver toggles (1 = compile & link, 0 = exclude that backend entirely):
#   USE_GUROBI, USE_CPLEX, USE_CBC, USE_HEXALY
#
# Examples:
#   make                                  # Gurobi + CPLEX + Cbc (Hexaly off)
#   make USE_HEXALY=0                     # same as default (explicit)
#   make USE_GUROBI=0 USE_CPLEX=0 USE_CBC=1 USE_HEXALY=0   # license-free (Cbc only, N1)
#
# Override solver locations as needed, e.g.:
#   make GUROBI_HOME=/opt/gurobi/linux64 CPLEX_HOME=/opt/ibm/ILOG/CPLEX_Studio2212
# =============================================================================

CPLEX_HOME  ?= /opt/ibm/ILOG/CPLEX_Studio2212
GUROBI_HOME ?= $(HOME)/solvers/gurobi1301/linux64
HEXALY_HOME ?= /opt/hexaly_14_5

# Solver toggles
USE_GUROBI ?= 1
USE_CPLEX  ?= 1
USE_CBC    ?= 1
USE_HEXALY ?= 0

CXX := g++
.DEFAULT_GOAL := all

CXXFLAGS := -I. -Wall -Wextra -std=c++17 -g
LDLIBS   :=
EXCLUDES :=

# ---- Gurobi ----
ifeq ($(USE_GUROBI),1)
  CXXFLAGS += -DUSE_GUROBI -I$(GUROBI_HOME)/include
  LDLIBS   += -L$(GUROBI_HOME)/lib -Wl,-rpath,$(GUROBI_HOME)/lib -lgurobi_c++ -lgurobi130 -lm
else
  CXXFLAGS += -DNO_GUROBI
  EXCLUDES += -not -path './SystemController/Problema/ProblemaGurobi/*'
endif

# ---- CPLEX ----
ifeq ($(USE_CPLEX),1)
  CXXFLAGS += -DUSE_CPLEX -I$(CPLEX_HOME)/cplex/include -I$(CPLEX_HOME)/concert/include
  LDLIBS   += -L$(CPLEX_HOME)/cplex/lib/x86-64_linux/static_pic \
              -L$(CPLEX_HOME)/concert/lib/x86-64_linux/static_pic \
              -lilocplex -lcplex -lconcert -lm -lpthread -ldl
else
  CXXFLAGS += -DNO_CPLEX
  EXCLUDES += -not -path './SystemController/Problema/ProblemaCplex/*'
endif

# ---- CBC (open source) ----
ifeq ($(USE_CBC),1)
  CXXFLAGS += -I/usr/include/coin
  LDLIBS   += -L/usr/lib/x86_64-linux-gnu -lCbcSolver -lCbc -lCgl \
              -lOsiClp -lClp -lOsi -lCoinUtils -lz -lbz2
else
  CXXFLAGS += -DNO_CBC
  EXCLUDES += -not -path './SystemController/Problema/ProblemaCbc/*'
endif

# ---- Hexaly (optional, metaheuristic) ----
ifeq ($(USE_HEXALY),1)
  CXXFLAGS += -DUSE_HEXALY -I$(HEXALY_HOME)/include
  LDLIBS   += -L$(HEXALY_HOME)/bin -Wl,-rpath,$(HEXALY_HOME)/bin -lhexaly145 -lpthread -lm
  export HX_LICENSE_PATH ?= $(HEXALY_HOME)/license.dat
else
  CXXFLAGS += -DNO_HEXALY
  EXCLUDES += -not -path './SystemController/Problema/ProblemaHexaly/*'
endif

BUILD_DIR := build
TARGET    := $(BUILD_DIR)/SistemaElectrico

SRCS := $(shell find . -name '*.cpp' -not -path './$(BUILD_DIR)/*' -not -path './utils/*' $(EXCLUDES))
OBJS := $(SRCS:./%.cpp=$(BUILD_DIR)/%.o)
DEPS := $(OBJS:.o=.d)
-include $(DEPS)

.PHONY: all clean run show-config

all: $(TARGET)
	@echo "Build done: $(TARGET)  (GUROBI=$(USE_GUROBI) CPLEX=$(USE_CPLEX) CBC=$(USE_CBC) HEXALY=$(USE_HEXALY))"

$(BUILD_DIR)/%.o: ./%.cpp Makefile
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) -MMD -MP -c $< -o $@

$(TARGET): $(OBJS)
	$(CXX) $^ -o $@ $(LDLIBS)

clean:
	rm -rf $(BUILD_DIR)

run: $(TARGET)
	./$(TARGET)

show-config:
	@echo "USE_GUROBI=$(USE_GUROBI) USE_CPLEX=$(USE_CPLEX) USE_CBC=$(USE_CBC) USE_HEXALY=$(USE_HEXALY)"
	@echo "CXXFLAGS=$(CXXFLAGS)"
	@echo "LDLIBS=$(LDLIBS)"
