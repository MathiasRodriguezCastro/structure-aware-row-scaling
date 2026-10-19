#!/bin/bash
#SBATCH --job-name=orf_cplex_api
#SBATCH --account=ute
#SBATCH --partition=ute
#SBATCH --qos=ute
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:10:00

set -euo pipefail
TASK_ROOT=${1:?isolated environment directory required}
export SINGULARITYENV_OPENBLAS_NUM_THREADS=1
export SINGULARITYENV_OMP_NUM_THREADS=1
export SINGULARITYENV_SLURM_JOB_ID="$SLURM_JOB_ID"
singularity exec --cleanenv -B "$HOME:$HOME" "$HOME/containers/gcc13.sif" \
 bash -s -- "$TASK_ROOT" <<'INNER'
set -euo pipefail
TASK_ROOT=$1
SOURCE="$HOME/solvers/CPLEX_Studio2212/cplex/lib/x86-64_linux/static_pic/libcplex.a"
TARGET="$TASK_ROOT/native-cplex-2212"
mkdir "$TARGET"
sha256sum "$SOURCE" > "$TASK_ROOT/CPLEX_STATIC.sha256"
g++ -shared -Wl,-soname,libcplex2212.so -o "$TARGET/libcplex2212.so" \
 -Wl,--whole-archive "$SOURCE" -Wl,--no-whole-archive -lm -lpthread -ldl
sha256sum "$TARGET/libcplex2212.so" > "$TASK_ROOT/CPLEX_NATIVE.sha256"
g++ --version > "$TARGET/compiler-version.txt"
export PYTHONPATH="$TASK_ROOT/python-deps-v1"
export LD_PRELOAD="$TARGET/libcplex2212.so"
python3 "$TASK_ROOT/cluster/preflight.py" "$TASK_ROOT/PREFLIGHT-installed.json"
INNER
