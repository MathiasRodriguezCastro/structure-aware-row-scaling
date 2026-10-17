#ifndef DESPACHOPROPORCIONAL_H
#define DESPACHOPROPORCIONAL_H

#include "SystemController/Despacho/Despacho.h"
#include <map>
#include <string>

class DespachoProporcional : public Despacho {
public:
    // ------------------ Constructor ------------------
    explicit DespachoProporcional(int horizonteTemporal, double proporcion, vector<double> demandaTotal)
        : Despacho(horizonteTemporal), proporcion(proporcion), demandaTotal(demandaTotal)
    {}

    // ------------------ Destructor ------------------
    virtual ~DespachoProporcional() override = default;

    // ------------------ Métodos principales ------------------
    void contribuirAlProblema(Problema* problema, vector<Generacion*> agentesGen, vector<double> demandas) override;

    void posprocesamiento(Problema* problema, vector<Generacion*> agentesGen) override;

    double getProporcion();
    void setProporcion(double nuevaProporcion);

    const std::vector<double>& getDemandaTotal() ;
    void setDemandaTotal(std::vector<double>& d);

private:
    double proporcion;
    vector<double> demandaTotal;
};

#endif // DESPACHOPROPORCIONAL_H