#include "DespachoFijo.h"
#include <iostream>
#include <stdexcept>

using namespace std;

void DespachoFijo::contribuirAlProblema(Problema* problema, vector<Generacion*> agentesGen, vector<double> demandas) {
    Despacho::contribuirAlProblema(problema,agentesGen, demandas);

    // El aporte de la generación a la función objetivo
    for (int i = 1; i <= periodo; i++) {  // Sumatoria de CF * (d[i]-g[i])
        problema->sumarConstanteFuncionObjetivo(costoDeFalla * demandas[i-1]);
        problema->añadirTerminoFuncionObjetivo(-1 * costoDeFalla, "g(" + to_string(i) + ")");
    }
}

double DespachoFijo::getCostoFalla() {
    return costoDeFalla;
}

void DespachoFijo::setCostoFalla(double cf) {
    costoDeFalla = cf;
}

void DespachoFijo::posprocesamiento(
    Problema* problema,
    vector<Generacion*> agentesGen
) {
    Despacho::posprocesamiento(problema, agentesGen);
}