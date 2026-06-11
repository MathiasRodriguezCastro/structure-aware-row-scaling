#ifndef SALTO_GRANDE_H
#define SALTO_GRANDE_H

#include <vector>
#include <string>
#include "../../Generacion.h"
#include <iostream>

using namespace std;

class SaltoGrande : public Generacion {
public:
    // Constructor 
    SaltoGrande(
        int id,
        int idGen,
        int h_c,
        double costoAguaSalto,
        const std::vector<double> aportesSalto,
        double volumenInicial,
        bool compactar8h = false
    );

    ~SaltoGrande() {
        // std::cout << "\033[31m[SaltoGrande] Destruido\033[0m" << std::endl;
    }

    string genEt(string nombre, int parametro);

    void contribuirAlProblema(Problema* problema, int horizonteTemporal) override;
    void generarAporteFuncionObjetivo(Problema* problema, int horizonteTemporal);

    void posprocesamiento(Problema* problema) override;

    // ===== Getters r =====
    double getR1() const;
    double getR2() const;
    double getR3() const;
    double getR4() const;

    // ===== Getters s =====
    double getS2() const;
    double getS3() const;
    double getS4() const;

    // ===== Getters Vh =====
    double getVh1() const;
    double getVh2() const;
    double getVh3() const;
    double getVh4() const;
    double getVh5() const;

    // ===== Getters DVh =====
    double getDVh2() const;
    double getDVh3() const;
    double getDVh4() const;
    double getDVh5() const;

    // ===== Setters r =====
    void setR1(double value);
    void setR2(double value);
    void setR3(double value);
    void setR4(double value);

    // ===== Setters s =====
    void setS2(double value);
    void setS3(double value);
    void setS4(double value);

    // ===== Setters Vh =====
    void setVh1(double value);
    void setVh2(double value);
    void setVh3(double value);
    void setVh4(double value);
    void setVh5(double value);

    // ===== Setters DVh =====
    void setDVh2(double value);
    void setDVh3(double value);
    void setDVh4(double value);
    void setDVh5(double value);

protected:
    // ================================
    // Datos físicos básicos
    // ================================

    double volumenInicial;
    double volumenMinimo;
    double volumenMaximo;

    double nivelMinimo;
    double nivelMaximo;

    double caudalTurbinadoMaximo;
    double vertimientoMaximo;

    // ================================
    // Cotas de la parte tangente z4h
    // ================================
    //
    // z4h no representa la generación total de Salto Grande.
    // Representa solo la parte cóncava:
    //
    // z4h ≈ p41*x4h - p44*x4h^2
    //
    // Por eso no debe acotarse con 1890 MW.
    // Su máximo natural se calcula como:
    //
    // maximoTangenteSalto = sal(p_hat, caudalTurbinadoMaximo)

    double minimoTangenteSalto;
    double maximoTangenteSalto;

    // ================================
    // Coeficientes de producción aproximada
    // ================================

    double p41;
    double p42;
    double p43;
    double p44;
    double p45;

    // ================================
    // Tangentes de z4h
    // ================================

    double r41;
    double r42;
    double r43;
    double r44;

    double s42;
    double s43;
    double s44;

    // ================================
    // Umbrales de volumen
    // ================================

    double V4h1;
    double V4h2;
    double V4h3;
    double V4h4;
    double V4h5;

    // ================================
    // Diferencias de volumen
    // ================================

    double DV4h2;
    double DV4h3;
    double DV4h4;
    double DV4h5;

    double DV4h22;
    double DV4h32;
    double DV4h42;
    double DV4h52;

    // ================================
    // Big-M
    // ================================

    double M4;

    // ================================
    // Costo de agua y aportes
    // ================================

    double costoAguaSalto;
    const std::vector<double> aportes;
    bool compactarActivacionTramos8h;
};

#endif // SALTO_GRANDE_H
