#ifndef SOLVERCONFIG_H
#define SOLVERCONFIG_H

#include <climits>

/**
 * Parámetros de configuración comunes a todos los solvers.
 *
 * Se pasa a Problema::setConfig() antes de llamar a resolver().
 * Cada implementación concreta (Gurobi, CPLEX, CBC) los aplica
 * usando la API nativa de su solver.
 *
 * Valores por defecto:
 *   timeoutSegundos : 1800.0  (30 minutos)
 *   mipGap          : 1e-4    (0.01 %)
 *   scaleFlagGurobi : SOLVER_PARAM_AUTO  (no se toca; Gurobi usa su default)
 *   scaleIndCplex   : SOLVER_PARAM_AUTO  (no se toca; CPLEX usa su default)
 *
 * Ejemplo de uso desde el intérprete de comandos:
 *   configurarSolver --Gurobi --timeout 600 --mipgap 1e-6
 *   configurarSolver --Gurobi --scaleflag 0       # baseline: escalado interno OFF
 *   configurarSolver --Cplex  --cplexscale 1      # baseline: escalado agresivo de CPLEX
 */
struct SolverConfig {
    /// Centinela para "no tocar el parámetro de escalado del solver".
    static const int SOLVER_PARAM_AUTO = INT_MIN;

    double timeoutSegundos = 1800.0;  ///< Límite de tiempo en segundos (≤ 0 → sin límite)
    double mipGap          = 1e-4;    ///< Tolerancia de optimalidad relativa para MIP

    /// Escalado interno de Gurobi (GRB_IntParam_ScaleFlag): -1 auto, 0 off, 1, 2, 3.
    /// SOLVER_PARAM_AUTO ⇒ no se modifica (default del solver). Baseline para la
    /// pregunta "¿es solo escalado genérico?" del revisor (R1).
    int scaleFlagGurobi = SOLVER_PARAM_AUTO;
    /// Escalado interno de CPLEX (IloCplex::Param::Read::Scale): -1 sin escalado,
    /// 0 equilibrado estándar (default), 1 agresivo. SOLVER_PARAM_AUTO ⇒ no se modifica.
    int scaleIndCplex   = SOLVER_PARAM_AUTO;
    /// Semilla aleatoria del solver (Gurobi GRB_IntParam_Seed / CPLEX Param::RandomSeed).
    /// SOLVER_PARAM_AUTO ⇒ no se modifica (default del solver, reproducible corrida a corrida).
    /// Permite estimar la variabilidad corrida-a-corrida del MIP, que es del mismo orden que
    /// los efectos ~1 % que reporta el paper: sin réplica de semilla no se puede separar el
    /// efecto del escalado del ruido del solver.
    int semillaSolver = SOLVER_PARAM_AUTO;
    /// Presolve de CPLEX (IloCplex::Param::Preprocessing::Presolve): 0 off, 1 on (default).
    /// SOLVER_PARAM_AUTO => no se modifica. Sondeo R1: ¿el presolve de CPLEX absorbe el efecto
    /// del escalado externo? (dependencia del solver).
    int presolveIndCplex = SOLVER_PARAM_AUTO;
};

#endif // SOLVERCONFIG_H
