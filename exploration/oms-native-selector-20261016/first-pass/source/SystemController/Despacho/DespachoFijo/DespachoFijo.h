#ifndef DESPACHOFIJO_H
#define DESPACHOFIJO_H

#include "SystemController/Despacho/Despacho.h"
#include <map>
#include <string>

class DespachoFijo : public Despacho {
public:
    // ------------------ Constructor ------------------
    explicit DespachoFijo(int horizonteTemporal, double cf)
        : Despacho(horizonteTemporal), costoDeFalla(cf)
    {}

    // ------------------ Destructor ------------------
    virtual ~DespachoFijo() override = default;

    double getCostoFalla();
    void setCostoFalla(double cf);

    // ------------------ Métodos principales ------------------
    void contribuirAlProblema(Problema* problema, vector<Generacion*> agentesGen, vector<double> demandas) override;

    void posprocesamiento(Problema* problema, vector<Generacion*> agentesGen) override;

private:
    double costoDeFalla;
};

#endif // DESPACHOFIJO_H