#include "UnidadTermicaSimple.h"

#include <string>
#include <stdexcept>
#include <algorithm>

UnidadTermicaSimple::UnidadTermicaSimple(
    int id,
    int idGen,
    int h_c,
    double MGT,
    double b
) : Generacion(id, h_c, idGen),
    potenciaMax(MGT),
    costoVariable(b)
{
    if (h_c <= 0) {
        throw std::invalid_argument("UnidadTermicaSimple: horizonte temporal inválido.");
    }

    if (MGT < 0.0) {
        throw std::invalid_argument("UnidadTermicaSimple: potenciaMax no puede ser negativa.");
    }

    if (b < 0.0) {
        throw std::invalid_argument("UnidadTermicaSimple: costoVariable no puede ser negativo.");
    }

    nombre = "Unidad Termica Simple (Agente: " + std::to_string(id) + ")";
}

std::string UnidadTermicaSimple::genEt(const std::string& nombreVar, int parametro) const {
    if (parametro < 0) {
        throw std::invalid_argument("UnidadTermicaSimple::genEt - parámetro negativo.");
    }

    std::string stringIdAgente = "a" + std::to_string(this->idAgente);

    if (parametro == 0) {
        return stringIdAgente + "_" + nombreVar;
    }

    return stringIdAgente + "_" + nombreVar + "(" + std::to_string(parametro) + ")";
}

void UnidadTermicaSimple::contribuirAlProblema(Problema* problema, int horizonteTemporal) {
    string StringIdGen = to_string(idGen);
    if (!problema) {
        throw std::invalid_argument("UnidadTermicaSimple::contribuirAlProblema - puntero 'problema' nulo.");
    }

    if (horizonteTemporal <= 0) {
        throw std::invalid_argument("UnidadTermicaSimple::contribuirAlProblema - horizonteTemporal inválido.");
    }

    if (potenciaMax < 0.0) {
        throw std::invalid_argument("UnidadTermicaSimple::contribuirAlProblema - potenciaMax no puede ser negativa.");
    }

    if (costoVariable < 0.0) {
        throw std::invalid_argument("UnidadTermicaSimple::contribuirAlProblema - costoVariable no puede ser negativo.");
    }

    for (int i = 1; i <= horizonteTemporal; ++i) {
        std::string g = "g" + std::to_string(idGen) + "(" + std::to_string(i) + ")";

        // Variable de generación térmica:
        //
        // 0 <= g_t <= potenciaMax
        //
        // Asumimos que tipo 0 representa una variable continua
        // con cota inferior y cota superior.
        problema->añadirVariable(g, 0, 0.0, potenciaMax);

        // Costo variable:
        //
        // costoVariable * g_t
        problema->añadirTerminoFuncionObjetivo(costoVariable, g);
    }

    std::string nombreVariableBase = "g" + std::to_string(idGen);

    if (std::find(
            nombresVariables.begin(),
            nombresVariables.end(),
            nombreVariableBase
        ) == nombresVariables.end()) {
        nombresVariables.push_back(nombreVariableBase);
    }
}

void UnidadTermicaSimple::posprocesamiento(Problema* problema) {
    (void)problema;
}