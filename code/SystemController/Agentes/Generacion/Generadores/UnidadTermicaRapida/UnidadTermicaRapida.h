#ifndef UNIDADTERMICARAPIDA_H
#define UNIDADTERMICARAPIDA_H

#include "../../Generacion.h"
#include <string>
#include <vector>
#include <map>
using namespace std;

class UnidadTermicaRapida : public Generacion {
public:
    // Constructor
    explicit UnidadTermicaRapida(
        int id,
        int idGen,
        double h_c,    // Horizonte temporal
        double mGT,    // Potencia mínima técnica
        double MGT,    // Potencia máxima técnica
        double a,      // Costo fijo por hora de operación
        double b,      // Costo variable asociado a la generación
        double alpha   // costoEncendido
    );

    virtual ~UnidadTermicaRapida() = default;

    // --- Métodos principales ---
    std::string genEt(const std::string& nombre, int parametro) const;
    void contribuirAlProblema(Problema* problema, int horizonteTemporal) override;
    void posprocesamiento(Problema* problema) override;

    // ===== Setters =====
    void setPotenciaMin(double mGT) { potenciaMin = mGT; }
    void setPotenciaMax(double MGT) { potenciaMax = MGT; }
    void setCostoFijo(double a) { costoFijo = a; }
    void setCostoVariable(double b) { costoVariable = b; }
    void setCostoEncendido(double alpha) { costoEncendido = alpha; }

    // ===== Getters =====
    double getPotenciaMin() const { return potenciaMin; }
    double getPotenciaMax() const { return potenciaMax; }
    double getCostoFijo() const { return costoFijo; }
    double getCostoVariable() const { return costoVariable; }
    double getCostoEncendido() const { return costoEncendido; }

private:
    double potenciaMin;    // mGT
    double potenciaMax;    // MGT
    double costoFijo;      // a
    double costoVariable;  // b
    double costoEncendido; // alpha
};

#endif // UNIDADTERMICARAPIDA_H