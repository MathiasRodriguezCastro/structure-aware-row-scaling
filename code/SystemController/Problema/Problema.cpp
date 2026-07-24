#include "SystemController/Problema/Problema.h"
#include "SystemController/Problema/PreprocesamientoMIP/PreprocesamientoMIP.h"
#include <stdexcept>
#include <algorithm>
#include <cctype>
#include <cmath>
#include <iostream>
#include <iomanip>
#include <fstream>
#include <random>
#include <chrono>
#include <limits>
#include <map>
#include <regex>
#include <set>
#include <sstream>

Problema::~Problema() {
    for (auto* p : variables)               delete p;
    for (auto* p : restricciones)           delete p;
    for (auto* p : binarios)                delete p;
    for (auto* p : terminosFuncionObjetivo) delete p;
}

namespace {

std::string normalizarNombreOpcion(const std::string& nombre) {
    std::string out;
    for (unsigned char c : nombre) {
        if (std::isalnum(c)) {
            out.push_back(static_cast<char>(std::tolower(c)));
        }
    }
    return out;
}

std::string nombresValidosPreprocesamiento() {
    return "Ninguno, Diagnostico, Estructurado, Filas, Bloque, Ruiz, RuizColumnas, NormalizacionFisica";
}

std::string formatearSegundos(double segundos) {
    std::ostringstream oss;
    oss << std::fixed << std::setprecision(6) << segundos;
    return oss.str();
}

PreprocesamientoMIP::Config configPreprocesamientoPorNombre(const std::string& canonico) {
    PreprocesamientoMIP::Config cfg;
    cfg.verbose = true;

    if (canonico == "Ninguno") {
        return cfg;
    }
    if (canonico == "Diagnostico") {
        cfg.solodiagnostico = true;
        return cfg;
    }
    if (canonico == "Estructurado") {
        cfg.escalamientoLocalPorFila = true;
        cfg.normalizarBloqueTrasFilas = true;
        cfg.usarEquilibradoRuiz = false;
        return cfg;
    }
    if (canonico == "Filas") {
        cfg.escalamientoLocalPorFila = true;
        cfg.normalizarBloqueTrasFilas = false;
        cfg.usarEquilibradoRuiz = false;
        return cfg;
    }
    if (canonico == "Bloque") {
        cfg.escalamientoLocalPorFila = false;
        cfg.normalizarBloqueTrasFilas = false;
        cfg.usarEquilibradoRuiz = false;
        return cfg;
    }
    if (canonico == "Ruiz") {
        cfg.usarEquilibradoRuiz = true;
        cfg.escalamientoLocalPorFila = true;
        cfg.normalizarBloqueTrasFilas = true;
        return cfg;
    }
    if (canonico == "RuizColumnas") {
        cfg.usarEquilibradoRuiz = true;
        cfg.escalamientoLocalPorFila = true;
        cfg.normalizarBloqueTrasFilas = true;
        cfg.escalarColumnasContinuas = true;
        cfg.normalizacionFisica = true;
        return cfg;
    }
    if (canonico == "NormalizacionFisica") {
        cfg.escalamientoLocalPorFila = true;
        cfg.normalizarBloqueTrasFilas = true;
        cfg.normalizacionFisica = true;
        return cfg;
    }

    throw std::invalid_argument(
        "configPreprocesamientoPorNombre - preprocesamiento no reconocido: " + canonico
    );
}

} // namespace

void Problema::habilitarPreprocesamiento(const std::string& nombre) {
    const std::string clave = normalizarNombreOpcion(nombre);

    static const std::map<std::string, std::string> aliases = {
        {"", "Ninguno"},
        {"ninguno", "Ninguno"},
        {"none", "Ninguno"},
        {"sinpreprocesamiento", "Ninguno"},
        {"diagnostico", "Diagnostico"},
        {"solodiagnostico", "Diagnostico"},
        {"estructurado", "Estructurado"},
        {"localestructurado", "Estructurado"},
        {"filas", "Filas"},
        {"fila", "Filas"},
        {"localfilas", "Filas"},
        {"bloque", "Bloque"},
        {"bloques", "Bloque"},
        {"localbloque", "Bloque"},
        {"ruiz", "Ruiz"},
        {"localruiz", "Ruiz"},
        {"ruizcolumnas", "RuizColumnas"},
        {"ruizcolumnascontinuas", "RuizColumnas"},
        {"columnascontinuas", "RuizColumnas"},
        {"normalizacionfisica", "NormalizacionFisica"},
        {"normalizacion", "NormalizacionFisica"},
        {"fisica", "NormalizacionFisica"}
    };

    auto it = aliases.find(clave);
    if (it == aliases.end()) {
        throw std::invalid_argument(
            "Problema::habilitarPreprocesamiento - preprocesamiento no reconocido: '" +
            nombre + "'. Opciones reconocidas actualmente: " + nombresValidosPreprocesamiento() +
            ". Para agregar nuevas opciones, registre un alias y una Config en Problema.cpp."
        );
    }

    preprocesamientoSeleccionado = it->second;
    preprocesamientoSeleccionadoAplicado = false;
}

void Problema::habilitarEstrategiaResolucion(const std::string& nombre) {
    const std::string clave = normalizarNombreOpcion(nombre);

    static const std::map<std::string, std::string> aliases = {
        {"", "Monolitica"},
        {"monolitica", "Monolitica"},
        {"monolitico", "Monolitica"},
        {"default", "Monolitica"}
    };

    auto it = aliases.find(clave);
    if (it == aliases.end()) {
        throw std::invalid_argument(
            "Problema::habilitarEstrategiaResolucion - estrategia no reconocida: '" +
            nombre + "'. Opciones reconocidas actualmente: Monolitica."
        );
    }

    estrategiaResolucionSeleccionada = it->second;
}

const std::string& Problema::getPreprocesamientoSeleccionado() const {
    return preprocesamientoSeleccionado;
}

const std::string& Problema::getEstrategiaResolucionSeleccionada() const {
    return estrategiaResolucionSeleccionada;
}

void Problema::aplicarPreprocesamientoSeleccionado() {
    if (preprocesamientoSeleccionadoAplicado) {
        return;
    }

    if (preprocesamientoSeleccionado == "Ninguno") {
        std::cout << "[pipeline] Preprocesamiento seleccionado: Ninguno" << std::endl;
        std::cout << "[pipeline] Modelo interno sin modificaciones de preprocesamiento." << std::endl;
        preprocesamientoSeleccionadoAplicado = true;
        return;
    }

    auto inicio = std::chrono::high_resolution_clock::now();
    std::cout << "[pipeline] Preprocesamiento seleccionado: "
              << preprocesamientoSeleccionado << std::endl;

    PreprocesamientoMIP::Config cfg = configPreprocesamientoPorNombre(preprocesamientoSeleccionado);
    PreprocesamientoMIP prep(*this, cfg);
    prep.registrarRestriccionGlobal({
        "gh_total",
        "gen_menor_demanda",
        "falla_tramo",
        "balance_",
        "demanda_",
        "falla_",
        "deficit_"
    });
    prep.registrarRestriccionAcoplamiento({
        "gh_total",
        "balance_"
    });

    if (cfg.solodiagnostico) {
        prep.diagnosticar();
        std::cout << "[pipeline] Diagnostico de preprocesamiento ejecutado; modelo sin modificar." << std::endl;
    } else {
        prep.ejecutar();
        std::cout << "[pipeline] Preprocesamiento aplicado efectivamente: "
                  << preprocesamientoSeleccionado << std::endl;
    }

    auto fin = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> duracion = fin - inicio;
    std::cout << "[pipeline] Tiempo de preprocesamiento: "
              << formatearSegundos(duracion.count()) << " s" << std::endl;

    preprocesamientoSeleccionadoAplicado = true;
}

void Problema::resolver() {
    aplicarPreprocesamientoSeleccionado();

    std::cout << "[pipeline] Estrategia de resolucion seleccionada: "
              << estrategiaResolucionSeleccionada << std::endl;

    auto inicio = std::chrono::high_resolution_clock::now();
    std::cout << "[pipeline] Resolviendo monoliticamente." << std::endl;
    resolverMonolitico();

    auto fin = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> duracion = fin - inicio;
    std::cout << "[pipeline] Tiempo de resolucion: "
              << formatearSegundos(duracion.count()) << " s" << std::endl;
}

// --- Variables ---
void Problema::añadirVariable(const std::string& nombre, int tipoCota, double cotaInf, double cotaSup) {
    variables.emplace_back(new Variable(nombre, tipoCota, cotaInf, cotaSup));
}

std::vector<Variable*>& Problema::getVariables() {
    return variables;
}

// --- Restricciones ---
void Problema::añadirRestriccion(const std::string& nombre,
                                  std::vector<std::pair<double, std::string>> terminos,
                                  const std::string& operador,
                                  double terminoIndependiente) {
    restricciones.emplace_back(
        new Restriccion(nombre, std::move(terminos), operador, terminoIndependiente));
}

std::vector<Restriccion*>& Problema::getRestricciones() {
    return restricciones;
}

// --- Binarios ---
void Problema::añadirBinario(const std::string& nombre) {
    binarios.emplace_back(new Binario(nombre));
}

std::vector<Binario*>& Problema::getBinarios() {
    return binarios;
}

void Problema::transformarVariablesAReales() {
    std::vector<Binario*> binariosOriginales = binarios;
    binarios.clear();

    for (std::size_t i = 0; i < binariosOriginales.size(); ++i) {
        Binario* bin = binariosOriginales[i];
        if (bin == nullptr) continue;

        añadirVariable(bin->getNombre(), 0, 0.0, 1.0);
        delete bin;
    }
}

// --- Función objetivo ---
void Problema::añadirTerminoFuncionObjetivo(double coef, const std::string& var) {
    AporteFuncionObjetivo* termino = new AporteFuncionObjetivo(coef, var);
    terminosFuncionObjetivo.emplace_back(termino);
}

void Problema::sumarConstanteFuncionObjetivo(double valor) {
    constanteFuncionObjetivo += valor;
    flagConstanteFuncionObjetivo = true;
}

// --- Términos de la función objetivo ---
std::vector<AporteFuncionObjetivo*>& Problema::getTerminosFuncionObjetivo() {
    return terminosFuncionObjetivo;
}

std::vector<std::pair<double, std::string>> Problema::getParesTerminosFuncionObjetivo() {
    std::vector<std::pair<double, std::string>> pares;
    for (const auto& termino : terminosFuncionObjetivo) {
        pares.emplace_back(termino->getCoeficiente(), termino->getVariable());
    }
    return pares;
}

// --- Getters y Setters ---
void Problema::setValoresVariables(std::map<std::string, double>& valores) {
    valoresVariables = valores;
}

std::map<std::string, double>& Problema::getValoresVariables() {
    return valoresVariables;
}

void Problema::registrarEscalamientoVariableSolucion(const std::string& nombre,
                                                     double factorOriginalPorInterna) {
    if (factorOriginalPorInterna <= 0.0 || factorOriginalPorInterna == 1.0) {
        return;
    }
    auto it = escalasSolucionVariables.find(nombre);
    if (it == escalasSolucionVariables.end()) {
        escalasSolucionVariables[nombre] = factorOriginalPorInterna;
    } else {
        it->second *= factorOriginalPorInterna;
    }
}

void Problema::aplicarEscalamientoValoresSolucion() {
    for (const auto& [nombre, escala] : escalasSolucionVariables) {
        auto it = valoresVariables.find(nombre);
        if (it != valoresVariables.end()) {
            it->second *= escala;
        }
    }
}

double Problema::getFactorOriginalPorInterna(const std::string& nombre) const {
    auto it = escalasSolucionVariables.find(nombre);
    if (it == escalasSolucionVariables.end() || it->second == 0.0) {
        return 1.0;
    }
    return it->second;
}

void Problema::guardarModeloOriginalParaVerificacion() {
    if (snapshotOriginalDisponible) {
        return;
    }

    variablesOriginales.clear();
    restriccionesOriginales.clear();
    binariosOriginales.clear();
    terminosFuncionObjetivoOriginal.clear();

    for (const auto* v : variables) {
        if (!v) continue;
        variablesOriginales.push_back({v->getNombre(), v->getTipoCota(), v->getCotaInf(), v->getCotaSup()});
    }
    for (const auto* r : restricciones) {
        if (!r) continue;
        restriccionesOriginales.push_back({
            r->getNombre(),
            r->getTerminos(),
            r->getOperador(),
            r->getTerminoIndependiente()
        });
    }
    for (const auto* b : binarios) {
        if (b) binariosOriginales.push_back(b->getNombre());
    }
    for (const auto* t : terminosFuncionObjetivo) {
        if (t) terminosFuncionObjetivoOriginal.emplace_back(t->getCoeficiente(), t->getVariable());
    }
    constanteFuncionObjetivoOriginal = constanteFuncionObjetivo;
    snapshotOriginalDisponible = true;
}

void Problema::restaurarDesdeSnapshotOriginal() {
    if (!snapshotOriginalDisponible) return;
    if (restricciones.size() != restriccionesOriginales.size()) return;  // estructura cambiada
    for (size_t i = 0; i < restricciones.size(); ++i) {
        if (!restricciones[i]) continue;
        restricciones[i]->setTerminos(restriccionesOriginales[i].terminos);
        restricciones[i]->setTerminoIndependiente(restriccionesOriginales[i].rhs);
    }
}

void Problema::setVerificarModeloOriginalActivo(bool activo) {
    verificarModeloOriginalActivo = activo;
}

bool Problema::getVerificarModeloOriginalActivo() const {
    return verificarModeloOriginalActivo;
}

bool Problema::tieneModeloOriginalParaVerificacion() const {
    return snapshotOriginalDisponible;
}

Problema::ResultadoVerificacionOriginal Problema::verificarFactibilidadOriginal(
    const std::map<std::string, double>& valores,
    bool incluirConstanteObjetivo
) const {
    ResultadoVerificacionOriginal res;
    if (!snapshotOriginalDisponible) {
        return res;
    }
    res.disponible = true;

    constexpr double tol = 1e-6;
    auto valor = [&](const std::string& nombre, int& faltantes) -> double {
        auto it = valores.find(nombre);
        if (it == valores.end()) {
            ++faltantes;
            return 0.0;
        }
        return it->second;
    };

    std::vector<double> violacionesFilas;          // viol. absoluta por restricción (≤,≥,=)
    violacionesFilas.reserve(restriccionesOriginales.size());
    for (const auto& r : restriccionesOriginales) {
        int faltantesFila = 0;
        double lhs = 0.0;
        double actividad = 0.0;   // Σ_j |a_rj · x_j| (refinamiento R5)
        for (const auto& [coef, var] : r.terminos) {
            double contrib = coef * valor(var, faltantesFila);
            lhs += contrib;
            actividad += std::abs(contrib);
        }
        res.variablesFaltantes += faltantesFila;

        double viol = 0.0;
        if (r.operador == "<=") {
            viol = std::max(0.0, lhs - r.rhs);
            if (viol > tol) ++res.restriccionesMenorIgualVioladas;
            if (viol > res.maxViolacionMenorIgual) {
                res.maxViolacionMenorIgual = viol;
                res.peorRestriccionMenorIgual = r.nombre;
            }
        } else if (r.operador == ">=") {
            viol = std::max(0.0, r.rhs - lhs);
            if (viol > tol) ++res.restriccionesMayorIgualVioladas;
            if (viol > res.maxViolacionMayorIgual) {
                res.maxViolacionMayorIgual = viol;
                res.peorRestriccionMayorIgual = r.nombre;
            }
        } else if (r.operador == "=") {
            viol = std::abs(lhs - r.rhs);
            if (viol > tol) ++res.igualdadesVioladas;
            if (viol > res.maxViolacionIgualdad) {
                res.maxViolacionIgualdad = viol;
                res.peorIgualdad = r.nombre;
            }
        }

        // Clasificación demanda vs local para las métricas DW de reconstrucción.
        if (r.nombre.rfind("gen_menor_demanda", 0) == 0)
            res.maxViolacionDemanda = std::max(res.maxViolacionDemanda, viol);
        else
            res.maxViolacionLocal = std::max(res.maxViolacionLocal, viol);

        // Estadísticos: guardar la violación y actualizar la máxima relativa a la escala
        // de la fila (|rhs| como proxy de magnitud; +1 evita dividir por cero).
        violacionesFilas.push_back(viol);
        res.maxViolacionRelativa = std::max(res.maxViolacionRelativa,
                                            viol / (1.0 + std::abs(r.rhs)));
        // Refinamiento R5: normalizar por la ACTIVIDAD de la fila, max{1,|rhs|,Σ|a·x|}.
        // Corrige el sub-normalizado de (1+|rhs|) en filas de actividad grande y RHS chico
        // (balances con RHS≈0), donde el denominador RHS-only se reduce al residuo absoluto.
        double denomActividad = std::max(1.0, std::max(std::abs(r.rhs), actividad));
        res.maxViolacionRelativaActividad = std::max(res.maxViolacionRelativaActividad,
                                                     viol / denomActividad);
    }

    // Promedio y percentiles (p95, p99) de la violación de restricciones sobre TODAS las filas.
    if (!violacionesFilas.empty()) {
        double suma = 0.0;
        for (double v : violacionesFilas) suma += v;
        res.avgViolacionRestricciones = suma / violacionesFilas.size();
        std::sort(violacionesFilas.begin(), violacionesFilas.end());
        auto percentil = [&](double p) {
            double idx = p * (violacionesFilas.size() - 1);
            std::size_t lo = static_cast<std::size_t>(idx);
            std::size_t hi = std::min(lo + 1, violacionesFilas.size() - 1);
            double frac = idx - lo;
            return violacionesFilas[lo] * (1.0 - frac) + violacionesFilas[hi] * frac;
        };
        res.p95ViolacionRestricciones = percentil(0.95);
        res.p99ViolacionRestricciones = percentil(0.99);
    }

    for (const auto& v : variablesOriginales) {
        int faltantesVar = 0;
        double x = valor(v.nombre, faltantesVar);
        res.variablesFaltantes += faltantesVar;

        if (v.tipoCota == 0 || v.tipoCota == 2) {
            double viol = std::max(0.0, v.cotaInf - x);
            if (viol > tol) ++res.cotasInfVioladas;
            if (viol > res.maxViolacionCotaInf) {
                res.maxViolacionCotaInf = viol;
                res.peorCotaInf = v.nombre;
            }
        }
        if (v.tipoCota == 0 || v.tipoCota == 1) {
            double viol = std::max(0.0, x - v.cotaSup);
            if (viol > tol) ++res.cotasSupVioladas;
            if (viol > res.maxViolacionCotaSup) {
                res.maxViolacionCotaSup = viol;
                res.peorCotaSup = v.nombre;
            }
        }
    }

    for (const auto& nombre : binariosOriginales) {
        int faltantesVar = 0;
        double x = valor(nombre, faltantesVar);
        res.variablesFaltantes += faltantesVar;

        double violInf = std::max(0.0, -x);
        double violSup = std::max(0.0, x - 1.0);
        if (violInf > tol) ++res.cotasInfVioladas;
        if (violSup > tol) ++res.cotasSupVioladas;
        if (violInf > res.maxViolacionCotaInf) {
            res.maxViolacionCotaInf = violInf;
            res.peorCotaInf = nombre;
        }
        if (violSup > res.maxViolacionCotaSup) {
            res.maxViolacionCotaSup = violSup;
            res.peorCotaSup = nombre;
        }

        double violInt = std::abs(x - std::round(x));
        if (violInt > tol) ++res.integridadViolada;
        if (violInt > res.maxViolacionIntegridad) {
            res.maxViolacionIntegridad = violInt;
            res.peorIntegridad = nombre;
        }
    }

    for (const auto& [coef, var] : terminosFuncionObjetivoOriginal) {
        int faltantesObj = 0;
        res.objetivoOriginalRecalculado += coef * valor(var, faltantesObj);
        res.variablesFaltantes += faltantesObj;
    }
    if (incluirConstanteObjetivo) {
        res.objetivoOriginalRecalculado += constanteFuncionObjetivoOriginal;
    }

    return res;
}

void Problema::imprimirVerificacionFactibilidadOriginal(
    const std::string& etiqueta,
    const std::map<std::string, double>& valores,
    bool incluirConstanteObjetivo
) const {
    if (!snapshotOriginalDisponible) {
        return;
    }

    auto r = verificarFactibilidadOriginal(valores, incluirConstanteObjetivo);
    std::cerr << std::setprecision(15)
              << "[VERIF ORIGINAL] etapa=" << etiqueta
              << " max_le=" << r.maxViolacionMenorIgual << " (" << r.peorRestriccionMenorIgual << ")"
              << " max_ge=" << r.maxViolacionMayorIgual << " (" << r.peorRestriccionMayorIgual << ")"
              << " max_eq=" << r.maxViolacionIgualdad << " (" << r.peorIgualdad << ")"
              << " max_lb=" << r.maxViolacionCotaInf << " (" << r.peorCotaInf << ")"
              << " max_ub=" << r.maxViolacionCotaSup << " (" << r.peorCotaSup << ")"
              << " max_int=" << r.maxViolacionIntegridad << " (" << r.peorIntegridad << ")"
              << " avg_viol=" << r.avgViolacionRestricciones
              << " p95_viol=" << r.p95ViolacionRestricciones
              << " p99_viol=" << r.p99ViolacionRestricciones
              << " max_viol_rel=" << r.maxViolacionRelativa
              << " max_viol_relact=" << r.maxViolacionRelativaActividad
              << " viol_le_count=" << r.restriccionesMenorIgualVioladas
              << " viol_ge_count=" << r.restriccionesMayorIgualVioladas
              << " viol_eq_count=" << r.igualdadesVioladas
              << " viol_lb_count=" << r.cotasInfVioladas
              << " viol_ub_count=" << r.cotasSupVioladas
              << " viol_int_count=" << r.integridadViolada
              << " missing_values=" << r.variablesFaltantes
              << " obj_original_recalc=" << r.objetivoOriginalRecalculado
              << std::endl;
}

void Problema::setValorFuncionObjetivo(double valor) {
    valorFuncionObjetivo = valor;
}

double Problema::getValorFuncionObjetivo() {
    return valorFuncionObjetivo;
}

void Problema::setFlagConstanteFuncionObjetivo(bool flag) {
    flagConstanteFuncionObjetivo = flag;
}

bool Problema::getFlagConstanteFuncionObjetivo() {
    return flagConstanteFuncionObjetivo;
}

double Problema::getConstanteFuncionObjetivo() {
    return constanteFuncionObjetivo;
}

double Problema::obtenerConstante(const std::string& nombre) {
    for (std::size_t i = 0; i < restricciones.size(); ++i) {
        if (restricciones[i]->getNombre() == nombre) {
            return restricciones[i]->getTerminoIndependiente();
        }
    }
    throw std::runtime_error("Problema::obtenerConstante() - Restricción con nombre '" + nombre + "' no encontrada");
}
