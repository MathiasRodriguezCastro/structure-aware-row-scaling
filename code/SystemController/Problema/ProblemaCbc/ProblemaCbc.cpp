#include "ProblemaCbc.h"
#include <iostream>
#include <map>
#include <vector>
#include <string>

// Headers de CBC con el prefijo coin/
#include <coin/OsiClpSolverInterface.hpp>
#include <coin/CbcModel.hpp>
#include <coin/CoinPackedMatrix.hpp>
#include <coin/CoinPackedVector.hpp>

using namespace std;

// Constructor: Inicializa punteros del solver y modelo
// En caso de fallo al crear el solver, libera memoria y propaga la excepción
ProblemaCbc::ProblemaCbc() : solver(nullptr), modelo(nullptr) {
    try {
        solver = new OsiClpSolverInterface();
        modelo = nullptr;
    } catch (...) {
        if (solver) { delete solver; solver = nullptr; }
        modelo = nullptr;
        throw; // Propaga la excepción para manejo externo
    }
}

ProblemaCbc::~ProblemaCbc() {
    if (modelo) { delete modelo; modelo = nullptr; }
    if (solver) { delete solver; solver = nullptr; }
}

// Procesar: construye el modelo CBC desde las variables, restricciones y función objetivo.
// Valida cotas, nombres, operadores y coherencia dimensional antes de cargar el modelo.
void ProblemaCbc::procesar(bool flagConstante) {
    // Liberar modelo anterior si existe
    if (modelo) {
        delete modelo;
        modelo = nullptr;
    }

    if (!solver) {
        throw std::runtime_error("ProblemaCbc::procesar - El solver no fue inicializado correctamente.");
    }


    int nVars = variables.size() + binarios.size();
    if (nVars == 0) {
        throw std::runtime_error("ProblemaCbc::procesar - No hay variables definidas.");
    }


    cerr << "\n[DEBUG] === INICIO DE PROCESAR CBC ===" << endl;
    cerr << "[DEBUG] Variables continuas: " << variables.size() << endl;
    cerr << "[DEBUG] Variables binarias: " << binarios.size() << endl;
    cerr << "[DEBUG] Restricciones: " << restricciones.size() << endl;

    vector<double> obj(nVars, 0.0);
    vector<double> colLower(nVars, 0.0);
    vector<double> colUpper(nVars, COIN_DBL_MAX);
    vector<char> colType(nVars, 'C'); // 'C' = continua, 'I' = entero

    varIndex.clear();
    int idx = 0;

    cerr << "\n[DEBUG] --- VARIABLES CONTINUAS ---" << endl;
    for (auto &v : variables) {
        if (std::isnan(v->getCotaInf()) || std::isnan(v->getCotaSup())) {
            throw std::invalid_argument(
                "ProblemaCbc::procesar - Cota inválida en variable '" + v->getNombre() + "'.");
        }

        varIndex[v->getNombre()] = idx;

        int tipoCota = v->getTipoCota();        
        if (tipoCota == 0) { // ambas cotas
            colLower[idx] = v->getCotaInf();
            colUpper[idx] = v->getCotaSup();
        } else if (tipoCota == 1) { // sin cota inferior
            colLower[idx] = -COIN_DBL_MAX;
            colUpper[idx] = v->getCotaSup();
        } else if (tipoCota == 2) { // sin cota superior  
            colLower[idx] = v->getCotaInf();
            colUpper[idx] = COIN_DBL_MAX;
        } else if (tipoCota == 3) { // sin cotas
            colLower[idx] = -COIN_DBL_MAX;
            colUpper[idx] = COIN_DBL_MAX;
        }
        

        colType[idx] = 'C';
        cerr << "  [" << idx << "] " << v->getNombre()
             << " ∈ [" << v->getCotaInf() << ", " << v->getCotaSup() << "] (continua)" << endl;
        idx++;
    }

    cerr << "\n[DEBUG] --- VARIABLES BINARIAS ---" << endl;
    for (auto &b : binarios) {
        varIndex[b->getNombre()] = idx;
        colLower[idx] = 0.0;
        colUpper[idx] = 1.0;
        colType[idx] = 'I';
        cerr << "  [" << idx << "] " << b->getNombre()
             << " ∈ [0, 1] (binaria)" << endl;
        idx++;
    }

    cerr << "\n[DEBUG] --- FUNCIÓN OBJETIVO ---" << endl;
    for (auto &t : terminosFuncionObjetivo) {
        if (!varIndex.count(t->getVariable())) {
            throw std::runtime_error(
                "ProblemaCbc::procesar - Variable '" + t->getVariable() +
                "' en función objetivo no encontrada en varIndex.");
        }
        int i = varIndex[t->getVariable()];
        obj[i] = t->getCoeficiente();
        cerr << "  + " << t->getCoeficiente() << " * " << t->getVariable() << endl;
    }

    if (flagConstante && constanteFuncionObjetivo != 0.0) {
        solver->setDblParam(OsiObjOffset, constanteFuncionObjetivo);
    }

    // --- Matriz de restricciones ---
    CoinPackedMatrix matrix(false, 0, nVars);
    vector<double> rowLower, rowUpper;

    cerr << "\n[DEBUG] --- RESTRICCIONES ---" << endl;
    int rIndex = 0;
    for (auto &r : restricciones) {
        CoinPackedVector row;

        cerr << "Restricción #" << rIndex << ": ";
        for (auto &t : r->getTerminos()) {
            if (!varIndex.count(t.second)) {
                throw std::runtime_error(
                    "ProblemaCbc::procesar - Variable '" + t.second +
                    "' en restricción '" + r->getNombre() + "' no encontrada en varIndex.");
            }
            int i = varIndex[t.second];
            row.insert(i, t.first);
            cerr << "  (" << t.first << " * " << t.second << ")";
        }

        cerr << "  " << r->getOperador() << "  " << r->getTerminoIndependiente() << endl;
        matrix.appendRow(row);

        if (r->getOperador() == "<=") {
            rowLower.push_back(-COIN_DBL_MAX);
            rowUpper.push_back(r->getTerminoIndependiente());
        } else if (r->getOperador() == ">=") {
            rowLower.push_back(r->getTerminoIndependiente());
            rowUpper.push_back(COIN_DBL_MAX);
        } else if (r->getOperador() == "=") {
            rowLower.push_back(r->getTerminoIndependiente());
            rowUpper.push_back(r->getTerminoIndependiente());
        } else {
            throw std::runtime_error(
                "ProblemaCbc::procesar - Operador desconocido '" + r->getOperador() +
                "' en restricción '" + r->getNombre() + "'.");
        }

        rIndex++;
    }

    cerr << "\n[DEBUG] --- RESUMEN DE MATRIZ ---" << endl;
    cerr << "  Filas: " << matrix.getNumRows() << endl;
    cerr << "  Columnas: " << nVars << endl;
    cerr << "  rowLower.size(): " << rowLower.size() << endl;
    cerr << "  rowUpper.size(): " << rowUpper.size() << endl;

    if (matrix.getNumRows() != (int)rowLower.size() ||
        matrix.getNumRows() != (int)rowUpper.size()) {
        throw std::runtime_error(
            "ProblemaCbc::procesar - Tamaños inconsistentes entre matriz y vectores de restricciones.");
    }

    cerr << "\n[DEBUG] Cargando problema en solver->.." << endl;
    solver->loadProblem(matrix, colLower.data(), colUpper.data(), obj.data(),
                        rowLower.data(), rowUpper.data());
    cerr << "[DEBUG] loadProblem completado correctamente." << endl;

    // Asignar nombres a las variables
    for (auto it = varIndex.begin(); it != varIndex.end(); ++it) {
        solver->setColName(it->second, it->first.c_str());
    }
    
    // Asignar nombres a las restricciones
    for (size_t i = 0; i < restricciones.size(); ++i) {
        // Si tus restricciones tienen un getter para el nombre
        solver->setRowName(i, restricciones[i]->getNombre().c_str());
    }

    // --- Variables enteras ---
    cerr << "\n[DEBUG] --- VARIABLES ENTERAS EN CBC ---" << endl;
    for (int i = 0; i < nVars; i++) {
        if (colType[i] == 'I') {
            solver->setInteger(i);
            cerr << "  Variable índice " << i << " marcada como entera." << endl;
        }
    }

    cerr << "\n[DEBUG] Creando modelo CBC..." << endl;
    modelo = new CbcModel(*solver);
    modelo->setLogLevel(1);
    cerr << "[DEBUG] Modelo CBC creado exitosamente." << endl;
    cerr << "[DEBUG] === FIN DE PROCESAR CBC ===\n" << endl;
}

// --- Resolver ---
void ProblemaCbc::resolverMonolitico() {
    if (!modelo) {
        throw std::runtime_error("Error: El modelo CBC no está inicializado. Llame a procesar() antes de resolver.");
    }

    // Aplicar configuración del solver
    if (config.timeoutSegundos > 0.0) {
        modelo->setMaximumSeconds(config.timeoutSegundos);
    }
    modelo->setAllowableFractionGap(config.mipGap);

    modelo->branchAndBound();

    const double* solution = modelo->bestSolution();
    if (!solution)
        throw std::runtime_error(
            "ProblemaCbc::resolverMonolitico - B&B finalizado sin solución factible.");

    for (auto &v : variables) {
        int i = varIndex[v->getNombre()];
        valoresVariables[v->getNombre()] = solution[i];
    }
    for (auto &b : binarios) {
        int i = varIndex[b->getNombre()];
        valoresVariables[b->getNombre()] = solution[i];
    }
    valorFuncionObjetivo = modelo->getObjValue();
    aplicarEscalamientoValoresSolucion();
}

void ProblemaCbc::grabar(string& rutaOriginal) {
    if (!modelo) {
        cerr << "[ERROR] Modelo no procesado." << endl;
        return;
    }

    string ruta = rutaOriginal;
    // Convertir ruta a minúsculas para comparar la extensión
    string rutaLower = ruta;
    transform(rutaLower.begin(), rutaLower.end(), rutaLower.begin(), ::tolower);

    // Detectar extensión
    if (rutaLower.size() >= 3 && rutaLower.substr(rutaLower.size() - 3) == ".lp") {
        ruta = ruta.substr(0, ruta.size() - 3); // quitar .lp
        modelo->solver()->writeLp(ruta.c_str());
        cerr << "[INFO] Modelo guardado en formato LP: " << ruta << ".lp" << endl;
    }
    else if (rutaLower.size() >= 4 && rutaLower.substr(rutaLower.size() - 4) == ".mps") {
        ruta = ruta.substr(0, ruta.size() - 4); // quitar .mps
        modelo->solver()->writeMps(ruta.c_str());
        cerr << "[INFO] Modelo guardado en formato MPS: " << ruta << ".mps" << endl;
    }
    else {
            cerr << "[ERROR] Extensión no reconocida. Usa .lp o .mps" << endl;
    }
}

// --- Mostrar ---
void ProblemaCbc::mostrar() {
    cout << "=== PROBLEMA CBC ===" << endl;
    cout << "Variables: " << variables.size() << endl;
    cout << "Binarios: " << binarios.size() << endl;
    cout << "Restricciones: " << restricciones.size() << endl;
    cout << "Terminos FO: " << terminosFuncionObjetivo.size() << endl;
    cout << "Constante FO: " << constanteFuncionObjetivo << endl;
    if (solver) {
        cout << "Solver: INICIALIZADO" << endl;
    } else {
        cout << "Solver: NO INICIALIZADO" << endl;
    }
}

// ============================================================
// Dantzig-Wolfe
// ============================================================
