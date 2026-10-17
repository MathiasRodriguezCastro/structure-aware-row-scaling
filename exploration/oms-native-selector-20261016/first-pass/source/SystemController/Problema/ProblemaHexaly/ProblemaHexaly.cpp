#include "ProblemaHexaly.h"

#include <iostream>
#include <sstream>
#include <stdexcept>
#include <map>
#include <set>
#include <string>
#include <vector>

using namespace std;

// Todo el cuerpo que usa la API de Hexaly queda dentro del guard.
// Cuando se compila con -DNO_HEXALY, el .cpp genera solo stubs que
// lanzan una excepción, de modo que el linker no necesita libhexaly.
#ifndef NO_HEXALY

#include "optimizer/hexalyoptimizer.h"
using namespace hexaly;

namespace {
const char* estadoHexalyComoTexto(HxSolutionStatus status) {
    switch (status) {
        case SS_Inconsistent: return "Inconsistent";
        case SS_Infeasible:   return "Infeasible";
        case SS_Feasible:     return "Feasible";
        case SS_Optimal:      return "Optimal";
    }
    return "Unknown";
}
}

// ---------------------------------------------------------------------------
// Constructor / Destructor
// ---------------------------------------------------------------------------

ProblemaHexaly::ProblemaHexaly() {
    try {
        optimizer = new HexalyOptimizer();
    } catch (const exception& e) {
        throw runtime_error(string("Error al inicializar Hexaly: ") + e.what());
    }
}

ProblemaHexaly::~ProblemaHexaly() {
    delete optimizer;
    optimizer = nullptr;
}

// ---------------------------------------------------------------------------
// procesar()
// ---------------------------------------------------------------------------

void ProblemaHexaly::procesar(bool flagConstante) {
    if (!optimizer)
        throw runtime_error("ProblemaHexaly::procesar - optimizer no inicializado.");

    HxModel model = optimizer->getModel();
    map<string, HxExpression> vars;

    // 1. Variables continuas
    const double INF = 1e15;
    for (const auto& v : variables) {
        int tipoCota = v->getTipoCota();
        double lb = (tipoCota == 0 || tipoCota == 2) ? v->getCotaInf() : -INF;
        double ub = (tipoCota == 0 || tipoCota == 1) ? v->getCotaSup() :  INF;
        HxExpression expr = model.floatVar(lb, ub);
        expr.setName(v->getNombre().c_str());
        vars[v->getNombre()] = expr;
    }

    // 2. Variables binarias
    for (const auto& b : binarios) {
        HxExpression expr = model.boolVar();
        expr.setName(b->getNombre().c_str());
        vars[b->getNombre()] = expr;
    }

    // 3. Restricciones
    for (const auto& r : restricciones) {
        HxExpression lhs = model.sum();
        for (const auto& termino : r->getTerminos()) {
            double coef       = termino.first;
            const string& nom = termino.second;
            if (!vars.count(nom))
                throw invalid_argument(
                    "ProblemaHexaly::procesar - Variable '" + nom +
                    "' en restriccion '" + r->getNombre() + "' no definida.");
            lhs.addOperand(coef * vars[nom]);
        }

        double rhs       = r->getTerminoIndependiente();
        const string& op = r->getOperador();
        HxExpression constraint;
        if      (op == "<=") constraint = model.leq(lhs, rhs);
        else if (op == ">=") constraint = model.geq(lhs, rhs);
        else if (op == "=" ) constraint = model.eq (lhs, rhs);
        else throw invalid_argument(
                "ProblemaHexaly::procesar - Operador desconocido '" + op +
                "' en restriccion '" + r->getNombre() + "'.");
        model.constraint(constraint);
    }

    // 4. Función objetivo
    HxExpression fo = model.sum();
    for (const auto& t : terminosFuncionObjetivo) {
        const string& nom = t->getVariable();
        if (!vars.count(nom))
            throw invalid_argument(
                "ProblemaHexaly::procesar - Variable '" + nom +
                "' en funcion objetivo no definida.");
        fo.addOperand(t->getCoeficiente() * vars[nom]);
    }
    if (flagConstante && constanteFuncionObjetivo != 0.0)
        fo.addOperand(model.createConstant(constanteFuncionObjetivo));

    model.minimize(fo);
    model.close();
}

// ---------------------------------------------------------------------------
// resolver()
// ---------------------------------------------------------------------------

void ProblemaHexaly::resolverMonolitico() {
    if (!optimizer)
        throw runtime_error("ProblemaHexaly::resolver - optimizer no inicializado.");

    HxParam param = optimizer->getParam();
    if (config.timeoutSegundos > 0.0)
        param.setTimeLimit(static_cast<int>(config.timeoutSegundos));
    // Hexaly 14.5 expone objectiveGap como métrica de la solución, pero no un
    // parámetro MIPGap relativo equivalente al de Gurobi/CPLEX. Por eso
    // config.mipGap no se usa como criterio de parada para este solver.

    optimizer->solve();

    HxSolution sol       = optimizer->getSolution();
    HxSolutionStatus st  = sol.getStatus();

    if (st == SS_Inconsistent)
        throw runtime_error("ProblemaHexaly::resolver - modelo infactible (SS_Inconsistent).");
    if (st == SS_Infeasible)
        throw std::runtime_error(
            "ProblemaHexaly::resolverMonolitico - sin solucion factible dentro del tiempo limite (SS_Infeasible).");

    HxModel model = optimizer->getModel();
    set<string> nombresContinuas;
    set<string> nombresBinarias;
    for (const auto& v : variables) {
        nombresContinuas.insert(v->getNombre());
    }
    for (const auto& b : binarios) {
        nombresBinarias.insert(b->getNombre());
    }

    for (int i = 0; i < model.getNbExpressions(); ++i) {
        HxExpression expr = model.getExpression(i);
        const string nombre(expr.getName());
        if (nombre.empty()) continue;

        if (nombresContinuas.count(nombre)) {
            valoresVariables[nombre] = sol.getDoubleValue(expr);
        } else if (nombresBinarias.count(nombre)) {
            valoresVariables[nombre] = static_cast<double>(sol.getIntValue(expr));
        }
    }
    if (model.getNbObjectives() > 0) {
        valorFuncionObjetivo = sol.getDoubleValue(model.getObjective(0));
        double bound = sol.getDoubleObjectiveBound(0);
        double gap = sol.getObjectiveGap(0);
        cout << "[HEXALY] status=" << estadoHexalyComoTexto(st)
             << " objective=" << valorFuncionObjetivo
             << " bound=" << bound
             << " gap=" << gap
             << endl;
    }
    aplicarEscalamientoValoresSolucion();
}

// ---------------------------------------------------------------------------
// grabar()
// ---------------------------------------------------------------------------

void ProblemaHexaly::grabar(string& ruta) {
    if (!optimizer)
        throw runtime_error("ProblemaHexaly::grabar - optimizer no inicializado.");
    try {
        string out = ruta;
        const string ext = ".lp";
        if (out.size() >= ext.size() && out.substr(out.size() - ext.size()) == ext) {
            out = out.substr(0, out.size() - ext.size()) + ".hxb";
            cout << "[info] ProblemaHexaly: exportando como '" << out << "' (formato HXB)." << endl;
        }
        optimizer->saveEnvironment(out.c_str());
    } catch (const exception& e) {
        throw runtime_error(string("ProblemaHexaly::grabar - ") + e.what());
    }
}

// ---------------------------------------------------------------------------
// mostrar()
// ---------------------------------------------------------------------------

void ProblemaHexaly::mostrar() {
    cout << "=== PROBLEMA HEXALY ===" << endl;
    cout << "Variables continuas : " << variables.size()               << endl;
    cout << "Variables binarias  : " << binarios.size()                << endl;
    cout << "Restricciones       : " << restricciones.size()           << endl;
    cout << "Terminos FO         : " << terminosFuncionObjetivo.size() << endl;
    cout << "Constante FO        : " << constanteFuncionObjetivo       << endl;
}

#else  // NO_HEXALY definido: stubs que evitan errores de linker

ProblemaHexaly::ProblemaHexaly() {
    throw runtime_error("ProblemaHexaly: Hexaly no fue incluido en esta compilacion (-DNO_HEXALY).");
}
ProblemaHexaly::~ProblemaHexaly() {}
void ProblemaHexaly::procesar(bool)    { throw runtime_error("Hexaly no disponible."); }
void ProblemaHexaly::resolverMonolitico()        { throw runtime_error("Hexaly no disponible."); }
void ProblemaHexaly::grabar(string&)   { throw runtime_error("Hexaly no disponible."); }
void ProblemaHexaly::mostrar()         { cerr << "Hexaly no disponible (-DNO_HEXALY)." << endl; }

#endif // NO_HEXALY
