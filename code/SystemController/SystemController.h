#ifndef SYSTEMCONTROLLER_H
#define SYSTEMCONTROLLER_H

#include <string>
#include <vector>
#include <memory>
#include <fstream>
#include <map>

#include "SystemController/Agentes/Agente.h"
#include "SystemController/Agentes/Demanda/Demandas/DemandaFija.h"
#include "SystemController/Agentes/Generacion/Generadores/RioNegro/RioNegro.h"
#include "SystemController/Agentes/Generacion/Generadores/RioNegro/RioNegroBoneteNoLineal/RioNegroBoneteNoLineal.h"
#include "SystemController/Agentes/Generacion/Generadores/UnidadTermicaRapida/UnidadTermicaRapida.h"
#include "SystemController/Agentes/Generacion/Generadores/UnidadTermicaSimple/UnidadTermicaSimple.h"
#include "SystemController/Agentes/Generacion/Generadores/SaltoGrande/SaltoGrande.h"
#include "SystemController/Despacho/Despacho.h"
#include "SystemController/Despacho/DespachoFijo/DespachoFijo.h"
#include "SystemController/Despacho/DespachoProporcional/DespachoProporcional.h"
#include "SystemController/Despacho/DespachoMercado/DespachoMercado.h"
#include "SystemController/Problema/Problema.h"
#include "SystemController/Problema/ProblemaLp/ProblemaLp.h"
#ifndef NO_GUROBI
#include "SystemController/Problema/ProblemaGurobi/ProblemaGurobi.h"
#endif
#ifndef NO_CBC
#include "SystemController/Problema/ProblemaCbc/ProblemaCbc.h"
#endif
#ifndef NO_CPLEX
#include "SystemController/Problema/ProblemaCplex/ProblemaCplex.h"
#endif
#ifndef NO_HEXALY
#include "SystemController/Problema/ProblemaHexaly/ProblemaHexaly.h"
#endif

#include "SystemController/Problema/SolverConfig.h"

// =============================================================================
// Fachada principal del sistema de despacho eléctrico (Singleton).
//
// CICLO DE VIDA OBLIGATORIO POR CORRIDA
// ──────────────────────────────────────
//   1. inicializar(T)               — define el horizonte temporal
//   2. agregar*(...)                — agrega agentes y despacho
//   3. configurarSolver(tipo, cfg)  — instancia el Problema concreto
//   4. resolver(flagCte, ruta)      — construye, procesa y resuelve monolíticamente
//   5. limpiar()                    — resetea todo para la siguiente corrida
//
// Entre corridas, llamar siempre a limpiar() para evitar estado residual
// (agentes, despacho, solver). El preprocesamiento numérico se aplica en
// Problema::aplicarPreprocesamientoSeleccionado() antes de la resolución.
// =============================================================================
class SystemController {
public:
    // Singleton access
    static SystemController& getInstance();

    // Inicialización del horizonte temporal
    void inicializar(int horizonteTemporal_value);

    // Getters/Setters
    const Despacho* getDespacho() const { return despacho; }
    void setDespacho(Despacho* d) { despacho = d; }

    const Problema* getProblema() const { return problema; }
    Problema*       getProblema()       { return problema; }
    void setProblema(Problema* p) {
        if (problema && problema != p) {
            delete problema;
        }
        problema = p;
        modeloConstruido = false;
        problemaProcesado = false;
    }

    int getHc() const { return horizonteTemporal; }

    // Agregar agentes
    void agregarDemandaFija(const std::vector<double>& demandas);  

    void agregarRioNegro(
        const std::vector<double>& aportesBonete,      
        const std::vector<double>& aportesBaygorria,   
        const std::vector<double>& aportesPalmar,      
        double volumenInicialBonete,
        double volumenInicialPalmar,
        double costoAguaBonete,
        double costoAguaPalmar,
        bool compactar8h = false);

    void agregarRioNegroBoneteNoLineal(
        const std::vector<double>& aportesBonete,
        const std::vector<double>& aportesBaygorria,
        const std::vector<double>& aportesPalmar,
        double volumenInicialBonete,
        double volumenInicialPalmar,
        double costoAguaPalmar,
        std::vector<double> volumenesBonete,
        std::vector<double> valoresBellman,
        std::vector<double> derivadasValoresBellman,
        bool compactar8h = false
    );

    void agregarUnidadTermicaRapida(
        double potenciaMin,
        double potenciaMax,
        double costoFijo,
        double costoVariable,
        double costoEncendido
    );

    void agregarUnidadTermicaSimple(
        double potenciaMax,
        double costoVariable
    );

    void agregarSaltoGrande(
        double costoAguaSalto,
        const std::vector<double> aportesSalto,
        double volumenInicial,
        bool compactar8h = false
    );

    // Métodos de despacho
    void crearDespachoFijo(double costoFalla);
    void crearDespachoProporcional(double proporcion, std::vector<double> demandaTotal);
    void crearDespachoMercado(
        const std::vector<double>& porcentajesTramos,
        const std::vector<double>& costosMarginales,
        const std::vector<double>& demandaTotal = {}
    );
    void grabar(bool flagConstante, std::string& ruta);  
    void resolver(bool flagConstante, std::string& ruta);

    void configurarSolver(const std::string& tipoSolver,
                          const SolverConfig& config = SolverConfig{});
    void prepararModeloParaPreprocesamiento(bool soloDiagnostico = false);

    void relajarVariablesBinarias();

    // Métodos de limpieza
    void limpiar();

    // Manejo de resultados globales
    void iniciarArchivoResultados(const std::string& ruta);
    void registrarResultado(const std::string& idProblema, long tiempoMs, const std::string& archivoSalida,
                           const std::string& t_modelo, const std::string& t_modeloAPI,
                           const std::string& t_resol, const std::string& t_post);
    void cerrarArchivoResultados();
    
    
    double getValorFOOriginal() const { return valorFOOriginal; }
    double getValorFOPostProcesado() const { return valorFOPostProcesado; }
    bool isArchivoResultadosActivo() const { return archivoResultadosActivo; }

    void guardarResultadosCSV(const std::string& ruta, const std::map<std::string, double>& valoresVariables,
                          std::string t_modelo, std::string t_modeloAPI, std::string t_resol, std::string t_post);

    std::string getUltimoTiempoModeloInterno() const { return ultimoTiempoModeloInterno; }
    std::string getUltimoTiempoModeloAPI() const { return ultimoTiempoModeloAPI; }
    std::string getUltimoTiempoResolucion() const { return ultimoTiempoResolucion; }
    std::string getUltimoTiempoPostprocesamiento() const { return ultimoTiempoPostprocesamiento; }

private:
    // Constructor/destructor privados (Singleton)
    SystemController();
    virtual ~SystemController();

    // Eliminar copy/move para seguridad Singleton
    SystemController(const SystemController&) = delete;
    SystemController& operator=(const SystemController&) = delete;
    SystemController(SystemController&&) = delete;
    SystemController& operator=(SystemController&&) = delete;

    // Atributos
    int contadorActualGenerador = 1;
    int contadorActualDemanda = 1;
    int contadorActualAgente = 1;

    std::string ultimoTiempoModeloInterno;
    std::string ultimoTiempoModeloAPI;
    std::string ultimoTiempoResolucion;
    std::string ultimoTiempoPostprocesamiento;

    std::vector<Agente*> agentes;
    Despacho* despacho = nullptr;
    Problema* problema = nullptr;
    bool modeloConstruido = false;
    bool problemaProcesado = false;
    int horizonteTemporal = 0;
    double constanteFuncionObjetivo = 0.0;

    std::ofstream archivoResultados;
    bool archivoResultadosActivo = false;

    double valorFOOriginal = 0.0;
    double valorFOPostProcesado = 0.0;

    // Métodos privados
    void construirModeloSiNecesario();
    void procesarProblemaSiNecesario(bool flagConstante);
    void realizarPostProcesamiento(bool flagConstante);
    double recalcularFuncionObjetivo(const std::map<std::string, double>& valoresVariables, bool flagConstante);
};

#endif // SYSTEMCONTROLLER_ 
