#ifndef PROBLEMA_H
#define PROBLEMA_H

#include "SystemController/Problema/Componentes/Variable.h"
#include "SystemController/Problema/Componentes/Restriccion.h"
#include "SystemController/Problema/Componentes/Binario.h"
#include "SystemController/Problema/Componentes/AporteFuncionObjetivo.h"
#include "SystemController/Problema/SolverConfig.h"

#include <string>
#include <vector>
#include <map>
#include <set>
#include <utility>
#include <stdexcept>

// =============================================================================
// Clase base para el modelo MIP de despacho eléctrico (versión de reproducibilidad).
//
// ESTRATEGIA DE RESOLUCIÓN: Monolítica
// ─────────────────────────────────────
// procesar() → resolver() → resolverMonolitico()
//   El modelo completo se pasa al solver en una sola llamada de branch-and-bound.
//
// Este es el único camino de resolución usado por el paper: el preprocesamiento
// numérico (PreprocesamientoMIP) transforma el modelo y luego el solver lo resuelve
// monolíticamente. La verificación en unidades originales comprueba la equivalencia.
// =============================================================================
class Problema {
public:
    struct ResultadoVerificacionOriginal {
        bool disponible = false;
        double maxViolacionMenorIgual = 0.0;
        double maxViolacionMayorIgual = 0.0;
        double maxViolacionIgualdad = 0.0;
        double maxViolacionCotaInf = 0.0;
        double maxViolacionCotaSup = 0.0;
        double maxViolacionIntegridad = 0.0;
        // Clasificación por tipo de restricción:
        // demanda = restricciones 'gen_menor_demanda(t)'; local = el resto.
        double maxViolacionDemanda = 0.0;
        double maxViolacionLocal = 0.0;
        // Estadísticos de violación de restricciones (≤,≥,=) sobre TODAS las filas:
        // promedio, percentiles y máxima RELATIVA viol/(1+|rhs|). La máxima relativa
        // distingue una violación grande en valor absoluto pero pequeña en escala (RHS
        // enorme) de una violación numéricamente significativa.
        double avgViolacionRestricciones = 0.0;
        double p95ViolacionRestricciones = 0.0;
        double p99ViolacionRestricciones = 0.0;
        double maxViolacionRelativa = 0.0;
        // Máxima relativa a la ACTIVIDAD de la fila: viol / max{1, |rhs|, Σ_j|a_rj·x_j|}
        // (refinamiento R5). El denominador RHS-only (1+|rhs|) sub-normaliza las filas de
        // actividad grande y RHS chico —en particular los balances con RHS cero, donde
        // se reduce al residuo absoluto—; el denominador por actividad corrige eso.
        double maxViolacionRelativaActividad = 0.0;
        double objetivoOriginalRecalculado = 0.0;
        int restriccionesMenorIgualVioladas = 0;
        int restriccionesMayorIgualVioladas = 0;
        int igualdadesVioladas = 0;
        int cotasInfVioladas = 0;
        int cotasSupVioladas = 0;
        int integridadViolada = 0;
        int variablesFaltantes = 0;
        std::string peorRestriccionMenorIgual;
        std::string peorRestriccionMayorIgual;
        std::string peorIgualdad;
        std::string peorCotaInf;
        std::string peorCotaSup;
        std::string peorIntegridad;
    };

    // Estadísticas de la última resolución monolítica, reportadas de forma SOLVER-AGNÓSTICA
    // (cada backend las puebla con su API). Permiten emitir un marcador [SOLVE] uniforme para
    // Gurobi y CPLEX, en vez de depender del formato de log de un solver.
    struct EstadisticasResolucion {
        std::string status = "DESCONOCIDO";  // OPTIMAL | TIME_LIMIT | SUBOPTIMAL | INFEASIBLE
        double gapPct        = -1.0;   // gap relativo final, en PORCENTAJE
        double bestBound     = 0.0;    // mejor cota dual
        double nodos         = -1.0;   // nodos del B&B
        double iteraciones   = -1.0;   // iteraciones de símplex
        double integralPrimal = -1.0;  // (1/T)∫ gap(t) dt sobre la resolución
    };
    const EstadisticasResolucion& getEstadisticasResolucion() const { return estadisticasResolucion; }

protected:
    EstadisticasResolucion estadisticasResolucion;
    std::map<std::string, double> valoresVariables;
    double valorFuncionObjetivo = 0.0;

    std::vector<Variable*> variables;
    std::vector<Restriccion*> restricciones;
    std::vector<Binario*> binarios;
    std::vector<AporteFuncionObjetivo*> terminosFuncionObjetivo;
    double constanteFuncionObjetivo = 0.0;
    double demandaTotal = 0.0;
    bool flagConstanteFuncionObjetivo = false;
    std::map<std::string, double> escalasSolucionVariables;
    std::string preprocesamientoSeleccionado = "Ninguno";
    std::string estrategiaResolucionSeleccionada = "Monolitica";
    bool preprocesamientoSeleccionadoAplicado = false;

    struct VariableOriginal {
        std::string nombre;
        int tipoCota;
        double cotaInf;
        double cotaSup;
    };
    struct RestriccionOriginal {
        std::string nombre;
        std::vector<std::pair<double, std::string>> terminos;
        std::string operador;
        double rhs;
    };
    bool snapshotOriginalDisponible = false;
    bool verificarModeloOriginalActivo = false;
    std::vector<VariableOriginal> variablesOriginales;
    std::vector<RestriccionOriginal> restriccionesOriginales;
    std::vector<std::string> binariosOriginales;
    std::vector<std::pair<double, std::string>> terminosFuncionObjetivoOriginal;
    double constanteFuncionObjetivoOriginal = 0.0;

protected:
    Problema() = default;  // solo construible como base

public:
    virtual ~Problema();

    // Problema gestiona recursos en heap: no copiable ni movible.
    Problema(const Problema&) = delete;
    Problema& operator=(const Problema&) = delete;
    Problema(Problema&&) = delete;
    Problema& operator=(Problema&&) = delete;

    double obtenerConstante(const std::string& nombre);

    // --- Términos de la función objetivo ---
    std::vector<AporteFuncionObjetivo*>& getTerminosFuncionObjetivo();
    std::vector<std::pair<double, std::string>> getParesTerminosFuncionObjetivo();

    // --- Variables ---
    void añadirVariable(const std::string& nombre, int tipoCota, double cotaInf, double cotaSup);
    std::vector<Variable*>& getVariables();

    // --- Restricciones ---
    void añadirRestriccion(const std::string& nombre,
                           std::vector<std::pair<double, std::string>> terminos,
                           const std::string& operador,
                           double terminoIndependiente);
    std::vector<Restriccion*>& getRestricciones();

    // --- Binarios ---
    void añadirBinario(const std::string& nombre);
    std::vector<Binario*>& getBinarios();

    // --- Relajación de binarias ---
    void transformarVariablesAReales();

    // --- Función objetivo ---
    void añadirTerminoFuncionObjetivo(double coef, const std::string& var);
    void sumarConstanteFuncionObjetivo(double valor);
    double getConstanteFuncionObjetivo();

    // --- Getters y Setters ---
    void setValoresVariables(std::map<std::string, double>& valores);
    std::map<std::string, double>& getValoresVariables();

    // --- Escalamiento controlado de columnas continuas ---
    void registrarEscalamientoVariableSolucion(const std::string& nombre, double factorOriginalPorInterna);
    void aplicarEscalamientoValoresSolucion();
    double getFactorOriginalPorInterna(const std::string& nombre) const;

    // --- Verificación en unidades originales del modelo ---
    void guardarModeloOriginalParaVerificacion();
    // Restaura los coeficientes y RHS de las restricciones desde el snapshot original.
    // Usado por el preprocesamiento para REVERTIR un escalamiento que empeoró el modelo.
    void restaurarDesdeSnapshotOriginal();
    void setVerificarModeloOriginalActivo(bool activo);
    bool getVerificarModeloOriginalActivo() const;
    bool tieneModeloOriginalParaVerificacion() const;
    ResultadoVerificacionOriginal verificarFactibilidadOriginal(
        const std::map<std::string, double>& valores,
        bool incluirConstanteObjetivo
    ) const;
    void imprimirVerificacionFactibilidadOriginal(
        const std::string& etiqueta,
        const std::map<std::string, double>& valores,
        bool incluirConstanteObjetivo
    ) const;

    void setValorFuncionObjetivo(double valor);
    double getValorFuncionObjetivo();

    void setFlagConstanteFuncionObjetivo(bool flag);
    bool getFlagConstanteFuncionObjetivo();

    // --- Pipeline solver-independiente ---
    void habilitarPreprocesamiento(const std::string& nombre);
    void habilitarEstrategiaResolucion(const std::string& nombre);
    const std::string& getPreprocesamientoSeleccionado() const;
    const std::string& getEstrategiaResolucionSeleccionada() const;
    void aplicarPreprocesamientoSeleccionado();

    // --- Configuración del solver (timeout, MIP gap) ---
    void setConfig(const SolverConfig& cfg) { config = cfg; }
    const SolverConfig& getConfig() const { return config; }

    // --- Procesar, grabar, resolver y mostrar ---
    virtual void procesar(bool flagConstante) = 0;
    virtual void grabar(std::string& ruta) = 0;
    void resolver();
    virtual void mostrar() = 0;

protected:
    SolverConfig config;  ///< Parámetros de configuración aplicados en resolver()
    virtual void resolverMonolitico() = 0;
};

#endif // PROBLEMA_H
