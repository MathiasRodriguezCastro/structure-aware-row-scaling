// ============================================================================
//  1_SistemaElectrico.cpp — Interprete de scripts de instancia
// ----------------------------------------------------------------------------
//  Lee comandos por stdin (o desde un archivo via 'ejecutarPruebas') y arma,
//  resuelve y exporta un modelo de despacho electrico a traves de
//  SystemController. Los valores numericos aceptan coma o punto decimal.
//
//  Gramatica de comandos (el orden importa; ver el README del repositorio):
//
//    Antes de inicializar:
//      inicializar [--t] <horizonteTemporal>
//      ejecutarPruebas <ruta_script.txt>
//      salir
//
//    Tras inicializar (cada 'agregarAgente'/'crearDespacho' lee sus
//    parametros de las lineas siguientes):
//      agregarAgente --RioNegro [--c8] | --RioNegroNoLineal [--c8]
//      agregarAgente --UnidadTermicaRapida | --UnidadTermicaSimple
//      agregarAgente --DemandaFija | --SaltoGrande [--c8]
//      crearDespacho --fija | --proporcional | --mercado [--conDemandaTotal]
//      configurarSolver --DummyLp|--Gurobi|--Cbc|--Cplex|--Hexaly
//                       [--timeout <seg>] [--mipgap <val>]
//      relajarVariablesBinarias
//      habilitarEstrategiaResolucion Monolitica
//      habilitarPreprocesamiento <variante>
//      preprocesar [flags...]   (ver bloque 'preprocesar' mas abajo)
//      grabar <ruta> [--noConstante]
//      resolver [--noConstante] <ruta.csv>
//      finalizar                (limpia para reusar el proceso)
//      salir
// ============================================================================

#include <string>
#include <sstream>
#include <iomanip>
#include <vector>
#include <iostream>
#include <fstream>
#include <stdexcept>
#include <algorithm>
#include <chrono>
#include <filesystem>

using namespace std;

#include "SystemController/SystemController.h"
#include "SystemController/Problema/SolverConfig.h"
#include "SystemController/Problema/PreprocesamientoMIP/PreprocesamientoMIP.h"
#include "synthetic/ComandoBenchmarkSintetico.h"


// Flag Global para salir
bool g_salir = false;

// Función para dividir la línea de entrada en tokens
vector<string> split(const string& str) {
    vector<string> tokens;
    istringstream iss(str);
    string token;
    while (iss >> token) {
        tokens.push_back(token);
    }
    return tokens;
}

string limpiarTokenNumerico(string token) {
    // Si usás coma decimal, la convierte a punto decimal
    for (char& c : token) {
        if (c == ',') c = '.';
    }
    return token;
}

// Imprime un mensaje de error en rojo a stderr (formato uniforme del CLI).
void printError(const string& msg) {
    cerr << "\033[31m[error] " << msg << "\033[0m" << endl;
}

bool parseDoubleStrict(const string& tokenOriginal, double& valor, const string& contexto = "") {
    string token = limpiarTokenNumerico(tokenOriginal);

    try {
        size_t pos = 0;
        valor = stod(token, &pos);

        // Verifica que stod haya consumido todo el token
        if (pos != token.size()) {
            printError((contexto.empty() ? "Token numérico" : contexto)
                       + " parcialmente leído: '" + tokenOriginal + "'");
            return false;
        }

        return true;
    } catch (...) {
        printError((contexto.empty() ? "Valor" : contexto)
                   + " no es un número válido: '" + tokenOriginal + "'");
        return false;
    }
}

// Lee una línea de `in` y la interpreta como un único escalar (acepta coma
// decimal). Imprime un error contextualizado y devuelve false si falta la
// línea o el valor no es numérico.
bool leerEscalarDesde(istream& in, const string& campo, double& valor) {
    string linea;
    if (!getline(in, linea)) { printError("Falta " + campo); return false; }
    istringstream iss(linea);
    string token;
    if (!(iss >> token)) { printError("Falta " + campo); return false; }
    return parseDoubleStrict(token, valor, campo);
}

// Variante para enteros estrictamente positivos.
bool leerEnteroPositivoDesde(istream& in, const string& campo, int& valor) {
    string linea;
    if (!getline(in, linea)) { printError("Falta " + campo); return false; }
    try {
        size_t pos = 0;
        valor = stoi(linea, &pos);
        if (valor <= 0) { printError(campo + " debe ser un entero positivo"); return false; }
        return true;
    } catch (...) {
        printError(campo + " inválido");
        return false;
    }
}

bool parseNDoublesFromLine(const string& line, int n, vector<double>& out) {
    out.clear();

    istringstream iss(line);
    string token;

    while (iss >> token) {
        // Permitir comentarios al final de línea
        if (!token.empty() && token[0] == '#') {
            break;
        }

        if ((int)out.size() >= n) {
            cerr << "[error] La línea tiene más valores que los esperados. "
                 << "Esperados: " << n << ". Token extra: "
                 << token << endl;
            return false;
        }

        double valor;
        if (!parseDoubleStrict(token, valor)) {
            return false;
        }

        out.push_back(valor);
    }

    if ((int)out.size() != n) {
        cerr << "[error] Cantidad incorrecta de valores. Esperados: "
             << n << ", leídos: " << out.size() << endl;
        return false;
    }

    return true;
}

// Normaliza una flag de solver tipo "--gurobi" -> "Gurobi": quita los guiones
// iniciales y matchea de forma case-insensitive contra los nombres canónicos.
// Si no reconoce el nombre lo devuelve sin guiones (el caller reporta el error).
string normalizeSolverFlag(const string& raw) {
    string s = raw;
    while (!s.empty() && s.front() == '-') s.erase(0, 1);

    string lower = s;
    transform(lower.begin(), lower.end(), lower.begin(),
              [](unsigned char c){ return tolower(c); });

    static const std::vector<std::string> canonicos =
        {"DummyLp", "Gurobi", "Cbc", "Cplex", "Hexaly"};
    for (const auto& canon : canonicos) {
        string canonLower = canon;
        transform(canonLower.begin(), canonLower.end(), canonLower.begin(),
                  [](unsigned char c){ return tolower(c); });
        if (lower == canonLower) return canon;
    }
    return s; // no reconocido: se devuelve sin guiones para el mensaje de error
}

// Procesar comando leyendo desde un istream (por defecto cin).
void procesarComando(bool& inicializado,const vector<string>& args, SystemController& systemController, istream& in = cin) {
    string linea;
    if (g_salir) return; // cada llamada verifica si ya se pidió salir
    if (args.empty()) return; // seguridad

    if(!inicializado){
        if (args[0] == "inicializar") {
            if ((args.size() == 3 && args[1] == "--t") || (args.size() == 2)) {
                try {
                    if(!inicializado){
                        int horizonteTemporal_value;
                        if (args.size() == 3) horizonteTemporal_value = stoi(args[2]);
                        else horizonteTemporal_value = stoi(args[1]);
                        if (horizonteTemporal_value <= 0) {
                            std::cerr << "\033[31m[error] El horizonte temporal debe ser un entero positivo\033[0m" << std::endl;
                            return;
                        }
                        systemController.inicializar(horizonteTemporal_value);
                        inicializado = true;
                        std::cout << "\033[32m[success] El programa se ha iniciado correctamente\033[0m" << std::endl;
                    }
                    
                } catch (const exception&) {
                    std::cerr << "\033[31m[error] Valor no numérico en inicializar\033[0m" << std::endl;
                }
            } else {
                std::cout << "\033[34m[info] Uso: inicializar --t <horizonteTemporal>\033[0m" << std::endl;
            }
        } else if (args[0] == "salir") {
            // Cerrar el archivo de resultados si quedó abierto.
            if (systemController.isArchivoResultadosActivo()) {
                systemController.cerrarArchivoResultados();
                std::cout << "\033[32m[success] Archivo de resultados cerrado.\033[0m" << std::endl;
            }

            systemController.limpiar();
            std::cout << "\033[32m[success] Saliendo del programa...\033[0m" << std::endl;
            g_salir = true;
        } else if (args[0] == "ejecutarPruebas") {
            if (args.size() != 2) {
                printError("Uso incorrecto del comando ejecutarPruebas");
                std::cout << "\033[34m[info] Uso: ejecutarPruebas <ruta_script.txt>\033[0m" << std::endl;
                return;
            }
            string ruta = args[1]; // ruta completa del archivo de prueba

            ifstream archivoCmd(ruta);
            if (!archivoCmd.is_open()) {
                printError("No se pudo abrir el archivo de pruebas: '" + ruta + "'");
                return;
            }

            // Inicializar el archivo SOLO SI NO ESTÁ ACTIVO para evitar sobrescribir.
            if (!systemController.isArchivoResultadosActivo()) {
                systemController.iniciarArchivoResultados("resultados/resultados.csv");
            }
            
            std::cout << "[info] Procesando comandos desde archivo: " << ruta << std::endl;
            string lineaArchivo;
            
            while (getline(archivoCmd, lineaArchivo)) {
                if (lineaArchivo.empty() || lineaArchivo[0] == '#') continue;
                std::cout << "> " << lineaArchivo << std::endl;
                vector<string> argsArchivo = split(lineaArchivo);
                if (!argsArchivo.empty()) {
                    
                    if (argsArchivo[0] == "resolver") {
                        // Medir tiempo de resolución
                        auto t_inicio = std::chrono::high_resolution_clock::now();
                        
                        procesarComando(inicializado, argsArchivo, systemController, archivoCmd);
    
                        auto t_fin = std::chrono::high_resolution_clock::now();
                        auto duracion = std::chrono::duration_cast<std::chrono::milliseconds>(t_fin - t_inicio).count();
                        
                        // Se usa la ruta del script como identificador del problema.
                        string idProblema = ruta;
                        string archivoSalida = argsArchivo.size() < 2 ? "" : argsArchivo.back();

                        // Obtener los tiempos desde el SystemController
                        systemController.registrarResultado(
                            idProblema,
                            duracion,
                            archivoSalida,
                            systemController.getUltimoTiempoModeloInterno(),
                            systemController.getUltimoTiempoModeloAPI(),
                            systemController.getUltimoTiempoResolucion(),
                            systemController.getUltimoTiempoPostprocesamiento()
                        );
                    } else {
                        procesarComando(inicializado, argsArchivo, systemController, archivoCmd);
                    }
                }

                // Limpiar el estado del stream (para robustez en lectura)
                if (archivoCmd.fail()) {
                    archivoCmd.clear(); 
                }
            }
            
            std::cout << "[success] Procesamiento del archivo completado" << std::endl;
        } else if (args[0] == "benchmarkSintetico") {
            // Módulo de benchmark sintético (independiente del despacho hidrotérmico).
            // Lee sus parámetros de las líneas siguientes (ver synthetic/README.md).
            try {
                ejecutarBenchmarkSintetico(in, args);
            } catch (const std::exception& e) {
                printError(std::string("benchmarkSintetico: ") + e.what());
            }
        } else {
            std::cerr << "\033[31m[error] Comando no valido. Los comandos válidos antes de inicializar son:\n"
                        "    1. inicializar --t <horizonteTemporal>\n"
                        "    2. ejecutarPruebas\n"
                        "    3. salir\n"
                        "    4. benchmarkSintetico\n\033[0m" << std::endl;
        }
    } else {
        if (args[0] == "inicializar") {
            std::cout << "\033[31m[error] El programa ya está inicializado. Debe finalizar previamente antes de inicializar nuevamente.\033[0m" << std::endl;
        } else if (args[0] == "agregarAgente") {
            int horizonteTemporal = systemController.getHc();
            if (horizonteTemporal <= 0) {
                cerr << "< Error: horizonteTemporal no inicializado o inválido. Ejecutar 'inicializar --t <horizonteTemporal>' primero." << endl;
                return;
            }

            if (args.size() >= 2 && args[1] == "--RioNegro") {
                if (!(args.size() == 2 || (args.size() == 3 && args[2] == "--c8"))) {
                    printError("Uso incorrecto del comando agregarAgente --RioNegro");
                    std::cout << "\033[34m[info] Uso: agregarAgente --RioNegro [--c8]\033[0m" << std::endl;
                    return;
                }

                const bool compactar8h = (args.size() == 3);

                // Bonete (una sola línea con horizonteTemporal doubles)
                if (!getline(in, linea)) { 
                    std::cerr << "\033[31m[error] Falta línea de aportes Bonete\033[0m" << std::endl; 
                    return; 
                }
                vector<double> aportesBonete;
                if (!parseNDoublesFromLine(linea, horizonteTemporal, aportesBonete)) {
                    std::cerr << "\033[31m[error] Aportes Bonete inválidos o cantidad incorrecta (se esperaban " << horizonteTemporal << ")\033[0m" << std::endl; 
                    return;
                }
            
                // Baygorria
                if (!getline(in, linea)) { 
                    std::cerr << "\033[31m[error] Falta línea de aportes Baygorria\033[0m" << std::endl; 
                    return; 
                }
                vector<double> aportesBaygorria;
                if (!parseNDoublesFromLine(linea, horizonteTemporal, aportesBaygorria)) {
                    std::cerr << "\033[31m[error] Aportes Baygorria inválidos o cantidad incorrecta (se esperaban " << horizonteTemporal << ")\033[0m" << std::endl; 
                    return;
                }
            
                // Palmar
                if (!getline(in, linea)) { 
                    std::cerr << "\033[31m[error] Falta línea de aportes Palmar\033[0m" << std::endl; 
                    return; 
                }
                vector<double> aportesPalmar;
                if (!parseNDoublesFromLine(linea, horizonteTemporal, aportesPalmar)) {
                    std::cerr << "\033[31m[error] Aportes Palmar inválidos o cantidad incorrecta (se esperaban " << horizonteTemporal << ")\033[0m" << std::endl; 
                    return;
                }
            
                double volumenInicialBonete;
                if (!leerEscalarDesde(in, "volumenInicialBonete", volumenInicialBonete)) return;
            
                double volumenInicialPalmar;
                if (!leerEscalarDesde(in, "volumenInicialPalmar", volumenInicialPalmar)) return;
            
                double costoAguaBonete;
                if (!leerEscalarDesde(in, "costoAguaBonete", costoAguaBonete)) return;

                double costoAguaPalmar;
                if (!leerEscalarDesde(in, "costoAguaPalmar", costoAguaPalmar)) return;
            
                systemController.agregarRioNegro(
                    aportesBonete, aportesBaygorria, aportesPalmar,
                    volumenInicialBonete, volumenInicialPalmar,
                    costoAguaBonete, costoAguaPalmar,
                    compactar8h
                );
            
                std::cout << "\033[32m[success] Se ha creado el agente 'Río Negro' exitosamente\033[0m" << std::endl;
            } else if (args.size() >= 2 && args[1] == "--RioNegroNoLineal") {
                if (!(args.size() == 2 || (args.size() == 3 && args[2] == "--c8"))) {
                    printError("Uso incorrecto del comando agregarAgente --RioNegroNoLineal");
                    std::cout << "\033[34m[info] Uso: agregarAgente --RioNegroNoLineal [--c8]\033[0m" << std::endl;
                    return;
                }

                const bool compactar8h = (args.size() == 3);

                // Bonete (una sola línea con horizonteTemporal doubles)
                if (!getline(in, linea)) { 
                    std::cerr << "\033[31m[error] Falta línea de aportes Bonete\033[0m" << std::endl; 
                    return; 
                }
                vector<double> aportesBonete;
                if (!parseNDoublesFromLine(linea, horizonteTemporal, aportesBonete)) {
                    std::cerr << "\033[31m[error] Aportes Bonete inválidos o cantidad incorrecta (se esperaban " << horizonteTemporal << ")\033[0m" << std::endl; 
                    return;
                }
            
                // Baygorria
                if (!getline(in, linea)) { 
                    std::cerr << "\033[31m[error] Falta línea de aportes Baygorria\033[0m" << std::endl; 
                    return; 
                }
                vector<double> aportesBaygorria;
                if (!parseNDoublesFromLine(linea, horizonteTemporal, aportesBaygorria)) {
                    std::cerr << "\033[31m[error] Aportes Baygorria inválidos o cantidad incorrecta (se esperaban " << horizonteTemporal << ")\033[0m" << std::endl; 
                    return;
                }
            
                // Palmar
                if (!getline(in, linea)) { 
                    std::cerr << "\033[31m[error] Falta línea de aportes Palmar\033[0m" << std::endl; 
                    return; 
                }
                vector<double> aportesPalmar;
                if (!parseNDoublesFromLine(linea, horizonteTemporal, aportesPalmar)) {
                    std::cerr << "\033[31m[error] Aportes Palmar inválidos o cantidad incorrecta (se esperaban " << horizonteTemporal << ")\033[0m" << std::endl; 
                    return;
                }
            
                double volumenInicialBonete;
                if (!leerEscalarDesde(in, "volumenInicialBonete", volumenInicialBonete)) return;

                int tamanioVectoresBellman;
                if (!leerEnteroPositivoDesde(in, "tamaño de vectores Bellman", tamanioVectoresBellman)) return;

                // volumenBonete (una sola línea con tamanioVectoresBellman doubles)
                if (!getline(in, linea)) { 
                    std::cerr << "\033[31m[error] Falta línea de volumenBonete\033[0m" << std::endl; 
                    return; 
                }
                vector<double> volumenBonete;
                if (!parseNDoublesFromLine(linea, tamanioVectoresBellman, volumenBonete)) {
                    std::cerr << "\033[31m[error] Volumen Bonete inválido o cantidad incorrecta (se esperaban " << tamanioVectoresBellman << ")\033[0m" << std::endl; 
                    return;
                }

                // valor Bellman (una sola línea con tamanioVectoresBellman doubles)
                if (!getline(in, linea)) { 
                    std::cerr << "\033[31m[error] Falta línea de valorBellman\033[0m" << std::endl; 
                    return; 
                }
                vector<double> valorBellman;
                if (!parseNDoublesFromLine(linea, tamanioVectoresBellman, valorBellman)) {
                    std::cerr << "\033[31m[error] Valor Bellman inválido o cantidad incorrecta (se esperaban " << tamanioVectoresBellman << ")\033[0m" << std::endl; 
                    return;
                }

                // derivada valor Bellman (una sola línea con tamanioVectoresBellman doubles)
                if (!getline(in, linea)) { 
                    std::cerr << "\033[31m[error] Falta línea de derivadaValorBellman\033[0m" << std::endl; 
                    return; 
                }
                vector<double> derivadaValorBellman;
                if (!parseNDoublesFromLine(linea, tamanioVectoresBellman, derivadaValorBellman)) {
                    std::cerr << "\033[31m[error] Derivada Valor Bellman inválida o cantidad incorrecta (se esperaban " << tamanioVectoresBellman << ")\033[0m" << std::endl; 
                    return;
                }

                double volumenInicialPalmar;
                if (!leerEscalarDesde(in, "volumenInicialPalmar", volumenInicialPalmar)) return;
            
                double costoAguaPalmar;
                if (!leerEscalarDesde(in, "costoAguaPalmar", costoAguaPalmar)) return;
            
                systemController.agregarRioNegroBoneteNoLineal(
                    aportesBonete, aportesBaygorria, aportesPalmar,
                    volumenInicialBonete, volumenInicialPalmar,
                    costoAguaPalmar, 
                    volumenBonete, valorBellman, derivadaValorBellman,
                    compactar8h
                );

                std::cout << "\033[32m[success] Se ha creado el agente 'Río Negro Bonete No Lineal' exitosamente\033[0m" << std::endl;
            } else if (args.size() == 2 && args[1] == "--UnidadTermicaRapida") {
                double potenciaMin, potenciaMax, costoFijo, costoVariable, costoEncendido;

                if (!leerEscalarDesde(in, "potencia mínima", potenciaMin)) return;
                if (!leerEscalarDesde(in, "potencia máxima", potenciaMax)) return;
                if (!leerEscalarDesde(in, "costo fijo", costoFijo)) return;
                if (!leerEscalarDesde(in, "costo variable", costoVariable)) return;
                if (!leerEscalarDesde(in, "costo de encendido", costoEncendido)) return;

                systemController.agregarUnidadTermicaRapida(
                    potenciaMin, potenciaMax, costoFijo, costoVariable, costoEncendido
                );
                std::cout << "\033[32m[success] Se ha creado el agente 'Unidad Térmica Rápida' exitosamente\033[0m" << std::endl;
            } else if (args.size() == 2 && args[1] == "--UnidadTermicaSimple") {
                double potenciaMax, costoVariable;

                std::cout << "\033[34m[info] Agregando agente Unidad Térmica Simple\033[0m" << std::endl;

                // Potencia máxima
                std::cout << "\033[34m[info] Ingrese potencia máxima de la unidad térmica simple:\033[0m" << std::endl;
                if (!leerEscalarDesde(in, "potencia máxima de la unidad térmica simple", potenciaMax)) return;

                // Costo variable
                std::cout << "\033[34m[info] Ingrese costo variable de la unidad térmica simple:\033[0m" << std::endl;
                if (!leerEscalarDesde(in, "costo variable de la unidad térmica simple", costoVariable)) return;

                systemController.agregarUnidadTermicaSimple(
                    potenciaMax,
                    costoVariable
                );

                std::cout << "\033[32m[success] Se ha creado el agente 'Unidad Térmica Simple' exitosamente\033[0m" << std::endl;
            } else if (args.size() == 2 && args[1] == "--DemandaFija") {
                vector<double> demandas;

                std::cout << "\033[34m[info] Agregando agente Demanda Fija\033[0m" << std::endl;

                // Demandas
                std::cout << "\033[34m[info] Ingrese demandas en una sola línea "
                        << "(" << horizonteTemporal << " valores):\033[0m" << std::endl;

                if (!getline(in, linea)) { 
                    std::cerr << "\033[31m[error] Falta línea de demandas\033[0m" << std::endl; 
                    return; 
                }

                if (!parseNDoublesFromLine(linea, horizonteTemporal, demandas)) {
                    std::cerr << "\033[31m[error] Demandas inválidas o cantidad incorrecta (se esperaban "
                            << horizonteTemporal << ")\033[0m" << std::endl; 
                    return;
                }

                systemController.agregarDemandaFija(demandas);

                std::cout << "\033[32m[success] Se ha creado el agente 'Demanda Fija' exitosamente\033[0m" << std::endl;
            } else if (args.size() >= 2 && args[1] == "--SaltoGrande") {
                if (args.size() > 3 || (args.size() == 3 && args[2] != "--c8")) {
                    printError("Uso inválido de SaltoGrande. Formas válidas: agregarAgente --SaltoGrande o agregarAgente --SaltoGrande --c8");
                    return;
                }
                const bool compactar8h = (args.size() == 3);
                double costoAguaSalto, volumenInicial;
                vector<double> aportesSalto;

                std::cout << "\033[34m[info] Agregando agente Salto Grande\033[0m" << std::endl;

                // Costo de agua
                std::cout << "\033[34m[info] Ingrese costo de agua de Salto Grande:\033[0m" << std::endl;
                if (!leerEscalarDesde(in, "costo de agua de Salto Grande", costoAguaSalto)) return;

                // Volumen inicial
                std::cout << "\033[34m[info] Ingrese volumen inicial de Salto Grande:\033[0m" << std::endl;
                if (!leerEscalarDesde(in, "volumen inicial de Salto Grande", volumenInicial)) return;

                // Aportes de Salto
                std::cout << "\033[34m[info] Ingrese aportes de Salto Grande en una sola línea "
                        << "(" << horizonteTemporal << " valores):\033[0m" << std::endl;

                if (!getline(in, linea)) {
                    std::cerr << "\033[31m[error] Falta línea de aportes de Salto Grande\033[0m" << std::endl;
                    return;
                }
                if (!parseNDoublesFromLine(linea, horizonteTemporal, aportesSalto)) {
                    std::cerr << "\033[31m[error] Aportes de Salto Grande inválidos o cantidad incorrecta (se esperaban "
                            << horizonteTemporal << ")\033[0m" << std::endl;
                    return;
                }

                systemController.agregarSaltoGrande(costoAguaSalto, aportesSalto, volumenInicial, compactar8h);

                std::cout << "\033[32m[success] Se ha creado el agente 'Salto Grande' exitosamente\033[0m" << std::endl;
            }
            else {
                    std::cerr << "\033[31m[error] Debe especificar una flag válida para agregarAgente\033[0m" << std::endl;
                    std::cout << "\033[34m[info] Uso: agregarAgente --RioNegro [--c8]\033[0m" << std::endl;
                    std::cout << "\033[34m[info] Uso: agregarAgente --RioNegroNoLineal [--c8]\033[0m" << std::endl;
                    std::cout << "\033[34m[info] Uso: agregarAgente --SaltoGrande [--c8]\033[0m" << std::endl;
                    std::cout << "\033[34m[info] Uso: agregarAgente --UnidadTermicaRapida | --UnidadTermicaSimple | --DemandaFija\033[0m" << std::endl;
                }
        } else if (args[0] == "crearDespacho") {
            if (args.size() == 2 && args[1] == "--fija") {
                // 1. Leer costo de falla
                double costoFalla;
                if (!leerEscalarDesde(in, "costo de falla", costoFalla)) return;

                systemController.crearDespachoFijo(costoFalla);
                std::cout << "\033[32m[success] Se ha creado el despacho fijo exitosamente\033[0m" << std::endl;

            } else if (args.size() == 2 && args[1] == "--proporcional") {
                int horizonteTemporal = systemController.getHc();

                // 1. Leer vector de demandas totales
                if (!getline(in, linea)) {
                    std::cerr << "\033[31m[error] Falta línea de demandas\033[0m" << std::endl;
                    return;
                }
                vector<double> demandas;
                if (!parseNDoublesFromLine(linea, horizonteTemporal, demandas)) {
                    std::cerr << "\033[31m[error] Demandas inválidas o cantidad incorrecta (se esperaban "
                            << horizonteTemporal << ")\033[0m" << std::endl;
                    return;
                }

                // 2. Leer parámetro proporción
                double proporcion;
                if (!leerEscalarDesde(in, "proporción", proporcion)) return;

                systemController.crearDespachoProporcional(proporcion, demandas);
                std::cout << "\033[32m[success] Se ha creado el despacho proporcional exitosamente\033[0m" << std::endl;

            } else if (
                (args.size() == 2 && args[1] == "--mercado") ||
                (args.size() == 3 && args[1] == "--mercado" && args[2] == "--conDemandaTotal")
            ) {
                int horizonteTemporal = systemController.getHc();
                bool usarDemandaTotal = (args.size() == 3 && args[2] == "--conDemandaTotal");

                std::cout << "\033[34m[info] Creando despacho de mercado\033[0m" << std::endl;

                if (usarDemandaTotal) {
                    std::cout << "\033[34m[info] Modo: despacho de mercado con demanda total explícita\033[0m" << std::endl;
                } else {
                    std::cout << "\033[34m[info] Modo: despacho de mercado sin demanda total explícita\033[0m" << std::endl;
                }

                // 1. Leer cantidad de tramos
                std::cout << "\033[34m[info] Ingrese cantidad de tramos del despacho de mercado:\033[0m" << std::endl;

                int cantidadTramos;
                if (!leerEnteroPositivoDesde(in, "cantidad de tramos", cantidadTramos)) return;

                // 2. Leer porcentajes acumulados de los tramos
                std::cout << "\033[34m[info] Ingrese porcentajes acumulados de los tramos en una sola línea "
                        << "(" << cantidadTramos << " valores):\033[0m" << std::endl;

                if (!getline(in, linea)) {
                    std::cerr << "\033[31m[error] Falta línea de porcentajes de tramo\033[0m" << std::endl;
                    return;
                }

                vector<double> porcentajesTramos;
                if (!parseNDoublesFromLine(linea, cantidadTramos, porcentajesTramos)) {
                    std::cerr << "\033[31m[error] Porcentajes de tramo inválidos o cantidad incorrecta "
                            << "(se esperaban " << cantidadTramos << ")\033[0m" << std::endl;
                    return;
                }

                // 3. Leer costos marginales
                std::cout << "\033[34m[info] Ingrese costos marginales de los tramos en una sola línea "
                        << "(" << cantidadTramos << " valores):\033[0m" << std::endl;

                if (!getline(in, linea)) {
                    std::cerr << "\033[31m[error] Falta línea de costos marginales\033[0m" << std::endl;
                    return;
                }

                vector<double> costosMarginales;
                if (!parseNDoublesFromLine(linea, cantidadTramos, costosMarginales)) {
                    std::cerr << "\033[31m[error] Costos marginales inválidos o cantidad incorrecta "
                            << "(se esperaban " << cantidadTramos << ")\033[0m" << std::endl;
                    return;
                }

                // 4. Leer demanda total solo si se pidió explícitamente
                vector<double> demandaTotal;
                if (usarDemandaTotal) {
                    std::cout << "\033[34m[info] Ingrese demanda total en una sola línea "
                            << "(" << horizonteTemporal << " valores):\033[0m" << std::endl;

                    if (!getline(in, linea)) {
                        std::cerr << "\033[31m[error] Falta línea de demanda total\033[0m" << std::endl;
                        return;
                    }

                    if (!parseNDoublesFromLine(linea, horizonteTemporal, demandaTotal)) {
                        std::cerr << "\033[31m[error] Demanda total inválida o cantidad incorrecta "
                                << "(se esperaban " << horizonteTemporal << ")\033[0m" << std::endl;
                        return;
                    }
                }

                systemController.crearDespachoMercado(
                    porcentajesTramos,
                    costosMarginales,
                    demandaTotal
                );

                std::cout << "\033[32m[success] Se ha creado el despacho de mercado exitosamente\033[0m" << std::endl;

            } else {
                std::cerr << "\033[31m[error] Debe especificar la flag --fija, --proporcional o --mercado para crearDespacho\033[0m" << std::endl;
                std::cout << "\033[34m[info] Uso: crearDespacho --fija|--proporcional|--mercado [--conDemandaTotal]\033[0m" << std::endl;
            }
        } else if (args[0] == "configurarSolver") {
            const std::vector<std::string> solvers = {"DummyLp", "Gurobi", "Cbc", "Cplex", "Hexaly"};

            if (args.size() >= 2) {
                string tipoSolver = normalizeSolverFlag(args[1]);

                if (std::find(solvers.begin(), solvers.end(), tipoSolver) != solvers.end()) {

                    // Parsear flags opcionales: --timeout <seg> y --mipgap <val>
                    SolverConfig config;
                    bool errorFlag = false;

                    for (size_t i = 2; i < args.size(); ++i) {
                        if (args[i] == "--timeout" || args[i] == "-timeout") {
                            if (i + 1 >= args.size()) {
                                std::cerr << "\033[31m[error] --timeout requiere un valor numérico\033[0m" << std::endl;
                                errorFlag = true; break;
                            }
                            double val;
                            if (!parseDoubleStrict(args[++i], val) || val < 0) {
                                std::cerr << "\033[31m[error] --timeout debe ser un número >= 0 (0 = sin límite)\033[0m" << std::endl;
                                errorFlag = true; break;
                            }
                            config.timeoutSegundos = val;

                        } else if (args[i] == "--mipgap" || args[i] == "-mipgap") {
                            if (i + 1 >= args.size()) {
                                std::cerr << "\033[31m[error] --mipgap requiere un valor numérico\033[0m" << std::endl;
                                errorFlag = true; break;
                            }
                            double val;
                            if (!parseDoubleStrict(args[++i], val) || val <= 0) {
                                std::cerr << "\033[31m[error] --mipgap debe ser un número > 0\033[0m" << std::endl;
                                errorFlag = true; break;
                            }
                            config.mipGap = val;

                        } else if (args[i] == "--scaleflag" || args[i] == "-scaleflag") {
                            // Baseline R1: escalado interno de Gurobi (GRB ScaleFlag: -1,0,1,2,3).
                            if (i + 1 >= args.size()) {
                                std::cerr << "\033[31m[error] --scaleflag requiere un valor entero en {-1,0,1,2,3}\033[0m" << std::endl;
                                errorFlag = true; break;
                            }
                            int val;
                            try { val = std::stoi(args[++i]); } catch (...) { val = 99; }
                            if (val < -1 || val > 3) {
                                std::cerr << "\033[31m[error] --scaleflag debe estar en {-1,0,1,2,3}\033[0m" << std::endl;
                                errorFlag = true; break;
                            }
                            config.scaleFlagGurobi = val;

                        } else if (args[i] == "--seed" || args[i] == "-seed") {
                            // Réplica de semilla: variabilidad corrida-a-corrida del MIP.
                            if (i + 1 >= args.size()) {
                                std::cerr << "\033[31m[error] --seed requiere un valor entero >= 0\033[0m" << std::endl;
                                errorFlag = true; break;
                            }
                            int val;
                            try { val = std::stoi(args[++i]); } catch (...) { val = -1; }
                            if (val < 0) {
                                std::cerr << "\033[31m[error] --seed debe ser un entero >= 0\033[0m" << std::endl;
                                errorFlag = true; break;
                            }
                            config.semillaSolver = val;

                        } else if (args[i] == "--cplexscale" || args[i] == "-cplexscale") {
                            // Baseline R1: escalado interno de CPLEX (Read::Scale: -1,0,1).
                            if (i + 1 >= args.size()) {
                                std::cerr << "\033[31m[error] --cplexscale requiere un valor entero en {-1,0,1}\033[0m" << std::endl;
                                errorFlag = true; break;
                            }
                            int val;
                            try { val = std::stoi(args[++i]); } catch (...) { val = 99; }
                            if (val < -1 || val > 1) {
                                std::cerr << "\033[31m[error] --cplexscale debe estar en {-1,0,1}\033[0m" << std::endl;
                                errorFlag = true; break;
                            }
                            config.scaleIndCplex = val;

                        } else if (args[i] == "--cplexpresolve" || args[i] == "-cplexpresolve") {
                            // Sondeo R1: presolve de CPLEX (0 off, 1 on). ¿Absorbe el escalado externo?
                            if (i + 1 >= args.size()) {
                                std::cerr << "\033[31m[error] --cplexpresolve requiere un valor en {0,1}\033[0m" << std::endl;
                                errorFlag = true; break;
                            }
                            int val;
                            try { val = std::stoi(args[++i]); } catch (...) { val = 99; }
                            if (val < 0 || val > 1) {
                                std::cerr << "\033[31m[error] --cplexpresolve debe estar en {0,1}\033[0m" << std::endl;
                                errorFlag = true; break;
                            }
                            config.presolveIndCplex = val;

                        } else {
                            std::cerr << "\033[31m[error] Flag desconocida: " << args[i] << "\033[0m" << std::endl;
                            std::cout << "\033[34m[info] Uso: configurarSolver --<solver> [--timeout <seg>] [--mipgap <val>] [--scaleflag <-1..3>] [--cplexscale <-1..1>] [--cplexpresolve <0|1>]\033[0m" << std::endl;
                            errorFlag = true; break;
                        }
                    }

                    if (!errorFlag) {
                        try {
                            systemController.configurarSolver(tipoSolver, config);

                            std::cout << "\033[32m[success] Solver '" << tipoSolver << "' configurado"
                                      << " | timeout=" << config.timeoutSegundos << "s"
                                      << " | mipgap=" << config.mipGap;
                            if (config.scaleFlagGurobi != SolverConfig::SOLVER_PARAM_AUTO)
                                std::cout << " | scaleflag=" << config.scaleFlagGurobi;
                            if (config.scaleIndCplex != SolverConfig::SOLVER_PARAM_AUTO)
                                std::cout << " | cplexscale=" << config.scaleIndCplex;
                            if (config.presolveIndCplex != SolverConfig::SOLVER_PARAM_AUTO)
                                std::cout << " | cplexpresolve=" << config.presolveIndCplex;
                            std::cout << "\033[0m" << std::endl;

                        } catch (const std::exception& e) {
                            std::cerr << "\033[31m[error] No se pudo configurar el solver:\033[0m "
                                    << e.what() << std::endl;
                            return;
                        }
                    }

                } else {
                    std::cerr << "\033[31m[error] Tipo de solver no reconocido. Opciones válidas:\033[0m" << std::endl;
                    for (const auto& s : solvers) {
                        std::cout << "\033[34m[info] Uso: configurarSolver --" << s << "\033[0m" << std::endl;
                    }
                }
            } else {
                std::cout << "\033[34m[info] Uso: configurarSolver --DummyLp|--Gurobi|--Cbc|--Cplex [--timeout <seg>] [--mipgap <val>]\033[0m" << std::endl;
            }
        } else if (args[0] == "relajarVariablesBinarias") {
            if (args.size() != 1) {
                std::cerr << "\033[31m[error] Uso incorrecto del comando relajarVariablesBinarias\033[0m" << std::endl;
                std::cout << "\033[34m[info] Uso: relajarVariablesBinarias\033[0m" << std::endl;
                return;
            }

            if (systemController.getProblema() == nullptr) {
                std::cerr << "\033[31m[error] No hay problema configurado. Debes configurar un problema antes de relajar variables binarias.\033[0m" << std::endl;
                return;
            }

            systemController.relajarVariablesBinarias();
            std::cout << "\033[32m[success] Las variables binarias fueron relajadas a variables reales en [0,1].\033[0m" << std::endl;
        } else if (args[0] == "habilitarEstrategiaResolucion") {
            if (args.size() != 2) {
                std::cerr << "\033[31m[error] Uso incorrecto del comando habilitarEstrategiaResolucion\033[0m" << std::endl;
                std::cout << "\033[34m[info] Uso: habilitarEstrategiaResolucion Monolitica\033[0m" << std::endl;
                return;
            }

            Problema* p = systemController.getProblema();
            if (!p) {
                std::cerr << "\033[31m[error] No hay problema configurado. Use configurarSolver primero.\033[0m" << std::endl;
                return;
            }

            try {
                p->habilitarEstrategiaResolucion(args[1]);
                std::cout << "\033[32m[success] Estrategia de resolucion habilitada: "
                          << p->getEstrategiaResolucionSeleccionada()
                          << "\033[0m" << std::endl;
            } catch (const std::exception& e) {
                std::cerr << "\033[31m[error] " << e.what() << "\033[0m" << std::endl;
                return;
            }

        } else if (args[0] == "habilitarPreprocesamiento") {
            if (args.size() != 2) {
                std::cerr << "\033[31m[error] Uso incorrecto del comando habilitarPreprocesamiento\033[0m" << std::endl;
                std::cout << "\033[34m[info] Uso: habilitarPreprocesamiento Ninguno|Estructurado|Ruiz|RuizColumnas|...\033[0m" << std::endl;
                return;
            }

            Problema* p = systemController.getProblema();
            if (!p) {
                std::cerr << "\033[31m[error] No hay problema configurado. Use configurarSolver primero.\033[0m" << std::endl;
                return;
            }

            try {
                p->habilitarPreprocesamiento(args[1]);
                std::cout << "\033[32m[success] Preprocesamiento habilitado: "
                          << p->getPreprocesamientoSeleccionado()
                          << "\033[0m" << std::endl;
            } catch (const std::exception& e) {
                std::cerr << "\033[31m[error] " << e.what() << "\033[0m" << std::endl;
                return;
            }

        } else if (args[0] == "grabar") {
            if (args.size() >= 2) {
                string ruta = args[1];
                bool flagConstante = true;
                if (args.size() == 3 && args[2] == "--noConstante") {
                    flagConstante = false;
                }
                systemController.grabar(flagConstante, ruta);
                std::cout << "\033[32m[success] Se ha guardado el modelo exitosamente\033[0m" << std::endl;
            } else {
                printError("Debes especificar la ruta de salida");
                std::cout << "\033[34m[info] Uso: grabar <ruta> [--noConstante]\033[0m" << std::endl;
            }

        } else if (args[0] == "preprocesar") {
            // Uso: preprocesar [--solodiagnostico] [--verificar-original] [--global <prefijos,...>] [--acoplamiento <prefijos,...>]
            //                  [--local-estructurado|--local-matricial|--local-filas|--local-bloque|--local-ruiz]
            //                  [--ruiz-iters N] [--columnas-continuas] [--normalizacion-fisica]
            // Ejemplo: preprocesar --global gh_total,gen_menor_demanda,falla_tramo --acoplamiento gh_total --local-ruiz --columnas-continuas
            // Si no se pasa --global, se usan prefijos por defecto.

            Problema* p = systemController.getProblema();
            if (!p) {
                std::cerr << "\033[31m[error] No hay problema configurado. Use configurarSolver primero.\033[0m" << std::endl;
                return;
            }

            PreprocesamientoMIP::Config cfg;
            cfg.verbose = true;
            std::vector<std::string> prefijosGlobales = {
                "gh_total",
                "gen_menor_demanda",
                "falla_tramo",
                "balance_",
                "demanda_",
                "falla_",
                "deficit_"
            };
            std::vector<std::string> prefijosAcoplamiento = {
                "gh_total",
                "balance_"
            };

            for (size_t i = 1; i < args.size(); ++i) {
                if (args[i] == "--solodiagnostico") {
                    cfg.solodiagnostico = true;
                } else if (args[i] == "--local-estructurado") {
                    cfg.escalamientoLocalPorFila = true;
                    cfg.normalizarBloqueTrasFilas = true;
                    cfg.usarEquilibradoRuiz = false;
                    cfg.modoMatricial = false;
                } else if (args[i] == "--local-matricial") {
                    // Estrategia 2: estructurado matricial (factores solo de A, sin RHS).
                    cfg.escalamientoLocalPorFila = true;
                    cfg.normalizarBloqueTrasFilas = true;
                    cfg.usarEquilibradoRuiz = false;
                    cfg.modoMatricial = true;
                } else if (args[i] == "--local-filas") {
                    cfg.escalamientoLocalPorFila = true;
                    cfg.normalizarBloqueTrasFilas = false;
                    cfg.usarEquilibradoRuiz = false;
                } else if (args[i] == "--local-bloque") {
                    cfg.escalamientoLocalPorFila = false;
                    cfg.normalizarBloqueTrasFilas = false;
                    cfg.usarEquilibradoRuiz = false;
                } else if (args[i] == "--local-ruiz") {
                    cfg.usarEquilibradoRuiz = true;
                    cfg.escalamientoLocalPorFila = true;
                    cfg.normalizarBloqueTrasFilas = true;
                } else if (args[i] == "--ruiz-iters" && i + 1 < args.size()) {
                    cfg.iteracionesRuiz = std::max(1, std::stoi(args[++i]));
                } else if (args[i] == "--banda-identidad" && i + 1 < args.size()) {
                    // R3: hiperparámetro u de la banda de cuasi-identidad [1/u, u].
                    double _u;
                    if (!parseDoubleStrict(args[++i], _u, "--banda-identidad")) return;
                    cfg.umbralFactorEscalamiento = std::max(1.0, _u);
                } else if (args[i] == "--ventana-coef" && i + 2 < args.size()) {
                    // R3: ventana de coeficiente admisible [ε_min, ε_max].
                    double _emin, _emax;
                    if (!parseDoubleStrict(args[++i], _emin, "--ventana-coef ε_min")) return;
                    if (!parseDoubleStrict(args[++i], _emax, "--ventana-coef ε_max")) return;
                    cfg.epsMinCoef = _emin;
                    cfg.epsMaxCoef = _emax;
                } else if (args[i] == "--piso-local" && i + 1 < args.size()) {
                    // Piso de confiabilidad para los factores locales AUMENTADOS de SA-Aug
                    // (protege filas con |RHS| dominante). Opt-in; 0 = inactivo.
                    double _piso;
                    if (!parseDoubleStrict(args[++i], _piso, "--piso-local")) return;
                    cfg.pisoMagnitudFactorLocal = std::max(0.0, _piso);
                } else if (args[i] == "--solo-local") {
                    // R5 (ablación): solo etapa local (fila/bloque), sin escalado de acoplamiento.
                    cfg.aplicarEscalamientoLocal  = true;
                    cfg.aplicarEscalamientoGlobal = false;
                } else if (args[i] == "--solo-acoplamiento") {
                    // R5 (ablación): solo escalado de filas de acoplamiento, sin etapa local.
                    cfg.aplicarEscalamientoLocal  = false;
                    cfg.aplicarEscalamientoGlobal = true;
                } else if (args[i] == "--plano") {
                    // Control experimental (flat/no-metadata): mismo kernel por fila (geomean
                    // de extremos) sobre TODAS las filas, SIN metadata de roles ni bloques.
                    // Los ajustes de config se imponen tras el parseo (ver bloque
                    // escalamientoPlano abajo), para que --plano gane sin importar el orden.
                    cfg.escalamientoPlano = true;
                } else if (args[i] == "--columnas-continuas") {
                    cfg.escalarColumnasContinuas = true;
                    cfg.usarEquilibradoRuiz = true;
                } else if (args[i] == "--normalizacion-fisica") {
                    cfg.normalizacionFisica = true;
                } else if (args[i] == "--verificar-original") {
                    cfg.verificarModeloOriginal = true;
                } else if (args[i] == "--global" && i + 1 < args.size()) {
                    prefijosGlobales.clear();
                    std::stringstream ss(args[++i]);
                    std::string tok;
                    while (std::getline(ss, tok, ','))
                        if (!tok.empty()) prefijosGlobales.push_back(tok);
                } else if (args[i] == "--acoplamiento" && i + 1 < args.size()) {
                    prefijosAcoplamiento.clear();
                    std::stringstream ss(args[++i]);
                    std::string tok;
                    while (std::getline(ss, tok, ','))
                        if (!tok.empty()) prefijosAcoplamiento.push_back(tok);
                } else {
                    std::cerr << "\033[31m[error] Flag desconocida: " << args[i] << "\033[0m" << std::endl;
                    std::cout << "\033[34m[info] Uso: preprocesar [--solodiagnostico] [--verificar-original] [--global prefijo1,prefijo2,...] [--acoplamiento prefijo1,prefijo2,...] [--local-estructurado|--local-matricial|--local-filas|--local-bloque|--local-ruiz] [--ruiz-iters N] [--banda-identidad u] [--ventana-coef epsMin epsMax] [--solo-local|--solo-acoplamiento|--plano] [--columnas-continuas] [--normalizacion-fisica]\033[0m" << std::endl;
                    return;
                }
            }

            // Modo plano: impone su semántica DESPUÉS del parseo para sobreescribir lo que
            // hayan seteado --local-estructurado/--local-matricial (p.ej. normalizarBloqueTrasFilas)
            // sin importar el orden. Plano = kernel por fila puro: sin beta de bloque, sin etapa
            // de acoplamiento, sin Ruiz; modoMatricial (estrategia 1 vs 2 del kernel) se respeta.
            if (cfg.escalamientoPlano) {
                cfg.aplicarEscalamientoLocal   = true;
                cfg.aplicarEscalamientoGlobal  = false;
                cfg.escalamientoLocalPorFila   = true;
                cfg.normalizarBloqueTrasFilas  = false;
                cfg.usarEquilibradoRuiz        = false;
            }

            try {
                systemController.prepararModeloParaPreprocesamiento(cfg.solodiagnostico);
            } catch (const std::exception& e) {
                std::cerr << "\033[31m[error] No se pudo preparar el modelo para preprocesar:\033[0m "
                          << e.what() << std::endl;
                return;
            }

            PreprocesamientoMIP prep(*p, cfg);
            prep.registrarRestriccionGlobal(prefijosGlobales);
            prep.registrarRestriccionAcoplamiento(prefijosAcoplamiento);

            if (cfg.solodiagnostico) {
                prep.diagnosticar();
                std::cout << "\033[32m[success] Diagnostico completado (modelo sin modificar).\033[0m" << std::endl;
            } else {
                auto _t0_preproc = std::chrono::high_resolution_clock::now();
                prep.ejecutar();
                double _t_preproc_s = std::chrono::duration<double>(
                    std::chrono::high_resolution_clock::now() - _t0_preproc).count();
                // Derivar slug estable a partir de la config aplicada
                std::string _slug_preproc;
                if (cfg.escalamientoPlano) {
                    // Control plano: alineado con las variantes del driver de validación
                    // (el sufijo _solo_local NO aplica: plano no es una etapa de la
                    // arquitectura, es el kernel sin metadata).
                    _slug_preproc = cfg.modoMatricial ? "matricial_plano" : "estructurado_plano";
                } else if (cfg.usarEquilibradoRuiz) {
                    _slug_preproc = cfg.escalarColumnasContinuas ? "ruiz_columnas" : "ruiz";
                } else if (cfg.modoMatricial) {
                    _slug_preproc = "estructurado_matricial";
                } else if (cfg.escalamientoLocalPorFila) {
                    _slug_preproc = cfg.normalizarBloqueTrasFilas ? "estructurado" : "filas";
                } else {
                    _slug_preproc = "bloque";
                }
                // R5 (ablación): sufijo cuando solo se aplica una etapa de la arquitectura.
                if (!cfg.escalamientoPlano) {
                    if (cfg.aplicarEscalamientoLocal && !cfg.aplicarEscalamientoGlobal)
                        _slug_preproc += "_solo_local";
                    else if (!cfg.aplicarEscalamientoLocal && cfg.aplicarEscalamientoGlobal)
                        _slug_preproc += "_solo_acoplamiento";
                }
                // Emitir vía ostringstream con formato propio: el estado de std::cout puede
                // quedar pegado en std::fixed/baja precisión por prints previos del modelo, lo
                // que distorsionaría el eco de u/ε (los valores en cfg son correctos).
                std::ostringstream _pt;
                _pt << std::defaultfloat << std::setprecision(10)
                    << "[PREPROC TIME] variante=" << _slug_preproc
                    << " tiempo_s=" << _t_preproc_s
                    << " u=" << cfg.umbralFactorEscalamiento
                    << " K=" << cfg.iteracionesRuiz
                    << " epsMin=" << cfg.epsMinCoef
                    << " epsMax=" << cfg.epsMaxCoef;
                std::cout << _pt.str() << std::endl;
                std::cout << "\033[32m[success] Preprocesamiento aplicado.\033[0m" << std::endl;
            }

        } else if (args[0] == "resolver") {
            if (args.size() < 2) {
                std::cerr << "\033[31m[error] Debes especificar la ruta de salida (.csv)\033[0m" << std::endl;
                std::cout << "\033[34m[info] Uso: resolver [--noConstante] <ruta.csv>\033[0m" << std::endl;
                return;
            }
            bool flagConstante = true;
            string ruta;
            if (args.size() == 2) {
                ruta = args[1];
            } else if (args.size() == 3 && args[1] == "--noConstante") {
                flagConstante = false;
                ruta = args[2];
            } else {
                std::cerr << "\033[31m[error] Uso incorrecto del comando resolver\033[0m" << std::endl;
                std::cout << "\033[34m[info] Uso: resolver [--noConstante] <ruta.csv>\033[0m" << std::endl;
                return;
            }
            try {
                systemController.resolver(flagConstante, ruta);
            } catch (const std::exception& e) {
                std::cerr << "\033[31m[error] Falló la resolución del problema:\033[0m "
                        << e.what() << std::endl;
                return;
            }

        } else if (args[0] == "salir") {
            // Cerrar el archivo de resultados si quedó abierto.
            if (systemController.isArchivoResultadosActivo()) {
                systemController.cerrarArchivoResultados();
                std::cout << "\033[32m[success] Archivo de resultados cerrado.\033[0m" << std::endl;
            }

            systemController.limpiar();
            std::cout << "\033[32m[success] Saliendo del programa...\033[0m" << std::endl;
            g_salir = true;
        } else if (args[0] == "finalizar") {
            systemController.limpiar();
            inicializado = false;
            std::cout << "\033[32m[success] Memoria limpiada exitosamente...\033[0m" << std::endl;
        } else {
            std::cerr << "\033[31m[error] Comando no reconocido\033[0m" << std::endl;
        }
    }
}

// ================ main ================
int main() {
    SystemController& systemController = SystemController::getInstance();
    string linea;
    bool inicializado = false;
    while (!g_salir) {
        cout << "> ";
        if (!getline(cin, linea)) break;   // EOF (p.ej. fin de un pipe) sin 'salir'
        vector<string> args = split(linea);
        if (args.empty() || args[0][0] == '#') continue;  // ignora líneas vacías y comentarios
        procesarComando(inicializado, args, systemController);
    }

    // Asegurar el cierre/flush del archivo de resultados y la limpieza aunque
    // la entrada termine por EOF sin un comando 'salir' explícito.
    if (!g_salir) {
        if (systemController.isArchivoResultadosActivo()) {
            systemController.cerrarArchivoResultados();
        }
        systemController.limpiar();
    }
    return 0;
}
