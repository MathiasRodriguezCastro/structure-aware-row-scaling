#include "synthetic/GeneradorBenchmarkSintetico.h"

#include <algorithm>
#include <cmath>
#include <limits>
#include <random>
#include <stdexcept>

namespace {

// Cota superior de las variables continuas de bloque.
const double kCotaSuperiorContinua = 100.0;
// Coeficiente "big-M" del shortage/surplus en la función objetivo.
const double kBigM                 = 1.0e6;
// Ancho de banda para la familia "banded" / tamaño del soporte de filas locales.
const int    kAnchoSoporteLocal    = 3;

// Magnitud base del bloque i (1-indexado) según la familia de coeficientes.
// BlockHeterogeneous reparte exponentes en [-2, 2] entre bloques → bloques con
// escalas muy distintas, donde el escalado generator-aware tiene efecto medible.
double magnitudBloque(int bloque1, int numBloques, FamiliaCoeficientes fam) {
    if (fam != FamiliaCoeficientes::BlockHeterogeneous) return 1.0;
    if (numBloques <= 1) return 1.0;
    double e = -2.0 + 4.0 * (static_cast<double>(bloque1 - 1) / (numBloques - 1));
    return std::pow(10.0, e);
}

} // namespace

GeneradorBenchmarkSintetico::GeneradorBenchmarkSintetico(const ParametrosSinteticos& p)
    : params(p) {}

MetadatosInstancia GeneradorBenchmarkSintetico::generar(Problema& problema) const {
    if (params.numBloques <= 0 || params.varsContinuasPorBloque <= 0) {
        throw std::runtime_error(
            "GeneradorBenchmarkSintetico::generar - numBloques y varsContinuasPorBloque "
            "deben ser positivos.");
    }
    if (params.severidadS < 0) {
        throw std::runtime_error(
            "GeneradorBenchmarkSintetico::generar - severidad S no puede ser negativa.");
    }

    MetadatosInstancia meta;
    meta.params = params;
    meta.prefijosGlobal       = {"coupling_"};
    meta.prefijosAcoplamiento = {"coupling_"};

    std::mt19937 rng(params.seed);
    std::uniform_real_distribution<double> unif01(0.0, 1.0);
    auto draw = [&](double a, double b) { return a + (b - a) * unif01(rng); };

    // θ_r = 10^{ξ}, ξ ~ U[-S, S]. Multiplica TODA la fila (coeficientes y RHS).
    // coupling_uniform: un ÚNICO θ por instancia, compartido por todas las filas de
    // acoplamiento (desbalance COLECTIVO tipo cambio de unidades: el caso de diseño de la
    // etapa de acoplamiento, que aplica un γ colectivo relativo a los bloques). El patrón
    // coupling (θ por fila) es el caso adversarial: heterogeneidad interna entre filas de
    // acoplamiento que un γ único no puede comprimir.
    double thetaUniforme = 1.0;
    if (params.patron == PatronDesbalance::CouplingUniform && params.severidadS > 0) {
        double xi = draw(-static_cast<double>(params.severidadS),
                          static_cast<double>(params.severidadS));
        thetaUniforme = std::pow(10.0, xi);
    }
    auto factorDesbalance = [&]() -> double {
        if (params.severidadS == 0) return 1.0;
        if (params.patron == PatronDesbalance::CouplingUniform) return thetaUniforme;
        double xi = draw(-static_cast<double>(params.severidadS),
                          static_cast<double>(params.severidadS));
        return std::pow(10.0, xi);
    };
    auto filaRecibeDesbalance = [&](bool esLocal) -> bool {
        switch (params.patron) {
            case PatronDesbalance::None:            return false;
            case PatronDesbalance::Local:           return esLocal;
            case PatronDesbalance::Coupling:        return !esLocal;
            case PatronDesbalance::CouplingUniform: return !esLocal;
            case PatronDesbalance::Mixed:           return true;
        }
        return false;
    };

    int colId = 0;
    int rowId = 0;

    // Helper: registra una columna en la metadata y la agrega al problema.
    auto agregarContinua = [&](const std::string& nombre, int bloqueId, double objCoef) {
        problema.añadirVariable(nombre, 0, 0.0, kCotaSuperiorContinua);
        problema.añadirTerminoFuncionObjetivo(objCoef, nombre);
        InfoColumnaSintetica c;
        c.colId = colId++; c.nombre = nombre; c.tipo = TipoColumnaSintetica::Continua;
        c.bloqueId = bloqueId; c.lowerBound = 0.0; c.upperBound = kCotaSuperiorContinua;
        c.objCoef = objCoef;
        meta.columnas.push_back(c);
    };
    auto agregarBinaria = [&](const std::string& nombre, int bloqueId, double objCoef) {
        problema.añadirBinario(nombre);
        problema.añadirTerminoFuncionObjetivo(objCoef, nombre);
        InfoColumnaSintetica c;
        c.colId = colId++; c.nombre = nombre; c.tipo = TipoColumnaSintetica::Binaria;
        c.bloqueId = bloqueId; c.lowerBound = 0.0; c.upperBound = 1.0; c.objCoef = objCoef;
        meta.columnas.push_back(c);
    };
    auto agregarSlack = [&](const std::string& nombre, double objCoef) {
        problema.añadirVariable(nombre, 2, 0.0, 0.0);  // tipoCota=2: [0, +inf)
        problema.añadirTerminoFuncionObjetivo(objCoef, nombre);
        InfoColumnaSintetica c;
        c.colId = colId++; c.nombre = nombre; c.tipo = TipoColumnaSintetica::Slack;
        c.bloqueId = -1; c.lowerBound = 0.0;
        c.upperBound = std::numeric_limits<double>::infinity(); c.objCoef = objCoef;
        meta.columnas.push_back(c);
    };

    // Helper: aplica θ a una fila completa (coeficientes + RHS), la agrega al
    // problema y la registra en la metadata.
    auto agregarFila = [&](const std::string& nombre, TipoFilaSintetica tipo, int bloqueId,
                           std::vector<std::pair<double, std::string>> terminos,
                           const std::string& op, double rhs, bool esLocal) {
        double theta = filaRecibeDesbalance(esLocal) ? factorDesbalance() : 1.0;
        if (theta != 1.0) {
            for (auto& t : terminos) t.first *= theta;
            rhs *= theta;
        }
        problema.añadirRestriccion(nombre, terminos, op, rhs);

        double norma2 = 0.0;
        for (const auto& t : terminos) norma2 += t.first * t.first;

        InfoFilaSintetica f;
        f.rowId = rowId++; f.nombre = nombre; f.tipo = tipo; f.bloqueId = bloqueId;
        f.rhs = rhs; f.nnz = static_cast<int>(terminos.size());
        f.normaL2 = std::sqrt(norma2); f.appliedScaleFactor = theta;
        meta.filas.push_back(f);
    };

    const int B  = params.numBloques;
    const int nc = params.varsContinuasPorBloque;
    const int nb = params.varsBinariasPorBloque;

    // ---------------------------------------------------------------------
    // Bloques locales (cada uno análogo a un generador)
    // ---------------------------------------------------------------------
    for (int i = 1; i <= B; ++i) {
        meta.prefijosBloque.push_back("a" + std::to_string(i) + "_");
        const std::string pre = "a" + std::to_string(i) + "_";
        const double mag = magnitudBloque(i, B, params.familiaCoef);

        // Variables continuas y binarias del bloque.
        for (int j = 1; j <= nc; ++j)
            agregarContinua(pre + "x" + std::to_string(j), i, draw(1.0, 10.0));
        for (int k = 1; k <= nb; ++k)
            agregarBinaria(pre + "z" + std::to_string(k), i, draw(5.0, 50.0));

        // Restricciones locales: combinaciones sparse de las continuas del bloque.
        const int soporte = std::min(nc, kAnchoSoporteLocal);
        for (int r = 1; r <= params.restrLocalesPorBloque; ++r) {
            std::vector<int> idx;
            if (params.familiaCoef == FamiliaCoeficientes::Banded) {
                for (int s = 0; s < soporte; ++s) idx.push_back(((r - 1 + s) % nc) + 1);
            } else {
                std::vector<int> todos(nc);
                for (int j = 0; j < nc; ++j) todos[j] = j + 1;
                std::shuffle(todos.begin(), todos.end(), rng);
                for (int s = 0; s < soporte; ++s) idx.push_back(todos[s]);
            }
            std::vector<std::pair<double, std::string>> terminos;
            double sumaCoef = 0.0;
            for (int j : idx) {
                double coef = draw(0.5, 1.5) * mag;
                terminos.emplace_back(coef, pre + "x" + std::to_string(j));
                sumaCoef += coef;
            }
            double rhs = sumaCoef * kCotaSuperiorContinua * draw(0.3, 0.7);
            agregarFila(pre + "local_" + std::to_string(r), TipoFilaSintetica::Local, i,
                        terminos, "<=", rhs, /*esLocal=*/true);
        }

        // Restricciones de activación: a{i}_x{j} - U*a{i}_z{k} <= 0 (gating binario).
        for (int k = 1; k <= nb; ++k) {
            int j = ((k - 1) % nc) + 1;
            std::vector<std::pair<double, std::string>> terminos = {
                {1.0, pre + "x" + std::to_string(j)},
                {-kCotaSuperiorContinua, pre + "z" + std::to_string(k)}
            };
            agregarFila(pre + "act_" + std::to_string(k), TipoFilaSintetica::Activacion, i,
                        terminos, "<=", 0.0, /*esLocal=*/true);
        }
    }

    // ---------------------------------------------------------------------
    // Restricciones globales de acoplamiento + holguras de factibilidad
    // ---------------------------------------------------------------------
    for (int t = 1; t <= params.restrAcoplamiento; ++t) {
        const std::string st = "short_" + std::to_string(t);
        const std::string sp = "surp_"  + std::to_string(t);
        agregarSlack(st, kBigM);
        agregarSlack(sp, kBigM);

        std::vector<std::pair<double, std::string>> terminos;
        double sumaCap = 0.0;
        int jSel = ((t - 1) % nc) + 1;
        for (int i = 1; i <= B; ++i) {
            const double mag = magnitudBloque(i, B, params.familiaCoef);
            double coef = draw(0.5, 1.5) * mag;
            terminos.emplace_back(coef, "a" + std::to_string(i) + "_x" + std::to_string(jSel));
            sumaCap += coef * kCotaSuperiorContinua;
        }
        terminos.emplace_back(1.0, st);
        terminos.emplace_back(-1.0, sp);
        // Demanda alcanzable (la holgura garantiza factibilidad en cualquier caso).
        double demanda = sumaCap * draw(0.2, 0.8);
        agregarFila("coupling_" + std::to_string(t), TipoFilaSintetica::Acoplamiento, -1,
                    terminos, "=", demanda, /*esLocal=*/false);
    }

    return meta;
}

// ----------------------------------------------------------------------------
// Helpers de parseo
// ----------------------------------------------------------------------------

bool GeneradorBenchmarkSintetico::parsearPatron(const std::string& s, PatronDesbalance& out) {
    if (s == "none")     { out = PatronDesbalance::None;     return true; }
    if (s == "local")    { out = PatronDesbalance::Local;    return true; }
    if (s == "coupling") { out = PatronDesbalance::Coupling; return true; }
    if (s == "coupling_uniform" || s == "coupling-uniform") {
        out = PatronDesbalance::CouplingUniform; return true;
    }
    if (s == "mixed")    { out = PatronDesbalance::Mixed;    return true; }
    return false;
}

bool GeneradorBenchmarkSintetico::parsearFamilia(const std::string& s, FamiliaCoeficientes& out) {
    if (s == "uniform")            { out = FamiliaCoeficientes::Uniform;            return true; }
    if (s == "block_heterogeneous"){ out = FamiliaCoeficientes::BlockHeterogeneous; return true; }
    if (s == "banded")             { out = FamiliaCoeficientes::Banded;             return true; }
    return false;
}

std::string GeneradorBenchmarkSintetico::patronAString(PatronDesbalance p) {
    switch (p) {
        case PatronDesbalance::None:            return "none";
        case PatronDesbalance::Local:           return "local";
        case PatronDesbalance::Coupling:        return "coupling";
        case PatronDesbalance::CouplingUniform: return "coupling_uniform";
        case PatronDesbalance::Mixed:           return "mixed";
    }
    return "none";
}

std::string GeneradorBenchmarkSintetico::familiaAString(FamiliaCoeficientes f) {
    switch (f) {
        case FamiliaCoeficientes::Uniform:            return "uniform";
        case FamiliaCoeficientes::BlockHeterogeneous: return "block_heterogeneous";
        case FamiliaCoeficientes::Banded:             return "banded";
    }
    return "uniform";
}
