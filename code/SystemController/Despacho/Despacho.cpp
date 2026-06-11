#include "SystemController/Despacho/Despacho.h"

#include <stdexcept>
#include <string>
#include <vector>
#include <map>
#include <algorithm>
#include <iostream>

using namespace std;

void Despacho::contribuirAlProblema(
    Problema* problema,
    vector<Generacion*> agentesGen,
    vector<double> demandas
) {
    if (!problema) {
        throw runtime_error("Despacho::contribuirAlProblema - El puntero a Problema es nulo.");
    }

    int horizonte = getPeriodo();

    if (horizonte < 1) {
        throw runtime_error("Despacho::contribuirAlProblema - El horizonte temporal debe ser mayor a cero.");
    }

    if (agentesGen.empty()) {
        throw runtime_error("Despacho::contribuirAlProblema - No hay generadores.");
    }

    if (demandas.size() != static_cast<size_t>(horizonte)) {
        throw runtime_error("Despacho::contribuirAlProblema - El tamaño de demandas no coincide con el horizonte.");
    }

    for (Generacion* gen : agentesGen) {
        if (!gen) {
            throw runtime_error("Despacho::contribuirAlProblema - Hay un generador nulo.");
        }
    }

    int numGeneradores = static_cast<int>(agentesGen.size());

    // Debug temporal: verificar idGen y coeficientes.
    for (int j = 0; j < numGeneradores; j++) {
        cout << "[DEBUG Despacho] j=" << j
             << " idGen=" << agentesGen[j]->getIdGen()
             << " coefParticipacionDespacho="
             << agentesGen[j]->getCoefParticipacionDespacho()
             << endl;
    }

    // ============= Crear variables de generación total =============
    for (int i = 1; i <= horizonte; i++) {
        problema->añadirVariable(
            "g(" + to_string(i) + ")",
            2, // sin cota superior
            0.0,
            0.0
        );
    }

    if (find(nombresVariables.begin(), nombresVariables.end(), "g") == nombresVariables.end()) {
        nombresVariables.push_back("g");
    }

    // RESTRICCIÓN:
    //
    // g(t) = sum_j coef_j * g_idGen_j(t)
    //
    // Ejemplo:
    //
    // g(t) = 0.5 * gSaltoGrande(t) + 1.0 * gTermica(t)
    //
    cout << "\n[DEBUG Despacho] Cantidad de generadores = "
     << agentesGen.size() << endl;

    for (size_t j = 0; j < agentesGen.size(); j++) {
        cout << "[DEBUG Despacho] j=" << j
            << " puntero=" << agentesGen[j]
            << " idGen=" << agentesGen[j]->getIdGen()
            << " coefParticipacionDespacho="
            << agentesGen[j]->getCoefParticipacionDespacho()
            << endl;
    }

    for (int i = 1; i <= horizonte; i++) {
        vector<pair<double, string>> terminos;

        terminos.emplace_back(1.0, "g(" + to_string(i) + ")");

        for (int j = 0; j < numGeneradores; j++) {
            double coef = agentesGen[j]->getCoefParticipacionDespacho();
            int idGen = agentesGen[j]->getIdGen();

            string nombreGenerador =
                "g" + to_string(idGen) + "(" + to_string(i) + ")";

            terminos.emplace_back(-coef, nombreGenerador);
        }

        problema->añadirRestriccion(
            "gh_total(" + to_string(i) + ")",
            terminos,
            "=",
            0.0
        );
    }

    // RESTRICCIÓN:
    //
    // g(t) <= demandaResidual(t)
    //
    for (int i = 1; i <= horizonte; i++) {
        problema->añadirRestriccion(
            "gen_menor_demanda(" + to_string(i) + ")",
            {
                {1.0, "g(" + to_string(i) + ")"}
            },
            "<=",
            demandas[i - 1]
        );
    }
}

void Despacho::posprocesamiento(
    Problema* problema,
    vector<Generacion*> agentesGen
) {
    if (!problema) {
        throw runtime_error("Despacho::posprocesamiento - El puntero a Problema es nulo.");
    }

    int horizonte = getPeriodo();

    if (horizonte < 1) {
        throw runtime_error("Despacho::posprocesamiento - El horizonte temporal debe ser mayor a cero.");
    }

    if (agentesGen.empty()) {
        throw runtime_error("Despacho::posprocesamiento - No hay generadores.");
    }

    for (Generacion* gen : agentesGen) {
        if (!gen) {
            throw runtime_error("Despacho::posprocesamiento - Hay un generador nulo.");
        }
    }

    int numGeneradores = static_cast<int>(agentesGen.size());

    std::map<std::string, double>& valoresVariables = problema->getValoresVariables();

    for (int t = 1; t <= horizonte; t++) {
        double genTotal = 0.0;

        for (int j = 0; j < numGeneradores; j++) {
            double coef = agentesGen[j]->getCoefParticipacionDespacho();
            int idGen = agentesGen[j]->getIdGen();

            string nombreGenerador =
                "g" + to_string(idGen) + "(" + to_string(t) + ")";

            genTotal += coef * valoresVariables[nombreGenerador];
        }

        valoresVariables["g(" + to_string(t) + ")"] = genTotal;
    }
}

// ================================
// Getters / Setters
// ================================

int Despacho::getPeriodo() {
    return periodo;
}

void Despacho::setPeriodo(int p) {
    periodo = p;
}

const std::vector<std::string>& Despacho::getNombresVariables() {
    return nombresVariables;
}

void Despacho::setNombresVariables(const std::vector<std::string>& nombres) {
    nombresVariables = nombres;
}