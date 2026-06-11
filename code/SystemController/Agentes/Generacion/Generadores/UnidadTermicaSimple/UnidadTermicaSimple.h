#ifndef UNIDADTERMICASIMPLE_H
#define UNIDADTERMICASIMPLE_H

#include "../../Generacion.h"
#include <string>
#include <vector>
#include <map>

using namespace std;

class UnidadTermicaSimple : public Generacion {
public:
    explicit UnidadTermicaSimple(
        int id,
        int idGen,
        int h_c,
        double MGT,   // Potencia máxima
        double b      // Costo variable
    );

    virtual ~UnidadTermicaSimple() = default;

    std::string genEt(const std::string& nombre, int parametro) const;
    void contribuirAlProblema(Problema* problema, int horizonteTemporal) override;
    void posprocesamiento(Problema* problema) override;

    void setPotenciaMax(double MGT) { potenciaMax = MGT; }
    void setCostoVariable(double b) { costoVariable = b; }

    double getPotenciaMax() const { return potenciaMax; }
    double getCostoVariable() const { return costoVariable; }

private:
    double potenciaMax;
    double costoVariable;
};

#endif // UNIDADTERMICASIMPLE_H