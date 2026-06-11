#include "UnidadTermicaRapida.h"
#include <iostream>
#include <string>
#include <map>
#include <stdexcept>

// Constructor
UnidadTermicaRapida::UnidadTermicaRapida(
    int id,
    int idGen,
    double h_c,
    double mGT,
    double MGT,
    double a,
    double b,
    double alpha
) : Generacion(id, h_c, idGen),
    potenciaMin(mGT),
    potenciaMax(MGT),
    costoFijo(a),
    costoVariable(b),
    costoEncendido(alpha)
{
    nombre = "Unidad Termica (Agente: " + std::to_string(id) + ")";
}

// Genera etiquetas para variables y restricciones
std::string UnidadTermicaRapida::genEt(const std::string& nombreVar, int parametro) const {
    std::string stringIdAgente = "a" + std::to_string(this->idAgente);
    if (parametro == 0) {
        return stringIdAgente + "_" + nombreVar;
    }
    return stringIdAgente + "_" + nombreVar + "(" + std::to_string(parametro) + ")";
}

// --- Método principal ---
void UnidadTermicaRapida::contribuirAlProblema(Problema* problema, int horizonteTemporal) {
    string StringIdAgente = "a" + to_string(idAgente); // ID del agente
    string StringIdGen = to_string(idGen);
    
    if (!problema) {
        throw std::invalid_argument("UnidadTermicaRapida::contribuirAlProblema - puntero 'problema' nulo.");
    }

    size_t h_c = static_cast<size_t>(horizonteTemporal);

    // --- RESTRICCIONES ---
    for (size_t i = 1; i <= h_c; ++i) {
        // Generación mínima: w_t >= mGT * x_t
        problema->añadirRestriccion(
            genEt("gen_min", i),
            {
                {1,           "g" + StringIdGen + "(" + to_string(i) + ")"},
                {-potenciaMin, genEt("xg", i)}
            },
            ">=",
            0
        );

        // Generación máxima
        problema->añadirRestriccion(
            genEt("gen_max", i),
            {
                {1, "g" + StringIdGen + "(" + to_string(i) + ")"},
                {-potenciaMax, genEt("xg", i)}
            },
            "<=",
            0
        );
    }

    // Encendido y apagado
    for (size_t i = 2; i <= h_c; ++i) {
        problema->añadirRestriccion(
            genEt("restriccion_encendido", i),
            {
                {1, genEt("yg", i)},
                {-1, genEt("xg", i)},
                {1, genEt("xg", i - 1)}
            },
            ">=",
            0
        );
    }

    // Duración mínima encendido/apagado
    auto agregarRestriccionesDuracion = [&](const std::string& nombre, size_t inicio, size_t fin) {
        for (size_t i = inicio; i <= fin; ++i) {
            problema->añadirRestriccion(
                genEt(nombre, i),
                {
                    {2, genEt("xg", i)},
                    {-2, genEt("xg", i + 1)},
                    {1, genEt("xg", i + 2)},
                    {1, genEt("xg", i + 3)}
                },
                ">=",
                0
            );
            problema->añadirRestriccion(
                genEt(nombre + "_off", i),
                {
                    {2, genEt("xg", i)},
                    {-2, genEt("xg", i + 1)},
                    {1, genEt("xg", i + 2)},
                    {1, genEt("xg", i + 3)}
                },
                "<=",
                2
            );
        }
    };
    if (h_c > 3) {
        agregarRestriccionesDuracion("duracion_min", 1, h_c - 3);
    }

    // --- VARIABLES ---
    for (size_t i = 1; i <= h_c; ++i) {
        // Variables continuas
        problema->añadirVariable("g" + StringIdGen + "(" + to_string(i) + ")", 2, 0, 0); 

        // Variables binarias
        problema->añadirBinario(genEt("xg", i));
        problema->añadirBinario(genEt("yg", i));
    }

    // Guardar nombres de variables internas
    nombresVariables.push_back(genEt("wg", 0));
    nombresVariables.push_back(genEt("xg", 0));
    nombresVariables.push_back(genEt("yg", 0));
    nombresVariables.push_back("g" + std::to_string(idGen));

    // --- FUNCIÓN OBJETIVO ---
    for (size_t i = 1; i <= h_c; ++i) {
        problema->añadirTerminoFuncionObjetivo(costoFijo, genEt("xg", i));
        problema->añadirTerminoFuncionObjetivo(costoVariable, "g" + StringIdGen + "(" + to_string(i) + ")");
        problema->añadirTerminoFuncionObjetivo(costoEncendido, genEt("yg", i));
    }
}

// --- Postprocesamiento ---
void UnidadTermicaRapida::posprocesamiento(Problema* problema) {
    (void)problema;  // parámetro no usado
    // Por ahora no hace nada
}