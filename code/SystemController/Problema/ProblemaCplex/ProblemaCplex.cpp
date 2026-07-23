#include "ProblemaCplex.h"
#include <ilcplex/ilocplex.h>
#include <iostream>
#include <sstream>
#include <fstream>
#include <map>
#include <set>
#include <stdexcept>
#include <cstdlib>

using namespace std;

// Estado acumulado por el callback informativo de CPLEX (integral primal–dual + raíz).
namespace {
struct EstadoMonitorCplex {
    double integral = 0.0, ultimoT = -1.0, ultimoGap = 1.0, tFinal = 0.0;
    double rootGap = -1.0, rootTime = -1.0;
    bool   rootCapturada = false;
    double integralPrimal() const { return tFinal > 0.0 ? integral / tFinal : -1.0; }
};
}

// Callback informativo de SOLO LECTURA: acumula el área de γ(t) por trapecios, luego
// la normaliza por el último timestamp observado, y captura el
// gap/tiempo al final del nodo raíz. No altera la búsqueda.
ILOMIPINFOCALLBACK1(MonitorCplexCB, EstadoMonitorCplex&, st) {
    double t = getCplexTime();
    double gap = 1.0;
    if (hasIncumbent()) {
        try { gap = getMIPRelativeGap(); } catch (...) { gap = 1.0; }
    }
    if (gap < 0.0) gap = 0.0; else if (gap > 1.0) gap = 1.0;
    if (st.ultimoT >= 0.0 && t > st.ultimoT)
        st.integral += 0.5 * (gap + st.ultimoGap) * (t - st.ultimoT);
    st.ultimoT = t; st.ultimoGap = gap; st.tFinal = t;
    if (!st.rootCapturada) {
        if (getNnodes() <= 0) {
            st.rootTime = t;
            if (hasIncumbent()) { try { st.rootGap = getMIPRelativeGap(); } catch (...) {} }
        } else {
            st.rootCapturada = true;   // ya pasamos la raíz
        }
    }
}

ProblemaCplex::ProblemaCplex() {
    try {
        env = IloEnv();
        modelo = IloModel(env);
        constanteFuncionObjetivo = 0.0;
        flagConstanteFuncionObjetivo = false;
        valorFuncionObjetivo = 0.0;
    }
    catch (...) {
        env.end();
        throw;
    }
}

ProblemaCplex::~ProblemaCplex() {
    modelo.end();
    env.end();
}

// --- Procesar ---
void ProblemaCplex::procesar(bool flagConstante) {
    IloNumVar var;
    flagConstanteFuncionObjetivo = flagConstante;
    
    // 1. Variables continuas
    for (std::vector<Variable*>::const_iterator it = variables.begin(); it != variables.end(); ++it) {
        int tipoCota = (*it)->getTipoCota();
        IloNumVar CplexVar;
        if (tipoCota == 0) {
            CplexVar = IloNumVar(env, (*it)->getCotaInf(), (*it)->getCotaSup(), ILOFLOAT, (*it)->getNombre().c_str());
        } else if (tipoCota == 1) {
            CplexVar = IloNumVar(env, -IloInfinity, (*it)->getCotaSup(), ILOFLOAT, (*it)->getNombre().c_str());
        } else if (tipoCota == 2) {
            CplexVar = IloNumVar(env, (*it)->getCotaInf(), IloInfinity, ILOFLOAT, (*it)->getNombre().c_str());
        } else if (tipoCota == 3) {
            CplexVar = IloNumVar(env, -IloInfinity, IloInfinity, ILOFLOAT, (*it)->getNombre().c_str());
        }
        vars.insert(std::make_pair((*it)->getNombre(), CplexVar));
    }

    // 2. Variables binarias
    for (std::vector<Binario*>::const_iterator it = binarios.begin(); it != binarios.end(); ++it) {
        IloNumVar CplexVar = IloNumVar(env, 0.0, 1.0, ILOBOOL, (*it)->getNombre().c_str());
        vars.insert(std::make_pair((*it)->getNombre(), CplexVar));
    }

    // 3. Restricciones
    for (std::vector<Restriccion*>::const_iterator it = restricciones.begin(); it != restricciones.end(); ++it) {
        IloExpr expr(env);
        const std::vector<std::pair<double, std::string>>& terminos = (*it)->getTerminos();
        for (std::vector<std::pair<double, std::string>>::const_iterator term = terminos.begin(); term != terminos.end(); ++term) {
            if (!vars.count(term->second)) {
                throw std::invalid_argument("ProblemaCplex::procesar - Variable '" + term->second + "' en restricción '"
                    + (*it)->getNombre() + "' no fue definida.");
            }
            expr += term->first * vars[term->second];
        }

        std::string op = (*it)->getOperador();
        if (op == "<=") {
            modelo.add(IloRange(env, -IloInfinity, expr, (*it)->getTerminoIndependiente(), (*it)->getNombre().c_str()));
        }
        else if (op == ">=") {
            modelo.add(IloRange(env, (*it)->getTerminoIndependiente(), expr, IloInfinity, (*it)->getNombre().c_str()));
        }
        else if (op == "=") {
            modelo.add(IloRange(env, (*it)->getTerminoIndependiente(), expr, (*it)->getTerminoIndependiente(), (*it)->getNombre().c_str()));
        }

        expr.end();
    }

    // 4. Función objetivo
    IloExpr objExpr(env);
    for (std::vector<AporteFuncionObjetivo*>::const_iterator it = terminosFuncionObjetivo.begin(); it != terminosFuncionObjetivo.end(); ++it) {
        if (!vars.count((*it)->getVariable())) {
            throw std::invalid_argument("ProblemaCplex::procesar - Variable '" + (*it)->getVariable() +
                "' en función objetivo no fue definida.");
        }
        objExpr += (*it)->getCoeficiente() * vars[(*it)->getVariable()];
    }
    if(flagConstante){
        objExpr += constanteFuncionObjetivo;
    }  

    objetivoModelo = IloMinimize(env, objExpr);   // se guarda el handle para la proyección
    modelo.add(objetivoModelo);
    objExpr.end();
}

// --- Proyección Π: min_{z∈Z(ξ)} Σ_j pesos_j (z_j - objetivo_j)² ---
void ProblemaCplex::resolverMonolitico() {
    try {
        IloCplex solver(modelo);

        if (config.timeoutSegundos > 0.0)
            solver.setParam(IloCplex::Param::TimeLimit, config.timeoutSegundos);
        solver.setParam(IloCplex::Param::MIP::Tolerances::MIPGap, config.mipGap);
        // Baseline de escalado interno del solver (R1): contrasta el escalado externo
        // generator-aware contra el escalado nativo de CPLEX. Solo se toca si el usuario
        // pasó --cplexscale; en caso contrario CPLEX usa su default (0, equilibrado estándar).
        if (config.scaleIndCplex != SolverConfig::SOLVER_PARAM_AUTO) {
            solver.setParam(IloCplex::Param::Read::Scale, config.scaleIndCplex);
        }
        // Sondeo R1: desactivar el presolve de CPLEX para ver si absorbe el efecto del
        // escalado externo. Solo se toca si el usuario pasó --cplexpresolve.
        if (config.presolveIndCplex != SolverConfig::SOLVER_PARAM_AUTO) {
            solver.setParam(IloCplex::Param::Preprocessing::Presolve,
                            config.presolveIndCplex != 0);
        }
        // Reproducibilidad: semilla fija y, si el entorno lo define, número de hilos fijo.
        // El default sigue siendo 1 (la semilla de todos los resultados publicados);
        // --seed N la cambia para estimar la variabilidad corrida-a-corrida.
        solver.setParam(IloCplex::Param::RandomSeed,
                        config.semillaSolver != SolverConfig::SOLVER_PARAM_AUTO
                            ? config.semillaSolver
                            : 1);
        if (const char* h = std::getenv("OMP_NUM_THREADS")) {
            try { int nh = std::stoi(h); if (nh > 0) solver.setParam(IloCplex::Param::Threads, nh); }
            catch (...) {}
        }
        // Condicionamiento a lo largo del árbol B&B (KappaStats): muestrea las bases de los
        // subproblemas para reportar κ_max, atención y fracciones de estabilidad. SAMPLE es el
        // modo práctico (FULL computa κ en cada nodo y frena la resolución).
        try {
            solver.setParam(IloCplex::Param::MIP::Strategy::KappaStats, CPX_MIPKAPPA_SAMPLE);
        } catch (...) { /* sin KappaStats: las qualities de árbol quedarán en -1 */ }

        // Callback informativo: integral primal–dual + métricas de raíz.
        EstadoMonitorCplex mon;
        solver.use(MonitorCplexCB(modelo.getEnv(), mon));

        const double detIni = solver.getDetTime();   // marca de tiempo determinista (ticks)

        if (!solver.solve())
            throw std::runtime_error("ProblemaCplex::resolverMonolitico - No se pudo resolver el modelo.");

        const double detFin = solver.getDetTime();

        cout << "Solución encontrada con valor óptimo = " << solver.getObjValue() << endl;
        for (auto& p : vars)
            valoresVariables[p.first] = solver.getValue(p.second);
        aplicarEscalamientoValoresSolucion();
        valorFuncionObjetivo = solver.getObjValue();

        // --- Condicionamiento medido por el solver (análogo a Gurobi Kappa/KappaExact) ---
        // Best-effort: cada quality puede no estar disponible (p.ej. sin base para un MIP, o sin
        // KappaStats producido) → queda en -1, sin abortar la resolución.
        auto q = [&](IloCplex::Quality qq) -> double {
            try { return solver.getQuality(qq); } catch (...) { return -1.0; }
        };
        const int esMip = solver.isMIP() ? 1 : 0;
        const double kappaSolver = q(IloCplex::Kappa);
        const double kappaExact  = q(IloCplex::ExactKappa);
        cout << "[NUM-KAPPA] kappa_solver=" << kappaSolver
             << " kappa_exact=" << kappaExact
             << " is_mip=" << esMip << endl;

        // Distribución de condicionamiento sobre el árbol (exclusivo de CPLEX).
        cout << "[NUM-KAPPA-ARBOL] kmax=" << q(IloCplex::KappaMax)
             << " attention=" << q(IloCplex::KappaAttention)
             << " stable="     << q(IloCplex::KappaStable)
             << " suspicious=" << q(IloCplex::KappaSuspicious)
             << " unstable="   << q(IloCplex::KappaUnstable)
             << " illposed="   << q(IloCplex::KappaIllposed) << endl;

        // --- Eficiencia robusta: tiempo determinista (ticks) + métricas de raíz del callback ---
        cout << "[NUM-EFIC] dettime=" << (detFin - detIni)
             << " root_gap=" << mon.rootGap
             << " root_time=" << mon.rootTime << endl;

        // --- Estadísticas solver-agnósticas (las emite SystemController en [SOLVE]) ---
        {
            IloAlgorithm::Status s = solver.getStatus();
            estadisticasResolucion.status =
                (s == IloAlgorithm::Optimal)    ? "OPTIMAL" :
                (s == IloAlgorithm::Feasible)   ? "TIME_LIMIT" :   // factible no probado óptimo (timeout)
                (s == IloAlgorithm::Infeasible) ? "INFEASIBLE" : "OTRO";
            try { estadisticasResolucion.gapPct = 100.0 * solver.getMIPRelativeGap(); } catch (...) {}
            try { estadisticasResolucion.bestBound = solver.getBestObjValue(); } catch (...) {}
            try { estadisticasResolucion.nodos = static_cast<double>(solver.getNnodes()); } catch (...) {}
            try { estadisticasResolucion.iteraciones = static_cast<double>(solver.getNiterations()); } catch (...) {}
            estadisticasResolucion.integralPrimal = mon.integralPrimal();
        }
    } catch (const IloException& e) {
        std::ostringstream oss;
        oss << "Error Cplex: " << e;
        throw std::runtime_error(oss.str());
    }
}


// --- Exportar ---
void ProblemaCplex::grabar(std::string& ruta) {
    try {
        IloCplex solver(modelo);
        solver.exportModel(ruta.c_str());
        cout << "Modelo guardado en: " << ruta << endl;
    } catch (IloException& e) {
        cerr << "Error al guardar el modelo: " << e.getMessage() << endl;
    }
}


// --- Mostrar ---
void ProblemaCplex::mostrar() {
    cout << "=== PROBLEMA Cplex ===" << endl;
    cout << "Variables: " << variables.size() << endl;
    cout << "Restricciones: " << restricciones.size() << endl;
    cout << "Binarios: " << binarios.size() << endl;
    cout << "Términos FO: " << terminosFuncionObjetivo.size() << endl;
    cout << "Constante FO: " << constanteFuncionObjetivo << endl;
}

// ============================================================
// Dantzig-Wolfe
// ============================================================
