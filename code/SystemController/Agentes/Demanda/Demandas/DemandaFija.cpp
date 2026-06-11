#include "DemandaFija.h"
#include <iostream>


using namespace std; 

void DemandaFija::contribuirAlProblema(Problema* problema, int horizonteTemporal) {
    if (!problema) {
        throw std::invalid_argument("DemandaFija::contribuirAlProblema - puntero 'problema' nulo.");
    }

    if (demandas.size() != static_cast<size_t>(horizonteTemporal)) {
        throw std::invalid_argument(
            "DemandaFija::contribuirAlProblema - tamaño de 'demandas' distinto que el horizonte temporal.");
    }
}

void DemandaFija::posprocesamiento(Problema* problema) {
    (void)problema;
}