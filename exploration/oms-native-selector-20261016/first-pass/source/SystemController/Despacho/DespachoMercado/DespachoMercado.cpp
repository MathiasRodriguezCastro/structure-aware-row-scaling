#include "DespachoMercado.h"
#include <stdexcept>
#include <string>
#include <vector>
#include <cmath>

#include <algorithm>
#include <iostream>
#include <iomanip>
#include <map>

using namespace std;

// ------------------ Getters / Setters ------------------

const vector<double>& DespachoMercado::getDemandaTotal() const {
    return demandaTotal;
}

void DespachoMercado::setDemandaTotal(const vector<double>& d) {
    demandaTotal = d;
}

const vector<double>& DespachoMercado::getPorcentajesTramos() const {
    return porcentajesTramos;
}

void DespachoMercado::setPorcentajesTramos(const vector<double>& tramos) {
    porcentajesTramos = tramos;
}

const vector<double>& DespachoMercado::getCostosMarginales() const {
    return costosMarginales;
}

void DespachoMercado::setCostosMarginales(const vector<double>& costos) {
    costosMarginales = costos;
}

size_t DespachoMercado::getCantidadTramos() const {
    return porcentajesTramos.size();
}

// ------------------ Métodos auxiliares ------------------

void DespachoMercado::validarParametros() const {
    if (porcentajesTramos.empty()) {
        throw invalid_argument("DespachoMercado: debe haber al menos un tramo.");
    }

    if (porcentajesTramos.size() != costosMarginales.size()) {
        throw invalid_argument("DespachoMercado: porcentajesTramos y costosMarginales deben tener el mismo tamaño.");
    }

    for (size_t i = 0; i < porcentajesTramos.size(); ++i) {
        if (porcentajesTramos[i] <= 0.0 || porcentajesTramos[i] > 1.0) {
            throw invalid_argument("DespachoMercado: los porcentajes deben estar en (0,1].");
        }

        if (i > 0 && porcentajesTramos[i] <= porcentajesTramos[i - 1]) {
            throw invalid_argument("DespachoMercado: los porcentajes de tramo deben ser estrictamente crecientes.");
        }
    }

    for (size_t i = 1; i < costosMarginales.size(); ++i) {
        if (costosMarginales[i] < costosMarginales[i - 1]) {
            throw invalid_argument("DespachoMercado: los costos marginales deben ser no decrecientes.");
        }
    }

    // Recomendable si se quiere cubrir hasta el 100% de la falla.
    if (std::abs(porcentajesTramos.back() - 1.0) > 1e-9) {
        throw invalid_argument("DespachoMercado: el último porcentaje de tramo debe ser 1.0.");
    }
}

// Calcula los interceptos p_k para que las rectas
//
//     costoFalla_t >= p_k + q_k * s_t
//
// sean continuas en los puntos de quiebre,
// donde:
//
//     s_t = d_t - g_t
//
// y d_t es la demanda usada para escalar los tramos.
vector<double> DespachoMercado::calcularInterceptos(double demandaHora) const {
    if (demandaHora < 0.0) {
        throw invalid_argument("DespachoMercado: la demanda horaria no puede ser negativa.");
    }

    vector<double> interceptos(costosMarginales.size(), 0.0);

    for (size_t k = 1; k < costosMarginales.size(); ++k) {
        double quiebreAnterior = porcentajesTramos[k - 1] * demandaHora;

        interceptos[k] = interceptos[k - 1]
                       + (costosMarginales[k - 1] - costosMarginales[k]) * quiebreAnterior;
    }

    return interceptos;
}

// ------------------ Método principal ------------------

void DespachoMercado::contribuirAlProblema(
    Problema* problema,
    vector<Generacion*> agentesGen,
    vector<double> demandas
) {
    if (problema == nullptr) {
        throw invalid_argument("DespachoMercado: problema es nullptr.");
    }

    validarParametros();
    Despacho::contribuirAlProblema(problema, agentesGen, demandas);

    if (demandas.size() != static_cast<size_t>(periodo)) {
        throw invalid_argument("DespachoMercado: el tamaño de demandas no coincide con el horizonte temporal.");
    }

    const vector<double>& demandaParaTramos = demandaTotal.empty() ? demandas : demandaTotal;

    if (demandaParaTramos.size() != static_cast<size_t>(periodo)) {
        throw invalid_argument("DespachoMercado: el tamaño de demandaTotal no coincide con el horizonte temporal.");
    }

    const int TIPO_COTA_COSTO_FALLA = 0;
    const double COTA_SUP_COSTO_FALLA = 1e20;

    for (int i = 1; i <= periodo; ++i) {
        string nombreCostoFalla = "costoFalla(" + to_string(i) + ")";
        string nombreGt = "g(" + to_string(i) + ")";

        double dFaltante = demandas[i - 1];
        double dEscalones = demandaParaTramos[i - 1];

        vector<double> interceptos = calcularInterceptos(dEscalones);

        problema->añadirVariable(
            nombreCostoFalla,
            TIPO_COTA_COSTO_FALLA,
            0.0,
            COTA_SUP_COSTO_FALLA
        );

        problema->añadirTerminoFuncionObjetivo(1.0, nombreCostoFalla);

        for (size_t k = 0; k < costosMarginales.size(); ++k) {
            double q = costosMarginales[k];
            double p = interceptos[k];

            problema->añadirRestriccion(
                "falla_tramo(" + to_string(i) + "," + to_string(k + 1) + ")",
                {
                    {1.0, nombreCostoFalla},
                    {q, nombreGt}
                },
                ">=",
                p + q * dFaltante
            );
        }
    }
}

void DespachoMercado::posprocesamiento(
    Problema* problema,
    vector<Generacion*> agentesGen
) {
    if (problema == nullptr) {
        throw invalid_argument("DespachoMercado::posprocesamiento - problema es nullptr.");
    }

    Despacho::posprocesamiento(problema, agentesGen);
}