#ifndef DESPACHOMERCADO_H
#define DESPACHOMERCADO_H

#include "SystemController/Despacho/Despacho.h"
#include <vector>
#include <string>
#include <cstddef>

class DespachoMercado : public Despacho {
public:
    // ------------------ Constructor ------------------
    explicit DespachoMercado(
        int horizonteTemporal,
        const std::vector<double>& porcentajesTramos,
        const std::vector<double>& costosMarginales
    )
        : Despacho(horizonteTemporal),
          porcentajesTramos(porcentajesTramos),
          costosMarginales(costosMarginales)
    {}

    // ------------------ Destructor ------------------
    virtual ~DespachoMercado() override = default;

    // ------------------ Getters / Setters ------------------
    const std::vector<double>& getDemandaTotal() const;
    void setDemandaTotal(const std::vector<double>& d);

    const std::vector<double>& getPorcentajesTramos() const;
    void setPorcentajesTramos(const std::vector<double>& tramos);

    const std::vector<double>& getCostosMarginales() const;
    void setCostosMarginales(const std::vector<double>& costos);

    std::size_t getCantidadTramos() const;

    // ------------------ Métodos principales ------------------
    void contribuirAlProblema(Problema* problema, vector<Generacion*> agentesGen, std::vector<double> demandas) override;

    void posprocesamiento(Problema* problema, vector<Generacion*> agentesGen) override;

private:
    std::vector<double> demandaTotal;

    // Porcentajes acumulados de demanda de cada quiebre.
    // Ejemplo: {0.02, 0.07, 0.145, 1.0}
    std::vector<double> porcentajesTramos;

    // Costos marginales por tramo.
    // Ejemplo: {370.0, 600.0, 2400.0, 4000.0}
    std::vector<double> costosMarginales;

    // Calcula los interceptos p_i para cada hora,
    // de forma que la función lineal a trozos sea continua.
    std::vector<double> calcularInterceptos(double demandaHora) const;

    // Validación básica de tamaños y orden de parámetros
    void validarParametros() const;
};

#endif // DESPACHOMERCADO_H