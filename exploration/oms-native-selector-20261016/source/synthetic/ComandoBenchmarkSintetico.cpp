#include "synthetic/ComandoBenchmarkSintetico.h"

#include "synthetic/RunnerBenchmarkSintetico.h"
#include "synthetic/GeneradorBenchmarkSintetico.h"

#include <algorithm>
#include <cctype>
#include <sstream>
#include <stdexcept>

namespace {

std::string trim(const std::string& s) {
    size_t a = s.find_first_not_of(" \t\r\n");
    if (a == std::string::npos) return "";
    size_t b = s.find_last_not_of(" \t\r\n");
    return s.substr(a, b - a + 1);
}

std::vector<std::string> tokenizar(const std::string& s) {
    std::vector<std::string> out;
    std::istringstream iss(s);
    std::string t;
    while (iss >> t) out.push_back(t);
    return out;
}

std::vector<std::string> separarPorComas(const std::string& s) {
    std::vector<std::string> out;
    std::stringstream ss(s);
    std::string item;
    while (std::getline(ss, item, ',')) {
        std::string t = trim(item);
        if (!t.empty()) out.push_back(t);
    }
    return out;
}

// Normaliza una flag de solver ("--gurobi" -> "Gurobi") case-insensitive.
std::string normalizarSolver(const std::string& raw) {
    std::string s = raw;
    while (!s.empty() && s.front() == '-') s.erase(0, 1);
    std::string lower = s;
    std::transform(lower.begin(), lower.end(), lower.begin(),
                   [](unsigned char c) { return std::tolower(c); });
    static const std::vector<std::string> canonicos =
        {"DummyLp", "Gurobi", "Cbc", "Cplex", "Hexaly"};
    for (const auto& canon : canonicos) {
        std::string cl = canon;
        std::transform(cl.begin(), cl.end(), cl.begin(),
                       [](unsigned char c) { return std::tolower(c); });
        if (lower == cl) return canon;
    }
    return s;  // sin reconocer: el caller reporta el error
}

int aEntero(const std::string& tok, const std::string& ctx) {
    try {
        size_t pos = 0;
        int v = std::stoi(tok, &pos);
        if (pos != tok.size()) throw std::invalid_argument("resto");
        return v;
    } catch (...) {
        throw std::runtime_error("benchmarkSintetico - entero inválido en " + ctx + ": '" + tok + "'");
    }
}

double aDouble(std::string tok, const std::string& ctx) {
    for (char& c : tok) if (c == ',') c = '.';
    try {
        size_t pos = 0;
        double v = std::stod(tok, &pos);
        if (pos != tok.size()) throw std::invalid_argument("resto");
        return v;
    } catch (...) {
        throw std::runtime_error("benchmarkSintetico - número inválido en " + ctx + ": '" + tok + "'");
    }
}

} // namespace

void ejecutarBenchmarkSintetico(std::istream& in, const std::vector<std::string>& args) {
    ConfiguracionRunner cfg;
    FamiliaCoeficientes familia = FamiliaCoeficientes::Uniform;

    // --- Flags opcionales (en la línea del comando) ---
    for (size_t i = 1; i < args.size(); ++i) {
        const std::string& a = args[i];
        auto requiereValor = [&](const std::string& flag) -> std::string {
            if (i + 1 >= args.size())
                throw std::runtime_error("benchmarkSintetico - falta valor para " + flag);
            return args[++i];
        };
        if (a == "--out")            cfg.outDir = requiereValor(a);
        else if (a == "--volcar-lp") cfg.lpDir  = requiereValor(a);
        else if (a == "--summary")   cfg.rutaSummary = requiereValor(a);
        else if (a == "--coef-family") {
            std::string fam = requiereValor(a);
            if (!GeneradorBenchmarkSintetico::parsearFamilia(fam, familia))
                throw std::runtime_error("benchmarkSintetico - coefficient_family inválida: '" + fam +
                    "'. Válidas: uniform, block_heterogeneous, banded.");
        }
        else if (a == "--timeout") cfg.solverConfig.timeoutSegundos = aDouble(requiereValor(a), "--timeout");
        else if (a == "--mipgap")  cfg.solverConfig.mipGap          = aDouble(requiereValor(a), "--mipgap");
        else throw std::runtime_error("benchmarkSintetico - flag desconocida: '" + a + "'");
    }

    // --- Lectura de parámetros posicionales (líneas siguientes) ---
    // Devuelve la siguiente línea no vacía / no comentario, ya trimmeada.
    auto lineaRaw = [&](const std::string& ctx) -> std::string {
        std::string l;
        while (std::getline(in, l)) {
            std::string t = trim(l);
            if (t.empty() || t[0] == '#') continue;
            return t;
        }
        throw std::runtime_error("benchmarkSintetico - fin de entrada inesperado leyendo " + ctx);
    };
    auto unToken = [&](const std::string& ctx) -> std::string {
        auto toks = tokenizar(lineaRaw(ctx));
        if (toks.size() != 1)
            throw std::runtime_error("benchmarkSintetico - se esperaba un único valor en " + ctx);
        return toks[0];
    };
    auto dosTokens = [&](const std::string& ctx) -> std::pair<std::string, std::string> {
        auto toks = tokenizar(lineaRaw(ctx));
        if (toks.size() != 2)
            throw std::runtime_error("benchmarkSintetico - se esperaban 2 valores en " + ctx);
        return {toks[0], toks[1]};
    };

    cfg.solver = normalizarSolver(unToken("solver"));

    ParametrosSinteticos& p = cfg.params;
    p.seed            = static_cast<unsigned int>(aEntero(unToken("seed"), "seed"));
    cfg.numInstancias = aEntero(unToken("numInstancias"), "numInstancias");
    p.numBloques      = aEntero(unToken("numBloques"), "numBloques");

    {
        auto [a, b] = dosTokens("nc nb (continuas/binarias por bloque)");
        p.varsContinuasPorBloque = aEntero(a, "varsContinuasPorBloque");
        p.varsBinariasPorBloque  = aEntero(b, "varsBinariasPorBloque");
    }
    {
        auto [a, b] = dosTokens("restrLocales restrAcoplamiento");
        p.restrLocalesPorBloque = aEntero(a, "restrLocalesPorBloque");
        p.restrAcoplamiento     = aEntero(b, "restrAcoplamiento");
    }

    // pattern: lista separada por comas (none,local,coupling,mixed) o un único valor.
    {
        auto pats = separarPorComas(lineaRaw("pattern"));
        if (pats.empty())
            throw std::runtime_error("benchmarkSintetico - lista de pattern vacía.");
        for (const auto& s : pats) {
            PatronDesbalance pd;
            if (!GeneradorBenchmarkSintetico::parsearPatron(s, pd))
                throw std::runtime_error("benchmarkSintetico - pattern inválido: '" + s +
                    "'. Válidos: none, local, coupling, coupling_uniform, coupling_heterogeneo, mixed.");
            cfg.patrones.push_back(pd);
        }
        p.patron = cfg.patrones.front();  // fallback
    }
    // S: lista separada por comas (0,3,6) o un único valor.
    {
        auto ss = separarPorComas(lineaRaw("S"));
        if (ss.empty())
            throw std::runtime_error("benchmarkSintetico - lista de S vacía.");
        for (const auto& s : ss) {
            int Sv = aEntero(s, "S");
            if (Sv < 0) throw std::runtime_error("benchmarkSintetico - S no puede ser negativo.");
            cfg.severidades.push_back(Sv);
        }
        p.severidadS = cfg.severidades.front();  // fallback
    }
    p.familiaCoef = familia;

    // La línea de variantes es una lista separada por comas (admite espacios).
    cfg.variantes = separarPorComas(lineaRaw("variantes"));
    if (cfg.variantes.empty())
        throw std::runtime_error("benchmarkSintetico - lista de variantes vacía.");

    cfg.rutaCsv = unToken("rutaCsvSalida");

    if (cfg.numInstancias <= 0)
        throw std::runtime_error("benchmarkSintetico - numInstancias debe ser positivo.");

    RunnerBenchmarkSintetico runner(cfg);
    runner.ejecutar();
}
