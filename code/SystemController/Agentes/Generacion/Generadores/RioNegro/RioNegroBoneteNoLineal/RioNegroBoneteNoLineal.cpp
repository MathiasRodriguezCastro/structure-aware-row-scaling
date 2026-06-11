#include "RioNegroBoneteNoLineal.h"

#include <iostream>
#include <cmath>
#include <stdexcept>
#include <iomanip>

using std::vector;
using std::string;
using std::to_string;

// =====================================================
// Constructor
// =====================================================
RioNegroBoneteNoLineal::RioNegroBoneteNoLineal(
    int id,
    int idGen,
    const std::vector<double>& aportesBonete,
    const std::vector<double>& aportesBaygorria,
    const std::vector<double>& aportesPalmar,
    double volumenInicialBonete,
    double volumenInicialPalmar,
    double costoAguaPalmar,
    int h_c,
    vector<double> volumenesBonete,
    vector<double> valoresBellman,
    vector<double> derivadasValoresBellman,
    bool compactar8h
) : RioNegro(
        id,
        idGen,
        aportesBonete,
        aportesBaygorria,
        aportesPalmar,
        volumenInicialBonete,
        volumenInicialPalmar,
        0.0,              // El costo de agua de Bonete no se utiliza en la versión no lineal
        costoAguaPalmar,
        h_c,
        compactar8h
    ),
    volumenesBonete(volumenesBonete),
    valoresBellman(valoresBellman),
    derivadasValoresBellman(derivadasValoresBellman)
{
    std::cerr << std::setprecision(15);
    std::cerr << "\n========== DEBUG CONSTRUCTOR RioNegroBoneteNoLineal ==========\n";
    std::cerr << "volumenesBonete.size()         = " << this->volumenesBonete.size() << "\n";
    std::cerr << "valoresBellman.size()          = " << this->valoresBellman.size() << "\n";
    std::cerr << "derivadasValoresBellman.size() = " << this->derivadasValoresBellman.size() << "\n";

    if (!this->volumenesBonete.empty()) {
        std::cerr << "volumenesBonete.front() = " << this->volumenesBonete.front() << "\n";
        std::cerr << "volumenesBonete.back()  = " << this->volumenesBonete.back() << "\n";
    }

    std::cerr << "==============================================================\n\n";
}


// =====================================================
// Funciones auxiliares para Bonete no lineal
// =====================================================

double RioNegroBoneteNoLineal::valorBellman(double x) {
    if (volumenesBonete.empty() || valoresBellman.empty()) {
        throw std::runtime_error(
            "RioNegroBoneteNoLineal::valorBellman: volumenesBonete o valoresBellman esta vacio."
        );
    }

    if (volumenesBonete.size() != valoresBellman.size()) {
        throw std::runtime_error(
            "RioNegroBoneteNoLineal::valorBellman: volumenesBonete y valoresBellman tienen distinto largo."
        );
    }

    if (x <= volumenesBonete.front()) {
        return valoresBellman.front();
    }

    if (x >= volumenesBonete.back()) {
        return valoresBellman.back();
    }

    size_t best = 0;
    double bestDist = std::fabs(x - volumenesBonete[0]);

    for (size_t i = 1; i < volumenesBonete.size(); i++) {
        double d = std::fabs(x - volumenesBonete[i]);

        if (d < bestDist) {
            bestDist = d;
            best = i;
        }
    }

    return valoresBellman[best];
}


double RioNegroBoneteNoLineal::valorMarginalBellman(double x) {
    if (volumenesBonete.empty() || derivadasValoresBellman.empty()) {
        throw std::runtime_error(
            "RioNegroBoneteNoLineal::valorMarginalBellman: volumenesBonete o derivadasValoresBellman esta vacio."
        );
    }

    if (volumenesBonete.size() != derivadasValoresBellman.size()) {
        throw std::runtime_error(
            "RioNegroBoneteNoLineal::valorMarginalBellman: volumenesBonete y derivadasValoresBellman tienen distinto largo."
        );
    }

    if (x <= volumenesBonete.front()) {
        return derivadasValoresBellman.front();
    }

    if (x >= volumenesBonete.back()) {
        return derivadasValoresBellman.back();
    }

    size_t best = 0;
    double bestDist = std::fabs(x - volumenesBonete[0]);

    for (size_t i = 1; i < volumenesBonete.size(); i++) {
        double d = std::fabs(x - volumenesBonete[i]);

        if (d < bestDist) {
            bestDist = d;
            best = i;
        }
    }

    return derivadasValoresBellman[best];
}


// =====================================================
// Restricciones Bonete no lineal
// =====================================================
void RioNegroBoneteNoLineal::generarRestriccionesBonete(Problema* problema, int h_c) {
    // 1. Restricciones base de Bonete
    RioNegro::generarRestriccionesBonete(problema, h_c);

    // 2. Chequeos de consistencia
    if (volumenesBonete.empty() || valoresBellman.empty() || derivadasValoresBellman.empty()) {
        throw std::runtime_error(
            "RioNegroBoneteNoLineal: los vectores de Bellman estan vacios."
        );
    }

    if (volumenesBonete.size() != valoresBellman.size() ||
        volumenesBonete.size() != derivadasValoresBellman.size()) {
        throw std::runtime_error(
            "RioNegroBoneteNoLineal: volumenesBonete, valoresBellman y derivadasValoresBellman no tienen el mismo largo."
        );
    }

    // 3. Variable adicional delta1h
    //
    // Esta variable representa el costo futuro aproximado de Bonete.
    problema->añadirVariable(genEt("delta1h", 0), 3, 0, 0);
    nombresVariables.push_back(genEt("delta1h", 0));

    // 4. Conversión de unidades
    //
    // El modelo hidráulico trabaja los volúmenes en m3:
    //      a1_v1h(t) está en m3.
    //
    // La curva de Bellman de Bonete viene en hm3:
    //      volumenesBonete está entre aprox. 1487 y 10239 hm3.
    //
    // Por tanto:
    //      1 hm3 = 1.000.000 m3.
    const double M3_A_HM3 = 1.0 / 1000000.0;

    // Volumen inicial en hm3
    const double v0 = volumenInicialBonete * M3_A_HM3;

    // Puntos de referencia deseados en hm3
    const double vRef1 = 0.85 * v0;
    const double vRef2 = v0;
    const double vRef3 = 1.15 * v0;

    // 5. Función local para encontrar el índice de la grilla más cercano
    //
    // Esto es clave para que el RHS coincida con el .lp de referencia:
    // no alcanza con usar B(vRef) y q(vRef); también hay que usar el volumen
    // de la grilla elegido en el término q * vCorte.
    auto indiceBellmanMasCercano = [&](double x) -> size_t {
        if (volumenesBonete.empty()) {
            throw std::runtime_error(
                "RioNegroBoneteNoLineal: volumenesBonete esta vacio."
            );
        }

        if (x <= volumenesBonete.front()) {
            return 0;
        }

        if (x >= volumenesBonete.back()) {
            return volumenesBonete.size() - 1;
        }

        size_t best = 0;
        double bestDist = std::fabs(x - volumenesBonete[0]);

        for (size_t i = 1; i < volumenesBonete.size(); ++i) {
            double d = std::fabs(x - volumenesBonete[i]);

            if (d < bestDist) {
                bestDist = d;
                best = i;
            }
        }

        return best;
    };

    // 6. Índices efectivos usados para los cortes
    const size_t i0 = indiceBellmanMasCercano(v0);
    const size_t i1 = indiceBellmanMasCercano(vRef1);
    const size_t i2 = indiceBellmanMasCercano(vRef2);
    const size_t i3 = indiceBellmanMasCercano(vRef3);

    // 7. Volúmenes reales de grilla usados en los cortes
    //
    // IMPORTANTE:
    // Estos son los que deben entrar en el RHS, no vRef1/vRef2/vRef3.
    const double vCorte0 = volumenesBonete[i0];
    const double vCorte1 = volumenesBonete[i1];
    const double vCorte2 = volumenesBonete[i2];
    const double vCorte3 = volumenesBonete[i3];

    // 8. Chequeo de rango
    std::cerr << std::setprecision(15);
    std::cerr << "\n========== DEBUG RANGO BONETE ==========\n";
    std::cerr << "volumenInicialBonete [m3] = " << volumenInicialBonete << "\n";
    std::cerr << "v0 [hm3]                  = " << v0 << "\n";
    std::cerr << "vRef1 [hm3]               = " << vRef1 << "\n";
    std::cerr << "vRef2 [hm3]               = " << vRef2 << "\n";
    std::cerr << "vRef3 [hm3]               = " << vRef3 << "\n";
    std::cerr << "min volumen Bellman [hm3] = " << volumenesBonete.front() << "\n";
    std::cerr << "max volumen Bellman [hm3] = " << volumenesBonete.back() << "\n";

    if (vRef1 > volumenesBonete.back() &&
        vRef2 > volumenesBonete.back() &&
        vRef3 > volumenesBonete.back()) {
        std::cerr << "[ALERTA] Los tres puntos de referencia estan por encima del rango Bellman.\n";
        std::cerr << "[ALERTA] Esto haria que q1=q2=q3 queden en la ultima derivada.\n";
    }

    if (vRef1 < volumenesBonete.front() ||
        vRef2 < volumenesBonete.front() ||
        vRef3 < volumenesBonete.front()) {
        std::cerr << "[ALERTA] Algun punto de referencia esta por debajo del rango Bellman.\n";
    }

    std::cerr << "========================================\n\n";

    // 9. Valores de Bellman tomados desde los índices efectivos
    const double B0 = valoresBellman[i0];

    const double B1 = valoresBellman[i1];
    const double B2 = valoresBellman[i2];
    const double B3 = valoresBellman[i3];

    // 10. Derivadas marginales tomadas desde los índices efectivos
    //
    // Estas derivadas están en:
    //      costo / hm3
    const double q1h_1 = derivadasValoresBellman[i1];
    const double q1h_2 = derivadasValoresBellman[i2];
    const double q1h_3 = derivadasValoresBellman[i3];

    // 11. Conversión de coeficientes para el LP
    //
    // La variable a1_v1h(h_c) está en m3.
    // Entonces el coeficiente que multiplica a1_v1h(h_c) debe estar en costo/m3.
    const double coef1 = q1h_1 * M3_A_HM3;
    const double coef2 = q1h_2 * M3_A_HM3;
    const double coef3 = q1h_3 * M3_A_HM3;

    // 12. RHS de las restricciones
    //
    // Forma deseada:
    //
    //      delta >= B(v0) - [B(vCorte) + q * (vFinal_hm3 - vCorte)]
    //
    // Equivalentemente:
    //
    //      delta + q * vFinal_hm3 >= B(v0) - B(vCorte) + q * vCorte
    //
    // Como en el LP vFinal está en m3:
    //
    //      delta + coef * vFinal_m3 >= B(v0) - B(vCorte) + q * vCorte
    //
    // Nota:
    //      vCorte está en hm3 y q está en costo/hm3.
    //      Por eso q * vCorte está en costo.
    const double rhs1 = (B0 - B1) + q1h_1 * vCorte1;
    const double rhs2 = (B0 - B2) + q1h_2 * vCorte2;
    const double rhs3 = (B0 - B3) + q1h_3 * vCorte3;

    // 13. Debug completo de Bellman
    std::cerr << std::setprecision(15);
    std::cerr << "\n========== DEBUG Bonete Bellman ==========\n";
    std::cerr << "volumenesBonete.size()          = " << volumenesBonete.size() << "\n";
    std::cerr << "valoresBellman.size()           = " << valoresBellman.size() << "\n";
    std::cerr << "derivadasValoresBellman.size()  = " << derivadasValoresBellman.size() << "\n";

    std::cerr << "v0 [hm3]       = " << v0 << "\n";
    std::cerr << "i0             = " << i0 << "\n";
    std::cerr << "vCorte0 [hm3]  = " << vCorte0 << "\n";
    std::cerr << "B0 = B(vCorte0)= " << B0 << "\n";

    std::cerr << "Corte 1:\n";
    std::cerr << "  vRef1 [hm3]       = " << vRef1 << "\n";
    std::cerr << "  i1                = " << i1 << "\n";
    std::cerr << "  vCorte1 [hm3]     = " << vCorte1 << "\n";
    std::cerr << "  B1                = " << B1 << "\n";
    std::cerr << "  q1 [costo/hm3]    = " << q1h_1 << "\n";
    std::cerr << "  coef1 [costo/m3]  = " << coef1 << "\n";
    std::cerr << "  rhs1              = " << rhs1 << "\n";

    std::cerr << "Corte 2:\n";
    std::cerr << "  vRef2 [hm3]       = " << vRef2 << "\n";
    std::cerr << "  i2                = " << i2 << "\n";
    std::cerr << "  vCorte2 [hm3]     = " << vCorte2 << "\n";
    std::cerr << "  B2                = " << B2 << "\n";
    std::cerr << "  q2 [costo/hm3]    = " << q1h_2 << "\n";
    std::cerr << "  coef2 [costo/m3]  = " << coef2 << "\n";
    std::cerr << "  rhs2              = " << rhs2 << "\n";

    std::cerr << "Corte 3:\n";
    std::cerr << "  vRef3 [hm3]       = " << vRef3 << "\n";
    std::cerr << "  i3                = " << i3 << "\n";
    std::cerr << "  vCorte3 [hm3]     = " << vCorte3 << "\n";
    std::cerr << "  B3                = " << B3 << "\n";
    std::cerr << "  q3 [costo/hm3]    = " << q1h_3 << "\n";
    std::cerr << "  coef3 [costo/m3]  = " << coef3 << "\n";
    std::cerr << "  rhs3              = " << rhs3 << "\n";

    std::cerr << "Variable final usada: " << genEt("v1h", h_c) << "\n";
    std::cerr << "Variable delta usada: " << genEt("delta1h", 0) << "\n";

    std::cerr << "Restriccion 1 esperada: "
              << genEt("delta1h", 0)
              << " + (" << coef1 << ") * "
              << genEt("v1h", h_c)
              << " >= " << rhs1 << "\n";

    std::cerr << "Restriccion 2 esperada: "
              << genEt("delta1h", 0)
              << " + (" << coef2 << ") * "
              << genEt("v1h", h_c)
              << " >= " << rhs2 << "\n";

    std::cerr << "Restriccion 3 esperada: "
              << genEt("delta1h", 0)
              << " + (" << coef3 << ") * "
              << genEt("v1h", h_c)
              << " >= " << rhs3 << "\n";

    std::cerr << "==========================================\n\n";

    // 14. Validación dura
    if (std::fabs(coef1) < 1e-12 &&
        std::fabs(coef2) < 1e-12 &&
        std::fabs(coef3) < 1e-12 &&
        std::fabs(rhs1) < 1e-12 &&
        std::fabs(rhs2) < 1e-12 &&
        std::fabs(rhs3) < 1e-12) {
        throw std::runtime_error(
            "RioNegroBoneteNoLineal: las tres restricciones de Bellman quedaron nulas. "
            "Revisar unidades, valoresBellman y derivadasValoresBellman."
        );
    }

    // 15. Restricciones adicionales de Bellman / tangentes
    problema->añadirRestriccion(
        genEt("restriccion_1_delta1h", 0),
        {
            {1.0, genEt("delta1h", 0)},
            {coef1, genEt("v1h", h_c)}
        },
        ">=",
        rhs1
    );

    problema->añadirRestriccion(
        genEt("restriccion_2_delta1h", 0),
        {
            {1.0, genEt("delta1h", 0)},
            {coef2, genEt("v1h", h_c)}
        },
        ">=",
        rhs2
    );

    problema->añadirRestriccion(
        genEt("restriccion_3_delta1h", 0),
        {
            {1.0, genEt("delta1h", 0)},
            {coef3, genEt("v1h", h_c)}
        },
        ">=",
        rhs3
    );
}


// =====================================================
// Función objetivo no lineal
// =====================================================
void RioNegroBoneteNoLineal::generarAporteFuncionObjetivo(Problema* problema, int h_c) {
    string StringIdGen = to_string(idGen);

    // Aporte de Bonete:
    // delta1h representa la aproximación lineal por cortes de Bellman.
    problema->añadirTerminoFuncionObjetivo(
        1.0,
        genEt("delta1h", 0)
    );

    // Aporte de Palmar:
    // Se mantiene el costo de agua lineal de Palmar tal como en la versión base.
    problema->añadirTerminoFuncionObjetivo(
        -1.0 * costoAguaPalmar,
        genEt("v3h", h_c)
    );

    problema->sumarConstanteFuncionObjetivo(
        costoAguaPalmar * volumenInicialPalmar
    );
}
