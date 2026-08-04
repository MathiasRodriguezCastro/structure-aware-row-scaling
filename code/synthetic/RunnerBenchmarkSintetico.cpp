#include "synthetic/RunnerBenchmarkSintetico.h"

#include "SystemController/SystemController.h"
#include "SystemController/Problema/PreprocesamientoMIP/PreprocesamientoMIP.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>

namespace {

// Mapea el nombre de variante del manuscrito a la Config de PreprocesamientoMIP.
// esBase=true significa "sin preprocesamiento" (no se instancia el escalado).
bool mapearVariante(const std::string& nombre, bool& esBase,
                    PreprocesamientoMIP::Config& cfg) {
    cfg = PreprocesamientoMIP::Config{};
    cfg.verbose = false;
    esBase = false;

    if (nombre == "Base") {
        esBase = true;
        return true;
    }
    if (nombre == "SA-Aug") {                  // Estructurado
        cfg.escalamientoLocalPorFila  = true;
        cfg.normalizarBloqueTrasFilas = true;
        cfg.usarEquilibradoRuiz       = false;
        return true;
    }
    if (nombre == "SA-Mat") {                  // Estructurado + modo matricial
        cfg.escalamientoLocalPorFila  = true;
        cfg.normalizarBloqueTrasFilas = true;
        cfg.usarEquilibradoRuiz       = false;
        cfg.modoMatricial             = true;
        return true;
    }
    if (nombre == "Ruiz") {
        cfg.usarEquilibradoRuiz       = true;
        cfg.escalamientoLocalPorFila  = true;
        cfg.normalizarBloqueTrasFilas = true;
        return true;
    }
    if (nombre == "Ruiz+Cols") {
        cfg.usarEquilibradoRuiz       = true;
        cfg.escalamientoLocalPorFila  = true;
        cfg.normalizarBloqueTrasFilas = true;
        cfg.escalarColumnasContinuas  = true;
        cfg.normalizacionFisica       = true;
        return true;
    }
    if (nombre == "Flat") {                    // Control role-blind (= --plano del CLI):
        cfg.escalamientoPlano         = true;  //   mismo kernel por fila sobre TODAS las filas,
        cfg.aplicarEscalamientoLocal  = true;  //   sin metadata de roles ni bloques (un único
        cfg.aplicarEscalamientoGlobal = false; //   bloque autodetectado), sin beta de bloque ni
        cfg.escalamientoLocalPorFila  = true;  //   etapa de acoplamiento ni Ruiz.
        cfg.normalizarBloqueTrasFilas = false;
        cfg.usarEquilibradoRuiz       = false;
        return true;
    }
    if (nombre == "Flat-Mat") {                // Flat role-blind con kernel matrix-only (sin RHS).
        cfg.escalamientoPlano         = true;  //   Mismo kernel que SA-Mat, sin la estructura:
        cfg.aplicarEscalamientoLocal  = true;  //   aisla el efecto de los metadatos (cf. Prop. de
        cfg.aplicarEscalamientoGlobal = false; //   atribucion).
        cfg.escalamientoLocalPorFila  = true;
        cfg.normalizarBloqueTrasFilas = false;
        cfg.usarEquilibradoRuiz       = false;
        cfg.modoMatricial             = true;
        return true;
    }
    if (nombre == "Flat-L2") {                 // Control kernel-matched: role-blind con NORMA EUCLIDEA
        cfg.escalamientoPlano         = true;  //   (1/||a_r||_2), el mismo kernel que SA-Mat aplica en
        cfg.aplicarEscalamientoLocal  = true;  //   las filas de acoplamiento, pero SIN s_i ni beta.
        cfg.aplicarEscalamientoGlobal = false; //   Aisla la NORMA de la metadata de bloque.
        cfg.escalamientoLocalPorFila  = true;
        cfg.normalizarBloqueTrasFilas = false;
        cfg.usarEquilibradoRuiz       = false;
        cfg.modoMatricial             = true;
        cfg.kernelEuclideo            = true;
        return true;
    }
    if (nombre == "SA-Mat-permB") {            // Auditoria: SA-Mat con el mapa de bloques PERMUTADO.
        cfg.escalamientoLocalPorFila  = true;  //   Mismo conjunto de escalas s_i, asignacion barajada.
        cfg.normalizarBloqueTrasFilas = true;  //   Si s_i=1, export byte-identico a SA-Mat.
        cfg.usarEquilibradoRuiz       = false;
        cfg.modoMatricial             = true;
        cfg.permutarBloques           = true;
        return true;
    }
    // Sensibilidad del piso de confiabilidad del γ colectivo: "SA-Aug-floor<val>" corre
    // SA-Aug con pisoMagnitudGammaColectivo = <val> ("SA-Aug-floor0" = piso deshabilitado).
    // Solo para el benchmark sintético (la campaña de sensibilidad usa seeds independientes).
    {
        const std::string pref = "SA-Aug-floor";
        if (nombre.rfind(pref, 0) == 0) {
            cfg.escalamientoLocalPorFila  = true;
            cfg.normalizarBloqueTrasFilas = true;
            cfg.usarEquilibradoRuiz       = false;
            try {
                cfg.pisoMagnitudGammaColectivo = std::stod(nombre.substr(pref.size()));
            } catch (...) { return false; }
            return true;
        }
    }
    // Sensibilidad del umbral de activación de la etapa de acoplamiento:
    // "SA-Aug-rho<val>" corre SA-Aug con umbralRhoEscalamientoGlobal = <val> (la etapa
    // dispara cuando ρ̂ > val). Solo benchmark sintético (donde el umbral discrimina).
    {
        const std::string pref = "SA-Aug-rho";
        if (nombre.rfind(pref, 0) == 0) {
            cfg.escalamientoLocalPorFila  = true;
            cfg.normalizarBloqueTrasFilas = true;
            cfg.usarEquilibradoRuiz       = false;
            try {
                cfg.umbralRhoEscalamientoGlobal = std::stod(nombre.substr(pref.size()));
            } catch (...) { return false; }
            return true;
        }
    }
    return false;
}

// Registra bloques y filas globales/acoplamiento en una pasada de preprocesamiento.
void registrarMetadata(PreprocesamientoMIP& prep, const MetadatosInstancia& meta) {
    for (size_t i = 0; i < meta.prefijosBloque.size(); ++i)
        prep.registrarBloque("bloque" + std::to_string(i + 1), {meta.prefijosBloque[i]});
    prep.registrarRestriccionGlobal(meta.prefijosGlobal);
    prep.registrarRestriccionAcoplamiento(meta.prefijosAcoplamiento);
}

std::string slug(const std::string& s) {
    std::string out;
    for (char c : s) {
        if (c == '+' ) { out += "Cols"; continue; }   // "Ruiz+Cols" -> "RuizCols"
        if (c == '-' || c == ' ') continue;
        out += c;
    }
    return out;
}

std::string sanitizarCSV(const std::string& s) {
    std::string out = s;
    for (char& c : out) {
        if (c == ',' ) c = ';';
        if (c == '\n' || c == '\r') c = ' ';
    }
    return out;
}

std::string fmtDouble(double v) {
    if (std::isnan(v)) return "NA";
    if (std::isinf(v)) return v > 0 ? "inf" : "-inf";
    std::ostringstream ss;
    ss << v;
    return ss.str();
}

void asegurarDirDe(const std::string& ruta) {
    std::filesystem::path p(ruta);
    if (!p.parent_path().empty())
        std::filesystem::create_directories(p.parent_path());
}

std::string tipoFilaAStr(TipoFilaSintetica t) {
    switch (t) {
        case TipoFilaSintetica::Local:        return "local";
        case TipoFilaSintetica::Activacion:   return "activacion";
        case TipoFilaSintetica::Acoplamiento: return "acoplamiento";
    }
    return "?";
}
std::string tipoColAStr(TipoColumnaSintetica t) {
    switch (t) {
        case TipoColumnaSintetica::Continua: return "continua";
        case TipoColumnaSintetica::Binaria:  return "binaria";
        case TipoColumnaSintetica::Slack:    return "slack";
    }
    return "?";
}

// Fila del CSV de métricas.
struct FilaMetrica {
    std::string instancia, variante, status, pattern, coefFamily;
    unsigned int seed = 0;
    int severityS = 0, filas = 0, cols = 0, binarias = 0;
    double kappaAntes = 0, kappaDespues = 0, rhoAntes = 0, rhoDespues = 0;
    double tiempoPreproc = 0, tiempoSolver = 0, wallTime = 0, objetivo = 0;
    bool tieneObjetivo = false;
    // Verificación en escala original (reutiliza Problema::verificarFactibilidadOriginal).
    double maxRowViol = 0, maxIntViol = 0;
    bool   tieneVerif = false;
    bool   factibleOriginal = false;
    // gap / best_bound: sin getter uniforme en los backends → NA por ahora
    // (esquema estable; se poblarán cuando se exponga el bound del solver).
};

void escribirCSVMetricas(const std::string& ruta, const std::vector<FilaMetrica>& filas) {
    asegurarDirDe(ruta);
    std::ofstream out(ruta);
    if (!out.is_open())
        throw std::runtime_error("RunnerBenchmarkSintetico - no se pudo abrir el CSV: " + ruta);
    out << "instancia,variante,seed,pattern,severity_S,coefficient_family,status,"
           "filas,cols,binarias,kappa_antes,kappa_despues,rho_antes,rho_despues,"
           "tiempo_preproc_s,tiempo_solver_s,wall_time_s,objetivo,"
           "gap,best_bound,max_original_row_violation,max_integrality_violation,"
           "is_feasible_original_scale\n";
    for (const auto& f : filas) {
        out << f.instancia << ',' << f.variante << ',' << f.seed << ','
            << f.pattern << ',' << f.severityS << ',' << f.coefFamily << ','
            << sanitizarCSV(f.status) << ','
            << f.filas << ',' << f.cols << ',' << f.binarias << ','
            << fmtDouble(f.kappaAntes) << ',' << fmtDouble(f.kappaDespues) << ','
            << fmtDouble(f.rhoAntes) << ',' << fmtDouble(f.rhoDespues) << ','
            << fmtDouble(f.tiempoPreproc) << ',' << fmtDouble(f.tiempoSolver) << ','
            << fmtDouble(f.wallTime) << ','
            << (f.tieneObjetivo ? fmtDouble(f.objetivo) : "NA") << ','
            << "NA" << ',' << "NA" << ','                          // gap, best_bound (sin getter)
            << (f.tieneVerif ? fmtDouble(f.maxRowViol) : "NA") << ','
            << (f.tieneVerif ? fmtDouble(f.maxIntViol) : "NA") << ','
            << (f.tieneVerif ? (f.factibleOriginal ? "true" : "false") : "NA") << '\n';
    }
}

void escribirRowMetadata(const std::string& ruta, const MetadatosInstancia& meta) {
    asegurarDirDe(ruta);
    std::ofstream out(ruta);
    out << "row_id,row_name,row_type,block_id,rhs,nnz,norm_L2,applied_scale_factor,"
           "synthetic_pattern,severity_S,seed\n";
    const std::string pat = GeneradorBenchmarkSintetico::patronAString(meta.params.patron);
    for (const auto& f : meta.filas) {
        out << f.rowId << ',' << f.nombre << ',' << tipoFilaAStr(f.tipo) << ','
            << f.bloqueId << ',' << fmtDouble(f.rhs) << ',' << f.nnz << ','
            << fmtDouble(f.normaL2) << ',' << fmtDouble(f.appliedScaleFactor) << ','
            << pat << ',' << meta.params.severidadS << ',' << meta.params.seed << '\n';
    }
}

void escribirColumnMetadata(const std::string& ruta, const MetadatosInstancia& meta) {
    asegurarDirDe(ruta);
    std::ofstream out(ruta);
    out << "col_id,col_name,var_type,block_id,lower_bound,upper_bound,objective_coefficient\n";
    for (const auto& c : meta.columnas) {
        out << c.colId << ',' << c.nombre << ',' << tipoColAStr(c.tipo) << ','
            << c.bloqueId << ',' << fmtDouble(c.lowerBound) << ','
            << fmtDouble(c.upperBound) << ',' << fmtDouble(c.objCoef) << '\n';
    }
}

double mediana(std::vector<double> v) {
    if (v.empty()) return std::numeric_limits<double>::quiet_NaN();
    std::sort(v.begin(), v.end());
    size_t n = v.size();
    return (n % 2) ? v[n / 2] : 0.5 * (v[n / 2 - 1] + v[n / 2]);
}

// Resumen agregado por (pattern, S, variant): conteos + medianas.
void escribirSummary(const std::string& ruta, const std::vector<FilaMetrica>& filas,
                     double timeoutSegundos) {
    asegurarDirDe(ruta);
    std::ofstream out(ruta);
    if (!out.is_open())
        throw std::runtime_error("RunnerBenchmarkSintetico - no se pudo abrir el summary: " + ruta);
    out << "pattern,severity_S,variante,n_runs,n_optimos,n_factibles,n_timeouts,"
           "median_kappa_antes,median_kappa_despues,median_rho_antes,median_rho_despues,"
           "median_tiempo_solver_s,median_wall_time_s,"
           "median_max_original_row_violation,median_max_integrality_violation\n";

    // Agrupar preservando un orden estable (pattern, S, variante).
    std::vector<std::string> claves;
    std::map<std::string, std::vector<const FilaMetrica*>> grupos;
    for (const auto& f : filas) {
        std::string clave = f.pattern + "\t" + std::to_string(f.severityS) + "\t" + f.variante;
        if (grupos.find(clave) == grupos.end()) claves.push_back(clave);
        grupos[clave].push_back(&f);
    }

    const double tolTimeout = 0.99 * timeoutSegundos;
    for (const auto& clave : claves) {
        const auto& g = grupos[clave];
        int nRuns = static_cast<int>(g.size());
        int nOpt = 0, nFact = 0, nTimeout = 0;
        std::vector<double> kA, kD, rA, rD, ts, wt, rv, iv;
        for (const FilaMetrica* f : g) {
            bool ok = (f->status == "ok");
            bool timeout = ok && f->tieneObjetivo && f->tiempoSolver >= tolTimeout;
            if (timeout) ++nTimeout;
            else if (ok) ++nOpt;            // proxy: resuelto dentro del límite de tiempo
            if (f->tieneVerif && f->factibleOriginal) ++nFact;
            kA.push_back(f->kappaAntes);   kD.push_back(f->kappaDespues);
            rA.push_back(f->rhoAntes);     rD.push_back(f->rhoDespues);
            if (f->tieneObjetivo) ts.push_back(f->tiempoSolver);
            wt.push_back(f->wallTime);
            if (f->tieneVerif) { rv.push_back(f->maxRowViol); iv.push_back(f->maxIntViol); }
        }
        // clave = pattern \t S \t variante
        std::string pattern = clave.substr(0, clave.find('\t'));
        std::string resto   = clave.substr(clave.find('\t') + 1);
        std::string sStr    = resto.substr(0, resto.find('\t'));
        std::string variante= resto.substr(resto.find('\t') + 1);
        out << pattern << ',' << sStr << ',' << variante << ','
            << nRuns << ',' << nOpt << ',' << nFact << ',' << nTimeout << ','
            << fmtDouble(mediana(kA)) << ',' << fmtDouble(mediana(kD)) << ','
            << fmtDouble(mediana(rA)) << ',' << fmtDouble(mediana(rD)) << ','
            << fmtDouble(mediana(ts)) << ',' << fmtDouble(mediana(wt)) << ','
            << fmtDouble(mediana(rv)) << ',' << fmtDouble(mediana(iv)) << '\n';
    }
}

void escribirManifest(const std::string& ruta, const MetadatosInstancia& meta,
                      const ConfiguracionRunner& cfg, const std::string& instanceId,
                      const std::string& rutaCsv, const std::string& rutaRow,
                      const std::string& rutaCol, const std::string& rutaLp) {
    asegurarDirDe(ruta);
    std::ofstream out(ruta);
    const auto& p = meta.params;
    out << "{\n";
    out << "  \"instancia\": \"" << instanceId << "\",\n";
    out << "  \"seed\": " << p.seed << ",\n";
    out << "  \"num_bloques\": " << p.numBloques << ",\n";
    out << "  \"vars_continuas_por_bloque\": " << p.varsContinuasPorBloque << ",\n";
    out << "  \"vars_binarias_por_bloque\": " << p.varsBinariasPorBloque << ",\n";
    out << "  \"restr_locales_por_bloque\": " << p.restrLocalesPorBloque << ",\n";
    out << "  \"restr_acoplamiento\": " << p.restrAcoplamiento << ",\n";
    out << "  \"pattern\": \"" << GeneradorBenchmarkSintetico::patronAString(p.patron) << "\",\n";
    out << "  \"severity_S\": " << p.severidadS << ",\n";
    out << "  \"coefficient_family\": \""
        << GeneradorBenchmarkSintetico::familiaAString(p.familiaCoef) << "\",\n";
    out << "  \"solver\": \"" << cfg.solver << "\",\n";
    out << "  \"variantes\": [";
    for (size_t i = 0; i < cfg.variantes.size(); ++i)
        out << (i ? ", " : "") << "\"" << cfg.variantes[i] << "\"";
    out << "],\n";
    out << "  \"timeout_s\": " << cfg.solverConfig.timeoutSegundos << ",\n";
    out << "  \"mipgap\": " << cfg.solverConfig.mipGap << ",\n";
    out << "  \"total_filas\": " << meta.filas.size() << ",\n";
    out << "  \"total_columnas\": " << meta.columnas.size() << ",\n";
    out << "  \"rutas\": {\n";
    out << "    \"csv_metricas\": \"" << rutaCsv << "\",\n";
    out << "    \"row_metadata\": \"" << rutaRow << "\",\n";
    out << "    \"column_metadata\": \"" << rutaCol << "\",\n";
    out << "    \"modelo_lp\": \"" << rutaLp << "\"\n";
    out << "  }\n";
    out << "}\n";
}

} // namespace

RunnerBenchmarkSintetico::RunnerBenchmarkSintetico(const ConfiguracionRunner& c) : cfg(c) {}

void RunnerBenchmarkSintetico::ejecutar() {
    if (cfg.variantes.empty())
        throw std::runtime_error("RunnerBenchmarkSintetico - no se especificaron variantes.");
    if (cfg.rutaCsv.empty())
        throw std::runtime_error("RunnerBenchmarkSintetico - falta la ruta del CSV de salida.");

    // Validar nombres de variante de antemano (falla rápido).
    for (const auto& v : cfg.variantes) {
        bool esBase; PreprocesamientoMIP::Config tmp;
        if (!mapearVariante(v, esBase, tmp))
            throw std::runtime_error("RunnerBenchmarkSintetico - variante desconocida: '" + v +
                "'. Válidas: Base, SA-Aug, SA-Mat, Ruiz, Ruiz+Cols, Flat.");
    }

    SystemController& sc = SystemController::getInstance();
    std::vector<FilaMetrica> metricas;
    const bool esDummy = (cfg.solver == "DummyLp");

    // Grilla: barre pattern × S × seeds. Si no se pasaron listas, una sola celda
    // con el (pattern, S) de params.
    const std::vector<PatronDesbalance> patrones = cfg.patrones.empty()
        ? std::vector<PatronDesbalance>{cfg.params.patron} : cfg.patrones;
    const std::vector<int> severidades = cfg.severidades.empty()
        ? std::vector<int>{cfg.params.severidadS} : cfg.severidades;

    for (PatronDesbalance pat : patrones)
    for (int S : severidades)
    for (int idx = 0; idx < cfg.numInstancias; ++idx) {
        ParametrosSinteticos params = cfg.params;
        params.patron     = pat;
        params.severidadS = S;
        params.seed       = cfg.params.seed + static_cast<unsigned int>(idx);

        // ID único por celda: <pattern>_S<S>_seed<seed>.
        const std::string instanceId =
            GeneradorBenchmarkSintetico::patronAString(pat) + "_S" + std::to_string(S) +
            "_seed" + std::to_string(params.seed);

        GeneradorBenchmarkSintetico generador(params);
        MetadatosInstancia metaSalida;   // capturada en la primera variante
        bool metaCapturada = false;

        for (const auto& variante : cfg.variantes) {
            auto wall0 = std::chrono::high_resolution_clock::now();

            bool esBase = false;
            PreprocesamientoMIP::Config cfgVar;
            mapearVariante(variante, esBase, cfgVar);

            // Problema limpio para esta variante.
            sc.limpiar();
            sc.configurarSolver(cfg.solver, cfg.solverConfig);
            Problema* p = sc.getProblema();
            if (!p)
                throw std::runtime_error("RunnerBenchmarkSintetico - configurarSolver no produjo "
                                         "un Problema (¿solver '" + cfg.solver + "' no compilado?).");

            // 1) Construir el MIP sintético (idéntico por seed en cada variante).
            MetadatosInstancia meta = generador.generar(*p);
            if (!metaCapturada) { metaSalida = meta; metaCapturada = true; }

            // El preprocesamiento lo aplicamos nosotros directamente; el pipeline
            // interno queda en 'Ninguno' (no-op) y resolvemos en Monolítica.
            p->habilitarPreprocesamiento("Ninguno");
            p->habilitarEstrategiaResolucion("Monolitica");

            // Snapshot del modelo ORIGINAL (con θ, antes del preprocesamiento) para
            // verificar factibilidad/objetivo en escala original tras resolver.
            p->guardarModeloOriginalParaVerificacion();

            FilaMetrica fm;
            fm.instancia = instanceId;
            fm.variante  = variante;
            fm.seed      = params.seed;
            fm.pattern   = GeneradorBenchmarkSintetico::patronAString(params.patron);
            fm.severityS = params.severidadS;
            fm.coefFamily= GeneradorBenchmarkSintetico::familiaAString(params.familiaCoef);
            fm.filas     = static_cast<int>(meta.filas.size());
            fm.cols      = static_cast<int>(meta.columnas.size());
            fm.binarias  = 0;
            for (const auto& c : meta.columnas)
                if (c.tipo == TipoColumnaSintetica::Binaria) ++fm.binarias;

            // 2) Diagnóstico κ/ρ ANTES (modo diagnóstico, no modifica el modelo).
            {
                PreprocesamientoMIP::Config cfgDiag; cfgDiag.verbose = false;
                PreprocesamientoMIP diag(*p, cfgDiag);
                registrarMetadata(diag, meta);
                diag.diagnosticar();
                fm.kappaAntes = diag.getDiagnosticoGlobal().kappaTotal;
                fm.rhoAntes   = diag.getDiagnosticoGlobal().rhoAprox;
            }

            // 3) Aplicar variante y medir después. Los campos CSV kappa_* conservan
            // el nombre heredado, pero almacenan el proxy max(|A|,|b|)/min+,
            // no el número de condición espectral kappa_2(A).
            if (esBase) {
                fm.kappaDespues = fm.kappaAntes;
                fm.rhoDespues   = fm.rhoAntes;
                fm.tiempoPreproc = 0.0;
            } else {
                PreprocesamientoMIP prep(*p, cfgVar);
                // Flat (role-blind) NO recibe metadata: el punto del control es correr el
                // kernel sin roles ni bloques. Con bloques vacíos, autodetectarBloques()
                // crea el bloque único "plano" con todas las filas (y la verificación de
                // cobertura del modo plano exige exactamente eso).
                if (!cfgVar.escalamientoPlano)
                    registrarMetadata(prep, meta);
                auto t0 = std::chrono::high_resolution_clock::now();
                prep.ejecutar();
                auto t1 = std::chrono::high_resolution_clock::now();
                fm.tiempoPreproc = std::chrono::duration<double>(t1 - t0).count();
                fm.kappaDespues = prep.getDiagnosticoGlobal().kappaTotal;
                fm.rhoDespues   = prep.getDiagnosticoGlobal().rhoAprox;
            }

            // 4) Procesar (traducir al solver) + volcado LP opcional + resolver.
            std::string rutaLp;
            try {
                p->procesar(true);
                if (!cfg.lpDir.empty()) {
                    rutaLp = cfg.lpDir + "/" + instanceId + "_" + slug(variante) + ".lp";
                    asegurarDirDe(rutaLp);
                    p->grabar(rutaLp);
                }
                if (esDummy) {
                    fm.status = "lp-export";
                } else {
                    auto t0 = std::chrono::high_resolution_clock::now();
                    p->resolver();
                    auto t1 = std::chrono::high_resolution_clock::now();
                    fm.tiempoSolver = std::chrono::duration<double>(t1 - t0).count();
                    fm.objetivo = p->getValorFuncionObjetivo();
                    fm.tieneObjetivo = true;
                    fm.status = "ok";

                    // Verificación en escala original: desescala la solución (no-op si
                    // la variante no escaló columnas) y la evalúa contra el snapshot.
                    p->aplicarEscalamientoValoresSolucion();
                    auto verif = p->verificarFactibilidadOriginal(p->getValoresVariables(), true);
                    if (verif.disponible) {
                        fm.maxRowViol = std::max({verif.maxViolacionMenorIgual,
                                                  verif.maxViolacionMayorIgual,
                                                  verif.maxViolacionIgualdad});
                        fm.maxIntViol = verif.maxViolacionIntegridad;
                        const double tolFact = 1e-5;
                        double maxCota = std::max(verif.maxViolacionCotaInf, verif.maxViolacionCotaSup);
                        fm.factibleOriginal = (fm.maxRowViol <= tolFact && maxCota <= tolFact &&
                                               fm.maxIntViol <= tolFact && verif.variablesFaltantes == 0);
                        fm.tieneVerif = true;
                    }
                }
            } catch (const std::exception& e) {
                fm.status = std::string("error: ") + e.what();
            }

            auto wall1 = std::chrono::high_resolution_clock::now();
            fm.wallTime = std::chrono::duration<double>(wall1 - wall0).count();
            metricas.push_back(fm);

            sc.limpiar();
        }

        // Salidas por instancia (opt-in con outDir).
        if (!cfg.outDir.empty() && metaCapturada) {
            const std::string base = cfg.outDir + "/" + instanceId;
            const std::string rutaRow = base + "_row_metadata.csv";
            const std::string rutaCol = base + "_column_metadata.csv";
            const std::string rutaMan = base + "_manifest.json";
            const std::string rutaLpInst =
                cfg.lpDir.empty() ? "" : (cfg.lpDir + "/" + instanceId + "_*.lp");
            escribirRowMetadata(rutaRow, metaSalida);
            escribirColumnMetadata(rutaCol, metaSalida);
            escribirManifest(rutaMan, metaSalida, cfg, instanceId, cfg.rutaCsv,
                             rutaRow, rutaCol, rutaLpInst);
        }
    }

    escribirCSVMetricas(cfg.rutaCsv, metricas);

    if (!cfg.rutaSummary.empty())
        escribirSummary(cfg.rutaSummary, metricas, cfg.solverConfig.timeoutSegundos);

    std::cout << "\033[32m[success] Benchmark sintético: " << metricas.size()
              << " corridas (instancia × variante). CSV: " << cfg.rutaCsv << "\033[0m"
              << std::endl;
    if (!cfg.outDir.empty())
        std::cout << "\033[34m[info] manifest.json + *_metadata.csv en: " << cfg.outDir
                  << "\033[0m" << std::endl;
    if (!cfg.rutaSummary.empty())
        std::cout << "\033[34m[info] resumen agregado en: " << cfg.rutaSummary << "\033[0m" << std::endl;
}
