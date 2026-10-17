#ifndef RUNNER_BENCHMARK_SINTETICO_H
#define RUNNER_BENCHMARK_SINTETICO_H

// =============================================================================
//  RunnerBenchmarkSintetico — orquesta el barrido (instancia × variante).
//
//  Por cada instancia (seed = seedBase + idx) y cada variante de preprocesamiento
//  (Base / SA-Aug / SA-Mat / Ruiz / Ruiz+Cols):
//    1. configurarSolver  → obtiene un Problema limpio del SystemController.
//    2. genera el MIP sintético dentro de ese Problema (mismo modelo base por seed).
//    3. diagnostica κ/ρ ANTES (PreprocesamientoMIP en modo diagnóstico).
//    4. aplica la variante (escala el modelo en sitio) y diagnostica κ/ρ DESPUÉS.
//    5. procesa y resuelve (estrategia Monolítica) y mide tiempos/objetivo.
//    6. limpia el estado para la siguiente variante.
//
//  Salidas: CSV de métricas (siempre) y, con outDir, manifest.json +
//  row_metadata.csv + column_metadata.csv por instancia. Con lpDir, exporta el
//  modelo a .lp.
//
//  NO toca agentes ni despacho: usa configurarSolver/getProblema/limpiar y la
//  API pública de Problema/PreprocesamientoMIP, todo reutilizado sin modificar.
// =============================================================================

#include "synthetic/GeneradorBenchmarkSintetico.h"
#include "SystemController/Problema/SolverConfig.h"

#include <string>
#include <vector>

struct ConfiguracionRunner {
    ParametrosSinteticos          params;         ///< params base (params.seed = seed base)
    int                           numInstancias = 1; ///< nº de seeds por celda (seed = base..base+N-1)
    std::string                   solver        = "Gurobi";
    SolverConfig                  solverConfig;    ///< timeout, mipgap
    std::vector<std::string>      variantes;       ///< Base, SA-Aug, SA-Mat, Ruiz, Ruiz+Cols
    std::string                   rutaCsv;          ///< CSV de métricas (obligatorio)
    std::string                   outDir;           ///< vacío = sin manifest/metadata
    std::string                   lpDir;            ///< vacío = sin volcado .lp
    // Grilla: si se pasan listas, se barre pattern × S × seeds (celdas).
    std::vector<PatronDesbalance> patrones;         ///< vacío ⇒ usa params.patron
    std::vector<int>              severidades;       ///< vacío ⇒ usa params.severidadS
    std::string                   rutaSummary;       ///< vacío = sin resumen agregado
};

class RunnerBenchmarkSintetico {
public:
    explicit RunnerBenchmarkSintetico(const ConfiguracionRunner& cfg);

    /** Ejecuta el barrido completo y escribe todas las salidas. */
    void ejecutar();

private:
    ConfiguracionRunner cfg;
};

#endif // RUNNER_BENCHMARK_SINTETICO_H
