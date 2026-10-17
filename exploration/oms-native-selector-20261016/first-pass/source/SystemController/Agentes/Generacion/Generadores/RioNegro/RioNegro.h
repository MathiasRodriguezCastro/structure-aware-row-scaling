#ifndef RIO_NEGRO_H
#define RIO_NEGRO_H

#include <vector>
#include <string>
#include "../../Generacion.h"
#include <iostream>

using namespace std;

class RioNegro : public Generacion {
public:
    // Constructor 
    RioNegro(
        int id,
        int idGen,
        const std::vector<double> aportesBonete,
        const std::vector<double> aportesBaygorria,
        const std::vector<double> aportesPalmar,
        double volumenInicialBonete,
        double volumenInicialPalmar,
        double costoAguaBonete,
        double costoAguaPalmar,
        int h_c,
        bool compactar8h = false
    );

    ~RioNegro() {
        // std::cout << "\033[31m[RioNegro] Destruido\033[0m" << std::endl;
    }

    string genEt(string nombre, int parametro);

    virtual void generarRestriccionesBonete(Problema* problema, int h_c);
    void generarRestriccionesBaygorria(Problema* problema, int h_c);
    void generarRestriccionesPalmar(Problema* problema, int h_c);

    virtual void generarAporteFuncionObjetivo(Problema* problema, int h_c);

    void contribuirAlProblema(Problema* problema, int horizonteTemporal) override;

    void generarRestriccionEnergia(Problema* problema, int h_c);

    void posprocesamiento(Problema* problema) override;

    // ===== Setters =====
    void setAjusteCoef(const double coef);
    void setAportesBonete(const std::vector<double> aportes);
    void setAportesBaygorria(const std::vector<double> aportes);
    void setAportesPalmar(const std::vector<double> aportes);
    void setVolumenInicialBonete(const double volumen);
    void setVolumenInicialPalmar(const double volumen);
    void setCostoAguaBonete(const double costo);
    void setCostoAguaPalmar(const double costo);

    // ===== Getters =====
    double getAjusteCoef() const;
    std::vector<double> getAportesBonete() const;
    std::vector<double> getAportesBaygorria() const;
    std::vector<double> getAportesPalmar() const;
    double getVolumenInicialBonete() const;
    double getVolumenInicialPalmar() const;
    double getCostoAguaBonete() const;
    double getCostoAguaPalmar() const;

protected:
    // ********* Pre-cálculos *********
    void inicializarLimites(double& minFlujo, double& maxFlujo,
                                  double& minVertido, double& maxVertido,
                                  double& volMin, double& volMax,
                                  double& minTang, double& maxTang,
                                  double& minGen,
                                  double flujoMin, double flujoMax,
                                  double vertidoMin, double vertidoMax,
                                  double vMin, double vMax,
                                  double tangMin, double tangMax,
                                  double genMin);
    void inicializarBonete();
    void inicializarBaygorria(); 
    void inicializarPalmar();
    void calcularCoeficientesTangentes();
    void min_sqr();
    void calcular_M1(int hc);
    void calcular_M3(int hc);


    double bon_function(double x);
    double dbon_function(double x);
    double bay_function(double x);
    double dbay_function(double x);
    double pal_function(double x);
    double dpal_function(double x);

    // === Datos básicos ===
    double ajuste_coef;

    // Aportes
    std::vector<double> aportesBonete, aportesBaygorria, aportesPalmar;
    // Volumen iniciales
    double volumenInicialBonete, volumenInicialPalmar;
    // Costos de agua
    double costoAguaBonete, costoAguaPalmar;

    // === Identificadores ===
    string idBonete, idBaygorria, idPalmar;

    // === Constantes y límites ===
    // Bonete
    double minimoFlujoBonete, maximoFlujoBonete;
    double minimoVertidoBonete, maximoVertidoBonete;
    double volumenMinimoBonete, volumenMaximoBonete;
    double minimoTangenteBonete, maximoTangenteBonete;

    // Baygorria
    double minimoFlujoBaygorria, maximoFlujoBaygorria;
    double minimoVertidoBaygorria, maximoVertidoBaygorria;
    double minimoTangenteBaygorria, maximoTangenteBaygorria;

    // Palmar
    double minimoFlujoPalmar, maximoFlujoPalmar;
    double minimoVertidoPalmar, maximoVertidoPalmar;
    double volumenMinimoPalmar, volumenMaximoPalmar;
    double minimoTangentePalmar, maximoTangentePalmar;

    // === Mínimos de generación ===
    double genMinBonete, genMinBaygorria, genMinPalmar;

    // === Coeficientes de producción ===
    // Bonete
    double p11, p12, p13, p14;
    // Baygorria
    double p21, p22, p23, p24;
    // Palmar
    double p31, p32, p33, p34, p35;

    // === Coeficientes de rectas tangentes ===
    // Bonete
    double r11_hat, r12_hat, s12_hat;
    // Baygorria
    double r21_hat, r22_hat, s22_hat;
    // Palmar
    double r31_hat, r32_hat, r33_hat, s32_hat, s33_hat;

    // === Coeficientes de regresión para Baygorria ===
    double bygX, bygV;

    // === Coeficientes k para la ecuación 10 ===
    // Bonete
    double k11, k12, k13;
    // Palmar
    double k31, k32, k33, k34, k35;

    // === M1 y M3 para restricciones big-M ===
    double M1, M3;

    double V1h2, V1h3;
    double V3h2, V3h3, V3h4, V3h5;

    bool compactarActivacionTramos8h;
};

#endif // RIO_NEGRO_H
