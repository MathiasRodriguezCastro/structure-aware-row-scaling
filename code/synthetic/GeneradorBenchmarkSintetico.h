#ifndef GENERADOR_BENCHMARK_SINTETICO_H
#define GENERADOR_BENCHMARK_SINTETICO_H

// =============================================================================
//  GeneradorBenchmarkSintetico — banco de pruebas MIP bloque-estructurado.
//
//  Genera, de forma reproducible por semilla, un MIP sintético análogo al
//  despacho hidrotérmico: B "bloques" (cada uno como un generador) con
//  variables continuas y binarias propias, restricciones locales y de
//  activación, y restricciones globales de acoplamiento con holgura de
//  shortage/surplus que garantizan factibilidad.
//
//  El modelo se construye POBLANDO un Problema ya existente mediante su API
//  pública (añadirVariable / añadirBinario / añadirRestriccion /
//  añadirTerminoFuncionObjetivo). NO se tocan agentes, despacho ni la lógica
//  hidrotérmica: este módulo es completamente independiente.
//
//  CONVENCIÓN DE NOMBRES (clave para el escalado generator-aware de
//  PreprocesamientoMIP, que detecta bloques por prefijo "a<i>_"):
//    - Continuas de bloque i:  a{i}_x{j}
//    - Binarias de bloque i:   a{i}_z{k}
//    - Restricción local:      a{i}_local_{r}
//    - Restricción activación: a{i}_act_{k}
//    - Restricción global:     coupling_{t}
//    - Holguras (sin prefijo de bloque, NO son columnas de bloque):
//                              short_{t}, surp_{t}
//
//  DESBALANCE ARTIFICIAL (parámetros del manuscrito):
//    - pattern ∈ {none, local, coupling, mixed}: qué FILAS reciben desbalance.
//    - S       ∈ {0, 3, 6}: para cada fila r seleccionada, θ_r = 10^{ξ_r},
//                            ξ_r ~ Uniform[-S, S]. Se multiplica TODA la fila,
//                            incluido el RHS (equivalencia algebraica).
//    - coefficient_family: familia/sparsity de los coeficientes base.
// =============================================================================

#include "SystemController/Problema/Problema.h"

#include <string>
#include <vector>

// ----------------------------------------------------------------------------
// Parámetros del generador
// ----------------------------------------------------------------------------

enum class PatronDesbalance { None, Local, Coupling, Mixed };
enum class FamiliaCoeficientes { Uniform, BlockHeterogeneous, Banded };

struct ParametrosSinteticos {
    unsigned int        seed                   = 0;
    int                 numBloques             = 0;   ///< B
    int                 varsContinuasPorBloque = 0;   ///< nc
    int                 varsBinariasPorBloque  = 0;   ///< nb
    int                 restrLocalesPorBloque  = 0;
    int                 restrAcoplamiento      = 0;   ///< T (filas coupling_)
    PatronDesbalance    patron                 = PatronDesbalance::None;
    int                 severidadS             = 0;   ///< 0 | 3 | 6
    FamiliaCoeficientes familiaCoef            = FamiliaCoeficientes::Uniform;
};

// ----------------------------------------------------------------------------
// Metadata explícita de la instancia generada (para debug/reproducibilidad)
// ----------------------------------------------------------------------------

enum class TipoFilaSintetica  { Local, Activacion, Acoplamiento };
enum class TipoColumnaSintetica { Continua, Binaria, Slack };

struct InfoFilaSintetica {
    int                 rowId            = 0;
    std::string         nombre;
    TipoFilaSintetica   tipo             = TipoFilaSintetica::Local;
    int                 bloqueId         = -1;   ///< -1 si es global (acoplamiento)
    double              rhs              = 0.0;  ///< RHS final (tras aplicar θ)
    int                 nnz              = 0;
    double              normaL2          = 0.0;
    double              appliedScaleFactor = 1.0; ///< θ_r aplicado (1.0 si ninguno)
};

struct InfoColumnaSintetica {
    int                   colId      = 0;
    std::string           nombre;
    TipoColumnaSintetica  tipo       = TipoColumnaSintetica::Continua;
    int                   bloqueId   = -1;   ///< -1 si es holgura (slack)
    double                lowerBound = 0.0;
    double                upperBound = 0.0;
    double                objCoef    = 0.0;
};

struct MetadatosInstancia {
    ParametrosSinteticos              params;
    std::vector<std::string>          prefijosBloque;        ///< {"a1_","a2_",...}
    std::vector<std::string>          prefijosGlobal;        ///< {"coupling_"}
    std::vector<std::string>          prefijosAcoplamiento;  ///< {"coupling_"}
    std::vector<InfoFilaSintetica>    filas;
    std::vector<InfoColumnaSintetica> columnas;
};

// ----------------------------------------------------------------------------
// Generador
// ----------------------------------------------------------------------------

class GeneradorBenchmarkSintetico {
public:
    explicit GeneradorBenchmarkSintetico(const ParametrosSinteticos& params);

    /**
     * Puebla `problema` con el MIP sintético y devuelve la metadata explícita.
     * Determinista para una misma `seed`: dos llamadas con los mismos parámetros
     * producen exactamente el mismo modelo (mismos coeficientes, nombres y θ).
     */
    MetadatosInstancia generar(Problema& problema) const;

    // --- Helpers de parseo (string → enum) para el comando ---
    static bool parsearPatron(const std::string& s, PatronDesbalance& out);
    static bool parsearFamilia(const std::string& s, FamiliaCoeficientes& out);
    static std::string patronAString(PatronDesbalance p);
    static std::string familiaAString(FamiliaCoeficientes f);

private:
    ParametrosSinteticos params;
};

#endif // GENERADOR_BENCHMARK_SINTETICO_H
