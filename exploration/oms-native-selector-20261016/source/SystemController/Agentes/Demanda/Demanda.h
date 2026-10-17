#ifndef DEMANDA_H
#define DEMANDA_H

#include <string>
#include <iostream>
#include <vector>
#include <stdexcept>  // para invalid_argument
#include "SystemController/Agentes/Agente.h"

using namespace std;

/// Representa una unidad de demanda de energía en el sistema.
class Demanda : public Agente {
public:
    explicit Demanda(int idAgente, int h_c, int idDemanda, vector<double> valores)
        : Agente(idAgente, h_c), idDem(idDemanda), demandas(valores) {
        if (valores.size() != static_cast<size_t>(h_c)) {
            throw invalid_argument("Demanda: tamaño de demandas (" + 
                                to_string(valores.size()) + ") no coincide con horizonte (" + 
                                to_string(h_c) + ")");
        }
    }

    virtual ~Demanda() = default;

    // Setter y getter
    void setIdDem(int id) { idDem = id; }
    int getIdDem() const { return idDem; }

    vector<double> getDemandas() { return demandas; }
    void setDemandas(vector<double> d) { demandas = d; }

protected:
    int idDem = -1;  ///< Identificador único de la demanda
    vector<double> demandas;
};

#endif // DEMANDA_H