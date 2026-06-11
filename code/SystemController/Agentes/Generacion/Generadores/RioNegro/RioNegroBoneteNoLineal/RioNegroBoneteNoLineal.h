#ifndef RIO_NEGRO_BONETE_NO_LINEAL_H
#define RIO_NEGRO_BONETE_NO_LINEAL_H

#include "../RioNegro.h"

class RioNegroBoneteNoLineal : public RioNegro {
public:
    RioNegroBoneteNoLineal(
        int id,
        int idGen,
        const std::vector<double>& aportesBonete,
        const std::vector<double>& aportesBaygorria,
        const std::vector<double>& aportesPalmar,
        double volumenInicialBonete,
        double volumenInicialPalmar,
        double costoAguaPalmar,
        int h_c,
        std::vector<double> volumenesBonete,
        std::vector<double> valoresBellman,
        std::vector<double> derivadasValoresBellman,
        bool compactar8h = false
    );

    // === Sobrescrituras específicas ===
    virtual void generarRestriccionesBonete(Problema* problema, int h_c) override;
    virtual void generarAporteFuncionObjetivo(Problema* problema, int h_c) override;

protected:
    double valorBellman(double x);
    double valorMarginalBellman(double x);
    vector<double> volumenesBonete;
    vector<double> valoresBellman;
    vector<double> derivadasValoresBellman;  
};

#endif // RIO_NEGRO_BONETE_NO_LINEAL_H
