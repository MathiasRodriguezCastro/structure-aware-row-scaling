#ifndef PROBLEMASCPLEX_H
#define PROBLEMASCPLEX_H

#include "SystemController/Problema/Problema.h"
#include <ilcplex/ilocplex.h>
#include <vector>
#include <string>
#include <map>
#include <set>

class ProblemaCplex : public Problema {
private:
    IloEnv env;
    IloModel modelo;
    std::map<std::string, IloNumVar> vars;
    std::map<std::string, int> varIndex;
    IloObjective objetivoModelo;   // objetivo lineal del modelo (handle para poder reemplazarlo en la proyección)

public:
    ProblemaCplex();
    virtual ~ProblemaCplex() override;

    void procesar(bool flagConstante) override;
    void grabar(std::string& ruta) override;
    void resolverMonolitico() override;
    void mostrar() override;

};

#endif // PROBLEMASCPLEX_H