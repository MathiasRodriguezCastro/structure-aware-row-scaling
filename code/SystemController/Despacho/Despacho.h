#ifndef DESPACHO_H
#define DESPACHO_H

#include "SystemController/Problema/Problema.h"
#include "SystemController/Agentes/Generacion/Generacion.h"
#include <vector>
#include <string>
#include <map>
using namespace std;

class Despacho {
public:
    // Constructor
    explicit Despacho(int horizonteTemporal) 
        : periodo(horizonteTemporal)
    {}

    // Destructor
    virtual ~Despacho() = default;

    // ------------------ Métodos principales ------------------
    virtual void contribuirAlProblema(Problema* problema, vector<Generacion*> agentesGen, vector<double> demandas);
    virtual void posprocesamiento(Problema* problema, vector<Generacion*> agentesGen);

    // ------------------ Getters / Setters ------------------
    int getPeriodo();
    void setPeriodo(int p);

    const std::vector<std::string>& getNombresVariables();
    void setNombresVariables(const std::vector<std::string>& nombres);

protected:
    std::vector<std::string> nombresVariables;
    int periodo;
    
};

#endif // DESPACHO_H