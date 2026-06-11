#include "SystemController.h"
#include "utils.h"
#include <algorithm> 
#include <iomanip>
#include <chrono>
#include <filesystem>
#include <cmath>
#include <sstream>

using namespace std;

// ************** SystemController **************

SystemController::SystemController() {
    horizonteTemporal = 0;
    std::cout << "\033[32m[success] SystemController creado\033[0m" << std::endl; // Verde
}

SystemController::~SystemController() {
    for (Agente* agente : agentes) {
        delete agente;
    }
    if (despacho) delete despacho;
    if (problema) delete problema;
    std::cout << "\033[32m[success] SystemController destruido\033[0m" << std::endl; // Verde
}

SystemController& SystemController::getInstance() {
    static SystemController instance;
    return instance;
}

void SystemController::inicializar(int horizonteTemporal_value) {
    horizonteTemporal = horizonteTemporal_value;
}

// filepath: SystemController.cpp
void SystemController::limpiar() {
    for (Agente* agente : agentes) {
        delete agente;
    }

    agentes.clear(); // este metodo elimina todos los elementos del vector y lo deja vacío

    if (despacho) { 
        delete despacho; 
        despacho = nullptr; 
    }

    if (problema) { 
        delete problema; 
        problema = nullptr; 
    }
    modeloConstruido = false;
    problemaProcesado = false;

    contadorActualAgente = 1;
    contadorActualGenerador = 1;
    contadorActualDemanda = 1;
    horizonteTemporal = 0;

    valorFOOriginal = 0.0;
    valorFOPostProcesado = 0.0;

}

// --- AGREGAR RIO NEGRO ---
void SystemController::agregarRioNegro(
    const std::vector<double>& aportesBonete,           
    const std::vector<double>& aportesBaygorria,        
    const std::vector<double>& aportesPalmar,           
    double volumenInicialBonete, 
    double volumenInicialPalmar,
    double costoAguaBonete, 
    double costoAguaPalmar,
    bool compactar8h)
{
    // Verificar si ya hay un RioNegro
    std::vector<Agente*>::iterator it = std::find_if(agentes.begin(), agentes.end(),
        [](Agente* agente) {
            return dynamic_cast<RioNegro*>(agente) != nullptr;
        });

    if (it != agentes.end()) {
        throw std::runtime_error("SystemController::agregarRioNegro - Ya existe un agente RioNegro en el sistema");
    }

    // Verificar si ya hay un RioNegroBoneteNoLineal
    std::vector<Agente*>::iterator itNoLineal = std::find_if(agentes.begin(), agentes.end(),
        [](Agente* agente) {
            return dynamic_cast<RioNegroBoneteNoLineal*>(agente) != nullptr;
        });

    if (itNoLineal != agentes.end()) {
        throw std::runtime_error("SystemController::agregarRioNegro - Ya existe un agente RioNegroBoneteNoLineal en el sistema. Solo se permite un tipo de Río Negro.");
    }

    // Crear nuevo RioNegro
    RioNegro* rioNegro = new RioNegro(
        contadorActualGenerador,
        contadorActualAgente,
        aportesBonete, 
        aportesBaygorria, 
        aportesPalmar, 
        volumenInicialBonete, 
        volumenInicialPalmar, 
        costoAguaBonete, 
        costoAguaPalmar,
        horizonteTemporal,
        compactar8h
    );
    std::cout << "[info] RioNegro: activación de tramos de altura "
              << (compactar8h ? "compactada cada 8 horas" : "horaria")
              << std::endl;
    agentes.push_back(rioNegro);
    contadorActualGenerador++;
    contadorActualAgente++;
}

// --- UNIDAD TERMICA RAPIDA ---
void SystemController::agregarUnidadTermicaRapida(
    double potenciaMin,
    double potenciaMax,
    double costoFijo,
    double costoVariable,
    double costoEncendido
) {
    UnidadTermicaRapida* unidad = new UnidadTermicaRapida(
        contadorActualAgente,
        contadorActualGenerador,
        horizonteTemporal,
        potenciaMin,
        potenciaMax,
        costoFijo,
        costoVariable,
        costoEncendido
    );
    agentes.push_back(unidad);
    contadorActualGenerador++;
    contadorActualAgente++;
}

void SystemController::agregarUnidadTermicaSimple(
    double potenciaMax,
    double costoVariable
) {
    UnidadTermicaSimple* unidad = new UnidadTermicaSimple(
        contadorActualAgente,
        contadorActualGenerador,
        horizonteTemporal,
        potenciaMax,
        costoVariable
    );

    agentes.push_back(unidad);
    contadorActualGenerador++;
    contadorActualAgente++;
}

void SystemController::agregarSaltoGrande(
    double costoAguaSalto,
    const std::vector<double> aportesSalto,
    double volumenInicial,
    bool compactar8h
) {
    SaltoGrande* sg = new SaltoGrande(
        contadorActualAgente,
        contadorActualGenerador,
        horizonteTemporal,
        costoAguaSalto,
        aportesSalto,
        volumenInicial,
        compactar8h
    );
    agentes.push_back(sg);
    contadorActualGenerador++;
    contadorActualAgente++;
    std::cout << "[info] SaltoGrande: activación de tramos de altura "
              << (compactar8h ? "compactada cada 8 horas" : "horaria")
              << std::endl;
}

// --- AGREGAR RIO NEGRO BONETE NO LINEAL ---
void SystemController::agregarRioNegroBoneteNoLineal(
    const std::vector<double>& aportesBonete,           
    const std::vector<double>& aportesBaygorria,        
    const std::vector<double>& aportesPalmar,           
    double volumenInicialBonete, 
    double volumenInicialPalmar,
    double costoAguaPalmar,
    vector<double> volumenBonete,
    vector<double> valorBellman,
    vector<double> derivadaValorBellman,
    bool compactar8h
)
{
    // Verificar si ya hay un RioNegroBoneteNoLineal
    std::vector<Agente*>::iterator it = std::find_if(agentes.begin(), agentes.end(),
        [](Agente* agente) {
            return dynamic_cast<RioNegroBoneteNoLineal*>(agente) != nullptr;
        });

    if (it != agentes.end()) {
        throw std::runtime_error("SystemController::agregarRioNegroBoneteNoLineal - Ya existe un agente RioNegroBoneteNoLineal en el sistema");
    }

    // Verificar si ya hay un RioNegro
    std::vector<Agente*>::iterator itRioNegro = std::find_if(agentes.begin(), agentes.end(),
        [](Agente* agente) {
            return dynamic_cast<RioNegro*>(agente) != nullptr;
        });

    if (itRioNegro != agentes.end()) {
        throw std::runtime_error("SystemController::agregarRioNegroBoneteNoLineal - Ya existe un agente RioNegro en el sistema. Solo se permite un tipo de Río Negro.");
    }

    // Crear nuevo RioNegroBoneteNoLineal
    RioNegroBoneteNoLineal* rioNegroNL = new RioNegroBoneteNoLineal(
        contadorActualGenerador,
        contadorActualAgente,
        aportesBonete, 
        aportesBaygorria, 
        aportesPalmar, 
        volumenInicialBonete, 
        volumenInicialPalmar, 
        costoAguaPalmar,
        horizonteTemporal,
        volumenBonete,
        valorBellman,
        derivadaValorBellman,
        compactar8h
    );
    std::cout << "[info] RioNegroNoLineal: activación de tramos de altura "
              << (compactar8h ? "compactada cada 8 horas" : "horaria")
              << std::endl;
    agentes.push_back(rioNegroNL);
    contadorActualGenerador++;
    contadorActualAgente++;
}


// --- AGREGAR DEMANDA FIJA ---
void SystemController::agregarDemandaFija(const std::vector<double>& demandas) {
    // Verificar si ya existe una DemandaFija
    std::vector<Agente*>::iterator it = std::find_if(agentes.begin(), agentes.end(),
        [](Agente* agente) {
            return dynamic_cast<DemandaFija*>(agente) != nullptr;
        });

    if (it != agentes.end()) {
        throw std::runtime_error("SystemController::agregarDemandaFija - Ya existe un agente DemandaFija en el sistema");
    }

    // Crear nuevo DemandaFija
    DemandaFija* df = new DemandaFija(
        contadorActualAgente,
        contadorActualDemanda,
        demandas,
        horizonteTemporal
    );
    agentes.push_back(df);
    contadorActualDemanda++;
    contadorActualAgente++;
}


// --- CREAR DESPACHO FIJO ---
void SystemController::crearDespachoFijo(double costoFalla) {
    if (despacho) {
        throw std::runtime_error(
            "SystemController:crearDespachoFijo - Ya existe un despacho creado. No se puede crear otro despacho fijo."
        );
    }

    despacho = new DespachoFijo(horizonteTemporal, costoFalla);
}

void SystemController::crearDespachoProporcional(double proporcion, vector<double> demandaTotal) {
    if (despacho) {
        throw std::runtime_error(
            "SystemController:crearDespachoProporcional - Ya existe un despacho creado. No se puede crear otro despacho fijo."
        );
    }

    if (demandaTotal.size() != static_cast<size_t>(horizonteTemporal)) {
        throw std::runtime_error(
            "SystemController::crearDespachoProporcional - Se debe especificar una demanda total para cada instante de tiempo."
        );
    }

    despacho = new DespachoProporcional(horizonteTemporal, proporcion, demandaTotal);
}

void SystemController::crearDespachoMercado(
    const std::vector<double>& porcentajesTramos,
    const std::vector<double>& costosMarginales,
    const std::vector<double>& demandaTotal
) {
    if (despacho) {
        throw std::runtime_error(
            "SystemController::crearDespachoMercado - Ya existe un despacho creado. No se puede crear otro despacho de mercado."
        );
    }

    if (porcentajesTramos.empty()) {
        throw std::runtime_error(
            "SystemController::crearDespachoMercado - Se debe especificar al menos un tramo."
        );
    }

    if (porcentajesTramos.size() != costosMarginales.size()) {
        throw std::runtime_error(
            "SystemController::crearDespachoMercado - porcentajesTramos y costosMarginales deben tener el mismo tamaño."
        );
    }

    if (!demandaTotal.empty() && demandaTotal.size() != static_cast<size_t>(horizonteTemporal)) {
        throw std::runtime_error(
            "SystemController::crearDespachoMercado - Si se especifica demandaTotal, debe haber un valor para cada instante de tiempo."
        );
    }

    DespachoMercado* nuevoDespacho =
        new DespachoMercado(horizonteTemporal, porcentajesTramos, costosMarginales);

    if (!demandaTotal.empty()) {
        nuevoDespacho->setDemandaTotal(demandaTotal);
    }

    despacho = nuevoDespacho;
}

void SystemController::configurarSolver(const std::string& tipoSolver,
                                        const SolverConfig& config) {
    if (problema) {
        throw std::runtime_error(
            "SystemController::configurarSolver - Ya existe un problema configurado."
        );
    }

    if (tipoSolver == "DummyLp") {
        problema = new ProblemaLp();
    } 
    #ifndef NO_GUROBI
    else if (tipoSolver == "Gurobi") {
        problema = new ProblemaGurobi();
    } 
    #endif
    #ifndef NO_CBC
    else if (tipoSolver == "Cbc") {
        problema = new ProblemaCbc();
    }
    #endif
    #ifndef NO_CPLEX
    else if (tipoSolver == "Cplex") {
        problema = new ProblemaCplex();
    }
    #endif
    #ifndef NO_HEXALY
    else if (tipoSolver == "Hexaly") {
        problema = new ProblemaHexaly();
    }
    #endif
    else {
        throw std::invalid_argument("SystemController::configurarSolver - Tipo de solver desconocido: " + tipoSolver);
    }

    problema->setConfig(config);
    setProblema(problema);
}



void SystemController::construirModeloSiNecesario() {
    if (!problema) {
        throw std::runtime_error(
            "SystemController - No se ha seleccionado ningún solver."
        );
    }

    if (modeloConstruido) {
        return;
    }
    
    if (!despacho) {
        throw std::runtime_error(
            "SystemController - No se ha seleccionado un despacho."
        );
    }

    if (contadorActualGenerador == 1) {
        throw std::runtime_error(
            "SystemController - No se ha creado ningún agente de generación."
        );
    }

    if (contadorActualDemanda == 1) {
        throw std::runtime_error(
            "SystemController - No se ha creado ningún agente de demanda."
        );
    }

    for (Agente* agente : agentes) {
        agente->contribuirAlProblema(problema, horizonteTemporal);
    }

    std::vector<double> demandas(horizonteTemporal, 0.0);

    for (Agente* agente : agentes) {
        Demanda* demanda = dynamic_cast<Demanda*>(agente);
        if (demanda != nullptr) {
            vector<double> demandas_agente = demanda->getDemandas();
            for (size_t t = 0; t < demandas.size() && t < demandas_agente.size(); ++t) {
                demandas[t] += demandas_agente[t];
            }
        }
    }

    std::vector<Generacion*> agentesGen;

    for (Agente* agente : agentes) {
        if (auto* gen = dynamic_cast<Generacion*>(agente)) {
            agentesGen.push_back(gen);
        }
    }

    despacho->contribuirAlProblema(problema, agentesGen, demandas);
    modeloConstruido = true;
}

void SystemController::procesarProblemaSiNecesario(bool flagConstante) {
    construirModeloSiNecesario();
    if (problemaProcesado) {
        return;
    }
    problema->aplicarPreprocesamientoSeleccionado();
    problema->procesar(flagConstante);
    problemaProcesado = true;
}

void SystemController::prepararModeloParaPreprocesamiento(bool soloDiagnostico) {
    if (problemaProcesado && !soloDiagnostico) {
        throw std::runtime_error(
            "SystemController::prepararModeloParaPreprocesamiento - El problema ya fue procesado. "
            "Ejecute preprocesar antes de grabar o resolver."
        );
    }
    construirModeloSiNecesario();
}

void SystemController::grabar(bool flagConstante, std::string& ruta) {
    if (!problema) {
        throw std::runtime_error(
            "SystemController::grabar - No se ha seleccionado ningún solver. No se puede grabar el problema."
        );
    }

    std::filesystem::path rutaModelo(ruta);
    if (!rutaModelo.parent_path().empty()) {
        std::filesystem::create_directories(rutaModelo.parent_path());
    }

    procesarProblemaSiNecesario(flagConstante);
    problema->grabar(ruta);
}


string quitarSufijoParentesis(const std::string& s) {
    size_t pos = s.find('('); // busca el primer '('
    if (pos != std::string::npos) {
        return s.substr(0, pos); // devuelve todo antes del '('
    }
    return s; // si no hay '(', devuelve la cadena original
}

void quitarNombre(std::vector<std::string>& vec, const std::string& nombre) {
    vec.erase(
        std::remove(vec.begin(), vec.end(), nombre), // std::string coincide con el vector
        vec.end()
    );
}

void SystemController::resolver(bool flagConstante, std::string& ruta) {  
    if (!problema) {
        throw std::runtime_error(
            "SystemController::resolver - No se ha seleccionado ningún solver. No se puede resolver el problema."
        );
    }

    if (!despacho) {
        throw std::runtime_error(
            "SystemController::resolver - No se ha seleccionado un despacho."
        );
    }

    if (contadorActualGenerador == 1) {
        throw std::runtime_error(
            "SystemController::resolver - No se ha creado ningún agente de generación."
        );
    }

    if (contadorActualDemanda == 1) {
        throw std::runtime_error(
            "SystemController::resolver - No se ha creado ningún agente de demanda."
        );
    }

    std::chrono::high_resolution_clock::time_point inicioModeloInterno = std::chrono::high_resolution_clock::now(); // Inicio de tiempo de generación del modelo interno
    construirModeloSiNecesario();
    std::chrono::high_resolution_clock::time_point finModeloInterno = std::chrono::high_resolution_clock::now(); // Fin de tiempo de generación del modelo interno
    std::chrono::duration<double> duracionModeloInterno = finModeloInterno - inicioModeloInterno;
    std::string duracionModeloInternoString = std::to_string(duracionModeloInterno.count());

    // Tamaño ORIGINAL del modelo (solver-agnóstico): el solver reporta el tamaño PRESOLVED en
    // su log; con este conteo el parser calcula la reducción de nonzeros también para CPLEX.
    {
        long rows = static_cast<long>(problema->getRestricciones().size());
        long cols = static_cast<long>(problema->getVariables().size()
                                      + problema->getBinarios().size());
        long nnz = 0;
        for (auto* r : problema->getRestricciones())
            if (r) nnz += static_cast<long>(r->getTerminos().size());
        std::cout << "[MODELO] rows=" << rows << " cols=" << cols << " nnz=" << nnz << std::endl;
    }

    // 2. Procesar y resolver el problema
    std::chrono::high_resolution_clock::time_point inicioModeloAPI = std::chrono::high_resolution_clock::now(); // Inicio de modelo interno a modelo de la API
    procesarProblemaSiNecesario(flagConstante);    // TIEMPO 2 (HASTA ACÁ)
    std::chrono::high_resolution_clock::time_point finModeloAPI = std::chrono::high_resolution_clock::now(); // Fin de modelo interno a modelo de la API
    std::chrono::duration<double> duracionModeloAPI = finModeloAPI - inicioModeloAPI;
    std::string duracionModeloAPIString = std::to_string(duracionModeloAPI.count());

    // TIEMPO 3 (DE ACÁ)
    std::chrono::high_resolution_clock::time_point inicioResolucion = std::chrono::high_resolution_clock::now(); // Inicio de resolución
    problema->resolver();
    std::chrono::high_resolution_clock::time_point finResolucion = std::chrono::high_resolution_clock::now(); // Fin de resolución
    std::chrono::duration<double> duracionResolucion = finResolucion - inicioResolucion;
    std::string duracionResolucionString = std::to_string(duracionResolucion.count());

    // Marcador SOLVER-AGNÓSTICO con el tiempo de solver medido aquí y las estadísticas que
    // pobló el backend (status/gap/nodos/iter/integral primal). Reemplaza la dependencia del
    // formato de log de cada solver: el parser lo lee igual para Gurobi y CPLEX.
    {
        const auto& est = problema->getEstadisticasResolucion();
        // obj con alta precisión: es el incumbente contra el que se chequea la equivalencia
        // (|obj recomputado − incumbente| < 1e-3); 6 cifras no alcanzan.
        std::cout << std::setprecision(15)
                  << "[SOLVE] tiempo_solver_s=" << duracionResolucion.count()
                  << " status=" << est.status
                  << " gap=" << est.gapPct
                  << " obj=" << problema->getValorFuncionObjetivo()
                  << " best_bound=" << est.bestBound
                  << " nodos=" << est.nodos
                  << " iter=" << est.iteraciones
                  << " primal_integral=" << est.integralPrimal << std::endl;
    }

    // TIEMPO 3 (HASTA ACÁ)
    
    valorFOOriginal = problema->getValorFuncionObjetivo();
    valorFOPostProcesado = valorFOOriginal;

    map<string, double> valoresVariables = problema->getValoresVariables();
    if (problema->getVerificarModeloOriginalActivo()) {
        problema->imprimirVerificacionFactibilidadOriginal("solver_desescalado", valoresVariables, flagConstante);
    }

    // 3. Validar ruta de salida
    if (ruta.size() < 4 || ruta.substr(ruta.size() - 4) != ".csv") {
        throw std::invalid_argument("SystemController::resolver - La ruta debe terminar en '.csv'. Ruta proporcionada: " + ruta);
    }

    std::filesystem::path rutaCsv(ruta);
    if (!rutaCsv.parent_path().empty()) {
        std::filesystem::create_directories(rutaCsv.parent_path());
    }

    ofstream archivo(ruta);
    if (!archivo.is_open()) {
        throw std::runtime_error("SystemController::resolver - No se pudo abrir el archivo CSV en la ruta: " + ruta);
    }

    guardarResultadosCSV(ruta, valoresVariables, duracionModeloInternoString, duracionModeloAPIString,duracionResolucionString, "N/A");

    archivo.close();
    std::cout << "\033[32m[success] Archivo CSV generado correctamente\033[0m" << std::endl;

    // 7. Post-procesamiento
    std::chrono::high_resolution_clock::time_point inicioPostprocesamiento = std::chrono::high_resolution_clock::now(); // Inicio de postprocesamiento
    realizarPostProcesamiento(flagConstante);
    std::chrono::high_resolution_clock::time_point finPostprocesamiento = std::chrono::high_resolution_clock::now(); // Fin de postprocesamiento
    std::chrono::duration<double> duracionPostprocesamiento = finPostprocesamiento - inicioPostprocesamiento;
    std::string duracionPostprocesamientoString = std::to_string(duracionPostprocesamiento.count());


    // Guardar resultados post-procesados en un nuevo archivo CSV
    // IMPORTANTE: volver a pedir los valores después del postprocesamiento.
    map<string, double> valoresVariablesPost = problema->getValoresVariables();
    if (problema->getVerificarModeloOriginalActivo()) {
        problema->imprimirVerificacionFactibilidadOriginal("postprocesado", valoresVariablesPost, flagConstante);
    }

    size_t pos = ruta.rfind(".csv");
    if (pos != std::string::npos) {
        ruta.insert(pos, "_postprocesado");
    } else {
        ruta += "_postprocesado";
    }

    guardarResultadosCSV(
        ruta,
        valoresVariablesPost,
        duracionModeloInternoString,
        duracionModeloAPIString,
        duracionResolucionString,
        duracionPostprocesamientoString
    );

    ultimoTiempoModeloInterno = duracionModeloInternoString;
    ultimoTiempoModeloAPI = duracionModeloAPIString;
    ultimoTiempoResolucion = duracionResolucionString;
    ultimoTiempoPostprocesamiento = duracionPostprocesamientoString;
}

void SystemController::guardarResultadosCSV(const string& ruta, const map<string, double>& valoresVariables, string t_modelo, string t_modeloAPI, string t_resol, string t_post) {
    if (!problema) {
        throw std::runtime_error(
            "SystemController::guardarResultados - No se ha seleccionado ningún solver. No se pueden guardar los resultados."
        );
    }

    std::filesystem::path rutaCsv(ruta);
    if (!rutaCsv.parent_path().empty()) {
        std::filesystem::create_directories(rutaCsv.parent_path());
    }

    ofstream archivo(ruta);
    if (!archivo.is_open()) {
        throw std::runtime_error("SystemController::guardarResultados - No se pudo abrir el archivo de resultados en la ruta: " + ruta);
    }

    archivo << "Valor de la función objetivo original: " << valorFOOriginal << "\n";
    archivo << "Valor de la función objetivo post-procesado: " << valorFOPostProcesado << "\n";
    archivo << "\n";
    archivo << "-- Tiempos de Ejecución --\n";
    archivo << "Tiempo generación modelo interno (s): " << t_modelo << "\n";
    archivo << "Tiempo procesamiento modelo API (s): " << t_modeloAPI << "\n";
    archivo << "Tiempo resolución (s): " << t_resol << "\n";
    archivo << "Tiempo post-procesamiento (s): " << t_post << "\n";
    archivo << "\n";
    std::cout << "\033[32m[success] Resultados guardados correctamente en " << ruta << "\033[0m" << std::endl;


    // Variables de los agentes
    for (Agente* agente : agentes) {
        archivo << "-- " << agente->getNombre() << " --\n";
        archivo << "- Variables -\n";
        vector<string> varAsociadasAgente = agente->getNombresVariables();
        for (const string& nombre : varAsociadasAgente) {
            for (int i = 1; i <= horizonteTemporal; i++) {
                string nombre_parametrizado = nombre + "(" + to_string(i) + ")";
                auto it = valoresVariables.find(nombre_parametrizado);
                if (it != valoresVariables.end()) {
                    archivo << nombre_parametrizado << " = " << it->second << "\n";
                } else {
                    archivo << nombre_parametrizado << " no tiene valor asignado\n";
                }
            }
        }
        archivo << "\n";
    }

    // Variables del despacho
    if (despacho) {
        archivo << "-- Despacho --\n";
        archivo << "- Variables -\n";
        vector<string> varAsociadasDespacho = despacho->getNombresVariables();
        for (const string& nombre : varAsociadasDespacho) {
            for (int i = 1; i <= horizonteTemporal; i++) {
                string nombre_parametrizado = nombre + "(" + to_string(i) + ")";
                auto it = valoresVariables.find(nombre_parametrizado);
                if (it != valoresVariables.end()) {
                    archivo << nombre_parametrizado << " = " << it->second << "\n";
                } else {
                    archivo << nombre_parametrizado << " no tiene valor asignado\n";
                }
            }
        }
    }
    archivo.close();
}

void SystemController::realizarPostProcesamiento(bool flagConstante) {
    if (!problema) {
        throw std::runtime_error(
            "SystemController::realizarPostProcesamiento - No hay problema definido para el post-procesamiento. Asegúrese de configurar un solver antes."
        );
    }

    if ((problema->getValoresVariables()).empty()) {
        throw std::runtime_error(
            "SystemController::realizarPostProcesamiento - No se encontraron valores de variables del problema. El solver podría no haber sido ejecutado correctamente."
        );
    }

    auto sumarBase = [&](const std::map<std::string, double>& valores,
                         const std::string& base) -> double {
        double suma = 0.0;

        for (int i = 1; i <= horizonteTemporal; i++) {
            std::string nombre = base + "(" + std::to_string(i) + ")";
            auto it = valores.find(nombre);
            if (it != valores.end()) {
                suma += it->second;
            }
        }

        return suma;
    };

    auto imprimir = [&](const std::string& etapa,
                        const std::map<std::string, double>& antes,
                        const std::map<std::string, double>& despues,
                        const std::string& base) {
        double a = sumarBase(antes, base);
        double d = sumarBase(despues, base);

        std::cerr << std::setprecision(15)
                  << "[POST DEBUG] " << etapa << " | "
                  << base
                  << " antes=" << a
                  << " despues=" << d
                  << " delta=" << (d - a)
                  << std::endl;
    };

    std::cerr << "\n[POST DEBUG] ===== INICIO POSTPROCESAMIENTO GLOBAL =====\n";

    std::map<std::string, double> valoresAntes = problema->getValoresVariables();

    // 1) Postprocesamiento de agentes
    for (Agente* agente : agentes) {
        if (!agente) {
            throw std::runtime_error(
                "SystemController::realizarPostProcesamiento - Se encontró un puntero nulo en la lista de agentes durante el post-procesamiento."
            );
        }

        agente->posprocesamiento(problema);
    }

    std::map<std::string, double> valoresDespuesAgentes = problema->getValoresVariables();

    std::cerr << "[POST DEBUG] --- DESPUÉS DE AGENTES ---\n";

    imprimir("Agentes", valoresAntes, valoresDespuesAgentes, "g1");
    imprimir("Agentes", valoresAntes, valoresDespuesAgentes, "g2");
    imprimir("Agentes", valoresAntes, valoresDespuesAgentes, "g");
    imprimir("Agentes", valoresAntes, valoresDespuesAgentes, "costoFalla");

    // 2) Generadores
    std::vector<Generacion*> agentesGen;

    for (Agente* agente : agentes) {
        if (auto* gen = dynamic_cast<Generacion*>(agente)) {
            agentesGen.push_back(gen);
        }
    }

    // 3) Postprocesamiento del despacho
    despacho->posprocesamiento(problema, agentesGen);

    std::map<std::string, double> valoresDespuesDespacho = problema->getValoresVariables();

    std::cerr << "[POST DEBUG] --- DESPUÉS DE DESPACHO ---\n";

    imprimir("Despacho", valoresDespuesAgentes, valoresDespuesDespacho, "g1");
    imprimir("Despacho", valoresDespuesAgentes, valoresDespuesDespacho, "g2");
    imprimir("Despacho", valoresDespuesAgentes, valoresDespuesDespacho, "g");
    imprimir("Despacho", valoresDespuesAgentes, valoresDespuesDespacho, "costoFalla");

    std::cerr << "[POST DEBUG] --- TOTAL ANTES VS FINAL ---\n";

    imprimir("Final", valoresAntes, valoresDespuesDespacho, "g1");
    imprimir("Final", valoresAntes, valoresDespuesDespacho, "g2");
    imprimir("Final", valoresAntes, valoresDespuesDespacho, "g");
    imprimir("Final", valoresAntes, valoresDespuesDespacho, "costoFalla");

    double nuevoValorFO = recalcularFuncionObjetivo(valoresDespuesDespacho, flagConstante);

    valorFOPostProcesado = nuevoValorFO;

    std::cerr << std::setprecision(15)
              << "[POST DEBUG] valorFOOriginal = " << valorFOOriginal << "\n"
              << "[POST DEBUG] valorFOPostProcesado = " << valorFOPostProcesado << "\n"
              << "[POST DEBUG] deltaFO = " << (valorFOPostProcesado - valorFOOriginal) << "\n";

    std::cerr << "[POST DEBUG] ===== FIN POSTPROCESAMIENTO GLOBAL =====\n\n";

    std::cout << "\033[32m[success] Post-procesamiento completado. Nuevo valor F.O.: "
              << nuevoValorFO << "\033[0m" << std::endl;
}

double SystemController::recalcularFuncionObjetivo(const std::map<std::string, double>& valoresVariables, bool flagConstante) {
    if (!problema) {
        throw std::runtime_error(
            "SystemController::recalcularFuncionObjetivo - No hay problema definido para recalcular la función objetivo. Asegúrese de configurar un solver antes."
        );
    }

    double valorFO = 0.0;

    // Recuperar los pares (coeficiente, variable) de la función objetivo
    std::vector<std::pair<double, std::string>> terminos = problema->getParesTerminosFuncionObjetivo();
    
    if (terminos.empty()) {
        throw std::runtime_error("SystemController::recalcularFuncionObjetivo - La función objetivo no contiene términos definidos.");
    }

    // Calcular la contribución de cada término usando los valores actualizados
    for (std::vector<std::pair<double, std::string>>::const_iterator it = terminos.begin(); it != terminos.end(); ++it) {
        const double& coeficiente = it->first;
        const std::string& variable = it->second;
        
        std::map<std::string, double>::const_iterator varIt = valoresVariables.find(variable);
        if (varIt != valoresVariables.end()) {
            double escalaOriginalPorInterna = problema->getFactorOriginalPorInterna(variable);
            valorFO += (coeficiente / escalaOriginalPorInterna) * varIt->second;
        } else {
            std::cerr << "\033[33m[warning] Término no encontrado en valoresVariables: " << variable << "\033[0m" << std::endl;
        }
    }

    // Sumar la constante de la función objetivo si corresponde
    if (flagConstante) {
        valorFO += problema->getConstanteFuncionObjetivo();
    }

    return valorFO;
}

// Inicia un archivo de resultados globales con cabecera CSV
void SystemController::iniciarArchivoResultados(const std::string& ruta) {
    if (archivoResultadosActivo) {
        cerrarArchivoResultados();
    }
    std::filesystem::path rutaResultados(ruta);
    if (!rutaResultados.parent_path().empty()) {
        std::filesystem::create_directories(rutaResultados.parent_path());
    }
    archivoResultados.open(ruta);
    archivoResultadosActivo = archivoResultados.is_open();
    if (archivoResultadosActivo) {
        // Nueva cabecera con tiempos
        archivoResultados << "id_problema,valor_fo_original,valor_fo_postprocesado,tiempo_ms,archivo_salida,tiempo_modelo_interno_s,tiempo_modelo_api_s,tiempo_resolucion_s,tiempo_postprocesamiento_s\n";
    } else {
        std::cerr << "[error] No se pudo abrir el archivo de resultados: " << ruta << std::endl;
    }
}

// Registra el resultado de un problema resuelto
void SystemController::registrarResultado(const std::string& idProblema, long tiempoMs, const std::string& archivoSalida,
                                          const std::string& t_modelo, const std::string& t_modeloAPI,
                                          const std::string& t_resol, const std::string& t_post) {
    if (!archivoResultadosActivo || !problema) {
        return;
    }
    
    double valorFO_orig = valorFOOriginal;
    double valorFO_post = valorFOPostProcesado;
    
    archivoResultados << std::fixed << std::setprecision(12);
    archivoResultados << idProblema << ","
                      << valorFO_orig << ","      
                      << valorFO_post << ","      
                      << tiempoMs << ","; 
    archivoResultados << std::setw(0) << archivoSalida << ",";
    // Agrega los tiempos
    archivoResultados << t_modelo << ","
                      << t_modeloAPI << ","
                      << t_resol << ","
                      << t_post << "\n";
    archivoResultados << std::defaultfloat; 
    archivoResultados.flush();
}

// Cierra el archivo de resultados
void SystemController::cerrarArchivoResultados() {
    if (archivoResultadosActivo) {
        archivoResultados.close();
        archivoResultadosActivo = false;
    }
}

void SystemController::relajarVariablesBinarias() {
    if (problema == nullptr) {
        throw std::runtime_error(
            "SystemController::relajarVariablesBinarias - No hay problema configurado."
        );
    }

    problema->transformarVariablesAReales();
}

// =============================================================================
// Red neuronal
// =============================================================================
