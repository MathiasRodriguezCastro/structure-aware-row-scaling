#include "RioNegro.h"
#include <cmath>
#include <numeric>
#include <vector>
#include <cstdio>
#include <iostream>
#include <string>


void verificarVector(const vector<double>& v, int esperado, const string& nombre) {
    if (v.size() != static_cast<size_t>(esperado))
        throw invalid_argument("RioNegro::verificarVector - el vector '" + nombre + "' no tiene tamaño h_c.");
}

// Constructor principal de RioNegro
// Inicializa todos los parámetros hidráulicos y llama a las funciones de cálculo
// Si algún vector de aportes no tiene tamaño h_c, lanza invalid_argument
RioNegro::RioNegro(
    int id,
    int idGen,
    const vector<double> aportesBonete,
    const vector<double> aportesBaygorria,
    const vector<double> aportesPalmar,
    double volumenInicialBonete,
    double volumenInicialPalmar,
    double costoAguaBonete,
    double costoAguaPalmar,
    int h_c,
    bool compactar8h
) :
    Generacion(id, h_c, idGen),
    ajuste_coef(0.9925),
    aportesBonete(aportesBonete),
    aportesBaygorria(aportesBaygorria),
    aportesPalmar(aportesPalmar),
    volumenInicialBonete(volumenInicialBonete),
    volumenInicialPalmar(volumenInicialPalmar),
    costoAguaBonete(costoAguaBonete),
    costoAguaPalmar(costoAguaPalmar),
    idBonete("1"),
    idBaygorria("2"),
    idPalmar("3"),
    compactarActivacionTramos8h(compactar8h)
{
    verificarVector(aportesBonete, h_c, "aportesBonete");
    verificarVector(aportesBaygorria, h_c, "aportesBaygorria");
    verificarVector(aportesPalmar, h_c, "aportesPalmar");
    
    // Inicializar constantes y límites
    minimoFlujoBonete = 0;
    maximoFlujoBonete = 680;
    minimoVertidoBonete = 0;
    maximoVertidoBonete = 400;
    volumenMinimoBonete = 1487e6;
    volumenMaximoBonete = 10717e6;
    minimoTangenteBonete = 0;
    maximoTangenteBonete = 94;

    minimoFlujoBaygorria = 0;
    maximoFlujoBaygorria = 828;
    minimoVertidoBaygorria = 0;
    maximoVertidoBaygorria = 400;
    minimoTangenteBaygorria = 0;
    maximoTangenteBaygorria = 121;

    minimoFlujoPalmar = 0;
    maximoFlujoPalmar = 1380;
    minimoVertidoPalmar = 0;
    maximoVertidoPalmar = 800;
    volumenMinimoPalmar = 176e6;
    volumenMaximoPalmar = 1740e6;
    minimoTangentePalmar = 0;
    maximoTangentePalmar = 303;

    // Llamar a las funciones de inicialización en el orden correcto
    inicializarBonete();
    inicializarBaygorria();
    inicializarPalmar();

    // ==== Funciones para calcular ====
    calcularCoeficientesTangentes();
    min_sqr(); // Calcula bygX y bygV
    calcular_M1(h_c);
    calcular_M3(h_c);
    // === Verificación de consistencia de M1 y M3 ===
    if (isnan(M1) || isinf(M1)) {
        throw invalid_argument("RioNegro::RioNegro - M1 tiene un valor no válido (NaN o inf).");
    }

    if (isnan(M3) || isinf(M3)) {
        throw invalid_argument("RioNegro::RioNegro - M3 tiene un valor no válido (NaN o inf).");
    }

    // Inicializar los mínimos de generación
    genMinBonete = 0;
    genMinBaygorria = -ceil(5.0 * (1.0 + 0.35) * volumenMinimoPalmar * bygV);
    genMinPalmar = 0;

    // Inicializar los mínimos de generación
    nombre = "Rio Negro";
} 



void RioNegro::inicializarBonete() {
    // Coeficientes de producción
    p11 = 0.1475 * ajuste_coef;
    p12 = 1.3124e-11 * ajuste_coef;
    p13 = 3.8380e-22 * ajuste_coef;
    p14 = 1.2796e-5 * ajuste_coef;

    // Discretización de volúmenes
    double V1h1 = 0.9528 * volumenInicialBonete;
    V1h2 = volumenInicialBonete;
    V1h3 = 1.0692 * volumenInicialBonete;

    double DV1h2 = V1h2 - V1h1;
    double DV1h22 = pow(V1h2, 2) - pow(V1h1, 2);
    double DV1h3 = V1h3 - V1h2;
    double DV1h32 = pow(V1h3, 2) - pow(V1h2, 2);

    // Coeficientes k
    k11 = p12 * V1h1 - p13 * pow(V1h1, 2);
    k12 = p12 * DV1h2 - p13 * DV1h22;
    k13 = p12 * DV1h3 - p13 * DV1h32;
}

void RioNegro::inicializarBaygorria() {
    // Coeficientes de producción
    p21 = 0.1523 * ajuste_coef;
    p22 = 7.5126e-6 * ajuste_coef;
    p23 = 3.3232e-11 * ajuste_coef;
    p24 = 4.4477e-21 * ajuste_coef;
}

void RioNegro::inicializarPalmar() {
    // Coeficientes de producción
    p31 = 0.2551 * ajuste_coef;
    p32 = 3.9848e-11 * ajuste_coef;
    p33 = 5.3332e-21 * ajuste_coef;
    p34 = 2.4902e-5 * ajuste_coef;
    p35 = 1.2854e-9 * ajuste_coef;

    // Discretización de volúmenes
    double V3h1 = 0.8833 * volumenInicialPalmar;
    V3h2 = 0.961174 * volumenInicialPalmar;
    V3h3 = volumenInicialPalmar;
    V3h4 = 1.02532 * volumenInicialPalmar;
    V3h5 = 1.1553 * volumenInicialPalmar;

    double DV3h2 = V3h2 - V3h1;
    double DV3h22 = pow(V3h2, 2) - pow(V3h1, 2);
    double DV3h3 = V3h3 - V3h2;
    double DV3h32 = pow(V3h3, 2) - pow(V3h2, 2);
    double DV3h4 = V3h4 - V3h3;
    double DV3h42 = pow(V3h4, 2) - pow(V3h3, 2);
    double DV3h5 = V3h5 - V3h4;
    double DV3h52 = pow(V3h5, 2) - pow(V3h4, 2);

    // Coeficientes k
    k31 = p32 * V3h1 - p33 * pow(V3h1, 2);
    k32 = p32 * DV3h2 - p33 * DV3h22;
    k33 = p32 * DV3h3 - p33 * DV3h32;
    k34 = p32 * DV3h4 - p33 * DV3h42;
    k35 = p32 * DV3h5 - p33 * DV3h52;
}

void RioNegro::calcularCoeficientesTangentes() {
    // Bonete
    r11_hat = dbon_function(minimoFlujoBonete);
    r12_hat = dbon_function(maximoFlujoBonete);
    s12_hat = bon_function(maximoFlujoBonete) - r12_hat * maximoFlujoBonete;

    // Baygorria
    r21_hat = dbay_function(minimoFlujoBaygorria);
    r22_hat = dbay_function(maximoFlujoBaygorria);
    s22_hat = bay_function(maximoFlujoBaygorria) - r22_hat * maximoFlujoBaygorria;

    // Palmar
    r31_hat = dpal_function(minimoFlujoPalmar);
    r32_hat = dpal_function(maximoFlujoPalmar / 2.0);
    r33_hat = dpal_function(maximoFlujoPalmar);
    s32_hat = pal_function(maximoFlujoPalmar / 2.0) - r32_hat * (maximoFlujoPalmar / 2.0);
    s33_hat = pal_function(maximoFlujoPalmar) - r33_hat * maximoFlujoPalmar;
}


double RioNegro::bon_function(double x) {
    return p11 * x - p14 * pow(x,2);
}

double RioNegro::dbon_function(double x) {
    return p11 - 2 * p14 * x;
}

double RioNegro::bay_function(double x)  {
    return p21 * x - p22 * pow(x,2);
}

double RioNegro::dbay_function(double x) {
    return p21 - 2 * p22 * x;
}

double RioNegro::pal_function(double x)  {
    return p31 * x - p34 * pow(x,2);
}

double RioNegro::dpal_function(double x) {
    return p31 - 2 * p34 * x;
}


void RioNegro::min_sqr()
{
    // 1. Generar x
    int nx = (int)ceil(829.0 / 23.0);
    vector<double> x(nx);

    double val = 0.0;
    for (int i = 0; i < nx; ++i) {
        x[i] = val;
        val += 23.0;
    }

    // 2. Generar vol
    double vol_min = (1.0 - 0.35) * volumenInicialPalmar;
    double vol_max = (1.0 + 0.35) * volumenInicialPalmar;
    int nv = (int)floor((vol_max - vol_min) / 1e7) + 1;

    vector<double> vol(nv);
    val = vol_min;
    for (int i = 0; i < nv; ++i) {
        vol[i] = val;
        val += 1e7;
    }

    // 3. Acumular sumas para mínimos cuadrados
    double S_xx = 0.0, S_xv = 0.0, S_vv = 0.0;
    double S_xz = 0.0, S_vz = 0.0;

    for (int i = 0; i < nx; ++i) {
        for (int j = 0; j < nv; ++j) {
            double Xi = x[i];
            double Vi = vol[j];
            double Zi = Vi * (p23 - p24 * Vi) * Xi;

            S_xx += Xi * Xi;
            S_xv += Xi * Vi;
            S_vv += Vi * Vi;
            S_xz += Xi * Zi;
            S_vz += Vi * Zi;
        }
    }

    // 4. Resolver sistema 2x2
    double det = S_xx * S_vv - S_xv * S_xv;
    if (fabs(det) < 1e-12) {
        throw runtime_error("RioNegro::min_sqr - Error: sistema de mínimos cuadrados singular en min_sqr().");
    }

    bygX = ( S_vv * S_xz - S_xv * S_vz ) / det;
    bygV = (-S_xv * S_xz + S_xx * S_vz ) / det;
}


void RioNegro::calcular_M1(int horizonte){
    double CT = 3600.0;
    if (aportesBonete.empty()) {
        throw runtime_error("RioNegro::calcular_M1 - Error: aportesBonete vacío en calcular_M1().");
    }
    
    double sumaAportes = accumulate(aportesBonete.begin(), aportesBonete.end(), 0.0);
    
    M1 = V1h3 - (volumenInicialBonete + sumaAportes * CT - 1.5 * 680 * CT * horizonte);
}

void RioNegro::calcular_M3(int horizonte){
    double CT = 3600.0;
    if (aportesBaygorria.empty()) {
        throw runtime_error("RioNegro::calcular_M3 - Error: aportesBaygorria vacío en calcular_M3().");
    }

    if (aportesPalmar.empty()) {
        throw runtime_error("RioNegro::calcular_M3 - Error: aportesPalmar vacío en calcular_M3().");
    }

    double sumaAportes2 = accumulate(aportesBaygorria.begin(), aportesBaygorria.end(), 0.0);
    double sumaAportes3 = accumulate(aportesPalmar.begin(), aportesPalmar.end(), 0.0);
    
    M3 = V3h5 - (volumenInicialPalmar + (sumaAportes2 + sumaAportes3) * CT - 1.5 * 828 * CT * horizonte);
}



// Setters
void RioNegro::setAjusteCoef(double coef) { this->ajuste_coef = coef; }
void RioNegro::setAportesBonete(const vector<double> aportes) { aportesBonete = aportes; }
void RioNegro::setAportesBaygorria(const vector<double> aportes) { aportesBaygorria = aportes; }
void RioNegro::setAportesPalmar(const vector<double> aportes) { aportesPalmar = aportes; }
void RioNegro::setVolumenInicialBonete(double volumen) { volumenInicialBonete = volumen; }
void RioNegro::setVolumenInicialPalmar(double volumen) { volumenInicialPalmar = volumen; }
void RioNegro::setCostoAguaBonete(double costo) { costoAguaBonete = costo; }
void RioNegro::setCostoAguaPalmar(double costo) { costoAguaPalmar = costo; }

// Getters
double RioNegro::getAjusteCoef() const { return ajuste_coef; }
vector<double> RioNegro::getAportesBonete() const { return aportesBonete; }
vector<double> RioNegro::getAportesBaygorria() const { return aportesBaygorria; }
vector<double> RioNegro::getAportesPalmar() const { return aportesPalmar; }
double RioNegro::getVolumenInicialBonete() const { return volumenInicialBonete; }
double RioNegro::getVolumenInicialPalmar() const { return volumenInicialPalmar; }
double RioNegro::getCostoAguaBonete() const { return costoAguaBonete; }
double RioNegro::getCostoAguaPalmar() const { return costoAguaPalmar; }


// Funcion para generar la ertiqueta de las variables y restricciones
string RioNegro::genEt(string nombre, int parametro) {
    if (parametro < 0) {
        throw invalid_argument("RioNegro::genEt - parámetro negativo en genEt().");
    }

    string stringIdAgente =  "a" + to_string(this->idAgente); // ID del agente
    if(parametro == 0) {
        return stringIdAgente + "_" + nombre;
    }
    else {
        return stringIdAgente + "_" + nombre + "(" + to_string(parametro) + ")";
    }
}

void RioNegro::generarRestriccionesBonete(Problema* problema, int h_c) {
    string StringIdAgente = "a" + to_string(idAgente); // ID del agente
    string StringIdGen = to_string(idGen);

    // bonete_tangente_1
    for(int i = 1; i <= h_c; i++){
        problema->añadirRestriccion( 
            genEt("bonete_tangente_1",i),
            {   
                {1, genEt("z1h",i)}, 
                {-r11_hat, genEt("x1h",i)}
            },
            "<=",
            0
        );
    }

    // bonete_tangente_2
    for(int i = 1; i <= h_c; i++){
        problema->añadirRestriccion(  
            genEt("bonete_tangente_2",i),
            { 
                {1, genEt("z1h",i)}, 
                {-r12_hat, genEt("x1h",i)}
            },
            "<=",
            s12_hat
        );
    }

    // g1h_def
    for(int i = 1; i <= h_c; i++){
        problema->añadirRestriccion(  
            genEt("g1h_def",i),
            { 
                {1, "g" + StringIdGen + idBonete + "(" + to_string(i) + ")"},
                {-1, genEt("z1h",i)}, 
                {-1, genEt("theta11",i)}, 
                {-1, genEt("theta12",i)}, 
                {-1, genEt("theta13",i)}
            },
            "=",
            0
        );
    }
    
    // discretizacion_bonete_restriccion_1i
    for(int i = 1; i <= h_c; i++){
        problema->añadirRestriccion(  
            genEt("discretizacion_bonete_restriccion_1i",i),
            { 
                {1, genEt("theta11",i)}, 
                {-k11, genEt("x1h",i)}
            },
            "<=",
            0
        );
    }

    // discretizacion_bonete_restriccion_1ii
    for(int i = 1; i <= h_c; i++){
        problema->añadirRestriccion(  
            genEt("discretizacion_bonete_restriccion_1ii",i),
            { 
                {1, genEt("theta12",i)}, 
                {-k12, genEt("x1h",i)}
            },
            "<=",
            0
        );
    }
    
    auto bloque8h = [](int hora) {
        return (hora - 1) / 8 + 1;
    };

    // discretizacion_bonete_restriccion_1iii
    for(int i = 1; i <= h_c; i++){
        problema->añadirRestriccion(  
            genEt("discretizacion_bonete_restriccion_1iii",i),
            { 
                {1, genEt("theta12",i)}, 
                {-680 * k12, genEt("varphi11", compactarActivacionTramos8h ? bloque8h(i) : i)}
            },
            "<=",
            0
        );
    }

    // discretizacion_bonete_restriccion_1iv
    for(int i = 1; i <= h_c; i++){
        problema->añadirRestriccion(  
            genEt("discretizacion_bonete_restriccion_1iv",i),
            { 
                {1, genEt("theta13",i)},
                {-k13, genEt("x1h",i)}
            },
            "<=",
            0
        );
    }

    // discretizacion_bonete_restriccion_1v
    for(int i = 1; i <= h_c; i++){
        problema->añadirRestriccion(  
            genEt("discretizacion_bonete_restriccion_1v",i),
            { 
                {1, genEt("theta13",i)}, 
                {-680 * k13, genEt("varphi12", compactarActivacionTramos8h ? bloque8h(i) : i)}
            },
            "<=",
            0
        );
    }

    // restriccion_varphi1_1
    if (!compactarActivacionTramos8h) {
        for(int i = 1; i <= h_c; i++){
            problema->añadirRestriccion(  
                genEt("restriccion_varphi1_1",i),
                { 
                    {M1, genEt("varphi11",i)}, 
                    {-1, genEt("v1h",i)}
                },
                "<=",
                -V1h2 + M1
            );
        }
    } else {
        int bloques = (h_c + 7) / 8;
        for (int k = 1; k <= bloques; k++) {
            int inicio = 8 * (k - 1) + 1;
            int fin = min(8 * k, h_c);
            double coefPromedio = -1.0 / static_cast<double>(fin - inicio + 1);
            vector<pair<double, string>> terminos = {{M1, genEt("varphi11", k)}};
            for (int i = inicio; i <= fin; i++) {
                terminos.push_back({coefPromedio, genEt("v1h", i)});
            }
            problema->añadirRestriccion(
                genEt("restriccion_varphi1_1", k),
                terminos,
                "<=",
                -V1h2 + M1
            );
        }
    }

    // restriccion_varphi1_2
    if (!compactarActivacionTramos8h) {
        for(int i = 1; i <= h_c; i++){
            problema->añadirRestriccion(  
                genEt("restriccion_varphi1_2",i),
                { 
                    {M1, genEt("varphi12",i)}, 
                    {-1, genEt("v1h",i)}
                },
                "<=",
                -V1h3 + M1
            );
        }
    } else {
        int bloques = (h_c + 7) / 8;
        for (int k = 1; k <= bloques; k++) {
            int inicio = 8 * (k - 1) + 1;
            int fin = min(8 * k, h_c);
            double coefPromedio = -1.0 / static_cast<double>(fin - inicio + 1);
            vector<pair<double, string>> terminos = {{M1, genEt("varphi12", k)}};
            for (int i = inicio; i <= fin; i++) {
                terminos.push_back({coefPromedio, genEt("v1h", i)});
            }
            problema->añadirRestriccion(
                genEt("restriccion_varphi1_2", k),
                terminos,
                "<=",
                -V1h3 + M1
            );
        }
    }

    // restriccion_varphi1_activacion
    for(int i = 1; i <= (compactarActivacionTramos8h ? (h_c + 7) / 8 : h_c); i++){
        problema->añadirRestriccion(
            genEt("restriccion_varphi1_activacion",i),
            { 
                {1, genEt("varphi12",i)},
                {-1 , genEt("varphi11",i)}
            },
            "<=",
            0
        );
    }
    
    // -----------> balance de agua en Bonete
    // Caso: t = 1
    problema->añadirRestriccion(   
        genEt("v1h_din",1),
        { 
            {1, genEt("v1h",1)}, 
            {3600, genEt("x1h",1)}, 
            {3600, genEt("y1h",1)}
        },
        "=",
        volumenInicialBonete + 3600 * aportesBonete[0]
    );

    for (int i = 2; i <= h_c; i++) {
        problema->añadirRestriccion(    
            genEt("v1h_din",i),
            { 
                {1, genEt("v1h",i)}, 
                {-1, genEt("v1h",i-1)}, 
                {3600, genEt("x1h",i)}, 
                {3600, genEt("y1h",i)}
            },
            "=",
            3600 * aportesBonete[i-1]
        );
    }

    // ============= AGREGAR VARIABLES =============
    for(int i = 1; i <= h_c; i++){
        // Añadir al modelo del problema
        // Variables continuas
        problema->añadirVariable(genEt("z1h",i),0,minimoTangenteBonete,maximoTangenteBonete);
        problema->añadirVariable(genEt("v1h",i),0,volumenMinimoBonete,volumenMaximoBonete);
        problema->añadirVariable(genEt("x1h",i),0,minimoFlujoBonete,maximoFlujoBonete);
        problema->añadirVariable(genEt("y1h",i),0,minimoVertidoBonete,maximoVertidoBonete);
        problema->añadirVariable(genEt("theta11",i),2,0,0);
        problema->añadirVariable(genEt("theta12",i),2,0,0);
        problema->añadirVariable(genEt("theta13",i),2,0,0);
        problema->añadirVariable("g" + StringIdGen + idBonete + "(" + to_string(i) + ")",2,genMinBonete,0);
    
    }

    for(int i = 1; i <= (compactarActivacionTramos8h ? (h_c + 7) / 8 : h_c); i++){
        problema->añadirBinario(genEt("varphi11",i));
        problema->añadirBinario(genEt("varphi12",i));
    }
    // Añadir variables internas
    nombresVariables.push_back(genEt("v1h",0));
    nombresVariables.push_back(genEt("v1h",0));
    nombresVariables.push_back(genEt("x1h",0));
    nombresVariables.push_back(genEt("y1h",0));
    nombresVariables.push_back(genEt("theta11",0));
    nombresVariables.push_back(genEt("theta12",0));
    nombresVariables.push_back(genEt("theta13",0));
    nombresVariables.push_back("g" + StringIdGen + idBonete);

    nombresVariables.push_back(genEt("varphi11",0));
    nombresVariables.push_back(genEt("varphi12",0));
}

void RioNegro::generarRestriccionesBaygorria(Problema* problema, int h_c) {
    string StringIdAgente = "a" + to_string(idAgente);
    string StringIdGen = to_string(idGen);

    // baygorria_tangente_1
    for(int i = 1; i <= h_c; i++){
        problema->añadirRestriccion(
            genEt("baygorria_tangente_1",i),
            { 
                {1 , genEt("z2h",i)}, 
                {-r21_hat, genEt("x2h",i)}
            },
            "<=",
            0
        );
    }

    // baygorria_tangente_2
    for(int i = 1; i <= h_c; i++){
        problema->añadirRestriccion( 
            genEt("baygorria_tangente_2",i),
            { 
                {1 , genEt("z2h",i)}, 
                {-r22_hat, genEt("x2h",i)}
            },
            "<=",
            s22_hat
        );
    }
    
    // g2h_def
    for (int i = 1; i <= h_c; i++){
        problema->añadirRestriccion( 
            genEt("g2h_def",i),
            { 
                {1e7, "g" + StringIdGen + idBaygorria + "(" + to_string(i) + ")"},
                {-1e7, genEt("z2h",i)}, 
                {1e7 * bygX, genEt("x2h",i)}, 
                {1e7 * bygV, genEt("v3h",i)}
            },
            "=",
            0
        );
    }

    // -----> balance de agua en Baygorria

    // Caso: 1 <= t <= 8
    for (int i = 1; i <= min(8,h_c); i++) {
        problema->añadirRestriccion(  
            genEt("v2h_din",i),
            { 
                {3600, genEt("x2h",i)}, 
                {3600, genEt("y2h",i)}
            },
            "=",
            3600 * aportesBaygorria[i-1]
        );
    }

    // Caso: t > 8
    for (int i = 9; i <= h_c; i++) {
        problema->añadirRestriccion(
            genEt("v2h_din",i),
            { 
                {3600, genEt("x2h",i)}, 
                {3600, genEt("y2h",i)},
                {-3600, genEt("x1h",i-8)}, 
                {-3600, genEt("y1h",i-8)}
            },
            "=",
            3600 * aportesBaygorria[i-1]
        );
    }

    // ============= AGREGAR VARIABLES =============
    for(int i = 1; i <= h_c; i++){
        // Añadir variables al modelo del problema
        problema->añadirVariable(genEt("z2h",i),0,minimoTangenteBaygorria,maximoTangenteBaygorria);
        problema->añadirVariable(genEt("x2h",i),0,minimoFlujoBaygorria,maximoFlujoBaygorria);
        problema->añadirVariable(genEt("y2h",i),0,minimoVertidoBaygorria,maximoVertidoBaygorria);
        problema->añadirVariable("g" + StringIdGen + idBaygorria + "(" + to_string(i) + ")",2,genMinBaygorria,0);
    }
    // Añadir variables internas
    nombresVariables.push_back(genEt("z2h",0));
    nombresVariables.push_back(genEt("x2h",0));
    nombresVariables.push_back(genEt("y2h",0));
    nombresVariables.push_back("g" + StringIdGen + idBaygorria);
}

void RioNegro::generarRestriccionesPalmar(Problema* problema, int h_c){
    string StringIdAgente = "a" + to_string(idAgente);
    string StringIdGen = to_string(idGen);
    auto bloque8h = [](int hora) {
        return (hora - 1) / 8 + 1;
    };

    // palmar_tangente_1
    for(int i = 1; i <= h_c; i++){
        problema->añadirRestriccion(
            genEt("palmar_tangente_1",i),
            { 
                {1 , genEt("z3h",i)}, 
                {-r31_hat, genEt("x3h",i)}
            },
            "<=",
            0
        );
    }

    // palmar_tangente_2
    for(int i = 1; i <= h_c; i++){
        problema->añadirRestriccion(
            genEt("palmar_tangente_2",i),
            {
                {1 , genEt("z3h",i)},
                {-r32_hat, genEt("x3h",i)}
            },
            "<=",
            s32_hat
        );
    }

    // palmar_tangente_3
    for(int i = 1; i <= h_c; i++){
        problema->añadirRestriccion( 
            genEt("palmar_tangente_3",i),
            {
                {1, genEt("z3h",i)},
                {-r33_hat, genEt("x3h",i)}
            },
            "<=",
            s33_hat
        );
    }

    // discretizacion_palmar_restriccion_3i
    for(int i = 1; i <= h_c; i++) {
        problema->añadirRestriccion(
            genEt("discretizacion_palmar_restriccion_3i",i),
            { 
                {1e3, genEt("theta31",i)},
                {-1e3 * k31, genEt("x3h",i)}
            },
            "<=",
            0
        );
    }

    // discretizacion_palmar_restriccion_3ii
    for(int i = 1; i <= h_c; i++) {
        problema->añadirRestriccion(
            genEt("discretizacion_palmar_restriccion_3ii",i),
            { 
                {1e3, genEt("theta32",i)},
                {-1e3 * k32, genEt("x3h",i)}
            },
            "<=",
            0
        );
    }

    // discretizacion_palmar_restriccion_3iii
    for(int i = 1; i <= h_c; i++) {
        problema->añadirRestriccion(
            genEt("discretizacion_palmar_restriccion_3iii",i),
            { 
                {1e3, genEt("theta32",i)},
                {-1e3*1380*k32, genEt("varphi31", compactarActivacionTramos8h ? bloque8h(i) : i)}
            },
            "<=",
            0
        );
    }
    
    // discretizacion_palmar_restriccion_3iv
    for(int i = 1; i <= h_c; i++) {
        problema->añadirRestriccion(
            genEt("discretizacion_palmar_restriccion_3iv",i),
            {
                {1e3, genEt("theta33",i)},
                {-1e3 * k33, genEt("x3h",i)}
            },
            "<=",
            0
        );
    }

    // discretizacion_palmar_restriccion_3v
    for(int i = 1; i <= h_c; i++) {
        problema->añadirRestriccion(
            genEt("discretizacion_palmar_restriccion_3v",i),
            {
                {1e3, genEt("theta33",i)},
                {-1e3 * 1380 * k33, genEt("varphi32", compactarActivacionTramos8h ? bloque8h(i) : i)}
            },
            "<=",
            0
        );
    }

    // discretizacion_palmar_restriccion_3vi
    for(int i = 1; i <= h_c; i++) {
        problema->añadirRestriccion( 
            genEt("discretizacion_palmar_restriccion_3vi",i),
            {
                {1e3, genEt("theta34",i)},
                {-1e3 * k34, genEt("x3h",i)}
            },
            "<=",
            0
        );
    }

    // discretizacion_palmar_restriccion_3vii
    for(int i = 1; i <= h_c; i++) {
        problema->añadirRestriccion(
            genEt("discretizacion_palmar_restriccion_3vii",i),
            {
                {1e3, genEt("theta34",i)},
                {-1e3 * k34 * 1380, genEt("varphi33", compactarActivacionTramos8h ? bloque8h(i) : i)}
            },
            "<=",
            0
        );
    }

    // discretizacion_palmar_restriccion_3viii
    for(int i = 1; i <= h_c; i++) {
        problema->añadirRestriccion( 
            genEt("discretizacion_palmar_restriccion_3viii",i),
            {
                {1e3, genEt("theta35",i)},
                {-1e3*k35, genEt("x3h",i)}
            },
            "<=",
            0
        );
    }

    // discretizacion_palmar_restriccion_3ix
    for(int i = 1; i <= h_c; i++) {
        problema->añadirRestriccion(  
            genEt("discretizacion_palmar_restriccion_3ix",i),
            {
                {1e3, genEt("theta35",i)},
                {-1e3*1380*k35 , genEt("varphi34", compactarActivacionTramos8h ? bloque8h(i) : i)}
            },
            "<=",
            0
        );
    }

    // restriccion_varphi_31
    if (!compactarActivacionTramos8h) {
        for (int i = 1; i <= h_c; i++) {
            problema->añadirRestriccion( 
                genEt("restriccion_varphi31",i),
                {
                    {M3, genEt("varphi31",i)},
                    {-1, genEt("v3h",i)}
                },
                "<=",
                M3-V3h2
            );
        }
    } else {
        int bloques = (h_c + 7) / 8;
        for (int k = 1; k <= bloques; k++) {
            int inicio = 8 * (k - 1) + 1;
            int fin = min(8 * k, h_c);
            double coefPromedio = -1.0 / static_cast<double>(fin - inicio + 1);
            vector<pair<double, string>> terminos = {{M3, genEt("varphi31", k)}};
            for (int i = inicio; i <= fin; i++) {
                terminos.push_back({coefPromedio, genEt("v3h", i)});
            }
            problema->añadirRestriccion(
                genEt("restriccion_varphi31", k),
                terminos,
                "<=",
                M3-V3h2
            );
        }
    }

    // restriccion_varphi_32
    if (!compactarActivacionTramos8h) {
        for (int i = 1; i <= h_c; i++) {
            problema->añadirRestriccion( 
                genEt("restriccion_varphi32",i),
                {
                    {M3, genEt("varphi32",i)},
                    {-1, genEt("v3h",i)}
                },
                "<=",
                M3-V3h3
            );
        }
    } else {
        int bloques = (h_c + 7) / 8;
        for (int k = 1; k <= bloques; k++) {
            int inicio = 8 * (k - 1) + 1;
            int fin = min(8 * k, h_c);
            double coefPromedio = -1.0 / static_cast<double>(fin - inicio + 1);
            vector<pair<double, string>> terminos = {{M3, genEt("varphi32", k)}};
            for (int i = inicio; i <= fin; i++) {
                terminos.push_back({coefPromedio, genEt("v3h", i)});
            }
            problema->añadirRestriccion(
                genEt("restriccion_varphi32", k),
                terminos,
                "<=",
                M3-V3h3
            );
        }
    }

    // restriccion_varphi_33
    if (!compactarActivacionTramos8h) {
        for (int i = 1; i <= h_c; i++) {
            problema->añadirRestriccion(  
                genEt("restriccion_varphi33",i),
                {
                    {M3, genEt("varphi33",i)},
                    {-1, genEt("v3h",i)}
                },
                "<=",
                M3-V3h4
            );
        }
    } else {
        int bloques = (h_c + 7) / 8;
        for (int k = 1; k <= bloques; k++) {
            int inicio = 8 * (k - 1) + 1;
            int fin = min(8 * k, h_c);
            double coefPromedio = -1.0 / static_cast<double>(fin - inicio + 1);
            vector<pair<double, string>> terminos = {{M3, genEt("varphi33", k)}};
            for (int i = inicio; i <= fin; i++) {
                terminos.push_back({coefPromedio, genEt("v3h", i)});
            }
            problema->añadirRestriccion(
                genEt("restriccion_varphi33", k),
                terminos,
                "<=",
                M3-V3h4
            );
        }
    }

    // restriccion_varphi_34
    if (!compactarActivacionTramos8h) {
        for (int i = 1; i <= h_c; i++) {
            problema->añadirRestriccion( 
                genEt("restriccion_varphi34",i),
                {
                    {M3, genEt("varphi34",i)},
                    {-1, genEt("v3h",i)}
                },
                "<=",
                M3-V3h5
            );
        }
    } else {
        int bloques = (h_c + 7) / 8;
        for (int k = 1; k <= bloques; k++) {
            int inicio = 8 * (k - 1) + 1;
            int fin = min(8 * k, h_c);
            double coefPromedio = -1.0 / static_cast<double>(fin - inicio + 1);
            vector<pair<double, string>> terminos = {{M3, genEt("varphi34", k)}};
            for (int i = inicio; i <= fin; i++) {
                terminos.push_back({coefPromedio, genEt("v3h", i)});
            }
            problema->añadirRestriccion(
                genEt("restriccion_varphi34", k),
                terminos,
                "<=",
                M3-V3h5
            );
        }
    }

    // restriccion_varphi31_activacion
    for (int i = 1; i <= (compactarActivacionTramos8h ? (h_c + 7) / 8 : h_c); i++) {
        problema->añadirRestriccion(
            genEt("restriccion_varphi31_activacion",i),
            {
                {1, genEt("varphi34",i)},
                {-1, genEt("varphi33",i)}
            },
            "<=",
            0
        );
    };

    // restriccion_varphi32_activacion
    for (int i = 1; i <= (compactarActivacionTramos8h ? (h_c + 7) / 8 : h_c); i++) {
        problema->añadirRestriccion(
            genEt("restriccion_varphi32_activacion",i),
            {
                {1, genEt("varphi33",i)},
                {-1, genEt("varphi32",i)}
            },
            "<=",
            0
        );
    };

    // restriccion_varphi33_activacion
    for (int i = 1; i <= (compactarActivacionTramos8h ? (h_c + 7) / 8 : h_c); i++) {
        problema->añadirRestriccion( 
            genEt("restriccion_varphi33_activacion",i),
            {
                {1, genEt("varphi32",i)},
                {-1, genEt("varphi31",i)}
            },
            "<=",
            0
        );
    };

    // g3h_def
    for(int i = 1; i <= h_c; i++){
        problema->añadirRestriccion( 
            genEt("g3h_def",i),
            { 
                {1, "g" + StringIdGen + idPalmar + "(" + to_string(i) + ")"},  // ← CORREGIR: usar idPalmar y agregar (i)
                {-1, genEt("z3h",i)}, 
                {-1, genEt("theta31",i)}, 
                {-1, genEt("theta32",i)}, 
                {-1, genEt("theta33",i)}, 
                {-1, genEt("theta34",i)}, 
                {-1, genEt("theta35",i)}
            },
            "=",
            0
        );
    }

    // Restricción de balance de agua de Palmar (ecuacion 6-(viii))
    // Caso: t = 1
    problema->añadirRestriccion(  
        genEt("v3h_din",1),
        { 
            {1, genEt("v3h",1)}, 
            {3600, genEt("x3h",1)}, 
            {3600, genEt("y3h",1)}
        },
        "=",
        volumenInicialPalmar + 3600 * aportesPalmar[0]
    );

    // Caso: 2 <= t <= 16
    for (int i = 2; i <= min(16,h_c); i++) {
        problema->añadirRestriccion(
            genEt("v3h_din", i),
            {
                {1, genEt("v3h", i)},
                {-1, genEt("v3h", i-1)},
                {3600, genEt("x3h", i)},
                {3600, genEt("y3h", i)}
            },
            "=",
            3600 * aportesPalmar[i-1]
        );
    }

    // Caso: 16 < t
    for (int i = 17; i <= h_c; i++) {
        problema->añadirRestriccion( 
            genEt("v3h_din", i),
            {
                {1, genEt("v3h", i)},
                {-1, genEt("v3h", i-1)},
                {3600, genEt("x3h", i)},
                {3600, genEt("y3h", i)},
                {-3600, genEt("x2h", i-16)},
                {-3600, genEt("y2h", i-16)}
            },
            "=",
            3600 * aportesPalmar[i-1]  
        );
    }

    // ============= AGREGAR VARIABLES =============
    for(int i = 1; i <= h_c; i++){
        // Añadir al modelo del problema
        // Variables continuas
        problema->añadirVariable(genEt("z3h",i),0,minimoTangentePalmar,maximoTangentePalmar);
        problema->añadirVariable(genEt("v3h",i),0,volumenMinimoPalmar,volumenMaximoPalmar);
        problema->añadirVariable(genEt("x3h",i),0,minimoFlujoPalmar,maximoFlujoPalmar);
        problema->añadirVariable(genEt("y3h",i),0,minimoVertidoPalmar,maximoVertidoPalmar);
        problema->añadirVariable(genEt("theta31",i),2,0,0);
        problema->añadirVariable(genEt("theta32",i),2,0,0);
        problema->añadirVariable(genEt("theta33",i),2,0,0);
        problema->añadirVariable(genEt("theta34",i),2,0,0);
        problema->añadirVariable(genEt("theta35",i),2,0,0);
    }

    // Añadir variables internas
    nombresVariables.push_back(genEt("z3h",0));
    nombresVariables.push_back(genEt("v3h",0));
    nombresVariables.push_back(genEt("x3h",0));
    nombresVariables.push_back(genEt("y3h",0));
    nombresVariables.push_back(genEt("theta31",0));
    nombresVariables.push_back(genEt("theta32",0));
    nombresVariables.push_back(genEt("theta33",0));
    nombresVariables.push_back(genEt("theta34",0));
    nombresVariables.push_back(genEt("theta35",0));

    // ============= BINARIOS =============
    for(int i = 1; i <= (compactarActivacionTramos8h ? (h_c + 7) / 8 : h_c); i++) {
        problema->añadirBinario(genEt("varphi31",i));
        problema->añadirBinario(genEt("varphi32",i));
        problema->añadirBinario(genEt("varphi33",i));
        problema->añadirBinario(genEt("varphi34",i));
    }

    for(int i = 1; i <= h_c; i++) {  
        // Añadir al modelo del problema
        problema->añadirVariable("g" + StringIdGen + idPalmar + "(" + to_string(i) + ")",2,genMinPalmar,0);
    }

    // Añadir variables internas
    nombresVariables.push_back(genEt("varphi31",0));
    nombresVariables.push_back(genEt("varphi32",0));
    nombresVariables.push_back(genEt("varphi33",0));
    nombresVariables.push_back(genEt("varphi34",0));
    nombresVariables.push_back("g" + StringIdGen + idPalmar);
}


void RioNegro::generarAporteFuncionObjetivo(Problema* problema, int h_c) {
    string StringIdGen = to_string(idGen);

    // Aporte de Bonete (costo del agua)
    problema->añadirTerminoFuncionObjetivo(-1 * costoAguaBonete, genEt("v1h", h_c));
    problema->sumarConstanteFuncionObjetivo(costoAguaBonete * volumenInicialBonete);

    // Aporte de Palmar (costo del agua)
    problema->añadirTerminoFuncionObjetivo(-1 * costoAguaPalmar, genEt("v3h", h_c));
    problema->sumarConstanteFuncionObjetivo(costoAguaPalmar * volumenInicialPalmar);
}


void RioNegro::generarRestriccionEnergia(Problema* problema, int h_c) {
    string StringIdGen = to_string(idGen);

    // gh_total - restricción de generación total del complejo
    for (int i = 1; i <= h_c; i++) {
        problema->añadirRestriccion( 
            genEt("gen_rio_negro",i),
            { 
                {1, "g" + StringIdGen + "(" + to_string(i) + ")"},  
                {-1, "g" + StringIdGen + idBonete + "(" + to_string(i) + ")"}, 
                {-1, "g" + StringIdGen + idBaygorria + "(" + to_string(i) + ")"}, 
                {-1, "g" + StringIdGen + idPalmar + "(" + to_string(i) + ")"}
            },
            "=",
            0
        );
    }
    
    // Agregar variable de generación total
    for (int i = 1; i <= h_c; i++){
        // Añadir al modelo del problema
        problema->añadirVariable("g" + StringIdGen + "(" + to_string(i) + ")",2,0,0);  
    }
    // Añadir variables internas
    nombresVariables.push_back("g" + StringIdGen);
}

void RioNegro::contribuirAlProblema(Problema* problema, int horizonteTemporal) {
    // Validar que el horizonte coincide
    if (horizonteTemporal != periodo) {
        cerr << "Error: Río Negro - horizonte proporcionado (" << horizonteTemporal 
                << ") no coincide con horizonte de construcción (" << periodo << ")" << endl;
        return;
    }

    // 1. Generar restricciones para cada central
    generarRestriccionesBonete(problema, horizonteTemporal);
    generarRestriccionesBaygorria(problema, horizonteTemporal); 
    generarRestriccionesPalmar(problema, horizonteTemporal);
    
    // 2. Generar restricciones de balance del complejo
    generarRestriccionEnergia(problema, horizonteTemporal);

    // 3. Agregar contribución a función objetivo
    generarAporteFuncionObjetivo(problema, horizonteTemporal);
}

double PotenciaVerdaderaBonete(double x1,double v1,double y1){
    double p11=0.1475;
    double p12=1.3124e-11;
    double p13=3.8380e-22;
    double p14=1.2796e-5;
    double PtBon = p11*x1 + p12*x1*v1 - p13*x1*pow(v1,2) - p14*pow(x1,2) - p14*x1*y1;
    return PtBon;
}
    

double PotenciaVerdaderaBaygorria(double x2, double v3, double y2){
    double p21=0.1523;
    double p22=7.5126e-6;
    double p23=3.3232e-11;
    double p24=4.4477e-21;
    double PtBay =  p21*x2 - p22*pow(x2,2) - p22*x2*y2 - p23*x2*v3 + p24*x2*pow(v3,2);
    return PtBay;
}
    

double PotenciaVerdaderaPalmar(double x3,double  v3,double y3){
    double p31=0.2551;
    double p32=3.9848e-11;
    double p33=5.3332e-21;
    double p34=2.4902e-5;
    double p35=1.2854e-9;
    double PtPal = p31*x3 + p32*x3*v3 - p33*x3*pow(v3,2) - p34*pow(x3,2) - p34*x3*y3 + p35*pow(x3,3) + p35*x3*pow(y3,2) + 2*p35*pow(x3,2)*y3;
    return PtPal;
}

void RioNegro::posprocesamiento(Problema* problema) {
    vector<double> PotenciaBoneteResolucion(periodo + 1, 0.0);
    vector<double> PotenciaBaygorriaResolucion(periodo + 1, 0.0);
    vector<double> PotenciaPalmarResolucion(periodo + 1, 0.0);
    vector<double> PotenciaTotalResolucion(periodo + 1, 0.0);

    map<string,double> valoresVariables = problema->getValoresVariables();
    double paso = 0.01;
    double TOLERANCIA = 0.1;

    vector<double> d(periodo,0);
    for(int i = 0; i <= periodo-1; i++){
        d[i] = problema->obtenerConstante("gen_menor_demanda(" + to_string(i+1) + ")");
    }
    
    

    for (int i = 1; i <= periodo; i++) { // Empieza en 1 si tus variables son (1...periodo)
        // Acceso seguro a las variables
        auto get = [&](const string& nombre) -> double {
            auto it = valoresVariables.find(nombre);
            if (it != valoresVariables.end()) return it->second;
            else {
                cerr << "RioNegro::posprocesamiento - Variable no encontrada: " << nombre << endl;
                return 0.0;
            }
        };

        double x1 = get(genEt("x1h", i));
        double v1 = get(genEt("v1h", i));
        double y1 = get(genEt("y1h", i));
        double x2 = get(genEt("x2h", i));
        double y2 = get(genEt("y2h", i));
        double x3 = get(genEt("x3h", i));
        double v3 = get(genEt("v3h", i));
        double y3 = get(genEt("y3h", i));

        PotenciaBoneteResolucion[i] = PotenciaVerdaderaBonete(x1, v1, y1);
        PotenciaBaygorriaResolucion[i] = PotenciaVerdaderaBaygorria(x2, v3, y2); // v3 para Baygorria
        PotenciaPalmarResolucion[i] = PotenciaVerdaderaPalmar(x3, v3, y3);

        PotenciaTotalResolucion[i] =
            PotenciaBoneteResolucion[i] +
            PotenciaBaygorriaResolucion[i] +
            PotenciaPalmarResolucion[i];

        // --- Ajustar Bonete ---
        string g11 = "g11(" + to_string(i) + ")";
        while ((PotenciaBoneteResolucion[i] > get(g11) + TOLERANCIA) &&
                (PotenciaTotalResolucion[i] > d[i-1] + TOLERANCIA)) {

            if (x1 - paso < 0 || y1 + paso > maximoVertidoBonete)
                break;

            valoresVariables[genEt("x1h", i)] -= paso;
            valoresVariables[genEt("y1h", i)] += paso;

            x1 = get(genEt("x1h", i));
            y1 = get(genEt("y1h", i));
            PotenciaBoneteResolucion[i] = PotenciaVerdaderaBonete(x1, v1, y1);
            PotenciaTotalResolucion[i] =
                PotenciaBoneteResolucion[i] +
                PotenciaBaygorriaResolucion[i] +
                PotenciaPalmarResolucion[i];
        }
        

        // --- Ajustar Baygorria ---
        string g12 = "g12(" + to_string(i) + ")";
        while ((PotenciaBaygorriaResolucion[i] > get(g12) + TOLERANCIA) &&
                (PotenciaTotalResolucion[i] > d[i-1] + TOLERANCIA)) {

            if (x2 - paso < 0 || y2 + paso > maximoVertidoBaygorria)
                break;

            valoresVariables[genEt("x2h", i)] -= paso;
            valoresVariables[genEt("y2h", i)] += paso;

            x2 = get(genEt("x2h", i));
            y2 = get(genEt("y2h", i));
            PotenciaBaygorriaResolucion[i] = PotenciaVerdaderaBaygorria(x2, v3, y2);
            PotenciaTotalResolucion[i] =
                PotenciaBoneteResolucion[i] +
                PotenciaBaygorriaResolucion[i] +
                PotenciaPalmarResolucion[i];
        }

        // --- Ajustar Palmar ---
        string g13 = "g13(" + to_string(i) + ")";
        while ((PotenciaPalmarResolucion[i] > get(g13) + TOLERANCIA) &&
                (PotenciaTotalResolucion[i] > d[i-1] + TOLERANCIA)) {

            if (x3 - paso < 0 || y3 + paso > maximoVertidoPalmar)
                break;

            valoresVariables[genEt("x3h", i)] -= paso;
            valoresVariables[genEt("y3h", i)] += paso;

            x3 = get(genEt("x3h", i));
            y3 = get(genEt("y3h", i));
            PotenciaPalmarResolucion[i] = PotenciaVerdaderaPalmar(x3, v3, y3);
            PotenciaTotalResolucion[i] =
                PotenciaBoneteResolucion[i] +
                PotenciaBaygorriaResolucion[i] +
                PotenciaPalmarResolucion[i];
        }
    }

    for (int i = 1; i <= periodo; i++) {
        valoresVariables["g" + to_string(idGen) + idBonete + "(" + to_string(i) + ")"] = PotenciaBoneteResolucion[i];
        valoresVariables["g" + to_string(idGen) + idBaygorria + "(" + to_string(i) + ")"] = PotenciaBaygorriaResolucion[i];
        valoresVariables["g" + to_string(idGen) + idPalmar + "(" + to_string(i) + ")"] = PotenciaPalmarResolucion[i];
        valoresVariables["g" + to_string(idGen) + "(" + to_string(i) + ")"] = PotenciaTotalResolucion[i];
    }

    problema->setValoresVariables(valoresVariables);
}
