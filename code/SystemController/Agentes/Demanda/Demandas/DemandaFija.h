#ifndef DEMANDAFIJA_H
#define DEMANDAFIJA_H

#include "SystemController/Agentes/Demanda/Demanda.h"
#include <vector>
using namespace std; 

class DemandaFija : public Demanda {
public:
    DemandaFija(int idAgente, int idDemanda, vector<double> valores, int horizonteTemporal):
        Demanda(idAgente, horizonteTemporal, idDemanda, valores)
    {
        nombre = "Demanda Fija";
    } 

    ~DemandaFija() {
        // std::cout << "\033[31m[DemandaFija] Destruida\033[0m" << std::endl; // Mensaje en rojo
    }

    void contribuirAlProblema(Problema* problema, int horizonteTemporal) override;

    void posprocesamiento(Problema* problema) override;

private:
};

#endif // DEMANDAFIJA_H