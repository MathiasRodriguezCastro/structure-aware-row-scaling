#ifndef SOLVERCONFIG_H
#define SOLVERCONFIG_H

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
 *
 * Ejemplo de uso desde el intérprete de comandos:
 *   configurarSolver --Gurobi --timeout 600 --mipgap 1e-6
 */
struct SolverConfig {
    double timeoutSegundos = 1800.0;  ///< Límite de tiempo en segundos (≤ 0 → sin límite)
    double mipGap          = 1e-4;    ///< Tolerancia de optimalidad relativa para MIP
};

#endif // SOLVERCONFIG_H
