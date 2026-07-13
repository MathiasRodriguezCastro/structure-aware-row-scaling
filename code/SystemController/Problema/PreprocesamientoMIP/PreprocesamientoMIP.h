#ifndef PREPROCESAMIENTO_MIP_H
#define PREPROCESAMIENTO_MIP_H

#include "SystemController/Problema/Problema.h"

#include <string>
#include <vector>
#include <map>
#include <set>
#include <functional>

/**
 * Parámetros de configuración del preprocesamiento.
 * Se define fuera de la clase para evitar problemas con
 * default member initializers en argumentos por defecto.
 */
struct PreprocesamientoConfig {
    bool   aplicarEscalamientoLocal  = true;   ///< Escalar bloques locales
    bool   aplicarEscalamientoGlobal = true;   ///< Escalar fila global de balance
    bool   escalamientoLocalPorFila  = true;   ///< Escalar cada fila local por su propia escala
    bool   normalizarBloqueTrasFilas = true;   ///< Luego normalizar cada bloque ya equilibrado
    bool   modoMatricial             = false;  ///< Estrategia 2: factores SOLO de la matriz A
                                               ///<  (norma L2 de fila y escalas de bloque por
                                               ///<  normas de fila); el RHS se escala pero no
                                               ///<  participa del diagnóstico de escala.
    bool   escalamientoPlano         = false;  ///< Control experimental (flat/no-metadata): el MISMO
                                               ///<  kernel por fila (alpha_r = 1/sqrt(M_r*m_r)) sobre
                                               ///<  TODAS las filas SIN metadata de roles ni bloques:
                                               ///<  un único bloque con todas las filas, sin
                                               ///<  clasificación global/acoplamiento, sin beta de
                                               ///<  bloque y sin etapa de acoplamiento. Mismas
                                               ///<  salvaguardas por fila.
    bool   usarEquilibradoRuiz       = false;  ///< Equilibrado iterativo interno por bloque
    bool   escalarColumnasContinuas  = false;  ///< Transformar columnas continuas y recuperar solución
    bool   normalizacionFisica       = false;  ///< Normalizar filas globales por unidades físicas/proxy
    bool   verificarModeloOriginal   = false;  ///< Guardar snapshot original y verificar solución desescalada
    bool   solodiagnostico           = false;  ///< Solo reportar, no modificar nada
    bool   verbose                   = true;   ///< Imprimir reporte al ejecutar
    int    iteracionesRuiz           = 4;      ///< Iteraciones del equilibrado Ruiz aproximado
    double umbralKappa               = 1e6;    ///< Umbral para reportar bloque mal condicionado
    double umbralRangoCoef           = 1e6;    ///< Umbral para reportar rango de coeficientes
    double umbralRhoEscalamientoGlobal = 10.0; ///< Solo escalar acoplamiento si rho supera este valor
    double umbralFactorEscalamiento  = 2.0;    ///< No aplicar factores dentro de [1/u, u]  (hiperparámetro u)
    double epsMinCoef                = 1e-9;   ///< Ventana de coeficiente admisible: cota inferior ε_min
    double epsMaxCoef                = 1e9;    ///< Ventana de coeficiente admisible: cota superior ε_max
    /// Piso de magnitud escalada para el γ COLECTIVO de acoplamiento: γ se aplica a una fila
    /// solo si su mayor |coef| escalado queda >= este piso. Acota la amplificación del residuo
    /// en escala original: la tolerancia absoluta ε del solver sobre la fila escalada mapea a
    /// lo sumo a ε/piso RELATIVO a la magnitud de la fila original (con piso 1e-3 y ε=1e-6,
    /// residuo relativo <= 1e-3). El kernel por fila lo garantiza solo (geomean escalada = 1);
    /// el γ colectivo, fijado por las filas grandes, puede empujar una fila individualmente
    /// chica al régimen frágil sin este piso (visto en el benchmark sintético, coupling S=6).
    double pisoMagnitudGammaColectivo = 1e-3;
    /// Piso de magnitud escalada para los factores LOCALES AUMENTADOS de SA-Aug (α_r con |RHS|
    /// en los extremos). Cuando el lado derecho domina la fila, α_r puede dejar el mayor |coef|
    /// (sin contar |RHS|) por debajo de la tolerancia del solver → el residuo original se
    /// amplifica (fallos de verificación de Simple/Full). Si >0, α_r se aplica solo si el mayor
    /// |coef| escalado (excluyendo |RHS|) queda >= este piso; si no, la fila queda a escala base.
    /// Default 0 = DESHABILITADO (byte-idéntico; el kernel matricial no lo necesita, no usa RHS).
    double pisoMagnitudFactorLocal = 0.0;
};

/**
 * Capa opcional de preprocesamiento numérico para el MIP.
 *
 * Actúa sobre un Problema ya construido, antes de llamar a resolver().
 * No modifica el modelo matemático en términos de conjunto factible:
 * todas las transformaciones son equivalentes (escalan filas y sus
 * lados derechos de forma coherente).
 *
 * Uso típico:
 *
 *   PreprocesamientoMIP prep(problema);
 *   prep.registrarBloque("RioNegro", {"Bon_", "Bay_", "Pal_"});
 *   prep.registrarBloque("SaltoGrande", {"SG_"});
 *   prep.registrarRestriccionGlobal({"balance_", "demanda_", "falla_"});
 *   prep.ejecutar();               // aplica diagnóstico + escalamiento
 *   prep.imprimirReporte();
 *
 * Si no se registran bloques, PreprocesamientoMIP los infiere
 * automáticamente agrupando por prefijo (texto antes del primer '_').
 *
 * El preprocesamiento es:
 *   - opcional: no se llama si no se instancia esta clase.
 *   - auditable: genera un reporte con todas las transformaciones.
 *   - matemáticamente equivalente: solo escala filas y RHS.
 *   - desactivable: se puede llamar solo diagnosticar() sin escalar.
 *   - compatible con todos los solvers del sistema.
 *   - seguro con variables binarias: no escala columnas.
 */
class PreprocesamientoMIP {
public:
    // Alias para compatibilidad con código existente
    using Config = PreprocesamientoConfig;

    // ----------------------------------------------------------------
    // Diagnóstico por bloque
    // ----------------------------------------------------------------

    struct DiagnosticoBloque {
        std::string nombre;
        std::vector<int> indicesRestricciones; ///< Índices en problema.restricciones
        std::string prefijoVariable; ///< Prefijo aN_ del agente si fue autodetectado
        std::string prefijoGeneracion; ///< Prefijo gN asociado si participa en despacho
        int numVariables = 0; ///< Variables/columnas detectadas para el agente
        double normaMax    = 0.0;   ///< max |coef| en el bloque  ≈ σ_max(Aᵢ)  (approx)
        double normaMin    = 1e300; ///< min |coef| no nulo       ≈ σ_min(Aᵢ)  (approx)
        double kappaAprox  = 0.0;  ///< normaMax / normaMin
        double alpha       = 1.0;  ///< Factor de escalamiento aplicado
        double alphaMin    = 1.0;  ///< Menor factor aplicado dentro del bloque
        double alphaMax    = 1.0;  ///< Mayor factor aplicado dentro del bloque
        double betaBloque  = 1.0;  ///< Factor posterior para normalizar entre bloques
        int    filasEscaladas = 0; ///< Cantidad de filas locales escaladas
        int    columnasEscaladas = 0; ///< Cantidad de variables continuas transformadas
        int    columnasDiscretasOmitidas = 0; ///< Binarias/discretas detectadas y no transformadas
        int    columnasAuxiliaresOmitidas = 0; ///< Continuas fuera de bloques de agente, no transformadas
        double escalaColumnaMin = 1.0; ///< Menor factor x=s*y aplicado
        double escalaColumnaMax = 1.0; ///< Mayor factor x=s*y aplicado
        int    iteracionesEquilibrado = 0; ///< Iteraciones internas usadas
        bool   escalado    = false;
        bool   bloqueNormalizado = false;
        bool   columnasTransformadas = false;
    };

    struct DiagnosticoGlobal {
        double normaMaxTotal   = 0.0;
        double normaMinTotal   = 1e300;
        double kappaTotal      = 0.0;
        double rhoAprox        = 0.0;  ///< ‖L D⁻¹‖ aproximado
        double gamma           = 1.0;  ///< Factor aplicado a fila global
        double gammaCandidato  = 1.0;  ///< Mejor gamma encontrado antes del umbral de identidad
        double phiGammaUno     = 0.0;  ///< Costo proxy con gamma=1
        double phiGammaCandidato = 0.0; ///< Costo proxy con gamma candidato
        bool   filaGlobalEscalada = false;
        int    filasGlobales = 0;
        int    filasAcoplamiento = 0;
        int    filasGlobalesNoAcoplamiento = 0;
        int    filasNormalizacionFisica = 0;
        std::vector<std::string> advertencias;
    };

    // ----------------------------------------------------------------
    // Constructor
    // ----------------------------------------------------------------

    explicit PreprocesamientoMIP(Problema& problema, const Config& config = Config{});

    // ----------------------------------------------------------------
    // Registro de bloques (opcional; si no se llama, se autodetecta)
    // ----------------------------------------------------------------

    /**
     * Registra un bloque con nombre dado y un conjunto de prefijos.
     * Una restricción pertenece al bloque si su nombre empieza con
     * alguno de los prefijos dados.
     */
    void registrarBloque(const std::string& nombreBloque,
                         const std::vector<std::string>& prefijos);

    /**
     * Registra qué prefijos corresponden a restricciones globales
     * (balance, demanda, falla...). Estas filas no se escalan junto
     * con los bloques locales.
     */
    void registrarRestriccionGlobal(const std::vector<std::string>& prefijos);

    /**
     * Registra restricciones globales que acoplan bloques locales con
     * variables agregadas. Estas filas entran en rho ~= ||L D^-1|| y son
     * candidatas al escalamiento global gamma.
     */
    void registrarRestriccionAcoplamiento(const std::vector<std::string>& prefijos);

    // ----------------------------------------------------------------
    // Ejecución
    // ----------------------------------------------------------------

    /** Solo calcula diagnóstico, no modifica el problema. */
    void diagnosticar();

    /** Calcula diagnóstico y aplica escalamiento (según Config). */
    void ejecutar();

    /** Imprime el reporte de diagnóstico y transformaciones. */
    void imprimirReporte() const;

    // ----------------------------------------------------------------
    // Acceso a resultados
    // ----------------------------------------------------------------

    const std::vector<DiagnosticoBloque>& getDiagnosticoPorBloque() const { return bloques; }
    const DiagnosticoGlobal&              getDiagnosticoGlobal()    const { return global;  }

private:
    Problema& prob;
    Config    cfg;

    std::vector<DiagnosticoBloque> bloques;
    DiagnosticoGlobal              global;

    // Prefijos registrados para restricciones globales
    std::set<std::string> prefijosGlobales;

    // Prefijos registrados para restricciones de acoplamiento global-local
    std::set<std::string> prefijosAcoplamiento;

    // Índices de restricciones globales
    std::vector<int> indicesGlobales;

    // Índices de restricciones globales que acoplan agentes
    std::vector<int> indicesAcoplamiento;

    // ----------------------------------------------------------------
    // Internos
    // ----------------------------------------------------------------

    void autodetectarBloques();
    void clasificarRestricciones();
    bool esRestriccionGlobal(int idx) const;
    bool esRestriccionAcoplamiento(int idx) const;
    void calcularDiagnosticoPorBloque();
    void calcularDiagnosticoGlobal();
    void aplicarEscalamientoLocal();
    void aplicarEscalamientoGlobal();
    void aplicarNormalizacionFisicaGlobal();
    void imprimirReporteComparativo(const std::vector<DiagnosticoBloque>& bloquesAntes,
                                    const DiagnosticoGlobal& globalAntes) const;

    static std::string extraerPrefijo(const std::string& nombre);
    static std::string extraerPrefijoAgente(const std::string& nombreVariable);
    static std::string extraerPrefijoAgenteLocal(const std::string& nombreVariable);
    static std::string extraerPrefijoGeneracion(const std::string& nombreVariable);
    static bool empiezaCon(const std::string& s, const std::string& prefijo);
    bool esVariableBinaria(const std::string& nombre) const;
    bool esVariableContinua(const std::string& nombre) const;
    bool esVariableContinuaEscalable(const std::string& nombre) const;
    void escalarFila(int idxRestriccion, double factor);
    static double normaL2Coeficientes(const Restriccion* r);   ///< ‖a_r‖₂ (sin RHS)
    void escalarVariableContinua(const std::string& nombre, double factorOriginalPorInterna);
    void aplicarEquilibradoRuiz(DiagnosticoBloque& bloque);
    static bool factorSignificativo(double factor, double umbral);
};

#endif // PREPROCESAMIENTO_MIP_H
