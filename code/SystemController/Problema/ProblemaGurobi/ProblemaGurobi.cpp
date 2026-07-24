#include "gurobi_c++.h"
#include "ProblemaGurobi.h"
#include <sstream>
#include <iostream>
#include <cstdlib>
#include <fstream>
#include <algorithm>
#include <cctype>
#include <cmath>
#include <iomanip>
#include <limits>
#include <regex>
#include <set>
#include <map>

namespace {

bool esBinaria(const std::set<std::string>& binarias, const std::string& nombre) {
    return binarias.find(nombre) != binarias.end();
}

double cotaInfVariable(const Variable* v) {
    if (v->getTipoCota() == 1 || v->getTipoCota() == 3) return -GRB_INFINITY;
    return v->getCotaInf();
}

double cotaSupVariable(const Variable* v) {
    if (v->getTipoCota() == 2 || v->getTipoCota() == 3) return GRB_INFINITY;
    return v->getCotaSup();
}

GRBVar crearVariableGurobi(GRBModel& m, const Variable* v, bool binaria) {
    if (binaria) {
        return m.addVar(0.0, 1.0, 0.0, GRB_BINARY, v->getNombre());
    }
    return m.addVar(
        cotaInfVariable(v),
        cotaSupVariable(v),
        0.0,
        GRB_CONTINUOUS,
        v->getNombre()
    );
}

// Callback de SOLO LECTURA: registra la cota dual y el tiempo al terminar el nodo raíz del
// B&B, y acumula el GAP RELATIVO MEDIO sobre el horizonte observado del callback. No agrega
// cortes ni lazy constraints, por lo que no altera la búsqueda (solo un overhead mínimo).
// Best-effort: si algún info no está disponible, los campos quedan en su valor centinela.
class MonitorCallback : public GRBCallback {
public:
    double rootBound  = -GRB_INFINITY;  // mejor cota dual al final de la raíz
    double rootObjBst =  GRB_INFINITY;  // incumbente (puede no existir aún en la raíz)
    double rootTime   = -1.0;           // tiempo de pared al final de la raíz
    bool   capturada  = false;
    // Área de γ(t) vs tiempo por trapecios; integralPrimal() la normaliza por tFinal.
    double integral   = 0.0;
    double ultimoT    = -1.0;
    double ultimoGap  = 1.0;
    double tFinal     = 0.0;
protected:
    static double gapRel(double bst, double bnd) {
        if (std::fabs(bst) >= 1e30 || std::fabs(bnd) >= 1e30) return 1.0;  // sin incumbente/cota
        double g = std::fabs(bst - bnd) / (std::fabs(bst) + 1e-10);
        return g < 0.0 ? 0.0 : (g > 1.0 ? 1.0 : g);
    }
    void acumularIntegral(double t, double gap) {
        if (ultimoT >= 0.0 && t > ultimoT)
            integral += 0.5 * (gap + ultimoGap) * (t - ultimoT);
        ultimoT = t; ultimoGap = gap; tFinal = t;
    }
    void callback() override {
        try {
            if (where == GRB_CB_MIP) {
                double bst = getDoubleInfo(GRB_CB_MIP_OBJBST);
                double bnd = getDoubleInfo(GRB_CB_MIP_OBJBND);
                double t   = getDoubleInfo(GRB_CB_RUNTIME);
                acumularIntegral(t, gapRel(bst, bnd));
            } else if (!capturada && where == GRB_CB_MIPNODE) {
                const int nodecount =
                    static_cast<int>(getDoubleInfo(GRB_CB_MIPNODE_NODCNT));
                if (nodecount <= 0) {
                    rootBound = getDoubleInfo(GRB_CB_MIPNODE_OBJBND);
                    try { rootObjBst = getDoubleInfo(GRB_CB_MIPNODE_OBJBST); } catch (...) {}
                    try { rootTime   = getDoubleInfo(GRB_CB_RUNTIME); } catch (...) {}
                } else {
                    capturada = true;   // ya pasamos la raíz: lo capturado en nodecount 0 es definitivo
                }
            }
        } catch (...) { /* best-effort, sin alterar la resolución */ }
    }
public:
    double integralPrimal() const { return tFinal > 0.0 ? integral / tFinal : -1.0; }
};

} // namespace

ProblemaGurobi::ProblemaGurobi() : env(nullptr), modelo(nullptr) {
    try {
        env = new GRBEnv();
        modelo = new GRBModel(*env);
    } catch (GRBException &e) {
        delete env;
        env = nullptr;
        modelo = nullptr;
        throw std::runtime_error(std::string("Error al inicializar Gurobi: ") + e.getMessage());
    } catch (...) {
        delete env;
        env = nullptr;
        modelo = nullptr;
        throw std::runtime_error("Error desconocido al inicializar Gurobi");
    }
}

ProblemaGurobi::~ProblemaGurobi() {
    delete modelo;
    delete env;
}

// --- Exportación ---
void ProblemaGurobi::procesar(bool flagConstante) {
    flagConstanteFuncionObjetivo = flagConstante;
    
    // 1. Variables continuas
    for (const auto* variable : variables) {
        vars.emplace(variable->getNombre(), crearVariableGurobi(*modelo, variable, false));
    }
    
    // 2. Variables binarias
    for (const auto* binario : binarios) {
        vars.emplace(binario->getNombre(),
                     modelo->addVar(0.0, 1.0, 0.0, GRB_BINARY, binario->getNombre()));
    }

    // 3. Restricciones
    for (const auto& restriccion : restricciones) {
        GRBLinExpr expr = 0.0;

        const auto& terminos = restriccion->getTerminos();

        for (size_t i = 0; i < terminos.size(); i++) {
            expr += terminos[i].first * vars[terminos[i].second];
        }

        if (restriccion->getOperador() == "<=") {
            modelo->addConstr(
                expr,
                GRB_LESS_EQUAL,
                restriccion->getTerminoIndependiente(),
                restriccion->getNombre()
            );
        } else if (restriccion->getOperador() == ">=") {
            modelo->addConstr(
                expr,
                GRB_GREATER_EQUAL,
                restriccion->getTerminoIndependiente(),
                restriccion->getNombre()
            );
        } else if (restriccion->getOperador() == "=") {
            modelo->addConstr(
                expr,
                GRB_EQUAL,
                restriccion->getTerminoIndependiente(),
                restriccion->getNombre()
            );
        }
    }

    // 4. Función objetivo
    GRBLinExpr funcion_objetivo = 0.0;

    for (const auto& termino : terminosFuncionObjetivo) {
        funcion_objetivo += termino->getCoeficiente() * vars[termino->getVariable()];
    }

    if (flagConstante && constanteFuncionObjetivo != 0.0) {
        funcion_objetivo += constanteFuncionObjetivo;
    }
    
    modelo->setObjective(funcion_objetivo, GRB_MINIMIZE);
}

void ProblemaGurobi::resolverMonolitico() {
    try {
        // Aplicar configuración del solver
        if (config.timeoutSegundos > 0.0) {
            modelo->set(GRB_DoubleParam_TimeLimit, config.timeoutSegundos);
        }
        modelo->set(GRB_DoubleParam_MIPGap, config.mipGap);

        // Baseline de escalado interno del solver (R1): permite contrastar el escalado
        // generator-aware externo contra las opciones nativas de Gurobi. Solo se toca si el
        // usuario pasó --scaleflag; en caso contrario Gurobi usa su default (-1, automático).
        if (config.scaleFlagGurobi != SolverConfig::SOLVER_PARAM_AUTO) {
            modelo->set(GRB_IntParam_ScaleFlag, config.scaleFlagGurobi);
        }

        // Reproducibilidad: semilla fija y, si el entorno la define (SLURM OMP_NUM_THREADS),
        // número de hilos fijo. Con semilla + hilos fijos Gurobi es determinista.
        // El default sigue siendo 1 (la semilla con la que se produjeron todos los resultados
        // publicados); --seed N la cambia para estimar la variabilidad corrida-a-corrida.
        modelo->set(GRB_IntParam_Seed,
                    config.semillaSolver != SolverConfig::SOLVER_PARAM_AUTO
                        ? config.semillaSolver
                        : 1);
        if (const char* h = std::getenv("OMP_NUM_THREADS")) {
            try { int nh = std::stoi(h); if (nh > 0) modelo->set(GRB_IntParam_Threads, nh); }
            catch (...) {}
        }

        // Callback de solo lectura: métricas del nodo raíz + integral primal–dual.
        MonitorCallback cbMonitor;
        modelo->setCallback(&cbMonitor);

        modelo->optimize();

        modelo->setCallback(nullptr);

        if (modelo->get(GRB_IntAttr_SolCount) <= 0) {
            throw std::runtime_error(
                "ProblemaGurobi::resolverMonolitico - Sin solución feasible. "
                "Status Gurobi: " + std::to_string(modelo->get(GRB_IntAttr_Status)));
        }

        for (auto &p : vars) {
            valoresVariables[p.first] = p.second.get(GRB_DoubleAttr_X);
        }
        valorFuncionObjetivo = modelo->get(GRB_DoubleAttr_ObjVal);
        aplicarEscalamientoValoresSolucion();

        // --- Número de condición de la base óptima reportado por el solver ---
        // κ real de la base símplex (atributos Kappa/KappaExact de Gurobi), distinto del
        // estimador de dispersión κ̂ que calcula PreprocesamientoMIP. Para un MIP se fija la
        // solución entera (fixedModel) y se resuelve el LP con símplex para disponer de una
        // base; para un LP se consulta directo. Best-effort: si no hay base, queda -1.
        // Esta medición ocurre DESPUÉS del cronómetro del solver, así que no altera T_solver.
        double kappaSolver = -1.0, kappaExact = -1.0;
        int esMip = 0;
        try {
            esMip = modelo->get(GRB_IntAttr_IsMIP);
            // KappaExact factoriza la base: solo en modelos no demasiado grandes.
            const long tamano = static_cast<long>(modelo->get(GRB_IntAttr_NumVars)) +
                                static_cast<long>(modelo->get(GRB_IntAttr_NumConstrs));
            const bool calcularExacto = tamano <= 10000;
            if (esMip) {
                GRBModel fijo = modelo->fixedModel();
                fijo.set(GRB_IntParam_OutputFlag, 0);
                fijo.set(GRB_IntParam_Method, 1);   // símplex dual → deja una base disponible
                // Cota dura de tiempo: el LP fijo se resuelve DESPUÉS del solve principal;
                // sin límite, en instancias grandes puede sumar minutos y disparar el timeout
                // externo del driver. Si no converge a tiempo, κ_solver queda -1 (best-effort).
                fijo.set(GRB_DoubleParam_TimeLimit, 120.0);
                fijo.optimize();
                if (fijo.get(GRB_IntAttr_SolCount) > 0) {
                    try { kappaSolver = fijo.get(GRB_DoubleAttr_Kappa); } catch (...) {}
                    if (calcularExacto)
                        try { kappaExact = fijo.get(GRB_DoubleAttr_KappaExact); } catch (...) {}

                    // --- R6: auditoría de duales desescalados (eq. 54) ---
                    // Reutiliza el LP de enteras FIJADAS (fijo): sus precios sombra son los del
                    // MIP en el incumbente. Se desescalan a unidades originales por
                    // pi_original = d_r · pi_scaled, con d_r el factor total de fila recuperado del
                    // snapshot original (coef escalado / coef original). Solo filas de balance de
                    // demanda y continuidad de embalse/agua. Opt-in; sin el flag no se ejecuta.
                    if (config.reportarDuales) {
                        // Reoptimizar el LP fijo con presolve OFF: el presolve por defecto agrega
                        // las igualdades de continuidad de embalse (a_vh_din) y quedan sin dual en
                        // su nombre original. Con presolve off toda fila original conserva su
                        // precio sombra. κ ya se leyó arriba, así que esto no altera esa medición.
                        try {
                            fijo.set(GRB_IntParam_Presolve, 0);
                            fijo.set(GRB_DoubleParam_TimeLimit, 120.0);
                            fijo.optimize();
                        } catch (GRBException&) { /* best-effort */ }

                        // d_r por NOMBRE de fila, tomado del factor EXACTO que el preprocesamiento
                        // acumuló al escalar (registrarFactorFilaDual), no reconstruido después: la
                        // reconstrucción post-hoc del coef/RHS es mal-puesta cuando la fila se escala
                        // a valores casi nulos (validaba la advertencia de R3 W1). El índice→nombre
                        // sale de la lista de restricciones del modelo.
                        std::map<std::string, double> dRPorNombre;
                        {
                            auto& rest = getRestricciones();
                            for (const auto& kv : getFactoresFilaDual())
                                if (kv.first >= 0 && kv.first < (int)rest.size())
                                    dRPorNombre[rest[kv.first]->getNombre()] = kv.second;
                        }
                        auto esFilaDualRelevante = [](const std::string& n) {
                            // Balance de demanda (= costo marginal del sistema) y continuidad de
                            // embalse (a_vh_din, la dinámica de volumen = valor del agua), más
                            // otras filas de balance/agua si el generador las nombra así.
                            return n.find("demanda")      != std::string::npos
                                || n.find("balance")      != std::string::npos
                                || n.find("h_din")        != std::string::npos  // vNh_din: continuidad de embalse
                                || n.find("continuidad")  != std::string::npos
                                || n.find("volumen")      != std::string::npos
                                || n.find("agua")         != std::string::npos;
                        };
                        int nc = fijo.get(GRB_IntAttr_NumConstrs);
                        GRBConstr* cons = fijo.getConstrs();
                        int emitidas = 0;
                        for (int k = 0; k < nc; ++k) {
                            std::string nombre = cons[k].get(GRB_StringAttr_ConstrName);
                            if (!esFilaDualRelevante(nombre)) continue;
                            double piEsc = 0.0;
                            try { piEsc = cons[k].get(GRB_DoubleAttr_Pi); } catch (...) { continue; }
                            // d_r desde la fila que resolvió el solver (autoritativa). Método
                            // primario: ratio del RHS (un escalar único, robusto cuando el RHS
                            // original es no nulo — p.ej. continuidad de embalse con volumen
                            // inicial). Fallback: ratio de coeficientes de una variable común no
                            // nula (para filas con RHS=0, p.ej. balances). El escalado por filas
                            // multiplica RHS y coeficientes por el mismo d_r>0.
                            // d_r EXACTO registrado por el preprocesamiento (1.0 si la fila no se
                            // escaló, p.ej. filas de acoplamiento por debajo del umbral).
                            auto id = dRPorNombre.find(nombre);
                            double d = (id != dRPorNombre.end()) ? id->second : 1.0;
                            // d_r EXTREMO (fila escalada a valores casi nulos): el LP queda mal
                            // condicionado en esa fila y su dual es degenerado, así que el desescale
                            // no es interpretable aunque d_r sea el factor exacto. Se marca d_r_ok=0
                            // para excluirlo del análisis (VALIDA la advertencia de R3 W1 sobre
                            // duales degenerados en LPs de despacho).
                            bool dOk = std::isfinite(d) && d > 1e-6 && d < 1e6;
                            std::ostringstream ln;
                            ln << std::scientific << std::setprecision(10);
                            ln << "[DUALES] fila=" << nombre
                               << " pi_scaled=" << piEsc
                               << " d_r=" << d
                               << " d_r_ok=" << (dOk ? 1 : 0)
                               << " pi_original=" << (dOk ? d * piEsc : piEsc);
                            std::cout << ln.str() << "\n";
                            ++emitidas;
                        }
                        delete[] cons;
                        std::cout << "[DUALES-RES] filas_reportadas=" << emitidas
                                  << " snapshot=" << (snapshotOriginalDisponible ? 1 : 0)
                                  << std::endl;
                    }
                }
            } else {
                try { kappaSolver = modelo->get(GRB_DoubleAttr_Kappa); } catch (...) {}
                if (calcularExacto)
                    try { kappaExact = modelo->get(GRB_DoubleAttr_KappaExact); } catch (...) {}
            }
        } catch (GRBException&) { /* sin κ del solver: queda -1 */ }
        std::cout << "[NUM-KAPPA] kappa_solver=" << kappaSolver
                  << " kappa_exact=" << kappaExact
                  << " is_mip=" << esMip << std::endl;

        // --- Métricas robustas de eficiencia ---
        // work: unidades de trabajo deterministas de Gurobi (independientes del hardware y del
        // número de hilos) → speedup reproducible. root_gap/root_time: gap relativo y tiempo al
        // final del nodo raíz (best-effort, vía CapturaRaizCallback).
        double work = -1.0;
        try { work = modelo->get(GRB_DoubleAttr_Work); } catch (...) {}
        double rootGap = -1.0;
        const double rb = cbMonitor.rootBound, rbst = cbMonitor.rootObjBst;
        // Descartar los centinelas ±GRB_INFINITY (1e100): sin incumbente o sin cota en la raíz.
        if (std::isfinite(rb) && std::isfinite(rbst) &&
            std::fabs(rb) < 1e30 && std::fabs(rbst) < 1e30 && std::fabs(rbst) > 1e-12)
            rootGap = std::fabs(rbst - rb) / std::fabs(rbst);
        std::cout << "[NUM-EFIC] work=" << work
                  << " root_gap=" << rootGap
                  << " root_time=" << cbMonitor.rootTime << std::endl;

        // Estadísticas solver-agnósticas de la resolución (las emite SystemController en [SOLVE]).
        {
            int st = modelo->get(GRB_IntAttr_Status);
            estadisticasResolucion.status =
                (st == GRB_OPTIMAL) ? "OPTIMAL" :
                (st == GRB_TIME_LIMIT) ? "TIME_LIMIT" :
                (st == GRB_SUBOPTIMAL) ? "SUBOPTIMAL" :
                (st == GRB_INFEASIBLE) ? "INFEASIBLE" : "OTRO";
            try { estadisticasResolucion.gapPct = 100.0 * modelo->get(GRB_DoubleAttr_MIPGap); } catch (...) {}
            try { estadisticasResolucion.bestBound = modelo->get(GRB_DoubleAttr_ObjBound); } catch (...) {}
            try { estadisticasResolucion.nodos = modelo->get(GRB_DoubleAttr_NodeCount); } catch (...) {}
            try { estadisticasResolucion.iteraciones = modelo->get(GRB_DoubleAttr_IterCount); } catch (...) {}
            estadisticasResolucion.integralPrimal = cbMonitor.integralPrimal();
        }
    } catch (GRBException &e) {
        throw std::runtime_error(std::string("Error al resolver Gurobi: ") + e.getMessage());
    } catch (...) {
        throw std::runtime_error("Error desconocido al resolver con Gurobi");
    }
}

// --- Proyección Π: min_{z∈Z(ξ)} Σ_j pesos_j (z_j - objetivo_j)² ---
void ProblemaGurobi::grabar(std::string& ruta) {
    try {
        if (!modelo) {
            std::cerr << "Error: modelo no inicializado." << std::endl;
            return;
        }

        modelo->write(ruta);
    } 
    catch (GRBException &e) {
        std::cerr << "Error Gurobi al guardar: " << e.getMessage() << std::endl;
    } 
    catch (...) {
        std::cerr << "Error desconocido al guardar el modelo" << std::endl;
    }
}


// --- Utilidad ---
void ProblemaGurobi::mostrar() {
    std::cout << "=== PROBLEMA GUROBI ===" << std::endl;
    std::cout << "Variables: " << variables.size() << std::endl;
    std::cout << "Restricciones: " << restricciones.size() << std::endl;
    std::cout << "Binarios: " << binarios.size() << std::endl;
    std::cout << "Terminos FO: " << terminosFuncionObjetivo.size() << std::endl;
    std::cout << "Constante FO: " << constanteFuncionObjetivo << std::endl;
}
