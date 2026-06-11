#include "SaltoGrande.h"

#include <cmath>
#include <stdexcept>
#include <numeric>
#include <algorithm>
#include <iostream>
#include <iomanip>
#include <map>
#include <vector>

using namespace std;

// ================================
// Parámetros reales y aproximados
// ================================

static constexpr double FACTOR_PHAT = 0.985;

// Coeficientes reales de la producción no lineal de Salto Grande.
// Estos NO deben multiplicarse por 0.985.
static constexpr double P41_REAL = 0.2090;
static constexpr double P42_REAL = 1.6241e-11;
static constexpr double P43_REAL = 4.534264e-22;
static constexpr double P44_REAL = 5.0540e-06;
static constexpr double P45_REAL = 3.9141e-11;

// ================================
// Funciones auxiliares
// ================================

static double sal(const std::vector<double>& p, double x4) {
    return p[0] * x4 - p[3] * std::pow(x4, 2.0);
}

static double dsal(const std::vector<double>& p, double x4) {
    return p[0] - 2.0 * p[3] * x4;
}

static double calcularM4(
    double V4h5,
    double volumenInicial,
    const std::vector<double>& aportes,
    double caudalTurbinadoMaximo,
    int horizonte
) {
    const double CT = 3600.0;

    if (horizonte <= 0) {
        throw std::invalid_argument("SaltoGrande::calcularM4 - horizonte inválido.");
    }

    if (static_cast<int>(aportes.size()) < horizonte) {
        throw std::runtime_error("SaltoGrande::calcularM4 - aportes insuficientes para el horizonte.");
    }

    double sumaAportes = std::accumulate(
        aportes.begin(),
        aportes.begin() + horizonte,
        0.0
    );

    double M4 =
        V4h5
        - (
            volumenInicial
            + sumaAportes * CT
            - 1.5 * caudalTurbinadoMaximo * CT * horizonte
        );

    if (std::isnan(M4) || std::isinf(M4) || M4 <= 0.0) {
        throw std::invalid_argument("SaltoGrande::calcularM4 - M4 inválido.");
    }

    return M4;
}

// ================================
// Constructor
// ================================

SaltoGrande::SaltoGrande(
    int id,
    int idGen,
    int h_c,
    double costoAguaSalto,
    const std::vector<double> aportesSalto,
    double volumenInicial,
    bool compactar8h
) : Generacion(id, h_c, idGen),
    volumenInicial(volumenInicial),
    volumenMinimo(0.0),
    volumenMaximo(4017.0e6),
    nivelMinimo(30.1),
    nivelMaximo(37.0),
    caudalTurbinadoMaximo(8300.0),
    vertimientoMaximo(3000.0),
    minimoTangenteSalto(0.0),
    maximoTangenteSalto(0.0),
    costoAguaSalto(costoAguaSalto),
    aportes(aportesSalto),
    compactarActivacionTramos8h(compactar8h)
{
    if (h_c <= 0) {
        throw invalid_argument("SaltoGrande::SaltoGrande - horizonte temporal inválido.");
    }

    if (aportes.size() != static_cast<size_t>(h_c)) {
        throw invalid_argument("SaltoGrande::SaltoGrande - tamaño de aportesSalto inconsistente con horizonte temporal.");
    }

    if (volumenInicial < volumenMinimo || volumenInicial > volumenMaximo) {
        throw invalid_argument(
            "SaltoGrande::SaltoGrande - volumenInicial fuera de rango. "
            "Revise unidades: este modelo espera volumen en m3."
        );
    }

    if (costoAguaSalto < 0.0) {
        throw invalid_argument("SaltoGrande::SaltoGrande - costoAguaSalto no puede ser negativo.");
    }

    for (double a : aportes) {
        if (a < 0.0) {
            throw invalid_argument("SaltoGrande::SaltoGrande - los aportes no pueden ser negativos.");
        }
    }

    nombre = "Salto Grande (Agente: " + std::to_string(id) + ")";

    // Parámetros aproximados del MIP:
    // p_hat = 0.985 * p_real.
    p41 = FACTOR_PHAT * P41_REAL;
    p42 = FACTOR_PHAT * P42_REAL;
    p43 = FACTOR_PHAT * P43_REAL;
    p44 = FACTOR_PHAT * P44_REAL;
    p45 = FACTOR_PHAT * P45_REAL;

    std::vector<double> p = {p41, p42, p43, p44, p45};

    // Rectas tangentes para z4h
    r41 = dsal(p, 0.0);
    r42 = dsal(p, 8300.0 / 3.0);
    r43 = dsal(p, 2.0 * 8300.0 / 3.0);
    r44 = dsal(p, 8300.0);

    s42 = sal(p, 8300.0 / 3.0) - r42 * (8300.0 / 3.0);
    s43 = sal(p, 2.0 * 8300.0 / 3.0) - r43 * (2.0 * 8300.0 / 3.0);
    s44 = sal(p, 8300.0) - r44 * 8300.0;

    // Umbrales de volumen
    V4h1 = 0.8769 * volumenInicial;
    V4h2 = 0.9802 * volumenInicial;
    V4h3 = volumenInicial;
    V4h4 = 1.0318 * volumenInicial;
    V4h5 = 1.1592 * volumenInicial;

    // Diferencias
    DV4h2 = V4h2 - V4h1;
    DV4h22 = std::pow(V4h2, 2.0) - std::pow(V4h1, 2.0);

    DV4h3 = V4h3 - V4h2;
    DV4h32 = std::pow(V4h3, 2.0) - std::pow(V4h2, 2.0);

    DV4h4 = V4h4 - V4h3;
    DV4h42 = std::pow(V4h4, 2.0) - std::pow(V4h3, 2.0);

    DV4h5 = V4h5 - V4h4;
    DV4h52 = std::pow(V4h5, 2.0) - std::pow(V4h4, 2.0);

    // Big-M para activación de intervalos
    M4 = calcularM4(
        V4h5,
        volumenInicial,
        aportes,
        caudalTurbinadoMaximo,
        h_c
    );

    coefParticipacionDespacho = 0.5;
}

// ================================
// Etiquetas
// ================================

string SaltoGrande::genEt(string nombre, int parametro) {
    if (parametro < 0) {
        throw invalid_argument("SaltoGrande::genEt - parámetro negativo.");
    }

    string stringIdAgente = "a" + to_string(this->idAgente);

    if (parametro == 0) {
        return stringIdAgente + "_" + nombre;
    }

    return stringIdAgente + "_" + nombre + "(" + to_string(parametro) + ")";
}

// ================================
// Método principal
// ================================

void SaltoGrande::contribuirAlProblema(Problema* problema, int h_c) {
    if (!problema) {
        throw invalid_argument("SaltoGrande::contribuirAlProblema - puntero problema nulo.");
    }

    if (h_c <= 0) {
        throw invalid_argument("SaltoGrande::contribuirAlProblema - horizonte temporal inválido.");
    }

    if (aportes.size() != static_cast<size_t>(h_c)) {
        throw invalid_argument("SaltoGrande::contribuirAlProblema - tamaño de aportes inconsistente con horizonte.");
    }

    string StringIdGen = to_string(idGen);

    std::vector<double> p = {p41, p42, p43, p44, p45};

    const double minimoTangenteSalto = 0.0;
    const double maximoTangenteSalto = sal(p, caudalTurbinadoMaximo);

    if (std::isnan(maximoTangenteSalto) || std::isinf(maximoTangenteSalto) || maximoTangenteSalto <= 0.0) {
        throw invalid_argument("SaltoGrande::contribuirAlProblema - maximoTangenteSalto inválido.");
    }

    // ---------------- Variables ----------------
    const int cantidadBloques8h = (h_c + 7) / 8;
    auto bloque8h = [](int hora) {
        return (hora - 1) / 8 + 1;
    };

    for (int i = 1; i <= h_c; i++) {
        problema->añadirVariable(genEt("z4h", i), 0, minimoTangenteSalto, maximoTangenteSalto);

        problema->añadirVariable(genEt("v4h", i), 0, volumenMinimo, volumenMaximo);
        problema->añadirVariable(genEt("x4h", i), 0, 0.0, caudalTurbinadoMaximo);
        problema->añadirVariable(genEt("y4h", i), 0, 0.0, vertimientoMaximo);

        // Sin cota superior directa: quedan acotadas por las restricciones con x4h y varphi.
        problema->añadirVariable(genEt("theta41", i), 2, 0.0, 0.0);
        problema->añadirVariable(genEt("theta42", i), 2, 0.0, 0.0);
        problema->añadirVariable(genEt("theta43", i), 2, 0.0, 0.0);
        problema->añadirVariable(genEt("theta44", i), 2, 0.0, 0.0);
        problema->añadirVariable(genEt("theta45", i), 2, 0.0, 0.0);

        // Sin cota superior directa: g4h queda definido por z4h + sum(theta).
        problema->añadirVariable("g" + StringIdGen + "(" + to_string(i) + ")",2,0,0); 

        if (!compactarActivacionTramos8h) {
            problema->añadirBinario(genEt("varphi41", i));
            problema->añadirBinario(genEt("varphi42", i));
            problema->añadirBinario(genEt("varphi43", i));
            problema->añadirBinario(genEt("varphi44", i));
        }
    }

    if (compactarActivacionTramos8h) {
        for (int k = 1; k <= cantidadBloques8h; k++) {
            problema->añadirBinario(genEt("varphi41", k));
            problema->añadirBinario(genEt("varphi42", k));
            problema->añadirBinario(genEt("varphi43", k));
            problema->añadirBinario(genEt("varphi44", k));
        }
    }

    // ---------------- Tangentes ----------------
    for (int i = 1; i <= h_c; i++) {
        problema->añadirRestriccion(
            genEt("salto_grande_tangente_1", i),
            {
                {1.0, genEt("z4h", i)},
                {-r41, genEt("x4h", i)}
            },
            "<=",
            0.0
        );

        problema->añadirRestriccion(
            genEt("salto_grande_tangente_2", i),
            {
                {1.0, genEt("z4h", i)},
                {-r42, genEt("x4h", i)}
            },
            "<=",
            s42
        );

        problema->añadirRestriccion(
            genEt("salto_grande_tangente_3", i),
            {
                {1.0, genEt("z4h", i)},
                {-r43, genEt("x4h", i)}
            },
            "<=",
            s43
        );

        problema->añadirRestriccion(
            genEt("salto_grande_tangente_4", i),
            {
                {1.0, genEt("z4h", i)},
                {-r44, genEt("x4h", i)}
            },
            "<=",
            s44
        );
    }

    // ---------------- Generación ----------------
    for (int i = 1; i <= h_c; i++) {
        problema->añadirRestriccion(
            genEt("g4h_def", i),
            {
                {1.0, "g" + StringIdGen + "(" + to_string(i) + ")"},
                {-1.0, genEt("z4h", i)},
                {-1.0, genEt("theta41", i)},
                {-1.0, genEt("theta42", i)},
                {-1.0, genEt("theta43", i)},
                {-1.0, genEt("theta44", i)},
                {-1.0, genEt("theta45", i)}
            },
            "=",
            0.0
        );
    }

    // ---------------- Efecto altura/cota ----------------
    //
    // IMPORTANTE:
    // Estas restricciones son algebraicamente las mismas que antes,
    // pero ahora se escriben escaladas por 1000, como en el .lp de Claudio:
    //
    //     1000 theta - 1000*C*x <= 0
    //
    // en vez de:
    //
    //     theta - C*x <= 0
    //
    // Esto busca replicar el escalado numérico del modelo de referencia.
    //
    const double C41 = p42 * V4h1 - p43 * std::pow(V4h1, 2.0);
    const double C42 = p42 * DV4h2 - p43 * DV4h22;
    const double C43 = p42 * DV4h3 - p43 * DV4h32;
    const double C44 = p42 * DV4h4 - p43 * DV4h42;
    const double C45 = p42 * DV4h5 - p43 * DV4h52;

    for (int i = 1; i <= h_c; i++) {
        problema->añadirRestriccion(
            genEt("cota_altura_1", i),
            {
                {1, genEt("theta41", i)},
                {-C41, genEt("x4h", i)}
            },
            "<=",
            0.0
        );

        problema->añadirRestriccion(
            genEt("cota_altura_2", i),
            {
                {1, genEt("theta42", i)},
                {-C42, genEt("x4h", i)}
            },
            "<=",
            0.0
        );

        problema->añadirRestriccion(
            genEt("cota_altura_3", i),
            {
                {1, genEt("theta42", i)},
                {- caudalTurbinadoMaximo * C42, genEt("varphi41", compactarActivacionTramos8h ? bloque8h(i) : i)}
            },
            "<=",
            0.0
        );

        problema->añadirRestriccion(
            genEt("cota_altura_4", i),
            {
                {1, genEt("theta43", i)},
                {- C43, genEt("x4h", i)}
            },
            "<=",
            0.0
        );

        problema->añadirRestriccion(
            genEt("cota_altura_5", i),
            {
                {1, genEt("theta43", i)},
                {-caudalTurbinadoMaximo * C43, genEt("varphi42", compactarActivacionTramos8h ? bloque8h(i) : i)}
            },
            "<=",
            0.0
        );

        problema->añadirRestriccion(
            genEt("cota_altura_6", i),
            {
                {1, genEt("theta44", i)},
                {-C44, genEt("x4h", i)}
            },
            "<=",
            0.0
        );

        problema->añadirRestriccion(
            genEt("cota_altura_7", i),
            {
                {1, genEt("theta44", i)},
                {-caudalTurbinadoMaximo * C44, genEt("varphi43", compactarActivacionTramos8h ? bloque8h(i) : i)}
            },
            "<=",
            0.0
        );

        problema->añadirRestriccion(
            genEt("cota_altura_8", i),
            {
                {1, genEt("theta45", i)},
                {-C45, genEt("x4h", i)}
            },
            "<=",
            0.0
        );

        problema->añadirRestriccion(
            genEt("cota_altura_9", i),
            {
                {1, genEt("theta45", i)},
                {-caudalTurbinadoMaximo * C45, genEt("varphi44", compactarActivacionTramos8h ? bloque8h(i) : i)}
            },
            "<=",
            0.0
        );
    }

    // ---------------- Activación de intervalos ----------------
    //
    // IMPORTANTE:
    // Antes estaba escrito como:
    //
    //     varphi - (1/M4) v <= 1 - V/M4
    //
    // Ahora se escribe como en Claudio:
    //
    //     M4 varphi - v <= M4 - V
    //
    // Es algebraicamente equivalente, pero con el mismo escalado numérico.
    //
    const int iteracionesActivacion = compactarActivacionTramos8h ? cantidadBloques8h : h_c;
    for (int i = 1; i <= iteracionesActivacion; i++) {
        if (!compactarActivacionTramos8h) {
            problema->añadirRestriccion(
                genEt("activacion_1", i),
                {
                    {M4, genEt("varphi41", i)},
                    {-1.0, genEt("v4h", i)}
                },
                "<=",
                M4 - V4h2
            );

            problema->añadirRestriccion(
                genEt("activacion_2", i),
                {
                    {M4, genEt("varphi42", i)},
                    {-1.0, genEt("v4h", i)}
                },
                "<=",
                M4 - V4h3
            );

            problema->añadirRestriccion(
                genEt("activacion_3", i),
                {
                    {M4, genEt("varphi43", i)},
                    {-1.0, genEt("v4h", i)}
                },
                "<=",
                M4 - V4h4
            );

            problema->añadirRestriccion(
                genEt("activacion_4", i),
                {
                    {M4, genEt("varphi44", i)},
                    {-1.0, genEt("v4h", i)}
                },
                "<=",
                M4 - V4h5
            );
        } else {
            const int inicio = 8 * (i - 1) + 1;
            const int fin = min(8 * i, h_c);
            const double coefPromedio = -1.0 / static_cast<double>(fin - inicio + 1);

            auto agregarActivacionCompactada = [&](const string& nombre, const string& varphi, double umbral) {
                vector<pair<double, string>> terminos = {{M4, genEt(varphi, i)}};
                for (int t = inicio; t <= fin; t++) {
                    terminos.push_back({coefPromedio, genEt("v4h", t)});
                }
                problema->añadirRestriccion(
                    genEt(nombre, i),
                    terminos,
                    "<=",
                    M4 - umbral
                );
            };

            agregarActivacionCompactada("activacion_1", "varphi41", V4h2);
            agregarActivacionCompactada("activacion_2", "varphi42", V4h3);
            agregarActivacionCompactada("activacion_3", "varphi43", V4h4);
            agregarActivacionCompactada("activacion_4", "varphi44", V4h5);
        }

        problema->añadirRestriccion(
            genEt("orden_varphi_42_41", i),
            {
                {1.0, genEt("varphi42", i)},
                {-1.0, genEt("varphi41", i)}
            },
            "<=",
            0.0
        );

        problema->añadirRestriccion(
            genEt("orden_varphi_43_42", i),
            {
                {1.0, genEt("varphi43", i)},
                {-1.0, genEt("varphi42", i)}
            },
            "<=",
            0.0
        );

        problema->añadirRestriccion(
            genEt("orden_varphi_44_43", i),
            {
                {1.0, genEt("varphi44", i)},
                {-1.0, genEt("varphi43", i)}
            },
            "<=",
            0.0
        );
    }

    // ---------------- Balance de volumen ----------------
    problema->añadirRestriccion(
        genEt("balance", 1),
        {
            {1.0, genEt("v4h", 1)},
            {3600.0, genEt("x4h", 1)},
            {3600.0, genEt("y4h", 1)}
        },
        "=",
        volumenInicial + 3600.0 * aportes[0]
    );

    for (int i = 2; i <= h_c; i++) {
        problema->añadirRestriccion(
            genEt("balance", i),
            {
                {1.0, genEt("v4h", i)},
                {-1.0, genEt("v4h", i - 1)},
                {3600.0, genEt("x4h", i)},
                {3600.0, genEt("y4h", i)}
            },
            "=",
            3600.0 * aportes[i - 1]
        );
    }

    // ---------------- Nombres de variables ----------------
    auto agregarNombre = [&](const string& n) {
        if (find(nombresVariables.begin(), nombresVariables.end(), n) == nombresVariables.end()) {
            nombresVariables.push_back(n);
        }
    };

    agregarNombre(genEt("z4h", 0));
    agregarNombre(genEt("v4h", 0));
    agregarNombre(genEt("x4h", 0));
    agregarNombre(genEt("y4h", 0));
    agregarNombre(genEt("theta41", 0));
    agregarNombre(genEt("theta42", 0));
    agregarNombre(genEt("theta43", 0));
    agregarNombre(genEt("theta44", 0));
    agregarNombre(genEt("theta45", 0));
    agregarNombre(genEt("varphi41", 0));
    agregarNombre(genEt("varphi42", 0));
    agregarNombre(genEt("varphi43", 0));
    agregarNombre(genEt("varphi44", 0));
    agregarNombre("g" + StringIdGen);

    generarAporteFuncionObjetivo(problema, h_c);
}

// ================================
// Función objetivo
// ================================

void SaltoGrande::generarAporteFuncionObjetivo(Problema* problema, int h_c) {
    if (!problema) {
        throw invalid_argument("SaltoGrande::generarAporteFuncionObjetivo - puntero problema nulo.");
    }

    if (h_c <= 0) {
        throw invalid_argument("SaltoGrande::generarAporteFuncionObjetivo - horizonte temporal inválido.");
    }

    // Costo de agua:
    // costoAguaSalto * (volumenInicial - v4h_T)
    problema->añadirTerminoFuncionObjetivo(-1.0 * costoAguaSalto, genEt("v4h", h_c));
    problema->sumarConstanteFuncionObjetivo(costoAguaSalto * volumenInicial);
}

// ================================
// Postprocesamiento
// ================================

static double PotenciaVerdaderaSalto(
    double x4,
    double y4,
    double v4,
    double p41,
    double p42,
    double p43,
    double p44,
    double p45
) {
    return
        p41 * x4
        + p42 * x4 * v4
        - p43 * x4 * v4 * v4
        - p44 * x4 * x4
        - p44 * x4 * y4
        + p45 * x4 * x4 * x4
        + p45 * x4 * y4 * y4
        + 2.0 * p45 * x4 * x4 * y4;
}

void SaltoGrande::posprocesamiento(Problema* problema) {
    if (!problema) {
        throw invalid_argument("SaltoGrande::posprocesamiento - puntero problema nulo.");
    }

    std::map<std::string, double> valoresVariables = problema->getValoresVariables();

    if (valoresVariables.empty()) {
        throw runtime_error("SaltoGrande::posprocesamiento - mapa de variables vacío.");
    }

    const double paso = 0.01;
    const double TOLERANCIA = 0.1;

    int cantidadWhile = 0;
    int periodosConWhile = 0;
    int periodosPotenciaRealMayorMIP = 0;
    int periodosPotenciaRealMenorMIP = 0;
    int periodosConErrorFinal = 0;

    double sumaGMip = 0.0;
    double sumaGRealInicial = 0.0;
    double sumaGRealFinal = 0.0;

    double sumaDeltaGInicial = 0.0;
    double sumaDeltaGFinal = 0.0;

    double maxAbsDeltaGInicial = 0.0;
    double maxAbsDeltaGFinal = 0.0;

    double sumaDeltaX = 0.0;
    double sumaDeltaY = 0.0;

    for (int i = 1; i <= periodo; i++) {
        auto get = [&](const std::string& nombre) -> double {
            auto it = valoresVariables.find(nombre);
            if (it != valoresVariables.end()) {
                return it->second;
            }

            std::cerr
                << "SaltoGrande::posprocesamiento - Variable no encontrada: "
                << nombre
                << std::endl;

            return 0.0;
        };

        const std::string nombreX = genEt("x4h", i);
        const std::string nombreY = genEt("y4h", i);
        const std::string nombreV = genEt("v4h", i);
        const std::string nombreG =
            "g" + std::to_string(idGen) + "(" + std::to_string(i) + ")";

        double x4 = get(nombreX);
        double y4 = get(nombreY);
        double v4 = get(nombreV);
        double gMip = get(nombreG);

        const double x4Inicial = x4;
        const double y4Inicial = y4;

        double potenciaRealInicial = PotenciaVerdaderaSalto(
            x4, y4, v4,
            P41_REAL, P42_REAL, P43_REAL, P44_REAL, P45_REAL
        );

        double potenciaReal = potenciaRealInicial;

        if (potenciaReal > gMip + TOLERANCIA) {
            periodosPotenciaRealMayorMIP++;
        }

        if (potenciaReal < gMip - TOLERANCIA) {
            periodosPotenciaRealMenorMIP++;
        }

        bool entroWhile = false;

        /*
         * Postprocesamiento físico:
         *
         * - La generación decidida por el MIP, gMip, NO se modifica.
         * - Si la producción real supera a gMip, reducimos x4 y aumentamos y4.
         * - Esto mantiene constante x4 + y4, por lo tanto no cambia el balance de agua.
         * - El objetivo es que P_real(x4,y4,v4) se acerque a gMip.
         *
         * Importante:
         * NO se debe hacer:
         *
         *     valoresVariables[nombreG] = potenciaReal;
         *
         * porque eso cambia la generación despachada y luego afecta g(t) y costoFalla.
         */
        while (potenciaReal > gMip + TOLERANCIA) {
            if (x4 - paso < 0.0 || y4 + paso > vertimientoMaximo) {
                break;
            }

            entroWhile = true;
            cantidadWhile++;

            valoresVariables[nombreX] -= paso;
            valoresVariables[nombreY] += paso;

            x4 = get(nombreX);
            y4 = get(nombreY);

            potenciaReal = PotenciaVerdaderaSalto(
                x4, y4, v4,
                P41_REAL, P42_REAL, P43_REAL, P44_REAL, P45_REAL
            );
        }

        if (entroWhile) {
            periodosConWhile++;
        }

        double deltaGInicial = potenciaRealInicial - gMip;
        double deltaGFinal = potenciaReal - gMip;

        sumaGMip += gMip;
        sumaGRealInicial += potenciaRealInicial;
        sumaGRealFinal += potenciaReal;

        sumaDeltaGInicial += deltaGInicial;
        sumaDeltaGFinal += deltaGFinal;

        maxAbsDeltaGInicial = std::max(maxAbsDeltaGInicial, std::abs(deltaGInicial));
        maxAbsDeltaGFinal = std::max(maxAbsDeltaGFinal, std::abs(deltaGFinal));

        sumaDeltaX += x4 - x4Inicial;
        sumaDeltaY += y4 - y4Inicial;

        if (std::abs(deltaGFinal) > TOLERANCIA) {
            periodosConErrorFinal++;
        }

        /*
         * NO modificar nombreG.
         *
         * g1(i) sigue siendo la generación decidida por el MIP.
         * El postprocesamiento solo ajusta x4h/y4h para que la producción física
         * real sea compatible con esa generación.
         */
        // valoresVariables[nombreG] = potenciaReal;  // NO HACER
    }

    problema->setValoresVariables(valoresVariables);

    std::cerr << std::setprecision(15)
              << "\n[SG POST] ===== Diagnóstico SaltoGrande =====\n"
              << "[SG POST] periodos = " << periodo << "\n"
              << "[SG POST] periodosPotenciaRealMayorMIP = " << periodosPotenciaRealMayorMIP << "\n"
              << "[SG POST] periodosPotenciaRealMenorMIP = " << periodosPotenciaRealMenorMIP << "\n"
              << "[SG POST] periodosConWhile = " << periodosConWhile << "\n"
              << "[SG POST] cantidadWhile = " << cantidadWhile << "\n"
              << "[SG POST] periodosConErrorFinal = " << periodosConErrorFinal << "\n"
              << "[SG POST] sumaGMip = " << sumaGMip << "\n"
              << "[SG POST] sumaGRealInicial = " << sumaGRealInicial << "\n"
              << "[SG POST] sumaGRealFinal = " << sumaGRealFinal << "\n"
              << "[SG POST] sumaDeltaGInicial = " << sumaDeltaGInicial << "\n"
              << "[SG POST] sumaDeltaGFinal = " << sumaDeltaGFinal << "\n"
              << "[SG POST] maxAbsDeltaGInicial = " << maxAbsDeltaGInicial << "\n"
              << "[SG POST] maxAbsDeltaGFinal = " << maxAbsDeltaGFinal << "\n"
              << "[SG POST] sumaDeltaX = " << sumaDeltaX << "\n"
              << "[SG POST] sumaDeltaY = " << sumaDeltaY << "\n"
              << "[SG POST] ===================================\n\n";
}

// ================================
// Getters r
// ================================

double SaltoGrande::getR1() const { return r41; }
double SaltoGrande::getR2() const { return r42; }
double SaltoGrande::getR3() const { return r43; }
double SaltoGrande::getR4() const { return r44; }

// ================================
// Setters r
// ================================

void SaltoGrande::setR1(double value) { r41 = value; }
void SaltoGrande::setR2(double value) { r42 = value; }
void SaltoGrande::setR3(double value) { r43 = value; }
void SaltoGrande::setR4(double value) { r44 = value; }

// ================================
// Getters s
// ================================

double SaltoGrande::getS2() const { return s42; }
double SaltoGrande::getS3() const { return s43; }
double SaltoGrande::getS4() const { return s44; }

// ================================
// Setters s
// ================================

void SaltoGrande::setS2(double value) { s42 = value; }
void SaltoGrande::setS3(double value) { s43 = value; }
void SaltoGrande::setS4(double value) { s44 = value; }

// ================================
// Getters Vh
// ================================

double SaltoGrande::getVh1() const { return V4h1; }
double SaltoGrande::getVh2() const { return V4h2; }
double SaltoGrande::getVh3() const { return V4h3; }
double SaltoGrande::getVh4() const { return V4h4; }
double SaltoGrande::getVh5() const { return V4h5; }

// ================================
// Setters Vh
// ================================

void SaltoGrande::setVh1(double value) { V4h1 = value; }
void SaltoGrande::setVh2(double value) { V4h2 = value; }
void SaltoGrande::setVh3(double value) { V4h3 = value; }
void SaltoGrande::setVh4(double value) { V4h4 = value; }
void SaltoGrande::setVh5(double value) { V4h5 = value; }

// ================================
// Getters DVh
// ================================

double SaltoGrande::getDVh2() const { return DV4h2; }
double SaltoGrande::getDVh3() const { return DV4h3; }
double SaltoGrande::getDVh4() const { return DV4h4; }
double SaltoGrande::getDVh5() const { return DV4h5; }

// ================================
// Setters DVh
// ================================

void SaltoGrande::setDVh2(double value) { DV4h2 = value; }
void SaltoGrande::setDVh3(double value) { DV4h3 = value; }
void SaltoGrande::setDVh4(double value) { DV4h4 = value; }
void SaltoGrande::setDVh5(double value) { DV4h5 = value; }
