#include "DespachoProporcional.h"
#include <iostream>
#include <stdexcept>

using namespace std;

void DespachoProporcional::contribuirAlProblema(Problema* problema, vector<Generacion*> agentesGen, vector<double> demandas) {
    Despacho::contribuirAlProblema(problema,agentesGen,demandas);

    // El aporte de la generación a la función objetivo
    for (int i = 1; i <= periodo; i++) {
        double CFt = proporcion/demandaTotal[i-1];
        problema->sumarConstanteFuncionObjetivo(CFt*demandas[i-1]);
        problema->añadirTerminoFuncionObjetivo(-1 * CFt, "g(" + to_string(i) + ")");
    }
}

double DespachoProporcional::getProporcion() {
    return proporcion;
}

void DespachoProporcional::setProporcion(double nuevaProporcion) {
    proporcion = nuevaProporcion;
}

const std::vector<double>& DespachoProporcional::getDemandaTotal() {
    return demandaTotal;
}

// Setter
void DespachoProporcional::setDemandaTotal(std::vector<double>& d) {
    demandaTotal = d;
}

void DespachoProporcional::posprocesamiento(Problema* problema, vector<Generacion*> agentesGen) {
    Despacho::posprocesamiento(problema,agentesGen);
}
