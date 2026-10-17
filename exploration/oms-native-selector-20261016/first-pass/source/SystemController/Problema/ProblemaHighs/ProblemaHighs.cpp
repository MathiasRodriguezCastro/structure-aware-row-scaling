#include "ProblemaHighs.h"

#include "Highs.h"

#include <chrono>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>

using namespace std;

ProblemaHighs::ProblemaHighs() : highs(new Highs()) {}

ProblemaHighs::~ProblemaHighs() = default;

void ProblemaHighs::procesar(bool flagConstante) {
    flagConstanteFuncionObjetivo = flagConstante;
    const size_t nVars = variables.size() + binarios.size();
    if (nVars == 0)
        throw runtime_error("ProblemaHighs::procesar - No hay variables definidas.");

    HighsLp lp;
    lp.num_col_ = static_cast<HighsInt>(nVars);
    lp.num_row_ = static_cast<HighsInt>(restricciones.size());
    lp.sense_ = ObjSense::kMinimize;
    lp.offset_ = flagConstante ? constanteFuncionObjetivo : 0.0;
    lp.col_cost_.assign(nVars, 0.0);
    lp.col_lower_.assign(nVars, 0.0);
    lp.col_upper_.assign(nVars, kHighsInf);
    lp.integrality_.assign(nVars, HighsVarType::kContinuous);

    varIndex.clear();
    nombresColumnas.clear();
    HighsInt j = 0;
    for (auto* v : variables) {
        if (!varIndex.emplace(v->getNombre(), j).second)
            throw runtime_error("ProblemaHighs::procesar - Variable duplicada '" + v->getNombre() + "'.");
        switch (v->getTipoCota()) {
            case 0: lp.col_lower_[j] = v->getCotaInf(); lp.col_upper_[j] = v->getCotaSup(); break;
            case 1: lp.col_lower_[j] = -kHighsInf;      lp.col_upper_[j] = v->getCotaSup(); break;
            case 2: lp.col_lower_[j] = v->getCotaInf(); lp.col_upper_[j] = kHighsInf;       break;
            default: lp.col_lower_[j] = -kHighsInf;     lp.col_upper_[j] = kHighsInf;       break;
        }
        nombresColumnas.push_back(v->getNombre());
        ++j;
    }
    for (auto* b : binarios) {
        if (!varIndex.emplace(b->getNombre(), j).second)
            throw runtime_error("ProblemaHighs::procesar - Variable duplicada '" + b->getNombre() + "'.");
        lp.col_lower_[j] = 0.0;
        lp.col_upper_[j] = 1.0;
        lp.integrality_[j] = HighsVarType::kInteger;
        nombresColumnas.push_back(b->getNombre());
        ++j;
    }

    for (auto* t : terminosFuncionObjetivo) {
        auto it = varIndex.find(t->getVariable());
        if (it == varIndex.end())
            throw runtime_error("ProblemaHighs::procesar - Variable '" + t->getVariable() +
                                "' de la función objetivo no definida.");
        lp.col_cost_[it->second] += t->getCoeficiente();
    }

    // Matriz por filas; los términos repetidos de una misma variable se suman, como en las
    // expresiones de Gurobi y CPLEX.
    lp.a_matrix_.format_ = MatrixFormat::kRowwise;
    lp.a_matrix_.num_col_ = lp.num_col_;
    lp.a_matrix_.num_row_ = lp.num_row_;
    lp.a_matrix_.start_.assign(1, 0);
    lp.row_lower_.reserve(restricciones.size());
    lp.row_upper_.reserve(restricciones.size());
    lp.row_names_.reserve(restricciones.size());
    map<HighsInt, double> fila;
    for (auto* r : restricciones) {
        fila.clear();
        for (const auto& t : r->getTerminos()) {
            auto it = varIndex.find(t.second);
            if (it == varIndex.end())
                throw runtime_error("ProblemaHighs::procesar - Variable '" + t.second +
                                    "' en restricción '" + r->getNombre() + "' no definida.");
            fila[it->second] += t.first;
        }
        for (const auto& kv : fila) {
            if (kv.second == 0.0) continue;
            lp.a_matrix_.index_.push_back(kv.first);
            lp.a_matrix_.value_.push_back(kv.second);
        }
        lp.a_matrix_.start_.push_back(static_cast<HighsInt>(lp.a_matrix_.index_.size()));
        const string& op = r->getOperador();
        const double rhs = r->getTerminoIndependiente();
        if (op == "<=")      { lp.row_lower_.push_back(-kHighsInf); lp.row_upper_.push_back(rhs); }
        else if (op == ">=") { lp.row_lower_.push_back(rhs);        lp.row_upper_.push_back(kHighsInf); }
        else if (op == "=")  { lp.row_lower_.push_back(rhs);        lp.row_upper_.push_back(rhs); }
        else throw runtime_error("ProblemaHighs::procesar - Operador desconocido '" + op +
                                 "' en restricción '" + r->getNombre() + "'.");
        lp.row_names_.push_back(r->getNombre());
    }
    lp.col_names_ = nombresColumnas;

    // Umbral de coeficientes pequeños en su mínimo admitido: HiGHS descarta por defecto
    // |a| <= 1e-9, lo que alteraría el modelo exportado por el preprocesamiento.
    highs->setOptionValue("small_matrix_value", 1e-12);
    highs->setOptionValue("output_flag", true);
    highs->setOptionValue("log_to_console", true);
    if (highs->passModel(std::move(lp)) == HighsStatus::kError)
        throw runtime_error("ProblemaHighs::procesar - HiGHS rechazó el modelo.");
}

void ProblemaHighs::resolverMonolitico() {
    if (config.timeoutSegundos > 0.0)
        highs->setOptionValue("time_limit", config.timeoutSegundos);
    highs->setOptionValue("mip_rel_gap", config.mipGap);
    highs->setOptionValue("random_seed",
                          config.semillaSolver != SolverConfig::SOLVER_PARAM_AUTO
                              ? static_cast<HighsInt>(config.semillaSolver) : HighsInt(1));
    if (const char* h = std::getenv("OMP_NUM_THREADS")) {
        try { int nh = std::stoi(h); if (nh > 0) highs->setOptionValue("threads", nh); }
        catch (...) {}
    }
    // HiGHS usa una única tolerancia de factibilidad MIP (filas e integralidad).
    if (config.tolFactibilidad > 0.0) {
        highs->setOptionValue("primal_feasibility_tolerance", config.tolFactibilidad);
        highs->setOptionValue("mip_feasibility_tolerance", config.tolFactibilidad);
    }

    const auto inicio = chrono::steady_clock::now();
    const HighsStatus runStatus = highs->run();
    const double segundos = chrono::duration<double>(chrono::steady_clock::now() - inicio).count();
    const HighsModelStatus ms = highs->getModelStatus();
    const HighsInfo& info = highs->getInfo();

    estadisticasResolucion.status =
        (ms == HighsModelStatus::kOptimal)    ? "OPTIMAL" :
        (ms == HighsModelStatus::kTimeLimit)  ? "TIME_LIMIT" :
        (ms == HighsModelStatus::kInfeasible) ? "INFEASIBLE" : "OTRO";
    if (info.mip_gap < kHighsInf) estadisticasResolucion.gapPct = 100.0 * info.mip_gap;
    estadisticasResolucion.bestBound = info.mip_dual_bound;
    estadisticasResolucion.nodos = static_cast<double>(info.mip_node_count);
    estadisticasResolucion.iteraciones = static_cast<double>(info.simplex_iteration_count);
    estadisticasResolucion.integralPrimal = -1.0;

    {
        ostringstream m;
        m << setprecision(numeric_limits<double>::max_digits10)
          << "[HIGHS] model_status=" << highs->modelStatusToString(ms)
          << " run_status=" << static_cast<int>(runStatus)
          << " primal_solution_status=" << info.primal_solution_status
          << " mip_node_count=" << info.mip_node_count
          << " lp_iterations=" << info.simplex_iteration_count
          << " primal_dual_integral=" << info.primal_dual_integral;
        cout << m.str() << endl;
    }

    if (info.primal_solution_status != kSolutionStatusFeasible) {
        ostringstream m;
        m << setprecision(numeric_limits<double>::max_digits10)
          << "[NOSOL] status=" << estadisticasResolucion.status
          << " tiempo_solver_s=" << segundos
          << " best_bound=" << info.mip_dual_bound
          << " nodos=" << info.mip_node_count;
        cout << m.str() << endl;
        throw runtime_error("ProblemaHighs::resolverMonolitico - Sin solución factible. Status HiGHS: " +
                            highs->modelStatusToString(ms));
    }

    const vector<double>& x = highs->getSolution().col_value;
    for (size_t k = 0; k < nombresColumnas.size(); ++k)
        valoresVariables[nombresColumnas[k]] = x[k];
    valorFuncionObjetivo = info.objective_function_value;
    aplicarEscalamientoValoresSolucion();
}

void ProblemaHighs::grabar(string& ruta) {
    if (highs->writeModel(ruta) == HighsStatus::kError)
        cerr << "[ERROR] HiGHS no pudo escribir el modelo en " << ruta << endl;
}

void ProblemaHighs::mostrar() {
    cout << "=== PROBLEMA HIGHS ===" << endl;
    cout << "Variables: " << variables.size() << endl;
    cout << "Binarios: " << binarios.size() << endl;
    cout << "Restricciones: " << restricciones.size() << endl;
    cout << "Terminos FO: " << terminosFuncionObjetivo.size() << endl;
    cout << "Constante FO: " << constanteFuncionObjetivo << endl;
}
