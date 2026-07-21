#include "PreprocesamientoMIP.h"

#include <iostream>
#include <iomanip>
#include <sstream>
#include <chrono>
#include <algorithm>
#include <cmath>
#include <cctype>
#include <stdexcept>

using namespace std;

// ============================================================
// Constructor
// ============================================================

PreprocesamientoMIP::PreprocesamientoMIP(Problema& problema, const Config& config)
    : prob(problema), cfg(config)
{}

// ============================================================
// Registro de bloques y restricciones globales
// ============================================================

void PreprocesamientoMIP::registrarBloque(const string& nombre,
                                          const vector<string>& prefijos) {
    DiagnosticoBloque bloque;
    bloque.nombre = nombre;

    auto& restricciones = prob.getRestricciones();
    for (int i = 0; i < (int)restricciones.size(); ++i) {
        const string& nomR = restricciones[i]->getNombre();
        bool agregada = false;
        for (const auto& p : prefijos) {
            if (empiezaCon(nomR, p)) {
                bloque.indicesRestricciones.push_back(i);
                agregada = true;
                break;
            }
        }
        if (agregada) continue;

        for (const auto& [_, var] : restricciones[i]->getTerminos()) {
            for (const auto& p : prefijos) {
                if (empiezaCon(var, p)) {
                    bloque.indicesRestricciones.push_back(i);
                    agregada = true;
                    break;
                }
            }
            if (agregada) break;
        }
    }
    bloques.push_back(move(bloque));
}

void PreprocesamientoMIP::registrarRestriccionGlobal(const vector<string>& prefijos) {
    for (const auto& p : prefijos)
        prefijosGlobales.insert(p);
}

void PreprocesamientoMIP::registrarRestriccionAcoplamiento(const vector<string>& prefijos) {
    for (const auto& p : prefijos)
        prefijosAcoplamiento.insert(p);
}

// ============================================================
// Ejecución principal
// ============================================================

void PreprocesamientoMIP::diagnosticar() {
    indicesGlobales.clear();
    indicesAcoplamiento.clear();
    if (bloques.empty())    autodetectarBloques();
    clasificarRestricciones();
    calcularDiagnosticoPorBloque();
    calcularDiagnosticoGlobal();
    // Verificación opcional sin escalar (variante 'base'): se snapshotea el modelo original
    // para que la solución desescalada/postprocesada se verifique sobre la formulación original.
    if (cfg.verificarModeloOriginal) {
        prob.guardarModeloOriginalParaVerificacion();
        prob.setVerificarModeloOriginalActivo(true);
    }
    if (cfg.verbose) imprimirReporte();
}

void PreprocesamientoMIP::ejecutar() {
    // Cronometraje por sub-fase (instrumentación; no altera el resultado). Separa el
    // coste de RECONSTRUIR la metadata estructural --que un generador que ya la mantiene
    // podría entregar sin recomputar-- del coste intrínseco de diagnosticar y escalar.
    using _reloj = std::chrono::steady_clock;
    double _t_metadata = 0.0, _t_diagnostico = 0.0, _t_aplicacion = 0.0;
    auto _cronometrar = [](double& acumulador, auto&& fn) {
        const auto inicio = _reloj::now();
        fn();
        acumulador += std::chrono::duration<double>(_reloj::now() - inicio).count();
    };

    indicesGlobales.clear();
    indicesAcoplamiento.clear();
    _cronometrar(_t_metadata, [&] {
        if (bloques.empty())    autodetectarBloques();
        clasificarRestricciones();
    });
    _cronometrar(_t_diagnostico, [&] {
        calcularDiagnosticoPorBloque();
        calcularDiagnosticoGlobal();
    });

    // Modo plano (control experimental): verificar que NINGUNA fila quede fuera del
    // bloque único (cobertura total) y dejar evidencia en el log.
    if (cfg.escalamientoPlano) {
        size_t filasEnBloques = 0;
        for (const auto& b : bloques) filasEnBloques += b.indicesRestricciones.size();
        const size_t filasModelo = prob.getRestricciones().size();
        if (filasEnBloques != filasModelo)
            throw runtime_error(
                "PreprocesamientoMIP: modo plano no cubre todas las filas (" +
                to_string(filasEnBloques) + " de " + to_string(filasModelo) + ")");
        cout << "[PREPROC] modo plano: " << filasModelo
             << " filas tratadas como un unico bloque sin roles (kernel geomean por fila)" << endl;
    }

    // Estado pre-escalamiento, usado por el reporte comparativo (imprimirReporteComparativo).
    vector<DiagnosticoBloque> bloquesAntes = bloques;
    DiagnosticoGlobal globalAntes = global;

    // Snapshot del modelo original para verificación: ortogonal al escalamiento. Se toma
    // aun con --solodiagnostico, de modo que la variante 'base' (sin escalar) también pueda
    // verificar su solución desescalada/postprocesada sobre la formulación original.
    if (cfg.verificarModeloOriginal) {
        prob.guardarModeloOriginalParaVerificacion();
        prob.setVerificarModeloOriginalActivo(true);
    }

    if (!cfg.solodiagnostico) {
        if (cfg.aplicarEscalamientoLocal) {
            _cronometrar(_t_aplicacion, [&] { aplicarEscalamientoLocal(); });
            _cronometrar(_t_diagnostico, [&] {
                calcularDiagnosticoPorBloque();
                calcularDiagnosticoGlobal();
            });
        }

        if (cfg.normalizacionFisica) {
            _cronometrar(_t_aplicacion, [&] { aplicarNormalizacionFisicaGlobal(); });
            _cronometrar(_t_diagnostico, [&] {
                calcularDiagnosticoPorBloque();
                calcularDiagnosticoGlobal();
            });
        }

        if (cfg.aplicarEscalamientoGlobal) {
            _cronometrar(_t_aplicacion, [&] { aplicarEscalamientoGlobal(); });
        }

        // Recalcular diagnóstico post-escalamiento para el reporte
        _cronometrar(_t_diagnostico, [&] {
            calcularDiagnosticoPorBloque();
            calcularDiagnosticoGlobal();
        });
    }

    {
        std::ostringstream _fases;
        _fases << std::defaultfloat << std::setprecision(10)
               << "[PREPROC PHASES] metadata_s=" << _t_metadata
               << " diagnostico_s=" << _t_diagnostico
               << " aplicacion_s=" << _t_aplicacion;
        std::cout << _fases.str() << std::endl;
    }

    if (cfg.verbose) {
        imprimirReporte();
        if (!cfg.solodiagnostico)
            imprimirReporteComparativo(bloquesAntes, globalAntes);
    }
}

// ============================================================
// Autodetección de bloques por prefijo
// ============================================================

void PreprocesamientoMIP::autodetectarBloques() {
    // Modo plano (control experimental): un método plano no conoce nombres de agentes
    // ni roles de fila, así que NO agrupa por prefijos: UN ÚNICO bloque con TODAS las filas
    // del modelo. El kernel por fila (y sus salvaguardas) se aplica igual que en la etapa
    // local normal; la clasificación global/acoplamiento queda vacía (ver esRestriccionGlobal
    // / esRestriccionAcoplamiento) y ninguna fila queda fuera.
    if (cfg.escalamientoPlano) {
        auto& restriccionesPlano = prob.getRestricciones();
        DiagnosticoBloque bloque;
        bloque.nombre = "plano";
        bloque.indicesRestricciones.reserve(restriccionesPlano.size());
        for (int i = 0; i < (int)restriccionesPlano.size(); ++i)
            bloque.indicesRestricciones.push_back(i);
        bloques.push_back(move(bloque));
        return;
    }

    // Agrupar restricciones locales por variables internas de agente:
    // a1_, a2_, ...  Las variables gN(t) se usan para reconocer agentes que
    // solo aparecen como columnas de despacho (por ejemplo una termica simple),
    // pero no para clasificar filas locales: g11(t) puede ser una subcentral
    // de Rio Negro, no el agente 11.
    map<string, vector<int>> grupos;
    map<string, int> variablesPorAgente;
    map<string, string> generacionPorAgente;
    auto& restricciones = prob.getRestricciones();

    for (auto* v : prob.getVariables()) {
        string pref = extraerPrefijoAgenteLocal(v->getNombre());
        if (!pref.empty()) variablesPorAgente[pref]++;
    }
    for (auto* b : prob.getBinarios()) {
        string pref = extraerPrefijoAgenteLocal(b->getNombre());
        if (!pref.empty()) variablesPorAgente[pref]++;
    }

    for (int i = 0; i < (int)restricciones.size(); ++i) {
        const string& nomR = restricciones[i]->getNombre();
        bool filaAcoplamiento = esRestriccionAcoplamiento(i);
        if (!filaAcoplamiento && !empiezaCon(nomR, "gh_total")) continue;

        for (const auto& [_, var] : restricciones[i]->getTerminos()) {
            string gen = extraerPrefijoGeneracion(var);
            if (gen.empty()) continue;

            string pref = extraerPrefijoAgente(var);
            if (!pref.empty()) {
                variablesPorAgente[pref]++;
                generacionPorAgente[pref] = gen;
            }
        }
    }

    for (int i = 0; i < (int)restricciones.size(); ++i) {
        if (esRestriccionGlobal(i)) continue;

        set<string> prefijosAgente;
        for (const auto& [_, var] : restricciones[i]->getTerminos()) {
            string pref = extraerPrefijoAgenteLocal(var);
            if (!pref.empty()) prefijosAgente.insert(pref);
        }

        if (prefijosAgente.size() == 1) {
            grupos[*prefijosAgente.begin()].push_back(i);
        } else {
            grupos["sin_agente"].push_back(i);
        }
    }

    for (const auto& [pref, _] : variablesPorAgente) {
        if (!grupos.count(pref)) grupos[pref] = {};
    }

    for (auto& [pref, indices] : grupos) {
        DiagnosticoBloque bloque;
        bloque.nombre = pref;
        bloque.prefijoVariable = pref;
        bloque.numVariables = variablesPorAgente[pref];
        auto itGen = generacionPorAgente.find(pref);
        if (itGen != generacionPorAgente.end()) bloque.prefijoGeneracion = itGen->second;
        bloque.indicesRestricciones = indices;
        bloques.push_back(move(bloque));
    }
}

// ============================================================
// Clasificar restricciones globales
// ============================================================

void PreprocesamientoMIP::clasificarRestricciones() {
    indicesGlobales.clear();
    indicesAcoplamiento.clear();
    auto& restricciones = prob.getRestricciones();

    for (int i = 0; i < (int)restricciones.size(); ++i) {
        bool acoplamiento = esRestriccionAcoplamiento(i);
        if (esRestriccionGlobal(i) || acoplamiento) indicesGlobales.push_back(i);
        if (acoplamiento) indicesAcoplamiento.push_back(i);
    }

    // Los roles de fila y la incidencia de bloque son metadatos separados: una fila
    // clasificada global/de-acoplamiento puede tocar variables de varios bloques, pero no es
    // fila local y no entra a la etapa local ni a las escalas de bloque (R_local y
    // R_coupling son disjuntos). El camino autodetectado ya lo garantiza (salta
    // esRestriccionGlobal al agrupar); esto lo impone también para bloques registrados por
    // prefijos, cuya membresía por incidencia de variables puede incluirlas.
    if (!cfg.escalamientoPlano && !indicesGlobales.empty()) {
        set<int> globales(indicesGlobales.begin(), indicesGlobales.end());
        for (auto& bloque : bloques) {
            auto& idx = bloque.indicesRestricciones;
            idx.erase(remove_if(idx.begin(), idx.end(),
                                [&](int i) { return globales.count(i) > 0; }),
                      idx.end());
        }
    }
}

bool PreprocesamientoMIP::esRestriccionGlobal(int idx) const {
    // Modo plano: sin metadata de roles, ninguna fila es "global".
    if (cfg.escalamientoPlano) return false;

    auto& restricciones = prob.getRestricciones();
    if (idx < 0 || idx >= (int)restricciones.size()) return false;

    const string& nomR = restricciones[idx]->getNombre();
    for (const auto& pg : prefijosGlobales)
        if (empiezaCon(nomR, pg)) return true;

    set<string> prefijosAgente;
    bool tocaVariableGlobal = false;
    for (const auto& [_, var] : restricciones[idx]->getTerminos()) {
        string pref = extraerPrefijoAgenteLocal(var);
        if (!pref.empty()) {
            prefijosAgente.insert(pref);
        } else if (empiezaCon(var, "g(") || empiezaCon(var, "costoFalla(")) {
            tocaVariableGlobal = true;
        }
    }

    return prefijosAgente.size() > 1 || (tocaVariableGlobal && !prefijosAgente.empty());
}

bool PreprocesamientoMIP::esRestriccionAcoplamiento(int idx) const {
    // Modo plano: sin metadata de roles, ninguna fila es "acoplamiento".
    if (cfg.escalamientoPlano) return false;

    auto& restricciones = prob.getRestricciones();
    if (idx < 0 || idx >= (int)restricciones.size()) return false;

    const string& nomR = restricciones[idx]->getNombre();
    for (const auto& pg : prefijosAcoplamiento)
        if (empiezaCon(nomR, pg)) return true;

    bool tocaGeneracionAgente = false;
    bool tocaGeneracionGlobal = false;
    set<string> prefijosLocales;

    for (const auto& [_, var] : restricciones[idx]->getTerminos()) {
        if (!extraerPrefijoGeneracion(var).empty()) tocaGeneracionAgente = true;
        if (empiezaCon(var, "g(")) tocaGeneracionGlobal = true;

        string prefLocal = extraerPrefijoAgenteLocal(var);
        if (!prefLocal.empty()) prefijosLocales.insert(prefLocal);
    }

    return (tocaGeneracionGlobal && tocaGeneracionAgente) || prefijosLocales.size() > 1;
}

// ============================================================
// Diagnóstico por bloque
//
// Aproximación barata de σ_max y σ_min:
//   σ_max(Aᵢ) ≈ max |coef|     (norma de fila máxima)
//   σ_min(Aᵢ) ≈ min |coef|≠0   (norma de fila mínima)
//
// Esto es una aproximación conservadora. No calcula SVD (caro),
// pero es suficiente para detectar desbalances de escala.
// ============================================================

void PreprocesamientoMIP::calcularDiagnosticoPorBloque() {
    auto& restricciones = prob.getRestricciones();

    for (auto& bloque : bloques) {
        bloque.normaMax = 0.0;
        bloque.normaMin = 1e300;

        for (int idx : bloque.indicesRestricciones) {
            const auto& terminos = restricciones[idx]->getTerminos();
            double rhs = std::abs(restricciones[idx]->getTerminoIndependiente());

            for (const auto& [coef, _] : terminos) {
                double ac = std::abs(coef);
                if (ac > 0.0) {
                    bloque.normaMax = max(bloque.normaMax, ac);
                    bloque.normaMin = min(bloque.normaMin, ac);
                }
            }
            // Incluir RHS en el rango
            if (rhs > 0.0) {
                bloque.normaMax = max(bloque.normaMax, rhs);
                bloque.normaMin = min(bloque.normaMin, rhs);
            }
        }

        if (bloque.normaMin < 1e300 && bloque.normaMin > 0.0)
            bloque.kappaAprox = bloque.normaMax / bloque.normaMin;
        else
            bloque.kappaAprox = 0.0;

        if (bloque.indicesRestricciones.empty()) {
            bloque.normaMin = 0.0;
        }
    }
}

// ============================================================
// Diagnóstico global
// ============================================================

void PreprocesamientoMIP::calcularDiagnosticoGlobal() {
    double gammaPrev = global.gamma;
    double gammaCandidatoPrev = global.gammaCandidato;
    double phiGammaUnoPrev = global.phiGammaUno;
    double phiGammaCandidatoPrev = global.phiGammaCandidato;
    bool filaGlobalEscaladaPrev = global.filaGlobalEscalada;
    int filasNormalizacionFisicaPrev = global.filasNormalizacionFisica;

    global = DiagnosticoGlobal{};
    global.gamma = gammaPrev;
    global.gammaCandidato = gammaCandidatoPrev;
    global.phiGammaUno = phiGammaUnoPrev;
    global.phiGammaCandidato = phiGammaCandidatoPrev;
    global.filaGlobalEscalada = filaGlobalEscaladaPrev;
    global.filasNormalizacionFisica = filasNormalizacionFisicaPrev;
    global.filasGlobales = static_cast<int>(indicesGlobales.size());
    global.filasAcoplamiento = static_cast<int>(indicesAcoplamiento.size());
    global.filasGlobalesNoAcoplamiento =
        max(0, global.filasGlobales - global.filasAcoplamiento);

    auto& restricciones = prob.getRestricciones();

    // Proxy global de rango sobre coeficientes y términos independientes.
    // Es max(|A|,|b|)/min^+(|A|,|b|), no un número de condición espectral.
    for (auto& r : restricciones) {
        double rhs = std::abs(r->getTerminoIndependiente());
        if (rhs > 0.0) {
            global.normaMaxTotal = max(global.normaMaxTotal, rhs);
            global.normaMinTotal = min(global.normaMinTotal, rhs);
        }
        for (const auto& [coef, _] : r->getTerminos()) {
            double ac = std::abs(coef);
            if (ac > 0.0) {
                global.normaMaxTotal = max(global.normaMaxTotal, ac);
                global.normaMinTotal = min(global.normaMinTotal, ac);
            }
        }
    }
    if (global.normaMinTotal < 1e300 && global.normaMinTotal > 0.0)
        global.kappaTotal = global.normaMaxTotal / global.normaMinTotal;

    map<string, double> escalaLocalPorAgente;
    set<string> agentesSinFilasLocales;
    double escalaLocalGeneral = 1.0;
    double sumaEscalasLocales = 0.0;
    int cantEscalasLocales = 0;
    for (const auto& bloque : bloques) {
        if (bloque.indicesRestricciones.empty() && !bloque.prefijoVariable.empty()) {
            agentesSinFilasLocales.insert(bloque.prefijoVariable);
            continue;
        }
        if (bloque.normaMin <= 0.0 || bloque.normaMin >= 1e300) continue;
        double escala = sqrt(bloque.normaMax * bloque.normaMin);
        if (escala <= 0.0 || escala >= 1e300) continue;
        sumaEscalasLocales += escala;
        ++cantEscalasLocales;
        if (!bloque.prefijoVariable.empty()) {
            escalaLocalPorAgente[bloque.prefijoVariable] = escala;
        }
    }
    if (cantEscalasLocales > 0)
        escalaLocalGeneral = sumaEscalasLocales / cantEscalasLocales;

    double sumaRho2 = 0.0;
    for (int idx : indicesAcoplamiento) {
        double filaRho2 = 0.0;
        for (const auto& [coef, var] : restricciones[idx]->getTerminos()) {
            string pref = extraerPrefijoAgente(var);
            if (pref.empty()) continue;

            double sigma = escalaLocalGeneral;
            auto it = escalaLocalPorAgente.find(pref);
            if (it != escalaLocalPorAgente.end()) sigma = it->second;
            else if (agentesSinFilasLocales.count(pref)) sigma = 1.0;
            if (sigma > 0.0 && sigma < 1e300) {
                double contrib = std::abs(coef) / sigma;
                filaRho2 += contrib * contrib;
            }
        }
        sumaRho2 = max(sumaRho2, filaRho2);
    }

    global.rhoAprox = sqrt(sumaRho2);

    // Advertencias
    if (global.kappaTotal > cfg.umbralRangoCoef)
        global.advertencias.push_back(
            "Rango de coeficientes elevado (" +
            to_string((long long)global.kappaTotal) + "). Riesgo de sensibilidad numerica.");

    for (const auto& bloque : bloques) {
        if (bloque.kappaAprox > cfg.umbralKappa)
            global.advertencias.push_back(
                "Bloque '" + bloque.nombre + "' internamente mal escalado (kappa~" +
                to_string((long long)bloque.kappaAprox) +
                "). Conviene comparar equilibrado interno por filas/columnas.");
    }

    if (global.rhoAprox > 100.0)
        global.advertencias.push_back(
            "Acoplamiento efectivo rho elevado (~" +
            to_string((int)global.rhoAprox) +
            "). La fila de balance puede deteriorar el condicionamiento.");
}

// ============================================================
// Escalamiento local (equivalente: escala fila + RHS)
//
// Modo por bloque:
//   α_i = 1 / sqrt(normaMax_i * normaMin_i)
//
// Modo por fila:
//   α_r = 1 / sqrt(M_r * m_r)
//
// Modo estructurado:
//   1) α_r por fila dentro de cada bloque A_i
//   2) β_i por bloque ya equilibrado para comparar escalas entre agentes
//
// Esto es la media geométrica de valores singulares aproximados,
// que centra la escala de cada bloque/fila alrededor de 1. El modo
// estructurado conserva la lectura por bloques del documento y agrega
// una limpieza interna previa de cada A_i.
// ============================================================

bool PreprocesamientoMIP::factorSignificativo(double factor, double umbral) {
    return factor > 0.0 && (factor < 1.0 / umbral || factor > umbral);
}

bool PreprocesamientoMIP::esVariableBinaria(const string& nombre) const {
    for (auto* b : prob.getBinarios()) {
        if (b && b->getNombre() == nombre) return true;
    }
    // Defensa adicional: si las binarias fueron relajadas antes del
    // preprocesamiento, ya no aparecen en prob.binarios. Conservamos por
    // convencion los nombres discretos del modelo hidraulico/termico.
    return nombre.find("varphi") != string::npos ||
           nombre.find("_xg(") != string::npos ||
           nombre.find("_yg(") != string::npos;
}

bool PreprocesamientoMIP::esVariableContinua(const string& nombre) const {
    for (auto* v : prob.getVariables()) {
        if (v && v->getNombre() == nombre) return true;
    }
    return false;
}

bool PreprocesamientoMIP::esVariableContinuaEscalable(const string& nombre) const {
    // En este modelo las variables reales viven en prob.variables y las binarias
    // en prob.binarios. Si un nombre aparece en ambos conjuntos, se trata como
    // discreta para no destruir dominios {0,1}.
    return esVariableContinua(nombre) && !esVariableBinaria(nombre);
}

void PreprocesamientoMIP::escalarFila(int idxRestriccion, double factor) {
    if (!factorSignificativo(factor, cfg.umbralFactorEscalamiento)) return;

    Restriccion* r = prob.getRestricciones()[idxRestriccion];
    auto terminos = r->getTerminos();
    for (auto& [coef, _] : terminos) {
        coef *= factor;
    }
    r->setTerminos(terminos);
    r->setTerminoIndependiente(r->getTerminoIndependiente() * factor);
}

// ‖a_r‖₂ sobre los coeficientes de la fila (excluye el RHS). Estrategia 2: el factor de
// escala depende únicamente de la matriz A; el RHS se escala para preservar equivalencia
// pero no entra en el diagnóstico de escala.
double PreprocesamientoMIP::normaL2Coeficientes(const Restriccion* r) {
    double suma = 0.0;
    for (const auto& [coef, _] : r->getTerminos()) {
        suma += coef * coef;
    }
    return std::sqrt(suma);
}

void PreprocesamientoMIP::escalarVariableContinua(const string& nombre,
                                                  double factorOriginalPorInterna) {
    if (!factorSignificativo(factorOriginalPorInterna, cfg.umbralFactorEscalamiento)) return;
    if (!esVariableContinuaEscalable(nombre)) {
        throw runtime_error(
            "PreprocesamientoMIP::escalarVariableContinua - intento de escalar una variable no continua: " +
            nombre
        );
    }

    for (auto* r : prob.getRestricciones()) {
        auto terminos = r->getTerminos();
        bool cambio = false;
        for (auto& [coef, var] : terminos) {
            if (var == nombre) {
                coef *= factorOriginalPorInterna;
                cambio = true;
            }
        }
        if (cambio) r->setTerminos(terminos);
    }

    for (auto* termino : prob.getTerminosFuncionObjetivo()) {
        if (termino && termino->getVariable() == nombre) {
            termino->setCoeficiente(termino->getCoeficiente() * factorOriginalPorInterna);
        }
    }

    for (auto* v : prob.getVariables()) {
        if (!v || v->getNombre() != nombre) continue;
        const double s = factorOriginalPorInterna;
        if (v->getTipoCota() == 0 || v->getTipoCota() == 2)
            v->setCotaInf(v->getCotaInf() / s);
        if (v->getTipoCota() == 0 || v->getTipoCota() == 1)
            v->setCotaSup(v->getCotaSup() / s);
        break;
    }

    prob.registrarEscalamientoVariableSolucion(nombre, factorOriginalPorInterna);
}

void PreprocesamientoMIP::aplicarEquilibradoRuiz(DiagnosticoBloque& bloque) {
    auto& restricciones = prob.getRestricciones();
    if (bloque.indicesRestricciones.empty()) return;

    set<string> variablesContinuasBloque;
    set<string> variablesDiscretasOmitidas;
    set<string> variablesAuxiliaresOmitidas;
    const bool bloqueDeAgente = !extraerPrefijoAgenteLocal(bloque.prefijoVariable).empty();
    for (int idx : bloque.indicesRestricciones) {
        for (const auto& [_, var] : restricciones[idx]->getTerminos()) {
            if (bloqueDeAgente && esVariableContinuaEscalable(var)) {
                variablesContinuasBloque.insert(var);
            } else if (esVariableBinaria(var)) {
                variablesDiscretasOmitidas.insert(var);
            } else if (!bloqueDeAgente && esVariableContinua(var)) {
                variablesAuxiliaresOmitidas.insert(var);
            }
        }
    }
    bloque.columnasDiscretasOmitidas = static_cast<int>(variablesDiscretasOmitidas.size());
    bloque.columnasAuxiliaresOmitidas = static_cast<int>(variablesAuxiliaresOmitidas.size());

    const int iteraciones = max(1, cfg.iteracionesRuiz);
    double alphaMin = 1e300;
    double alphaMax = 0.0;
    double logAlpha = 0.0;
    int filas = 0;
    int columnas = 0;
    double colMin = 1e300;
    double colMax = 0.0;

    for (int it = 0; it < iteraciones; ++it) {
        for (int idx : bloque.indicesRestricciones) {
            Restriccion* r = restricciones[idx];
            double normaInf = std::abs(r->getTerminoIndependiente());
            for (const auto& [coef, _] : r->getTerminos()) {
                normaInf = max(normaInf, std::abs(coef));
            }
            if (normaInf <= 0.0) continue;

            double alpha = 1.0 / sqrt(normaInf);
            if (!factorSignificativo(alpha, cfg.umbralFactorEscalamiento)) continue;
            escalarFila(idx, alpha);
            alphaMin = min(alphaMin, alpha);
            alphaMax = max(alphaMax, alpha);
            logAlpha += log(alpha);
            ++filas;
        }

        if (!cfg.escalarColumnasContinuas) continue;

        map<string, double> maxCol;
        for (const auto& var : variablesContinuasBloque) maxCol[var] = 0.0;

        for (int idx : bloque.indicesRestricciones) {
            for (const auto& [coef, var] : restricciones[idx]->getTerminos()) {
                auto itCol = maxCol.find(var);
                if (itCol != maxCol.end()) {
                    itCol->second = max(itCol->second, std::abs(coef));
                }
            }
        }

        for (const auto& [var, normaInf] : maxCol) {
            if (normaInf <= 0.0) continue;
            double s = 1.0 / sqrt(normaInf); // x = s*y; coeficiente interno a*s
            if (!factorSignificativo(s, cfg.umbralFactorEscalamiento)) continue;
            escalarVariableContinua(var, s);
            colMin = min(colMin, s);
            colMax = max(colMax, s);
            ++columnas;
        }
    }

    if (filas > 0) {
        bloque.alpha = exp(logAlpha / filas);
        bloque.alphaMin = alphaMin;
        bloque.alphaMax = alphaMax;
        bloque.filasEscaladas += filas;
        bloque.escalado = true;
    }
    if (columnas > 0) {
        bloque.columnasEscaladas += columnas;
        bloque.escalaColumnaMin = colMin;
        bloque.escalaColumnaMax = colMax;
        bloque.columnasTransformadas = true;
        bloque.escalado = true;
    }
    bloque.iteracionesEquilibrado = iteraciones;
}

void PreprocesamientoMIP::aplicarEscalamientoLocal() {
    auto& restricciones = prob.getRestricciones();

    for (auto& bloque : bloques) {
        if (bloque.normaMax <= 0.0 || bloque.normaMin <= 0.0 || bloque.normaMin >= 1e300)
            continue;

        bloque.alpha = 1.0;
        bloque.alphaMin = 1.0;
        bloque.alphaMax = 1.0;
        bloque.betaBloque = 1.0;
        bloque.filasEscaladas = 0;
        bloque.columnasEscaladas = 0;
        bloque.columnasDiscretasOmitidas = 0;
        bloque.columnasAuxiliaresOmitidas = 0;
        bloque.escalaColumnaMin = 1.0;
        bloque.escalaColumnaMax = 1.0;
        bloque.iteracionesEquilibrado = 0;
        bloque.escalado = false;
        bloque.bloqueNormalizado = false;
        bloque.columnasTransformadas = false;

        if (cfg.usarEquilibradoRuiz) {
            aplicarEquilibradoRuiz(bloque);

            if (cfg.normalizarBloqueTrasFilas) {
                double bloqueMax = 0.0;
                double bloqueMin = 1e300;

                for (int idx : bloque.indicesRestricciones) {
                    Restriccion* r = restricciones[idx];
                    for (const auto& [coef, _] : r->getTerminos()) {
                        double ac = std::abs(coef);
                        if (ac > 0.0) {
                            bloqueMax = max(bloqueMax, ac);
                            bloqueMin = min(bloqueMin, ac);
                        }
                    }
                }

                if (bloqueMax > 0.0 && bloqueMin > 0.0 && bloqueMin < 1e300) {
                    double beta = 1.0 / sqrt(bloqueMax * bloqueMin);
                    if (factorSignificativo(beta, cfg.umbralFactorEscalamiento)) {
                        for (int idx : bloque.indicesRestricciones) {
                            escalarFila(idx, beta);
                        }
                        bloque.betaBloque = beta;
                        bloque.bloqueNormalizado = true;
                        bloque.escalado = true;
                    }
                }
            }
            continue;
        }

        if (cfg.escalamientoLocalPorFila) {
            double logAlpha = 0.0;
            double alphaMin = 1e300;
            double alphaMax = 0.0;

            for (int idx : bloque.indicesRestricciones) {
                Restriccion* r = restricciones[idx];
                auto terminos = r->getTerminos();

                double alpha;
                if (cfg.modoMatricial) {
                    // Estrategia 2: α_r = 1/√(M_r·m_r) con M_r,m_r = extremos de |coef| (solo A, sin
                    // RHS). Se usa la MEDIA GEOMÉTRICA de extremos, no la norma L2: es independiente
                    // de la cantidad de coeficientes de la fila y centra la escala sin que el factor
                    // quede dominado por el coeficiente mayor ni por la densidad de la fila (la norma
                    // L2 sí dependía de ambos y descompensaba el rango global).
                    double cmin = 1e300, cmax = 0.0;
                    for (const auto& [coef, _] : terminos) {
                        double ac = std::abs(coef);
                        if (ac > 0.0) { cmin = std::min(cmin, ac); cmax = std::max(cmax, ac); }
                    }
                    if (cmax <= 0.0 || cmin >= 1e300) continue;
                    alpha = 1.0 / sqrt(cmax * cmin);
                    // Salvaguarda de ventana: no escalar si el factor sacaría algún coeficiente de la
                    // fila fuera de [ε_min, ε_max].
                    if (cmin * alpha < cfg.epsMinCoef || cmax * alpha > cfg.epsMaxCoef)
                        continue;
                } else {
                    // Estrategia 1: α_r = 1/√(M_r·m_r) con M_r,m_r sobre |coef| y |RHS|.
                    double filaMax = 0.0;
                    double filaMin = 1e300;
                    for (const auto& [coef, _] : terminos) {
                        double ac = std::abs(coef);
                        if (ac > 0.0) {
                            filaMax = max(filaMax, ac);
                            filaMin = min(filaMin, ac);
                        }
                    }
                    double rhs = std::abs(r->getTerminoIndependiente());
                    if (rhs > 0.0) {
                        filaMax = max(filaMax, rhs);
                        filaMin = min(filaMin, rhs);
                    }
                    if (filaMax <= 0.0 || filaMin <= 0.0 || filaMin >= 1e300)
                        continue;
                    alpha = 1.0 / sqrt(filaMax * filaMin);
                    // Piso de confiabilidad LOCAL (opt-in): el residuo en escala original de una
                    // fila escalada por d_r queda acotado por ε_solver/d_r (la solución cumple la
                    // fila escalada a tolerancia ε; al desescalar se amplifica por 1/d_r). Cuando
                    // |RHS| domina los extremos, α_r se vuelve diminuto y amplifica el residuo
                    // (fallos de Simple/Full). El piso acota d_r≥piso ⇒ residuo≤ε_solver/piso, sin
                    // referir a ε_solver: si α_r<piso la fila queda a escala base. Default 0=inactivo.
                    if (cfg.pisoMagnitudFactorLocal > 0.0 && alpha < cfg.pisoMagnitudFactorLocal)
                        continue;
                }
                if (alpha > 0.5 && alpha < 2.0)
                    continue;

                for (auto& [coef, _] : terminos)
                    coef *= alpha;
                r->setTerminos(terminos);
                r->setTerminoIndependiente(r->getTerminoIndependiente() * alpha);

                logAlpha += log(alpha);
                alphaMin = min(alphaMin, alpha);
                alphaMax = max(alphaMax, alpha);
                ++bloque.filasEscaladas;
            }

            if (bloque.filasEscaladas > 0) {
                bloque.alpha = exp(logAlpha / bloque.filasEscaladas);
                bloque.alphaMin = alphaMin;
                bloque.alphaMax = alphaMax;
                bloque.escalado = true;
            }

            if (cfg.normalizarBloqueTrasFilas) {
                double bloqueMax = 0.0;
                double bloqueMin = 1e300;

                for (int idx : bloque.indicesRestricciones) {
                    Restriccion* r = restricciones[idx];
                    if (cfg.modoMatricial) {
                        // Estrategia 2: M_i,m_i sobre los EXTREMOS de |coef| del bloque (ya escalado
                        // por fila), sin RHS. Solo coeficientes en rango razonable [1e-6,1e6], para
                        // que las filas que el row-guard dejó sin escalar no dominen β.
                        for (const auto& [coef, _] : r->getTerminos()) {
                            double ac = std::abs(coef);
                            if (ac > 1e-6 && ac < 1e6) {
                                bloqueMax = max(bloqueMax, ac);
                                bloqueMin = min(bloqueMin, ac);
                            }
                        }
                        continue;
                    }
                    // Estrategia 1: M_i,m_i sobre |coef| y |RHS|.
                    double rhs = std::abs(r->getTerminoIndependiente());
                    if (rhs > 0.0) {
                        bloqueMax = max(bloqueMax, rhs);
                        bloqueMin = min(bloqueMin, rhs);
                    }
                    for (const auto& [coef, _] : r->getTerminos()) {
                        double ac = std::abs(coef);
                        if (ac > 0.0) {
                            bloqueMax = max(bloqueMax, ac);
                            bloqueMin = min(bloqueMin, ac);
                        }
                    }
                }

                if (bloqueMax > 0.0 && bloqueMin > 0.0 && bloqueMin < 1e300) {
                    double beta = 1.0 / sqrt(bloqueMax * bloqueMin);
                    // (matricial) salvaguarda: no aplicar β si llevaría algún coeficiente del
                    // bloque fuera de [1e-12, 1e12] (mismo riesgo de aplastamiento que el row-guard).
                    bool seguro = true;
                    if (cfg.modoMatricial) {
                        double cmn = 1e300, cmx = 0.0;
                        for (int idx : bloque.indicesRestricciones)
                            for (const auto& [coef, _] : restricciones[idx]->getTerminos()) {
                                double ac = std::abs(coef);
                                if (ac > 0.0) { cmn = std::min(cmn, ac); cmx = std::max(cmx, ac); }
                            }
                        if (cmn < 1e300 && (cmn * beta < cfg.epsMinCoef || cmx * beta > cfg.epsMaxCoef))
                            seguro = false;
                    }
                    if (seguro && !(beta > 0.5 && beta < 2.0)) {
                        for (int idx : bloque.indicesRestricciones) {
                            Restriccion* r = restricciones[idx];
                            auto terminos = r->getTerminos();
                            for (auto& [coef, _] : terminos)
                                coef *= beta;
                            r->setTerminos(terminos);
                            r->setTerminoIndependiente(r->getTerminoIndependiente() * beta);
                        }
                        bloque.betaBloque = beta;
                        bloque.bloqueNormalizado = true;
                        bloque.escalado = true;
                    }
                }
            }
            continue;
        }

        double alpha = 1.0 / sqrt(bloque.normaMax * bloque.normaMin);

        // No escalar si alpha es cercano a 1 (ya está bien escalado)
        if (alpha > 0.5 && alpha < 2.0) {
            bloque.alpha  = 1.0;
            bloque.escalado = false;
            continue;
        }

        for (int idx : bloque.indicesRestricciones) {
            Restriccion* r = restricciones[idx];

            // Escalar coeficientes de la fila
            auto terminos = r->getTerminos();
            for (auto& [coef, _] : terminos)
                coef *= alpha;
            r->setTerminos(terminos);

            // Escalar RHS (CRÍTICO: mantiene equivalencia matemática)
            r->setTerminoIndependiente(r->getTerminoIndependiente() * alpha);
        }

        bloque.alpha   = alpha;
        bloque.alphaMin = alpha;
        bloque.alphaMax = alpha;
        bloque.betaBloque = 1.0;
        bloque.filasEscaladas = static_cast<int>(bloque.indicesRestricciones.size());
        bloque.escalado = true;
    }
}

// ============================================================
// Escalamiento de la fila global
//
// γ se elige para minimizar Φ(γ) = κ(T(γρ)) * κ(B(γ)),
// donde κ(T) = ((√(ρ²+4)+ρ)/2)².
// En la práctica se evalúa Φ en una grilla logarítmica y se
// toma el mínimo. Esto es barato y robusto.
// ============================================================

void PreprocesamientoMIP::aplicarEscalamientoGlobal() {
    if (indicesAcoplamiento.empty()) return;

    auto& restricciones = prob.getRestricciones();

    // ----------------------------------------------------------------
    // Estrategia 2 (matricial): acoplamiento por fila.
    //   ρ̂_r = sqrt( Σ_j (|a_rj| / s_{b(j)})² ),   γ_r = 1/ρ̂_r,
    // con s_{b(j)} = escala MATRICIAL del bloque (√(M_i·m_i) sobre extremos de |coef|).
    // Cada fila de acoplamiento recibe su propio factor (no un único γ global).
    // ----------------------------------------------------------------
    if (cfg.modoMatricial) {
        map<string, double> escalaBloque;   // prefijoVariable -> √(M_i·m_i)
        double sumaEscala = 0.0; int cantEscala = 0;
        for (const auto& bloque : bloques) {
            if (bloque.indicesRestricciones.empty()) continue;
            double Mi = 0.0, mi = 1e300;
            for (int idx : bloque.indicesRestricciones) {
                // s del bloque = √(M_i·m_i) sobre EXTREMOS de |coef| (ya escalado por fila), sin RHS.
                // Solo coeficientes razonables: los extremos (sin escalar por el row-guard) NO deben
                // inflar s y, con ello, el factor de acoplamiento γ=1/ρ̂.
                for (const auto& [coef, _] : restricciones[idx]->getTerminos()) {
                    double ac = std::abs(coef);
                    if (ac > 1e-6 && ac < 1e6) { Mi = max(Mi, ac); mi = min(mi, ac); }
                }
            }
            if (Mi <= 0.0 || mi >= 1e300) continue;
            double s = sqrt(Mi * mi);
            if (s <= 0.0 || s >= 1e300) continue;
            if (!bloque.prefijoVariable.empty()) escalaBloque[bloque.prefijoVariable] = s;
            sumaEscala += s; ++cantEscala;
        }
        double escalaGeneral = (cantEscala > 0) ? sumaEscala / cantEscala : 1.0;

        int filasEscaladas = 0; double logGamma = 0.0;
        for (int idx : indicesAcoplamiento) {
            double rho2 = 0.0;
            for (const auto& [coef, var] : restricciones[idx]->getTerminos()) {
                string pref = extraerPrefijoAgente(var);
                double s = escalaGeneral;
                auto it = escalaBloque.find(pref);
                if (it != escalaBloque.end()) s = it->second;
                if (s > 0.0 && s < 1e300) {
                    double contrib = std::abs(coef) / s;
                    rho2 += contrib * contrib;
                }
            }
            double rho = sqrt(rho2);
            if (rho <= 0.0) continue;
            double gamma = 1.0 / rho;
            // Salvaguarda de rango máximo permitido (evita sobreescalar).
            gamma = std::min(1e8, std::max(1e-8, gamma));
            // Salvaguarda de ventana: no aplicar γ si llevaría algún coeficiente de la fila de
            // acoplamiento fuera de [ε_min, ε_max] (mismo criterio que fila/bloque).
            double cmin = 1e300, cmax = 0.0;
            for (const auto& [coef, _] : restricciones[idx]->getTerminos()) {
                double ac = std::abs(coef);
                if (ac > 0.0) { cmin = std::min(cmin, ac); cmax = std::max(cmax, ac); }
            }
            if (cmin < 1e300 && (cmin * gamma < cfg.epsMinCoef || cmax * gamma > cfg.epsMaxCoef))
                continue;
            if (factorSignificativo(gamma, cfg.umbralFactorEscalamiento)) {
                escalarFila(idx, gamma);   // aplica solo si se aparta de la identidad
                logGamma += log(gamma);
                ++filasEscaladas;
            }
        }
        if (filasEscaladas > 0) {
            global.gamma = exp(logGamma / filasEscaladas);   // γ medio (reporte)
            global.filaGlobalEscalada = true;
        }
        return;
    }

    // Parámetros del sistema después del escalamiento local
    double M = 0.0, m = 1e300;
    for (const auto& bloque : bloques) {
        if (bloque.indicesRestricciones.empty() ||
            bloque.normaMax <= 0.0 ||
            bloque.normaMin <= 0.0 ||
            bloque.normaMin >= 1e300) {
            continue;
        }
        if (!bloque.escalado) {
            M = max(M, bloque.normaMax);
            m = min(m, bloque.normaMin);
        } else {
            // Post-escalamiento: α_i * normaMax_i ≈ sqrt(Mi/mi) = sqrt(κ_i)
            double sqrtKappa = sqrt(bloque.kappaAprox);
            M = max(M, sqrtKappa);
            m = min(m, 1.0 / sqrtKappa);
        }
    }
    if (m >= 1e300 || M <= 0.0) return;

    double rho = global.rhoAprox;

    // Φ(γ): función de costo a minimizar
    auto phi = [&](double gamma) -> double {
        double gr = gamma * rho;
        double kT = pow((sqrt(gr*gr + 4.0) + gr) / 2.0, 2.0);
        double Mg = max(M, gamma);
        double mg = min(m, gamma);
        double kB = (mg > 0.0) ? Mg / mg : 1e300;
        return kT * kB;
    };

    // Búsqueda en grilla logarítmica: γ ∈ [1e-6, 1e6]
    double bestGamma = 1.0;
    double bestPhi   = phi(1.0);
    double phiUno = bestPhi;
    for (int exp = -60; exp <= 60; ++exp) {
        double g = pow(10.0, exp / 10.0);
        double p = phi(g);
        if (p < bestPhi) { bestPhi = p; bestGamma = g; }
    }

    global.gammaCandidato = bestGamma;
    global.phiGammaUno = phiUno;
    global.phiGammaCandidato = bestPhi;

    if (rho <= cfg.umbralRhoEscalamientoGlobal) {
        global.gamma = 1.0;
        global.filaGlobalEscalada = false;
        return;
    }

    // No escalar si γ es cercano a 1
    if (bestGamma > 0.5 && bestGamma < 2.0) {
        global.gamma = 1.0;
        global.filaGlobalEscalada = false;
        return;
    }

    int filasGammaAplicadas = 0;
    for (int idx : indicesAcoplamiento) {
        Restriccion* r = restricciones[idx];
        // Ventana admisible (misma salvaguarda que la rama matricial y que las filas
        // locales): el γ colectivo se aplica POR FILA solo si no saca ningún coeficiente
        // de [ε_min, ε_max]; la fila que lo violaría queda a su escala base. Sin este
        // chequeo, un γ≪1 sobre una fila de acoplamiento ya diminuta la empuja bajo la
        // tolerancia de factibilidad del solver (la fila se vuelve numéricamente nula y
        // la solución devuelta viola la fila original en O(1)).
        double cmin = 1e300, cmax = 0.0;
        for (const auto& [coef, _] : r->getTerminos()) {
            double ac = std::abs(coef);
            if (ac > 0.0) { cmin = std::min(cmin, ac); cmax = std::max(cmax, ac); }
        }
        if (cmin < 1e300 && (cmin * bestGamma < cfg.epsMinCoef || cmax * bestGamma > cfg.epsMaxCoef))
            continue;
        // Piso de magnitud escalada (salvaguarda de confiabilidad): si el γ colectivo dejara
        // el mayor |coef| de ESTA fila por debajo del piso, la fila queda a su escala base.
        // Ver Config::pisoMagnitudGammaColectivo.
        if (cmax > 0.0 && cmax * bestGamma < cfg.pisoMagnitudGammaColectivo)
            continue;
        auto terminos = r->getTerminos();
        for (auto& [coef, _] : terminos)
            coef *= bestGamma;
        r->setTerminos(terminos);
        r->setTerminoIndependiente(r->getTerminoIndependiente() * bestGamma);
        ++filasGammaAplicadas;
    }

    if (filasGammaAplicadas > 0) {
        global.gamma = bestGamma;
        global.filaGlobalEscalada = true;
    } else {
        global.gamma = 1.0;
        global.filaGlobalEscalada = false;
    }
}

// ============================================================
// Normalización física/proxy de filas globales
//
// Es una transformación equivalente de filas: se usan nombres globales
// asociados a potencia/demanda/falla/acoplamiento y se lleva la unidad
// dominante de la fila cerca de 1. No toca variables ni objetivo.
// ============================================================

void PreprocesamientoMIP::aplicarNormalizacionFisicaGlobal() {
    auto& restricciones = prob.getRestricciones();
    int escaladas = 0;

    for (int idx : indicesGlobales) {
        Restriccion* r = restricciones[idx];
        const string& nombre = r->getNombre();

        bool candidata =
            nombre.find("demanda") != string::npos ||
            nombre.find("Demanda") != string::npos ||
            nombre.find("falla") != string::npos ||
            nombre.find("Falla") != string::npos ||
            nombre.find("balance") != string::npos ||
            nombre.find("gh_total") != string::npos ||
            nombre.find("gen_menor_demanda") != string::npos;
        if (!candidata) continue;

        double escala = std::abs(r->getTerminoIndependiente());
        for (const auto& [coef, _] : r->getTerminos()) {
            escala = max(escala, std::abs(coef));
        }
        if (escala <= 0.0) continue;

        double factor = 1.0 / escala;
        if (!factorSignificativo(factor, cfg.umbralFactorEscalamiento)) continue;
        escalarFila(idx, factor);
        ++escaladas;
    }

    global.filasNormalizacionFisica += escaladas;
}

// ============================================================
// Reporte
// ============================================================

void PreprocesamientoMIP::imprimirReporte() const {
    const string sep(60, '-');
    cout << "\n" << sep << "\n";
    cout << "  PREPROCESAMIENTO MIP - Diagnostico Numerico\n";
    cout << sep << "\n";

    // Rango global
    cout << "Rango de coeficientes (toda la matriz):\n";
    cout << "  max |coef| = " << scientific << setprecision(3) << global.normaMaxTotal << "\n";
    cout << "  min |coef| = " << scientific << setprecision(3) << global.normaMinTotal << "\n";
    cout << "  proxy rango= " << scientific << global.kappaTotal << "\n\n";

    // Por bloque
    cout << "Diagnostico por bloque:\n";
    cout << left << setw(20) << "Bloque"
         << setw(15) << "max|coef|"
         << setw(15) << "min|coef|"
         << setw(14) << "kappa_aprox"
         << setw(8) << "vars"
         << setw(10) << "alpha"
         << setw(10) << "beta"
         << setw(10) << "cols"
         << setw(10) << "disc_omit"
         << setw(10) << "aux_omit"
         << "escalado\n";
    cout << string(126, '-') << "\n";

    for (const auto& b : bloques) {
        cout << setw(20) << b.nombre;
        if (b.indicesRestricciones.empty()) {
            cout << setw(15) << "sin filas"
                 << setw(15) << "sin filas"
                 << setw(14) << "N/A";
        } else {
            cout << setw(15) << scientific << setprecision(3) << b.normaMax
                 << setw(15) << scientific << setprecision(3) << b.normaMin
                 << setw(14) << scientific << setprecision(2) << b.kappaAprox;
        }
        cout << setw(8) << b.numVariables
             << setw(10) << scientific << setprecision(2) << b.alpha
             << setw(10) << scientific << setprecision(2) << b.betaBloque
             << setw(10) << b.columnasEscaladas
             << setw(10) << b.columnasDiscretasOmitidas
             << setw(10) << b.columnasAuxiliaresOmitidas
             << (b.escalado ? "SI" : "no");
        if (b.escalado && b.filasEscaladas > 0) {
            cout << "  (filas=" << b.filasEscaladas
                 << ", alpha_min=" << scientific << setprecision(2) << b.alphaMin
                 << ", alpha_max=" << scientific << setprecision(2) << b.alphaMax << ")";
        }
        if (b.columnasTransformadas) {
            cout << "  (columnas continuas=" << b.columnasEscaladas
                 << ", s_min=" << scientific << setprecision(2) << b.escalaColumnaMin
                 << ", s_max=" << scientific << setprecision(2) << b.escalaColumnaMax << ")";
        }
        if (b.columnasDiscretasOmitidas > 0) {
            cout << "  (discretas/binarias omitidas=" << b.columnasDiscretasOmitidas << ")";
        }
        if (b.columnasAuxiliaresOmitidas > 0) {
            cout << "  (continuas auxiliares omitidas=" << b.columnasAuxiliaresOmitidas << ")";
        }
        if (b.iteracionesEquilibrado > 0)
            cout << "  (Ruiz it=" << b.iteracionesEquilibrado << ")";
        if (b.bloqueNormalizado)
            cout << "  (normalizado entre bloques)";
        if (b.indicesRestricciones.empty() && !b.prefijoGeneracion.empty())
            cout << "  (sin filas locales; aporta " << b.prefijoGeneracion << " al despacho)";
        cout << "\n";
    }

    cout << "\nRestriccion(es) global(es): "
         << global.filasGlobales << " fila(s)\n";
    cout << "  acoplamiento balance = " << global.filasAcoplamiento << " fila(s)\n";
    cout << "  global no acoplante  = " << global.filasGlobalesNoAcoplamiento << " fila(s)\n";
    cout << "  rho aprox (solo acoplamiento) = " << scientific << setprecision(3) << global.rhoAprox << "\n";
    cout << "  gamma acoplamiento   = " << fixed << setprecision(6) << global.gamma << "\n";
    cout << "  gamma candidato      = " << fixed << setprecision(6) << global.gammaCandidato << "\n";
    if (global.phiGammaUno > 0.0 || global.phiGammaCandidato > 0.0) {
        cout << "  Phi(gamma=1)         = " << scientific << setprecision(3) << global.phiGammaUno << "\n";
        cout << "  Phi(gamma cand.)     = " << scientific << setprecision(3) << global.phiGammaCandidato << "\n";
    }
    cout << "  filas acop. escaladas= " << (global.filaGlobalEscalada ? "SI" : "no") << "\n";
    cout << "  filas normaliz. fisica= " << global.filasNormalizacionFisica << "\n";
    if (!global.filaGlobalEscalada && global.rhoAprox <= cfg.umbralRhoEscalamientoGlobal)
        cout << "  motivo gamma=1       = rho bajo; no se escala la fila de acoplamiento\n";
    else if (!global.filaGlobalEscalada && std::abs(global.gammaCandidato - 1.0) > 1e-12)
        cout << "  motivo gamma=1       = candidato cercano a identidad; no se aplica escalamiento marginal\n";

    if (!global.advertencias.empty()) {
        cout << "\nADVERTENCIAS:\n";
        for (const auto& w : global.advertencias)
            cout << "  [!] " << w << "\n";
    }

    if (cfg.solodiagnostico)
        cout << "\n[Modo diagnostico: no se modifico el modelo]\n";

    cout << sep << "\n\n";
}

void PreprocesamientoMIP::imprimirReporteComparativo(
    const vector<DiagnosticoBloque>& bloquesAntes,
    const DiagnosticoGlobal& globalAntes) const {

    const string sep(60, '-');
    auto ratio = [](double antes, double despues) -> double {
        if (antes <= 0.0) return 0.0;
        return despues / antes;
    };

    cout << sep << "\n";
    cout << "  COMPARACION NUMERICA ANTES / DESPUES\n";
    cout << sep << "\n";
    cout << left << setw(28) << "Indicador"
         << setw(16) << "antes"
         << setw(16) << "despues"
         << "despues/antes\n";
    cout << string(76, '-') << "\n";
    cout << left << setw(28) << "rango global"
         << setw(16) << scientific << setprecision(3) << globalAntes.kappaTotal
         << setw(16) << scientific << setprecision(3) << global.kappaTotal
         << scientific << setprecision(3) << ratio(globalAntes.kappaTotal, global.kappaTotal) << "\n";
    cout << left << setw(28) << "rho acoplamiento"
         << setw(16) << scientific << setprecision(3) << globalAntes.rhoAprox
         << setw(16) << scientific << setprecision(3) << global.rhoAprox
         << scientific << setprecision(3) << ratio(globalAntes.rhoAprox, global.rhoAprox) << "\n";
    cout << left << setw(28) << "gamma aplicado"
         << setw(16) << fixed << setprecision(6) << 1.0
         << setw(16) << fixed << setprecision(6) << global.gamma
         << fixed << setprecision(6) << global.gamma << "\n";

    cout << "\nBloques locales:\n";
    cout << left << setw(20) << "Bloque"
         << setw(16) << "kappa antes"
         << setw(16) << "kappa despues"
         << setw(12) << "alpha"
         << setw(12) << "beta"
         << setw(12) << "filas"
         << setw(12) << "cols"
         << setw(12) << "disc_omit"
         << setw(12) << "aux_omit"
         << "escalado\n";
    cout << string(132, '-') << "\n";

    for (size_t i = 0; i < bloques.size(); ++i) {
        const auto& despues = bloques[i];
        double kappaAntes = (i < bloquesAntes.size()) ? bloquesAntes[i].kappaAprox : 0.0;
        cout << left << setw(20) << despues.nombre;
        if (despues.indicesRestricciones.empty()) {
            cout << setw(16) << "N/A"
                 << setw(16) << "N/A";
        } else {
            cout << setw(16) << scientific << setprecision(3) << kappaAntes
                 << setw(16) << scientific << setprecision(3) << despues.kappaAprox;
        }
        cout << setw(12) << scientific << setprecision(3) << despues.alpha
             << setw(12) << scientific << setprecision(3) << despues.betaBloque
             << setw(12) << fixed << setprecision(0) << despues.filasEscaladas
             << setw(12) << fixed << setprecision(0) << despues.columnasEscaladas
             << setw(12) << fixed << setprecision(0) << despues.columnasDiscretasOmitidas
             << setw(12) << fixed << setprecision(0) << despues.columnasAuxiliaresOmitidas
             << (despues.escalado ? "SI" : "no") << "\n";
    }

    cout << "\nInterpretacion: valores despues/antes menores que 1 indican mejora del proxy.\n";
    cout << "rho se calcula solo con filas de acoplamiento; las cotas de demanda sobre g quedan fuera.\n";
    if (cfg.usarEquilibradoRuiz) {
        cout << "El escalamiento local activo fue Ruiz aproximado: filas internas iterativas"
             << (cfg.escalarColumnasContinuas ? " y columnas continuas con recuperacion de solucion.\n" : ".\n");
        if (cfg.escalarColumnasContinuas)
            cout << "Las columnas binarias/discretas no se transforman: una columna x binaria conservaria dominio {0,1} y no admite x=s*y sin cambiar el MIP.\n"
                 << "Tampoco se transforman columnas de bloques auxiliares sin prefijo de agente, para no reparametrizar variables globales o de despacho fuera de A_i.\n";
    } else if (cfg.escalamientoLocalPorFila && cfg.normalizarBloqueTrasFilas)
        cout << "El escalamiento local activo fue estructurado: alpha_r interno y beta_i entre bloques.\n";
    else if (cfg.escalamientoLocalPorFila)
        cout << "El escalamiento local activo fue solo por fila: alpha_r = 1/sqrt(M_r*m_r).\n";
    else
        cout << "El escalamiento local activo fue escalar por bloque: alpha_i = 1/sqrt(M_i*m_i).\n";
    cout << sep << "\n\n";
}

// ============================================================
// Helpers
// ============================================================

string PreprocesamientoMIP::extraerPrefijo(const string& nombre) {
    size_t pos = nombre.find('_');
    if (pos == string::npos) return nombre;
    return nombre.substr(0, pos);
}

string PreprocesamientoMIP::extraerPrefijoAgente(const string& nombreVariable) {
    string prefLocal = extraerPrefijoAgenteLocal(nombreVariable);
    if (!prefLocal.empty()) return prefLocal;

    string prefGen = extraerPrefijoGeneracion(nombreVariable);
    if (prefGen.empty()) return "";
    return "a" + prefGen.substr(1) + "_";
}

string PreprocesamientoMIP::extraerPrefijoAgenteLocal(const string& nombreVariable) {
    if (nombreVariable.size() < 3 || nombreVariable[0] != 'a') return "";

    size_t i = 1;
    while (i < nombreVariable.size() &&
           std::isdigit(static_cast<unsigned char>(nombreVariable[i]))) {
        ++i;
    }

    if (i == 1 || i >= nombreVariable.size() || nombreVariable[i] != '_') {
        return "";
    }

    return nombreVariable.substr(0, i + 1);
}

string PreprocesamientoMIP::extraerPrefijoGeneracion(const string& nombreVariable) {
    if (nombreVariable.size() >= 3 && nombreVariable[0] == 'g' &&
        std::isdigit(static_cast<unsigned char>(nombreVariable[1]))) {
        size_t i = 1;
        while (i < nombreVariable.size() &&
               std::isdigit(static_cast<unsigned char>(nombreVariable[i]))) {
            ++i;
        }
        if (i > 1 && i < nombreVariable.size() && nombreVariable[i] == '(') {
            return nombreVariable.substr(0, i);
        }
    }

    return "";
}

bool PreprocesamientoMIP::empiezaCon(const string& s, const string& prefijo) {
    return s.size() >= prefijo.size() &&
           s.compare(0, prefijo.size(), prefijo) == 0;
}
