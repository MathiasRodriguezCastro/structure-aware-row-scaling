// =============================================================================
// Branch-and-price EXTERNO para el despacho hidrotérmico modular.
//
// Implementa la estrategia metodológica de la tesis (documento de diseño B&P):
//   - El árbol de branch-and-bound se administra FUERA del solver; Gurobi (u otro
//     backend) solo resuelve maestros restringidos LP/IP y subproblemas de pricing.
//   - Cada columna es una trayectoria local COMPLETA y factible de un agente
//     (misma definición que la descomposición Dantzig-Wolfe existente).
//   - En cada nodo se cierra la relajación lineal por generación de columnas con
//     pricing exacto, respetando las fijaciones de ramificación acumuladas B_{v,i}.
//   - Ramificación principal (Variante 2, regla "binarias"): sobre variables
//     binarias locales reconstruidas desde las columnas, ȳ_{i,h} = Σ_k λ_ik·y_{i,h}^k.
//     Se implementa por FILTRADO de columnas compatibles en el maestro y por
//     FIJACIÓN local (LB=UB) en el pricing del agente — preserva la separabilidad.
//   - Ramificación de diagnóstico (Variante 1, regla "lambda" o fallback): sobre
//     λ_{i,k} (hijo λ=0: columna prohibida por firma; hijo λ=1: columna forzada).
//     Si el pricing regenera una columna prohibida, se descarta y el nodo queda
//     marcado como NO certificado (limitación conocida de esta regla).
//   - El maestro entero restringido NO se vende como branch-and-price: se usa como
//     generador de incumbentes (en la raíz = Variante 0, periódicamente sobre el
//     pool global, y como test de integralidad por nodo).
//   - La falla permanece como holgura penalizada del maestro (implícita en el costo
//     ajustado de las columnas para DespachoFijo; explícita vía costoFalla(t) para
//     DespachoMercado). No genera columnas ni se ramifica.
//
// Cotas: el valor z_v^LP de un nodo cerrado con pricing exacto es cota inferior
// certificada del subárbol. Si la CG se trunca (presupuesto/iteraciones), se usa la
// mejor cota Lagrangiana LB = z_RMP + Σ_i c̄_i de las pasadas de pricing (válida con
// subproblemas resueltos a optimalidad). La LB global solo se reporta certificada si
// ningún nodo dependió de pricing fallido ni de columnas prohibidas regeneradas.
// =============================================================================

#include "SystemController/Problema/Problema.h"
#include "SystemController/Problema/GeneradorColumnas/GeneradorColumnas.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <queue>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

// Fijación de ramificación operativa: variable binaria local de un agente.
struct BPFijacion {
    int agente = -1;
    std::string variable;
    double valor = 0.0;  // 0.0 o 1.0
};

// Nodo del árbol externo. Solo guarda las decisiones de ramificación acumuladas;
// las columnas compatibles se reconstruyen desde el pool global al procesarlo.
struct BPNodo {
    int id = 0;
    int padre = -1;
    int profundidad = 0;
    double cota = -std::numeric_limits<double>::infinity();  // LB heredada del padre
    std::vector<BPFijacion> fijaciones;                            // regla "binarias"
    std::vector<std::pair<int, std::string>> columnasProhibidas;   // (agente, firma), λ=0
    std::map<int, std::string> columnaForzada;                     // agente → firma, λ=1
};

}  // namespace

void Problema::resolverBranchAndPrice() {
    resultadoBranchAndPrice = ResultadoBranchAndPrice{};
    ResultadoBranchAndPrice& res = resultadoBranchAndPrice;
    res.disponible = true;
    res.regla = configBP.regla;
    dwTiempoRestante = 0.0;
    dwFijacionesPorBloque.clear();

    std::cout << "[BP] Branch-and-price externo activado (regla=" << configBP.regla
              << ", maxNodos=" << configBP.maxNodos
              << ", maxIterCGNodo=" << configBP.maxIterCGNodo
              << ", incumbenteCadaNodos=" << configBP.incumbenteCadaNodos << ")." << std::endl;

    if (variables.empty() || restricciones.empty()) {
        throw std::runtime_error("Problema::resolverBranchAndPrice - El modelo interno esta vacio.");
    }
    if (configBP.regla != "binarias" && configBP.regla != "lambda") {
        throw std::invalid_argument(
            "Problema::resolverBranchAndPrice - regla de branching no reconocida: '" +
            configBP.regla + "'. Opciones: binarias, lambda.");
    }
    if (configBP.regla == "binarias" && !bpFijacionesLocalesSoportadas()) {
        throw std::runtime_error(
            "Problema::resolverBranchAndPrice - el backend configurado no soporta fijaciones "
            "locales en el pricing (requerido por la regla 'binarias'). Use --Gurobi, o "
            "configure la regla de diagnostico 'lambda'.");
    }
    if (generadorColumnas) {
        std::cout << "[BP] GeneradorColumnas inyectado: la red propone columnas INICIALES "
                  << "(validadas a factibilidad local); el pricing del arbol sigue siendo "
                  << "exacto (Etapa 5: asistencia aprendida validada)." << std::endl;
    }
    const bool usarBarrier = (configBP.duales == "barrier");
    if (configBP.duales != "simplex" && configBP.duales != "barrier") {
        throw std::invalid_argument(
            "Problema::resolverBranchAndPrice - modo de duales no reconocido: '" +
            configBP.duales + "'. Opciones: simplex, barrier.");
    }
    if (configBP.estab != "neame" && configBP.estab != "inout") {
        throw std::invalid_argument(
            "Problema::resolverBranchAndPrice - esquema de estabilizacion no reconocido: '" +
            configBP.estab + "'. Opciones: neame, inout.");
    }
    const bool usarPricingRelajado =
        configBP.pricingRelajado && dwPricingRelajadoSoportado();
    if (configBP.pricingRelajado && !dwPricingRelajadoSoportado())
        std::cout << "[BP] Aviso: pricing relajado pedido pero no soportado por el backend; "
                  << "se usa solo pricing exacto." << std::endl;
    if (usarPricingRelajado)
        std::cout << "[BP] Pricing por relajacion LP habilitado (saltea el MIP del bloque "
                  << "cuando el LP relajado certifica ausencia de columna)." << std::endl;

    // Modo EXACTO/certificable: la cota del nodo y el cierre se basan en la COTA DUAL del
    // subproblema (ObjBound), no en el costo reducido de la incumbente del pricing.
    const bool modoExacto = configBP.exacto && bpModoExactoSoportado();
    if (configBP.exacto && !bpModoExactoSoportado())
        throw std::runtime_error(
            "Problema::resolverBranchAndPrice - modo exacto requiere un backend que devuelva "
            "la cota dual del subproblema (bpModoExactoSoportado). Use --Gurobi.");
    res.modoExacto = modoExacto;
    res.gapPricingUsado = configBP.gapPricing >= 0.0 ? configBP.gapPricing : config.mipGap;
    if (modoExacto)
        std::cout << "[BP] Modo EXACTO/certificable habilitado: cota Lagrangiana y cierre por "
                  << "cota dual (ObjBound); gap_pricing=" << res.gapPricingUsado
                  << " gap_objetivo=" << configBP.gapObjetivo << "." << std::endl;
    dwMetodoMaestroLP = 0;

    const auto t0 = std::chrono::high_resolution_clock::now();
    auto segundosDesde = [](std::chrono::high_resolution_clock::time_point ini) {
        return std::chrono::duration<double>(
            std::chrono::high_resolution_clock::now() - ini).count();
    };
    auto transcurrido = [&]() { return segundosDesde(t0); };

    // --- Descomposición en bloques (pool GLOBAL de columnas) ---
    DWContexto ctx = dwConstruirContexto();
    const int horizonte = ctx.horizonte;
    const std::vector<double>& demanda = ctx.demanda;
    const std::vector<double>& costoFalla = ctx.costoFalla;
    std::map<int, DWBloque>& pool = ctx.bloques;

    prepararDWHook(pool);

    // Binarias locales por bloque: candidatas a branching operativo.
    std::set<std::string> binariasSet;
    for (auto* b : binarios) if (b) binariasSet.insert(b->getNombre());
    std::map<int, std::vector<std::string>> binariasPorBloque;
    int totalBinariasLocales = 0;
    for (auto& par : pool) {
        auto& lista = binariasPorBloque[par.first];
        for (const auto& v : par.second.variablesLocales)
            if (binariasSet.count(v)) lista.push_back(v);
        totalBinariasLocales += static_cast<int>(lista.size());
        std::cout << "[BP] Bloque " << par.first << ": "
                  << par.second.variablesLocales.size() << " variables locales, "
                  << par.second.restriccionesLocales.size() << " filas locales, "
                  << lista.size() << " binarias de branching." << std::endl;
    }
    if (configBP.regla == "binarias" && totalBinariasLocales == 0) {
        std::cout << "[BP] Aviso: ningun bloque tiene binarias locales; el arbol solo puede "
                  << "ramificar por la regla de diagnostico lambda." << std::endl;
    }

    // --- Presupuesto de tiempo ---
    const double presupuestoTotal =
        config.timeoutSegundos > 0.0 ? config.timeoutSegundos : 3600.0;
    const double presupuestoArbol = 0.92 * presupuestoTotal;  // el resto: cierre + IP final
    const double topeMasterIP = std::min(120.0, std::max(15.0, 0.10 * presupuestoTotal));
    const double topeSemilla  = std::min(60.0,  std::max(15.0, 0.05 * presupuestoTotal));
    // Columnas proposal del enriquecimiento (reparación del perfil LP): mismo criterio
    // de tope que el DW; definen la calidad del maestro entero de la raíz.
    const double topeProposal = std::min(120.0, std::max(30.0, 0.08 * presupuestoTotal));
    // Pricing en pasadas SUAVIZADAS (heurísticas): basta una incumbente mejorante, no
    // el óptimo; un tope corto evita que un subproblema duro (e.g. RioNegroNoLineal)
    // devore el presupuesto. Las pasadas PURAS no se acotan: certifican el cierre.
    const double topePricingHeur = std::min(60.0, std::max(10.0, 0.02 * presupuestoTotal));
    auto actualizarTiempoRestante = [&]() {
        dwTiempoRestante = std::max(5.0, presupuestoTotal - transcurrido());
    };
    auto acotarTiempo = [&](double tope) {
        actualizarTiempoRestante();
        dwTiempoRestante = std::min(dwTiempoRestante, tope);
    };

    const double epsCG  = configBP.epsCG;
    const double epsInt = configBP.epsInt;
    const double menosInf = -std::numeric_limits<double>::infinity();

    double tMasterLP = 0.0, tPricing = 0.0, tMasterIP = 0.0;
    bool huboPricingFallido = false;  // pricing sin solución dentro de un nodo (no certifica)

    // Agrega una columna al pool global de su bloque (deduplicada por firma).
    // Devuelve true si era nueva.
    auto agregarColumnaGlobal = [&](DWBloque& b, const DWColumna& col) -> bool {
        if (!b.firmas.insert(col.firma).second) return false;
        b.columnas.push_back(col);
        return true;
    };

    // ========================= Semillas de la raíz =========================
    // Mismo criterio que la CG existente: respuestas del subproblema a precios
    // γ·escalaPrecio (γ ∈ {0, 0.5, 1}) más una columna reparada hacia demanda/B,
    // para que el maestro pueda cubrir la demanda desde la primera iteración.
    std::vector<double> preciosCero(horizonte, 0.0);
    {
        for (auto& par : pool) {
            DWBloque& b = par.second;
            for (double gamma : {0.0, 0.5, 1.0}) {
                std::vector<double> precios(horizonte, 0.0);
                for (int t = 0; t < horizonte; ++t) precios[t] = gamma * ctx.escalaPrecio[t];
                actualizarTiempoRestante();
                auto pIni = std::chrono::high_resolution_clock::now();
                DWColumna col = resolverSubproblemaDW(b, precios, demanda,
                                                      static_cast<int>(b.columnas.size()));
                tPricing += segundosDesde(pIni);
                ++res.pricingSolves;
                agregarColumnaGlobal(b, col);
            }
        }
        const double cuota = 1.0 / static_cast<double>(pool.size());
        const double muSemilla = 10.0 * (1.0 + ctx.escalaPrecioMax);
        std::vector<double> perfilCuota(horizonte, 0.0);
        for (int t = 0; t < horizonte; ++t) perfilCuota[t] = cuota * demanda[t];
        for (auto& par : pool) {
            acotarTiempo(topeSemilla);
            auto pIni = std::chrono::high_resolution_clock::now();
            DWColumna col = resolverValidacionDW(par.second, preciosCero, demanda, perfilCuota,
                                                 muSemilla,
                                                 static_cast<int>(par.second.columnas.size()));
            tPricing += segundosDesde(pIni);
            ++res.pricingSolves;
            agregarColumnaGlobal(par.second, col);
        }
        // Etapa 5 (asistencia aprendida validada): si hay un GeneradorColumnas
        // inyectado, la red propone una trayectoria por bloque que se REPARA a
        // factibilidad local con el LP de validación L1 antes de entrar al pool.
        // Solo semillas: el pricing del árbol y la certificación siguen exactos.
        if (generadorColumnas) {
            generadorColumnas->prepararEscenario();
            const double muRed = (validacionDWHabilitada && validacionDWMu > 0.0)
                                     ? validacionDWMu
                                     : 10.0 * (1.0 + ctx.escalaPrecioMax);
            for (auto& par : pool) {
                DWBloque& b = par.second;
                acotarTiempo(topeSemilla);
                auto pIni = std::chrono::high_resolution_clock::now();
                DWColumna col;
                bool ok = true;
                try {
                    DWColumna sugerida = generadorColumnas->generar(
                        b, preciosCero, demanda, static_cast<int>(b.columnas.size()));
                    col = resolverValidacionDW(b, preciosCero, demanda,
                                               sugerida.generacion, muRed,
                                               static_cast<int>(b.columnas.size()));
                } catch (const std::exception&) {
                    ok = false;
                }
                tPricing += segundosDesde(pIni);
                ++res.pricingSolves;
                if (ok && agregarColumnaGlobal(b, col))
                    ++res.columnasAprendidas;
            }
            std::cout << "[BP] Semillas aprendidas validadas: "
                      << res.columnasAprendidas << std::endl;
        }

        for (const auto& par : pool)
            res.columnasRaiz += static_cast<int>(par.second.columnas.size());
        std::cout << "[BP] Semillas iniciales: " << res.columnasRaiz << " columnas." << std::endl;
    }

    // ========================= Estructuras del árbol =========================
    std::vector<BPNodo> nodos;
    // Best-first: min-heap por cota heredada (par {cota, id}).
    std::priority_queue<std::pair<double, int>,
                        std::vector<std::pair<double, int>>,
                        std::greater<std::pair<double, int>>> abiertos;
    nodos.push_back(BPNodo{});
    abiertos.push({menosInf, 0});
    res.nodosCreados = 1;

    // ========================= Incumbente =========================
    double UB = std::numeric_limits<double>::infinity();
    bool hayIncumbente = false;
    std::map<std::string, double> mejorSolucion;  // solución completa en variables originales
    // Tolerancia de poda por cota. En modo exacto usa gapObjetivo (consistente con el gap
    // certificado reportado); en modo heurístico, config.mipGap como antes.
    const double gapPoda = modoExacto ? configBP.gapObjetivo : config.mipGap;
    auto tolPoda = [&]() {
        return hayIncumbente ? std::max(1e-9, gapPoda * std::abs(UB)) : 0.0;
    };

    // Mapa base de la solución: todas las variables del modelo en cero.
    auto solucionBase = [&]() {
        std::map<std::string, double> vals;
        for (auto* v : variables) if (v) vals[v->getNombre()] = 0.0;
        for (auto* b : binarios)  if (b) vals[b->getNombre()] = 0.0;
        return vals;
    };

    auto registrarIncumbente = [&](double obj, std::map<std::string, double>&& valores,
                                   const char* origen) -> bool {
        if (hayIncumbente && obj >= UB - 1e-9) return false;
        const bool esPrimerIncumbente = !hayIncumbente;
        UB = obj;
        mejorSolucion = std::move(valores);
        hayIncumbente = true;
        ++res.mejorasIncumbente;
        if (esPrimerIncumbente) res.tiempoPrimerIncumbente = transcurrido();
        std::cout << "[BP] Nuevo incumbente UB=" << std::setprecision(12) << UB
                  << " (origen=" << origen << ")." << std::endl;
        return true;
    };

    // Maestro entero restringido sobre un conjunto de bloques/columnas: si mejora el
    // incumbente, lo actualiza con las columnas seleccionadas (λ binaria, una por
    // agente: la solución reconstruida es factible del modelo compacto porque cada
    // columna es localmente factible y el maestro impone las restricciones globales).
    // Devuelve el objetivo del IP, o NaN si no obtuvo solución.
    auto intentarIncumbenteIP = [&](const std::map<int, DWBloque>& bloquesIP,
                                    const char* origen) -> double {
        acotarTiempo(topeMasterIP);
        auto ipIni = std::chrono::high_resolution_clock::now();
        DWResultadoMaestro r;
        try {
            r = resolverMaestroRestringidoDW(bloquesIP, costoFalla, demanda, true);
        } catch (const std::exception& e) {
            tMasterIP += segundosDesde(ipIni);
            ++res.masterIPSolves;
            std::cout << "[BP] Maestro entero (" << origen << ") sin solucion: "
                      << e.what() << std::endl;
            return std::numeric_limits<double>::quiet_NaN();
        }
        tMasterIP += segundosDesde(ipIni);
        ++res.masterIPSolves;
        if (!hayIncumbente || r.objetivo < UB - 1e-9) {
            std::map<std::string, double> vals = solucionBase();
            std::vector<double> genTotal(horizonte, 0.0);
            for (const auto& par : bloquesIP) {
                auto itL = r.lambdas.find(par.second.agente);
                if (itL == r.lambdas.end() || itL->second.empty()) continue;
                std::size_t sel = 0;
                double mejor = -1.0;
                for (std::size_t k = 0; k < itL->second.size(); ++k)
                    if (itL->second[k] > mejor) { mejor = itL->second[k]; sel = k; }
                const DWColumna& col = par.second.columnas[sel];
                for (const auto& val : col.valoresLocales) vals[val.first] = val.second;
                for (int t = 0; t < horizonte; ++t) genTotal[t] += col.generacion[t];
            }
            for (const auto& par : r.variablesGlobales) vals[par.first] = par.second;
            for (int t = 0; t < horizonte; ++t)
                vals["g(" + std::to_string(t + 1) + ")"] = genTotal[t];
            registrarIncumbente(r.objetivo, std::move(vals), origen);
        }
        return r.objetivo;
    };

    // ¿La columna es admisible en el nodo (fijaciones + prohibiciones + forzadas)?
    auto columnaCompatible = [&](const BPNodo& n, const DWColumna& col) -> bool {
        for (const auto& f : n.fijaciones) {
            if (f.agente != col.agente) continue;
            auto it = col.valoresLocales.find(f.variable);
            const double v = (it != col.valoresLocales.end()) ? it->second : 0.0;
            if (std::abs(v - f.valor) > 0.5) return false;
        }
        for (const auto& p : n.columnasProhibidas)
            if (p.first == col.agente && p.second == col.firma) return false;
        auto itF = n.columnaForzada.find(col.agente);
        if (itF != n.columnaForzada.end() && itF->second != col.firma) return false;
        return true;
    };

    int nodosDesdeUltimoIP = 0;
    const bool reglaBinarias = (configBP.regla == "binarias");
    // Mínima cota entre los nodos podados por cota: al podar con tolerancia
    // (mipGap·|UB|), la LB global honesta es el mínimo entre las cotas de los nodos
    // abiertos y las de los podados (no UB).
    double peorCotaPodada = std::numeric_limits<double>::infinity();

    // ========================= Loop principal del árbol =========================
    while (!abiertos.empty()) {
        if (res.nodosProcesados >= configBP.maxNodos) { res.razonParada = "max_nodos"; break; }
        if (transcurrido() > presupuestoArbol)        { res.razonParada = "tiempo";    break; }

        const auto [cotaTop, idNodo] = abiertos.top();
        abiertos.pop();
        const BPNodo nodo = nodos[idNodo];

        // Poda perezosa por cota heredada (el incumbente pudo mejorar tras encolarlo).
        if (hayIncumbente && cotaTop >= UB - tolPoda()) {
            ++res.nodosPodadosCota;
            peorCotaPodada = std::min(peorCotaPodada, cotaTop);
            continue;
        }

        ++res.nodosProcesados;
        res.profundidadMax = std::max(res.profundidadMax, nodo.profundidad);

        // Fijaciones activas del nodo, visibles para el pricing del backend.
        dwFijacionesPorBloque.clear();
        for (const auto& f : nodo.fijaciones)
            dwFijacionesPorBloque[f.agente][f.variable] = f.valor;
        dwFirmasPurgadas.clear();   // purga local a este nodo

        // --- Columnas compatibles heredadas del pool global ---
        std::map<int, DWBloque> bloquesNodo;
        for (auto& par : pool) {
            const DWBloque& b = par.second;
            DWBloque bn;
            bn.agente = b.agente;
            bn.coefDespacho = b.coefDespacho;
            bn.varsInterfaz = b.varsInterfaz;
            bn.variablesLocales = b.variablesLocales;
            bn.restriccionesLocales = b.restriccionesLocales;
            for (const auto& col : b.columnas) {
                if (columnaCompatible(nodo, col)) {
                    bn.columnas.push_back(col);
                    bn.firmas.insert(col.firma);
                }
            }
            bloquesNodo.emplace(par.first, std::move(bn));
        }

        // --- Asegurar ≥1 columna compatible por bloque (semilla bajo fijaciones) ---
        bool nodoInfactible = false;
        for (auto& par : bloquesNodo) {
            DWBloque& bn = par.second;
            if (!bn.columnas.empty()) continue;
            if (nodo.columnaForzada.count(bn.agente)) { nodoInfactible = true; break; }
            actualizarTiempoRestante();
            auto pIni = std::chrono::high_resolution_clock::now();
            DWColumna col;
            bool ok = true;
            try {
                col = resolverSubproblemaDW(pool.at(bn.agente), preciosCero, demanda,
                                            static_cast<int>(pool.at(bn.agente).columnas.size()));
            } catch (const std::exception&) {
                ok = false;  // pricing infactible bajo fijaciones → nodo infactible
            }
            tPricing += segundosDesde(pIni);
            ++res.pricingSolves;
            if (!ok) { nodoInfactible = true; break; }
            agregarColumnaGlobal(pool.at(bn.agente), col);
            if (columnaCompatible(nodo, col)) {
                bn.columnas.push_back(col);
                bn.firmas.insert(col.firma);
            } else {
                // Solo posible con columnas prohibidas (regla lambda): el pricing exacto
                // devolvió justamente la prohibida y no hay otra disponible.
                ++res.columnasIncompatiblesPricing;
                nodoInfactible = true;
                break;
            }
        }
        if (nodoInfactible) {
            ++res.nodosPodadosInfactibles;
            std::cout << "[BP] nodo=" << nodo.id << " prof=" << nodo.profundidad
                      << " estado=infactible." << std::endl;
            continue;
        }

        // Warm-start del pricing entre nodos: sembrar el modelo del subproblema de cada
        // bloque con una columna compatible del nodo (cumple las fijaciones por
        // construcción). El MIP del pricing arranca con una incumbente factible y no
        // tiene que reconstruirla bajo las nuevas cotas — clave en bloques cuyo MIP es
        // caro (RN-NL). Se elige la columna de menor costo local del nodo.
        if (nodo.id != 0) {
            for (auto& par : bloquesNodo) {
                const DWBloque& bn = par.second;
                if (bn.columnas.empty()) continue;
                const DWColumna* mejor = &bn.columnas.front();
                for (const auto& c : bn.columnas)
                    if (c.costoLocal < mejor->costoLocal) mejor = &c;
                dwSembrarPricingStart(pool.at(bn.agente), mejor->valoresLocales);
            }
        }

        // --- Generación de columnas del nodo (pricing exacto, duales puros) ---
        double zLP = std::numeric_limits<double>::quiet_NaN();
        double mejorLBNodo = nodo.cota;  // arranque: cota heredada (válida para el subárbol)
        bool cerradoExacto = false;
        bool pricingContaminado = false;
        bool masterInfactible = false;
        bool reparacionIntentada = false;
        DWResultadoMaestro resLP;
        int iterNodo = 0;
        int columnasNodo = 0;
        // Estabilización dual de la CG del nodo. Dos esquemas:
        //   neame → smoothing de trayectoria π_sep^k = α·π_sep^{k−1}+(1−α)·π_master.
        //   inout → Ben-Ameur–Neto: π_sep = π_in + κ(π_master − π_in), donde π_in es el
        //           mejor dual hallado (el que dio la cota Lagrangiana más alta). El
        //           in-point se actualiza al mejorar la cota; combate el tailing-off con
        //           más fuerza que el smoothing puro.
        // Las pasadas PURAS (π_master) certifican el cierre y refrescan la cota.
        const double alphaEstabilizacion = configBP.alphaEstab;
        const bool   modoInOut = (configBP.estab == "inout");
        const double kappaInOut = configBP.kappaInOut;
        const int iterPuroCada = 10;
        std::vector<double> piSepAnterior;   // neame: π_sep de la iteración previa
        std::vector<double> piIn;            // inout: in-point (mejor dual)
        double mejorLBParaInPoint = -std::numeric_limits<double>::infinity();
        // Modo exacto: ¿la última pasada pura certificó (vía cota dual) que NINGÚN bloque
        // tiene columna de costo reducido < −epsCG? Solo entonces el cierre es riguroso.
        bool cierreDualCertificado = false;

        while (iterNodo < configBP.maxIterCGNodo) {
            // Durante la CG, los duales pueden pedirse al barrier (interiores, bien
            // centrados); el re-solve de vértice posterior repone λ extremas.
            dwMetodoMaestroLP = usarBarrier ? 1 : 0;
            actualizarTiempoRestante();
            auto mIni = std::chrono::high_resolution_clock::now();
            bool masterOk = true;
            try {
                resLP = resolverMaestroRestringidoDW(bloquesNodo, costoFalla, demanda, false);
            } catch (const std::exception&) {
                masterOk = false;
            }
            tMasterLP += segundosDesde(mIni);
            ++res.masterLPSolves;

            if (!masterOk) {
                // El maestro restringido puede ser infactible solo por SOBRE-generación
                // forzada de las columnas presentes. Antes de podar, intentar restaurar
                // factibilidad con columnas de generación mínima (precios negativos),
                // como exige la regla de poda por infactibilidad del diseño.
                if (!reparacionIntentada) {
                    reparacionIntentada = true;
                    std::vector<double> preciosNeg(horizonte, 0.0);
                    for (int t = 0; t < horizonte; ++t)
                        preciosNeg[t] = -(1.0 + ctx.escalaPrecio[t]);
                    bool alguna = false;
                    for (auto& par : bloquesNodo) {
                        DWBloque& bn = par.second;
                        if (nodo.columnaForzada.count(bn.agente)) continue;
                        actualizarTiempoRestante();
                        auto pIni = std::chrono::high_resolution_clock::now();
                        try {
                            DWColumna col = resolverSubproblemaDW(
                                pool.at(bn.agente), preciosNeg, demanda,
                                static_cast<int>(pool.at(bn.agente).columnas.size()));
                            agregarColumnaGlobal(pool.at(bn.agente), col);
                            if (columnaCompatible(nodo, col) &&
                                bn.firmas.insert(col.firma).second) {
                                bn.columnas.push_back(col);
                                alguna = true;
                            }
                        } catch (const std::exception&) {}
                        tPricing += segundosDesde(pIni);
                        ++res.pricingSolves;
                    }
                    if (alguna) continue;  // reintentar el maestro con las columnas nuevas
                }
                masterInfactible = true;
                break;
            }

            zLP = resLP.objetivo;
            ++res.iteracionesCGTotales;
            ++iterNodo;

            // Column pool management: si un bloque acumuló demasiadas columnas, desactivar
            // las de mayor costo reducido y λ≈0 (las que el maestro no usa). El maestro
            // las mantendrá con UB=0; si el pricing regenera alguna con c̄<0 se resucita.
            if (configBP.purgarColumnas) {
                for (auto& par : bloquesNodo) {
                    const DWBloque& bn = par.second;
                    auto itL = resLP.lambdas.find(bn.agente);
                    if (itL == resLP.lambdas.end()) continue;
                    const auto& lambda = itL->second;
                    const std::size_t nCols = std::min(lambda.size(), bn.columnas.size());
                    if (static_cast<int>(nCols) <= configBP.purgaMaxActivas) continue;
                    const double alphaConv = resLP.dualConvexidad.count(bn.agente)
                                                 ? resLP.dualConvexidad.at(bn.agente) : 0.0;
                    // (costo reducido, firma) de las columnas no básicas (λ≈0, no purgadas).
                    std::vector<std::pair<double, const std::string*>> cand;
                    for (std::size_t k = 0; k < nCols; ++k) {
                        if (lambda[k] > 1e-7) continue;
                        const DWColumna& c = bn.columnas[k];
                        if (dwFirmasPurgadas.count(c.firma)) continue;
                        double rc = c.costoLocal - alphaConv;
                        for (int t = 0; t < horizonte; ++t)
                            rc -= resLP.dualDemanda[t] * c.generacion[t];
                        cand.emplace_back(rc, &c.firma);
                    }
                    // Mantener las purgaMaxActivas mejores: purgar el resto (mayor rc primero).
                    const int aPurgar = static_cast<int>(nCols) - configBP.purgaMaxActivas;
                    if (aPurgar <= 0 || cand.empty()) continue;
                    std::sort(cand.begin(), cand.end(),
                              [](const auto& a, const auto& b) { return a.first > b.first; });
                    const int n = std::min(aPurgar, static_cast<int>(cand.size()));
                    for (int i = 0; i < n; ++i)
                        dwFirmasPurgadas.insert(*cand[i].second);
                }
            }

            if (transcurrido() > presupuestoArbol) break;  // nodo queda heurístico

            // Pasada de pricing sobre `precios` (estabilización de Neame). La aceptación
            // de columnas usa el costo reducido respecto de los duales PUROS del maestro
            // (garantiza progreso del RMP); la cota Lagrangiana del nodo solo se
            // actualiza en pasadas puras (esPuro): LB = z_RMP + Σ_i min(0, c̄_i).
            auto pasadaPricingNodo = [&](const std::vector<double>& precios,
                                         bool esPuro, int& nuevas) -> bool {
                nuevas = 0;
                double sumaReducidos = 0.0;   // heurístico: usa la incumbente del pricing
                double sumaCotaDual  = 0.0;   // exacto: usa la cota dual (ObjBound / ζ_LP)
                bool sumaValida = true;
                bool todosCertificados = true;  // exacto: cada bloque certificó cierre por cota dual
                // El filtro relajado da una cota dual barata (ζ_LP ≤ ζ_MIP); se usa en modo
                // exacto SIEMPRE (es certificación válida) y en el modo rápido si está pedido.
                const bool filtroRelajado = (usarPricingRelajado || modoExacto)
                                            && dwPricingRelajadoSoportado();
                for (auto& par : bloquesNodo) {
                    DWBloque& bn = par.second;
                    // Columna forzada (rama λ=1): la trayectoria del agente está fija; su
                    // λ es básica en el maestro, c̄ = 0, y no admite columnas nuevas.
                    if (nodo.columnaForzada.count(bn.agente)) continue;

                    const double alphaConv = resLP.dualConvexidad.count(bn.agente)
                                                 ? resLP.dualConvexidad.at(bn.agente) : 0.0;

                    // Pricing por relajación: ζ_LP ≤ ζ_MIP, así que si el costo reducido
                    // del LP relajado del bloque es ≥ −εCG, el MIP exacto tampoco tiene
                    // columna mejorante → se saltea el MIP caro (clave en el completo,
                    // donde el subproblema RN-NL domina el tiempo). ζ_LP es cota dual
                    // válida: certifica el cierre del bloque y entra a la cota Lagrangiana.
                    if (filtroRelajado) {
                        actualizarTiempoRestante();
                        auto pRel = std::chrono::high_resolution_clock::now();
                        double zRelax = -std::numeric_limits<double>::infinity();
                        bool relOk = true;
                        try {
                            zRelax = dwCostoReducidoRelajado(pool.at(bn.agente), precios, demanda);
                        } catch (const std::exception&) { relOk = false; }
                        tPricing += segundosDesde(pRel);
                        if (relOk && std::isfinite(zRelax)) {
                            const double rcRelax = zRelax - alphaConv;
                            if (rcRelax >= -epsCG) {
                                sumaReducidos += std::min(0.0, rcRelax);  // ≈ 0: bloque cerrado
                                sumaCotaDual  += std::min(0.0, rcRelax);
                                continue;  // sin columna mejorante (certificado): no MIP
                            }
                        }
                    }

                    if (esPuro) actualizarTiempoRestante();
                    else        acotarTiempo(topePricingHeur);
                    auto pIni = std::chrono::high_resolution_clock::now();
                    // En modo exacto, el pricing certificado devuelve también la cota dual
                    // (ObjBound) del subproblema; en modo rápido, solo las columnas.
                    std::vector<DWColumna> cols;
                    DWResultadoPricing rp;
                    bool ok = true;
                    try {
                        if (modoExacto) {
                            rp = resolverSubproblemaDWPoolCert(
                                pool.at(bn.agente), precios, demanda,
                                static_cast<int>(pool.at(bn.agente).columnas.size()), 5);
                            cols = std::move(rp.columnas);
                        } else {
                            cols = resolverSubproblemaDWPool(
                                pool.at(bn.agente), precios, demanda,
                                static_cast<int>(pool.at(bn.agente).columnas.size()), 5);
                        }
                    } catch (const std::exception&) {
                        ok = false;
                    }
                    tPricing += segundosDesde(pIni);
                    ++res.pricingSolves;

                    // Cota dual del bloque (modo exacto): rcDual = ObjBound − α ≤ c̄_min real.
                    // Es cota inferior válida del costo reducido mínimo del subproblema, con
                    // CUALQUIER gap del MIP (incluso truncado por tiempo).
                    if (modoExacto) {
                        if (ok && rp.cotaDualValida) {
                            const double rcDual = rp.cotaDual - alphaConv;
                            sumaCotaDual += std::min(0.0, rcDual);
                            if (rcDual < -epsCG) todosCertificados = false;  // bloque no cerrado
                        } else {
                            // Sin cota dual válida: el bloque no se puede certificar.
                            todosCertificados = false;
                            if (esPuro) ++res.pricingTruncadoSinObjBound;
                        }
                    }

                    if (!ok) {
                        sumaValida = false;
                        huboPricingFallido = true;
                        continue;
                    }
                    if (cols.empty()) {
                        // En modo exacto, "sin columna" con cota dual válida es legítimo:
                        // el bloque no tiene columna mejorante (ya contabilizado arriba).
                        if (modoExacto && rp.cotaDualValida) continue;
                        sumaValida = false;
                        huboPricingFallido = true;
                        continue;
                    }
                    auto costoReducidoPuro = [&](const DWColumna& c) {
                        double r = c.costoLocal - alphaConv;
                        for (int t = 0; t < horizonte; ++t)
                            r -= resLP.dualDemanda[t] * c.generacion[t];
                        return r;
                    };
                    auto costoReducidoSep = [&](const DWColumna& c) {
                        double r = c.costoLocal - alphaConv;
                        for (int t = 0; t < horizonte; ++t)
                            r -= precios[t] * c.generacion[t];
                        return r;
                    };
                    // Cota Lagrangiana del modo heurístico: usa la incumbente del pricing
                    // (válida solo si el subproblema cerró a gap 0; por eso el modo exacto
                    // usa sumaCotaDual en su lugar).
                    sumaReducidos += std::min(0.0, costoReducidoSep(cols.front()));

                    for (const auto& col : cols) {
                        if (std::min(costoReducidoPuro(col), costoReducidoSep(col)) >= -epsCG)
                            continue;
                        if (!columnaCompatible(nodo, col)) {
                            // Pricing devolvió una columna prohibida (rama λ=0): se descarta
                            // y la cota del nodo deja de ser certificable.
                            ++res.columnasIncompatiblesPricing;
                            pricingContaminado = true;
                            continue;
                        }
                        agregarColumnaGlobal(pool.at(bn.agente), col);
                        if (bn.firmas.insert(col.firma).second) {
                            bn.columnas.push_back(col);
                            ++nuevas;
                            ++columnasNodo;
                        } else if (dwFirmasPurgadas.erase(col.firma) > 0) {
                            // El pricing regeneró una columna purgada con c̄<0: era
                            // necesaria. Resucitarla (reactivar en el maestro) y contar
                            // como nueva para que el nodo NO declare cierre prematuro.
                            ++nuevas;
                        } else {
                            ++res.columnasDescartadasRepeticion;
                        }
                    }
                }
                if (esPuro && sumaValida)
                    mejorLBNodo = std::max(mejorLBNodo,
                                          zLP + (modoExacto ? sumaCotaDual : sumaReducidos));
                if (esPuro && modoExacto)
                    cierreDualCertificado = todosCertificados;
                return sumaValida;
            };

            // Punto de separación: pasada pura (π_master) la primera vez, cada
            // iterPuroCada iteraciones, o si no hay estabilización; si no, según el modo.
            std::vector<double> piSep = resLP.dualDemanda;
            bool esPuro = true;
            const bool tocaPura = (iterNodo % iterPuroCada) == 0;
            if (modoInOut && kappaInOut < 1.0 && !piIn.empty() && !tocaPura) {
                esPuro = false;
                for (int t = 0; t < horizonte; ++t)
                    piSep[t] = piIn[t] + kappaInOut * (resLP.dualDemanda[t] - piIn[t]);
            } else if (!modoInOut && alphaEstabilizacion > 0.0 &&
                       !piSepAnterior.empty() && !tocaPura) {
                esPuro = false;
                for (int t = 0; t < horizonte; ++t)
                    piSep[t] = alphaEstabilizacion * piSepAnterior[t]
                             + (1.0 - alphaEstabilizacion) * resLP.dualDemanda[t];
            }

            int nuevas = 0;
            bool sumaValida = pasadaPricingNodo(piSep, esPuro, nuevas);
            if (nuevas == 0 && !esPuro) {
                // Mis-pricing: re-valorar con los duales puros del maestro. Solo una
                // pasada pura sin columnas certifica el cierre del nodo.
                int nuevasPuro = 0;
                sumaValida = pasadaPricingNodo(resLP.dualDemanda, true, nuevasPuro);
                nuevas += nuevasPuro;
                esPuro = true;
                piSep = resLP.dualDemanda;
            }
            // In-out: el in-point se mueve al dual del maestro cuando una pasada pura
            // mejora la cota Lagrangiana (ese dual es el centro estable más informativo).
            if (modoInOut && esPuro && mejorLBNodo > mejorLBParaInPoint + 1e-9) {
                mejorLBParaInPoint = mejorLBNodo;
                piIn = resLP.dualDemanda;
            } else if (modoInOut && piIn.empty()) {
                piIn = resLP.dualDemanda;  // semilla inicial del in-point
            }
            piSepAnterior = std::move(piSep);

            if (nuevas == 0) {
                if (modoExacto)
                    // Cierre riguroso: pasada pura, sin fallos, sin columna prohibida
                    // regenerada, y TODOS los bloques certificados por cota dual.
                    cerradoExacto = esPuro && sumaValida && cierreDualCertificado
                                    && !pricingContaminado;
                else
                    cerradoExacto = esPuro && sumaValida && !pricingContaminado;
                // Si en modo exacto no se certificó (algún bloque truncado sin ObjBound o
                // con rcDual < −εCG), cerradoExacto queda false: el nodo NO cierra, sale
                // del loop como heurístico y se re-encola con mejorLBNodo (cota dual válida).
                break;
            }
        }

        if (masterInfactible) {
            ++res.nodosPodadosInfactibles;
            std::cout << "[BP] nodo=" << nodo.id << " prof=" << nodo.profundidad
                      << " estado=maestro_infactible (reparacion agotada)." << std::endl;
            continue;
        }

        // Con duales barrier, recuperar una solución de VÉRTICE del mismo LP antes del
        // chequeo de integralidad y del enriquecimiento: las λ interiores reparten masa
        // entre óptimos alternativos y vuelven ȳ artificialmente fraccionaria.
        if (usarBarrier && !std::isnan(zLP)) {
            dwMetodoMaestroLP = 0;
            actualizarTiempoRestante();
            auto mIni = std::chrono::high_resolution_clock::now();
            try {
                resLP = resolverMaestroRestringidoDW(bloquesNodo, costoFalla, demanda, false);
                zLP = resLP.objetivo;
            } catch (const std::exception&) {
                // Se conserva la solución barrier (válida; solo menos extremal).
            }
            tMasterLP += segundosDesde(mIni);
            ++res.masterLPSolves;
        }

        if (cerradoExacto) ++res.nodosCerradosExacto; else ++res.nodosHeuristicos;
        if (modoExacto && cerradoExacto) ++res.nodosCertificadosCotaDual;

        // Cota inferior del nodo: zLP si la CG cerró; si no, la mejor Lagrangiana
        // observada (válida); como último recurso, la heredada.
        double cotaNodo = cerradoExacto ? zLP : mejorLBNodo;
        if (std::isnan(cotaNodo)) cotaNodo = nodo.cota;

        if (idNodo == 0) {
            res.zRaizLP = zLP;
            res.raizCerradaExacto = cerradoExacto;
            res.tRaiz = transcurrido();

            // Enriquecimiento con déficit (heurística de incumbentes, como en el DW):
            // el perfil agregado ĝ_i = Σ_k λ_ik·gen_ik del maestro LP se repara por
            // bloque a una columna entera factible cercana; lo que un bloque no puede
            // reproducir (su conjunto local no es convexo) se traslada como déficit al
            // siguiente. Sin esto, el maestro entero de la raíz solo dispone de
            // respuestas extremas del pricing y sus incumbentes son pobres.
            const double muProposal = 10.0 * (1.0 + ctx.escalaPrecioMax);
            for (int ronda = 0; ronda < 2; ++ronda) {
                if (transcurrido() > presupuestoArbol) break;
                if (resLP.lambdas.empty()) break;
                std::vector<DWBloque*> orden;
                for (auto& par : bloquesNodo) orden.push_back(&par.second);
                if (ronda % 2 == 1) std::reverse(orden.begin(), orden.end());
                std::vector<double> deficit(horizonte, 0.0);
                int nuevasProposal = 0;
                for (DWBloque* pb : orden) {
                    DWBloque& bn = *pb;
                    auto itL = resLP.lambdas.find(bn.agente);
                    if (itL == resLP.lambdas.end() || itL->second.empty()) continue;
                    const auto& lambda = itL->second;
                    double maxLambda = 0.0;
                    std::vector<double> perfil(horizonte, 0.0);
                    const std::size_t nCols = std::min(lambda.size(), bn.columnas.size());
                    for (std::size_t k = 0; k < nCols; ++k) {
                        maxLambda = std::max(maxLambda, lambda[k]);
                        for (int t = 0; t < horizonte; ++t)
                            perfil[t] += lambda[k] * bn.columnas[k].generacion[t];
                    }
                    double deficitTotal = 0.0;
                    for (int t = 0; t < horizonte; ++t)
                        deficitTotal += std::max(0.0, deficit[t]);
                    if (maxLambda >= 1.0 - 1e-6 && deficitTotal < 1e-6) continue;
                    std::vector<double> objetivoPerfil(horizonte, 0.0);
                    for (int t = 0; t < horizonte; ++t)
                        objetivoPerfil[t] = std::max(0.0, perfil[t] + deficit[t]);
                    acotarTiempo(topeProposal);
                    auto pIni = std::chrono::high_resolution_clock::now();
                    DWColumna prop;
                    bool ok = true;
                    try {
                        prop = resolverValidacionDW(
                            pool.at(bn.agente), resLP.dualDemanda, demanda,
                            objetivoPerfil, muProposal,
                            static_cast<int>(pool.at(bn.agente).columnas.size()));
                    } catch (const std::exception&) {
                        ok = false;
                    }
                    tPricing += segundosDesde(pIni);
                    ++res.pricingSolves;
                    if (!ok) continue;
                    for (int t = 0; t < horizonte; ++t)
                        deficit[t] = objetivoPerfil[t] - prop.generacion[t];
                    agregarColumnaGlobal(pool.at(bn.agente), prop);
                    if (columnaCompatible(nodo, prop) &&
                        bn.firmas.insert(prop.firma).second) {
                        bn.columnas.push_back(prop);
                        ++nuevasProposal;
                        ++res.columnasProposal;
                    }
                }
                std::cout << "[BP] Enriquecimiento raiz ronda " << ronda + 1
                          << " | columnas proposal nuevas=" << nuevasProposal << std::endl;
                if (nuevasProposal == 0) break;
                // Re-resolver el maestro LP: la ronda siguiente y el IP de raíz ven las
                // proposals con λ frescas (con CG cerrada el valor no cambia: las
                // proposals son columnas de costo reducido no negativo).
                actualizarTiempoRestante();
                auto mIni = std::chrono::high_resolution_clock::now();
                bool lpOk = true;
                try {
                    resLP = resolverMaestroRestringidoDW(bloquesNodo, costoFalla,
                                                         demanda, false);
                } catch (const std::exception&) {
                    lpOk = false;
                }
                tMasterLP += segundosDesde(mIni);
                ++res.masterLPSolves;
                if (!lpOk) break;
                zLP = resLP.objetivo;
            }

            // Variante 0 (baseline): maestro entero restringido sobre las columnas de la raíz.
            res.zRaizIP = intentarIncumbenteIP(bloquesNodo, "raiz");

            // Cota dual Lagrangiana de la raíz (subgradiente): ataca el tailing-off de la
            // CG. Maximiza L(u) dualizando las restricciones globales; cada L(u) es cota
            // inferior válida. Usa el incumbente como target de Polyak. Solo SUBE la cota
            // del nodo (max), nunca la baja. Si la relajación es fuerte, cierra la raíz.
            if (configBP.cotaLagrangianaRaiz) {
                const double UBtarget = hayIncumbente ? UB
                                                       : std::numeric_limits<double>::infinity();
                ResultadoCotaDualLagrangiana lag =
                    (configBP.lagMetodo == "bundle")
                        ? resolverCotaDualLagrangianaBundle(ctx, UBtarget, resLP.dualPorRestriccion)
                        : resolverCotaDualLagrangianaRaiz(ctx, UBtarget, resLP.dualPorRestriccion);
                tPricing += lag.tTotal;  // las evaluaciones de L(u) son rondas de pricing
                res.lagActiva = lag.disponible;
                res.lagLBraiz = lag.disponible ? lag.mejorLB : -1.0;
                res.lagIteraciones = lag.iteraciones;
                res.lagRazonParada = lag.razon;
                res.lagCotaCertificada = lag.cotaDualValida;
                res.lagTiempo = lag.tTotal;
                res.lagMetodoUsado = configBP.lagMetodo;
                if (lag.disponible && std::isfinite(lag.mejorLB)) {
                    if (lag.mejorLB > cotaNodo) cotaNodo = lag.mejorLB;
                    mejorLBNodo = std::max(mejorLBNodo, lag.mejorLB);
                    res.zRaizLP = std::max(res.zRaizLP, lag.mejorLB);
                    // Si la cota Lagrangiana usó algún pricing sin ObjBound, no es certificable.
                    if (!lag.cotaDualValida) ++res.pricingTruncadoSinObjBound;
                    std::cout << "[BP] Cota dual Lagrangiana raiz: LB=" << std::setprecision(12)
                              << lag.mejorLB << " iters=" << lag.iteraciones
                              << " razon=" << lag.razon
                              << " gap_vs_UB=" << lag.gapVsUB
                              << " cert=" << (lag.cotaDualValida ? 1 : 0)
                              << " t=" << lag.tTotal << "s" << std::endl;
                }
            }
        }

        // --- Poda por cota ---
        if (hayIncumbente && cotaNodo >= UB - tolPoda()) {
            ++res.nodosPodadosCota;
            peorCotaPodada = std::min(peorCotaPodada, cotaNodo);
            std::cout << "[BP] nodo=" << nodo.id << " prof=" << nodo.profundidad
                      << " estado=podado_cota zLP=" << zLP << " cota=" << cotaNodo
                      << " UB=" << UB << std::endl;
            continue;
        }

        // --- Integralidad y selección de rama ---
        // ȳ_{i,h} = Σ_k λ_ik · y_{i,h}^k reconstruida desde las columnas del nodo.
        int aFrac = -1; std::string varFrac; double fracBin = -1.0, valFrac = 0.0;
        int aLam = -1, kLam = -1; double fracLam = -1.0;
        for (const auto& par : bloquesNodo) {
            const DWBloque& bn = par.second;
            auto itL = resLP.lambdas.find(bn.agente);
            if (itL == resLP.lambdas.end()) continue;
            const auto& lambda = itL->second;
            const std::size_t nCols = std::min(lambda.size(), bn.columnas.size());

            if (reglaBinarias) {
                for (const auto& var : binariasPorBloque[bn.agente]) {
                    double ybar = 0.0;
                    for (std::size_t k = 0; k < nCols; ++k) {
                        auto itv = bn.columnas[k].valoresLocales.find(var);
                        if (itv != bn.columnas[k].valoresLocales.end())
                            ybar += lambda[k] * itv->second;
                    }
                    const double frac = std::min(ybar, 1.0 - ybar);
                    if (frac > epsInt && frac > fracBin) {
                        fracBin = frac; aFrac = bn.agente; varFrac = var; valFrac = ybar;
                    }
                }
            }
            for (std::size_t k = 0; k < nCols; ++k) {
                const double frac = std::min(lambda[k], 1.0 - lambda[k]);
                if (frac > epsInt && frac > fracLam) {
                    fracLam = frac; aLam = bn.agente; kLam = static_cast<int>(k);
                }
            }
        }
        const bool hayBinariaFrac = aFrac >= 0;
        const bool hayLambdaFrac  = aLam >= 0;

        if (!hayBinariaFrac) {
            // Integralidad operativa alcanzada (con regla "lambda" la verificación contra
            // el modelo original cubre también la integralidad de las binarias).
            // Como ȳ_{i,h} entera implica que todas las columnas activas de
            // un agente comparten el valor de cada binaria, y con binarias fijas el resto
            // del conjunto local es un poliedro, la combinación convexa x̂_i = Σ_k λ_ik·x_i^k
            // es localmente factible; las restricciones globales son lineales y el maestro
            // ya las impone. La regla conservadora del diseño exige verificarla contra el
            // modelo compacto antes de aceptarla como incumbente.
            std::map<std::string, double> vals = solucionBase();
            std::vector<double> genTotal(horizonte, 0.0);
            for (const auto& par : bloquesNodo) {
                const DWBloque& bn = par.second;
                auto itL = resLP.lambdas.find(bn.agente);
                if (itL == resLP.lambdas.end()) continue;
                const auto& lambda = itL->second;
                const std::size_t nCols = std::min(lambda.size(), bn.columnas.size());
                for (std::size_t k = 0; k < nCols; ++k) {
                    if (lambda[k] <= 1e-12) continue;
                    for (const auto& val : bn.columnas[k].valoresLocales)
                        vals[val.first] += lambda[k] * val.second;
                    for (int t = 0; t < horizonte; ++t)
                        genTotal[t] += lambda[k] * bn.columnas[k].generacion[t];
                }
            }
            for (const auto& par : resLP.variablesGlobales) vals[par.first] = par.second;
            for (int t = 0; t < horizonte; ++t)
                vals["g(" + std::to_string(t + 1) + ")"] = genTotal[t];

            bool aceptada = false;
            double objCandidato = zLP;
            if (snapshotOriginalDisponible) {
                auto verif = verificarFactibilidadOriginal(vals, false);
                const double maxViol = std::max({verif.maxViolacionMenorIgual,
                                                 verif.maxViolacionMayorIgual,
                                                 verif.maxViolacionIgualdad,
                                                 verif.maxViolacionCotaInf,
                                                 verif.maxViolacionCotaSup,
                                                 verif.maxViolacionIntegridad});
                if (maxViol <= 1e-5) {
                    aceptada = true;
                    objCandidato = verif.objetivoOriginalRecalculado;
                }
            } else {
                // Sin snapshot: aceptar solo el caso trivialmente reconstruible
                // (una única columna por agente con λ ≈ 1).
                aceptada = true;
                for (const auto& par : resLP.lambdas) {
                    double maxLambda = 0.0;
                    for (double l : par.second) maxLambda = std::max(maxLambda, l);
                    if (maxLambda < 1.0 - epsInt) { aceptada = false; break; }
                }
            }

            if (aceptada) {
                registrarIncumbente(objCandidato, std::move(vals), "nodo_lp_integral");
                // La poda por integralidad solo es válida con la CG CERRADA: ahí
                // z_v^LP es la cota del nodo y coincide con el incumbente. Con CG
                // truncada el RMP solo da una cota superior de la relajación del
                // nodo: puede existir una solución mejor en el subárbol, así que el
                // nodo vuelve a la cola con su cota Lagrangiana para continuar.
                if (cerradoExacto) {
                    ++res.nodosPodadosIntegralidad;
                    std::cout << "[BP] nodo=" << nodo.id << " prof=" << nodo.profundidad
                              << " estado=podado_integralidad zLP=" << zLP
                              << " obj=" << objCandidato << std::endl;
                } else if (hayIncumbente && cotaNodo >= UB - tolPoda()) {
                    ++res.nodosPodadosCota;
                    peorCotaPodada = std::min(peorCotaPodada, cotaNodo);
                } else {
                    ++res.nodosReencolados;
                    nodos[idNodo].cota = cotaNodo;
                    abiertos.push({cotaNodo, idNodo});
                    std::cout << "[BP] nodo=" << nodo.id << " prof=" << nodo.profundidad
                              << " estado=reencolado (CG sin cerrar) cota=" << cotaNodo
                              << " UB=" << UB << std::endl;
                }
                continue;
            }
        }

        if (!hayBinariaFrac) {
            // Reconstrucción directa no verificable: el maestro entero del nodo decide.
            // Si su valor alcanza z_v^LP con la CG cerrada, el nodo está resuelto.
            const double zIPNodo = intentarIncumbenteIP(bloquesNodo, "nodo");
            const double tolInt = std::max(1e-6, 1e-9 * std::abs(zLP));
            if (cerradoExacto &&
                !std::isnan(zIPNodo) && !std::isnan(zLP) && zIPNodo <= zLP + tolInt) {
                ++res.nodosPodadosIntegralidad;
                std::cout << "[BP] nodo=" << nodo.id << " prof=" << nodo.profundidad
                          << " estado=podado_integralidad zLP=" << zLP
                          << " zIP=" << zIPNodo << std::endl;
                continue;
            }
            if (hayIncumbente && cotaNodo >= UB - tolPoda()) {
                ++res.nodosPodadosCota;
                peorCotaPodada = std::min(peorCotaPodada, cotaNodo);
                continue;
            }
            if (!hayLambdaFrac || !cerradoExacto) {
                if (cerradoExacto) {
                    // λ esencialmente entera, binarias enteras y CG cerrada: el IP del
                    // nodo ya extrajo lo posible; no queda regla de ramificación.
                    ++res.nodosPodadosIntegralidad;
                    std::cout << "[BP] nodo=" << nodo.id << " prof=" << nodo.profundidad
                              << " estado=podado_sin_rama zLP=" << zLP << std::endl;
                } else {
                    ++res.nodosReencolados;
                    nodos[idNodo].cota = cotaNodo;
                    abiertos.push({cotaNodo, idNodo});
                    std::cout << "[BP] nodo=" << nodo.id << " prof=" << nodo.profundidad
                              << " estado=reencolado (CG sin cerrar) cota=" << cotaNodo
                              << " UB=" << UB << std::endl;
                }
                continue;
            }
        }

        // --- Crear hijos ---
        int hijoA = -1, hijoB = -1;
        if (hayBinariaFrac) {
            ++res.ramificacionesBinarias;
            for (double valor : {0.0, 1.0}) {
                BPNodo hijo;
                hijo.id = static_cast<int>(nodos.size());
                hijo.padre = nodo.id;
                hijo.profundidad = nodo.profundidad + 1;
                hijo.cota = cotaNodo;
                hijo.fijaciones = nodo.fijaciones;
                hijo.columnasProhibidas = nodo.columnasProhibidas;
                hijo.columnaForzada = nodo.columnaForzada;
                hijo.fijaciones.push_back({aFrac, varFrac, valor});
                (valor == 0.0 ? hijoA : hijoB) = hijo.id;
                nodos.push_back(std::move(hijo));
                abiertos.push({cotaNodo, nodos.back().id});
                ++res.nodosCreados;
            }
            std::cout << "[BP] nodo=" << nodo.id << " prof=" << nodo.profundidad
                      << " estado=ramificado_binaria var=" << varFrac
                      << " ybar=" << valFrac << " zLP=" << zLP
                      << " cota=" << cotaNodo << " iters=" << iterNodo
                      << " cols+=" << columnasNodo
                      << (cerradoExacto ? "" : " (heuristico)")
                      << " hijos=" << hijoA << "," << hijoB
                      << " abiertos=" << abiertos.size() << std::endl;
        } else {
            // Regla de diagnóstico: ramificar sobre la λ más fraccionaria.
            ++res.ramificacionesLambda;
            const DWColumna& colRef = bloquesNodo.at(aLam).columnas[kLam];
            BPNodo hijo0;  // λ = 0: columna prohibida
            hijo0.id = static_cast<int>(nodos.size());
            hijo0.padre = nodo.id;
            hijo0.profundidad = nodo.profundidad + 1;
            hijo0.cota = cotaNodo;
            hijo0.fijaciones = nodo.fijaciones;
            hijo0.columnasProhibidas = nodo.columnasProhibidas;
            hijo0.columnaForzada = nodo.columnaForzada;
            hijo0.columnasProhibidas.emplace_back(aLam, colRef.firma);
            hijoA = hijo0.id;
            nodos.push_back(std::move(hijo0));
            abiertos.push({cotaNodo, nodos.back().id});

            BPNodo hijo1;  // λ = 1: columna forzada
            hijo1.id = static_cast<int>(nodos.size());
            hijo1.padre = nodo.id;
            hijo1.profundidad = nodo.profundidad + 1;
            hijo1.cota = cotaNodo;
            hijo1.fijaciones = nodo.fijaciones;
            hijo1.columnasProhibidas = nodo.columnasProhibidas;
            hijo1.columnaForzada = nodo.columnaForzada;
            hijo1.columnaForzada[aLam] = colRef.firma;
            hijoB = hijo1.id;
            nodos.push_back(std::move(hijo1));
            abiertos.push({cotaNodo, nodos.back().id});
            res.nodosCreados += 2;

            std::cout << "[BP] nodo=" << nodo.id << " prof=" << nodo.profundidad
                      << " estado=ramificado_lambda agente=" << aLam
                      << " k=" << kLam << " zLP=" << zLP
                      << " cota=" << cotaNodo << " iters=" << iterNodo
                      << " cols+=" << columnasNodo
                      << (cerradoExacto ? "" : " (heuristico)")
                      << " hijos=" << hijoA << "," << hijoB
                      << " abiertos=" << abiertos.size() << std::endl;
        }

        // Incumbente periódico sobre el pool global (toda columna del pool es una
        // trayectoria local factible: el IP global siempre da soluciones válidas).
        if (configBP.incumbenteCadaNodos > 0 &&
            ++nodosDesdeUltimoIP >= configBP.incumbenteCadaNodos) {
            nodosDesdeUltimoIP = 0;
            intentarIncumbenteIP(pool, "pool");
        }
    }
    dwFijacionesPorBloque.clear();
    dwMetodoMaestroLP = 0;

    if (res.razonParada.empty()) res.razonParada = "arbol_agotado";
    res.nodosAbiertosAlTerminar = static_cast<int>(abiertos.size());

    // --- LB global ---
    // Mínimo entre las cotas de los nodos abiertos y las de los podados por cota
    // (la poda admite tolerancia mipGap·|UB|, así que UB no es LB salvo que no se
    // haya podado nada por cota). Si el árbol se agotó sin podas por cota, LB = UB.
    double lb = menosInf;
    if (abiertos.empty()) {
        lb = std::isfinite(peorCotaPodada) ? peorCotaPodada : UB;
        // Árbol agotado = óptimo, salvo que en modo exacto haya quedado algún pricing puro
        // truncado sin cota dual (entonces la cota no es certificada y no se afirma óptimo).
        if (res.razonParada == "arbol_agotado" &&
            (!modoExacto || res.pricingTruncadoSinObjBound == 0))
            res.razonParada = "optimo";
    } else {
        lb = std::min(abiertos.top().first, peorCotaPodada);
    }
    lb = std::min(lb, UB);

    // --- Incumbente final (último recurso con el presupuesto restante) ---
    if (!hayIncumbente) {
        intentarIncumbenteIP(pool, "final");
    }
    if (!hayIncumbente) {
        throw std::runtime_error(
            "Problema::resolverBranchAndPrice - No se obtuvo ninguna solucion entera factible "
            "(razon de parada: " + res.razonParada + ").");
    }

    // --- Solución final: el mejor incumbente registrado (ya en variables originales) ---
    valoresVariables = mejorSolucion;
    valorFuncionObjetivo = UB;

    // --- Métricas finales ---
    res.ub = UB;
    res.hayIncumbente = true;
    res.lb = std::isfinite(lb) ? lb : UB;
    // Certificación: cota finita, sin pricing fallido ni columnas prohibidas regeneradas,
    // y en modo exacto, sin ninguna pasada pura truncada sin cota dual (ObjBound).
    res.lbCertificada = std::isfinite(lb) &&
                        !huboPricingFallido &&
                        res.columnasIncompatiblesPricing == 0 &&
                        (!modoExacto || res.pricingTruncadoSinObjBound == 0);
    res.gapFinal = std::isfinite(lb)
                       ? std::max(0.0, (UB - lb) / std::max(1.0, std::abs(UB)))
                       : -1.0;
    // Gap CERTIFICADO: solo se reporta si la LB es certificada (cota dual válida).
    res.gapCertificado = res.lbCertificada ? res.gapFinal : -1.0;
    res.columnasTotales = 0;
    for (const auto& par : pool)
        res.columnasTotales += static_cast<int>(par.second.columnas.size());
    res.columnasArbol = res.columnasTotales - res.columnasRaiz;
    res.tMasterLP = tMasterLP;
    res.tPricing  = tPricing;
    res.tMasterIP = tMasterIP;
    res.tTotal    = transcurrido();

    // OPTIMAL solo con cota válida dentro del gap objetivo. En modo exacto, además, la LB
    // debe ser certificada (cota dual sin truncamientos); el gap se mide contra gapObjetivo.
    {
        const double gapRef = modoExacto ? configBP.gapObjetivo : config.mipGap;
        const bool dentroGap = res.gapFinal >= 0.0 && res.gapFinal <= gapRef;
        const bool certOk = !modoExacto || res.lbCertificada;
        estadisticasResolucion.status =
            (certOk && (res.razonParada == "optimo" || dentroGap)) ? "OPTIMAL" : "TIME_LIMIT";
    }
    estadisticasResolucion.gapPct = res.gapFinal >= 0.0 ? 100.0 * res.gapFinal : -1.0;
    estadisticasResolucion.bestBound = res.lb;
    estadisticasResolucion.nodos = res.nodosProcesados;

    std::cout << std::setprecision(12)
              << "[BP-RES] regla=" << res.regla
              << " razon=" << res.razonParada
              << " ub=" << res.ub
              << " lb=" << res.lb
              << " lb_certificada=" << (res.lbCertificada ? 1 : 0)
              << " gap=" << res.gapFinal
              << " gap_certificado=" << res.gapCertificado
              << " z_raiz_lp=" << res.zRaizLP
              << " z_raiz_ip=" << res.zRaizIP
              << " raiz_cerrada=" << (res.raizCerradaExacto ? 1 : 0)
              << std::endl;
    if (res.modoExacto)
        std::cout << "[BP-RES] modo_exacto=1"
                  << " gap_pricing=" << res.gapPricingUsado
                  << " gap_objetivo=" << configBP.gapObjetivo
                  << " nodos_cert_cota_dual=" << res.nodosCertificadosCotaDual
                  << " pricing_truncado_sin_objbound=" << res.pricingTruncadoSinObjBound
                  << std::endl;
    if (res.lagActiva)
        std::cout << "[BP-RES] lag_raiz=1"
                  << " lag_metodo=" << res.lagMetodoUsado
                  << " lag_lb=" << std::setprecision(12) << res.lagLBraiz
                  << " lag_iters=" << res.lagIteraciones
                  << " lag_razon=" << res.lagRazonParada
                  << " lag_cert=" << (res.lagCotaCertificada ? 1 : 0)
                  << " lag_t=" << res.lagTiempo
                  << std::endl;
    std::cout << "[BP-RES] nodos_creados=" << res.nodosCreados
              << " nodos_procesados=" << res.nodosProcesados
              << " podados_cota=" << res.nodosPodadosCota
              << " podados_infactibles=" << res.nodosPodadosInfactibles
              << " podados_integralidad=" << res.nodosPodadosIntegralidad
              << " cerrados_exacto=" << res.nodosCerradosExacto
              << " heuristicos=" << res.nodosHeuristicos
              << " reencolados=" << res.nodosReencolados
              << " abiertos_final=" << res.nodosAbiertosAlTerminar
              << " profundidad_max=" << res.profundidadMax
              << " ramif_binarias=" << res.ramificacionesBinarias
              << " ramif_lambda=" << res.ramificacionesLambda
              << " mejoras_incumbente=" << res.mejorasIncumbente
              << " t_primer_incumbente=" << res.tiempoPrimerIncumbente
              << std::endl;
    std::cout << "[BP-RES] columnas_totales=" << res.columnasTotales
              << " columnas_raiz=" << res.columnasRaiz
              << " columnas_arbol=" << res.columnasArbol
              << " repetidas=" << res.columnasDescartadasRepeticion
              << " incompatibles_pricing=" << res.columnasIncompatiblesPricing
              << " proposal=" << res.columnasProposal
              << " aprendidas=" << res.columnasAprendidas
              << " iter_cg_totales=" << res.iteracionesCGTotales
              << std::endl;
    std::cout << std::setprecision(6)
              << "[BP-RES] t_total=" << res.tTotal
              << " t_raiz=" << res.tRaiz
              << " t_master_lp=" << res.tMasterLP
              << " t_pricing=" << res.tPricing
              << " t_master_ip=" << res.tMasterIP
              << " solves_lp=" << res.masterLPSolves
              << " solves_pricing=" << res.pricingSolves
              << " solves_ip=" << res.masterIPSolves
              << std::endl;

    dwTiempoRestante = 0.0;
    aplicarEscalamientoValoresSolucion();
}
