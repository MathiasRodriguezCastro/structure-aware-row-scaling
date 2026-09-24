// ProblemaLp.cpp
#include "ProblemaLp.h"
#include "../../utils.h"
#include <sstream>
#include <iostream>
#include <fstream>
#include <iomanip>
#include <limits>


using namespace std;

namespace {
// max_digits10 significant digits preserve the stored binary64 value on readback.
// Fixed decimal precision can erase small coefficients, RHS values and bounds.
string numeroLp(double value, bool signoExplicito = false) {
    ostringstream stream;
    if (signoExplicito && value > 0) stream << '+';
    stream << setprecision(numeric_limits<double>::max_digits10) << defaultfloat << value;
    return stream.str();
}
}

// Constructor
ProblemaLp::ProblemaLp() : archivo("") {}

// --- Procesar ---
void ProblemaLp::procesar(bool flagConstante) {
    string resultado = "";
    
    // 1. Función objetivo
    resultado += "min\n";
    resultado += "obj:";
    if (!terminosFuncionObjetivo.empty()) resultado += " ";
    resultado += "\n";
    for (size_t i = 0; i < terminosFuncionObjetivo.size(); ++i) {
        const auto& termino = terminosFuncionObjetivo[i];
        resultado += "  " + numeroLp(termino->getCoeficiente(), true) + " " + termino->getVariable();
        resultado += "\n";
    }
    if (flagConstante && constanteFuncionObjetivo != 0.0) {
        resultado += "  " + numeroLp(constanteFuncionObjetivo, true) + "\n";
    }
    resultado += "\n";
    
    // 2. Restricciones
    resultado += "s.t.\n";
    for (const auto& restriccion : restricciones) {
        resultado += "\n";
        resultado += restriccion->getNombre() + ": ";
        resultado += "\n";
        const auto& terminos = restriccion->getTerminos();
        for (size_t i = 0; i < terminos.size(); ++i) {
            resultado += numeroLp(terminos[i].first, true) + " " + terminos[i].second + "\n";
        }
        resultado += restriccion->getOperador() + " " + numeroLp(restriccion->getTerminoIndependiente()) + "\n";
    }
    resultado += "\n";
    
    // 3. Cotas (Bounds)
    resultado += "bounds\n";
    for (const auto& variable : variables) {
        int tipoCota = variable->getTipoCota();
        if (tipoCota == 0) { // ambas cotas
            resultado += "  " + numeroLp(variable->getCotaInf()) + " <= " + variable->getNombre() + " <= " + numeroLp(variable->getCotaSup()) + "\n";
        } else if (tipoCota == 1) { // sin cota inferior
            resultado += "  -inf <= " + variable->getNombre() + " <= " + numeroLp(variable->getCotaSup()) + "\n";
        } else if (tipoCota == 2) { // sin cota superior  
            resultado += "  " + numeroLp(variable->getCotaInf()) + " <= " + variable->getNombre() + " <= +inf\n";
        } else if (tipoCota == 3) { // sin cotas
            resultado += "  " + variable->getNombre() + " free\n";
        }
    }
    if (!binarios.empty()) {
        for (const auto& binario : binarios) {
            resultado += " 0 <= " + binario->getNombre() + " <= 1\n";
        }
    }
    resultado += "\n";
        
    // 4. Variables binarias
    if (!binarios.empty()) {
        resultado += "binary\n";
        for (const auto& binario : binarios) {
            resultado += "  " + binario->getNombre() + "\n";
        }
    }
    
    resultado += "end\n";

    // store generated LP in archivo
    archivo = resultado;
}

// --- Graba en memoria ---
void ProblemaLp::grabar(string& ruta) {
    // Ensure procesar has been called to fill 'archivo' (or call it here)
    // Optionally call procesar() so file is up-to-date:

    ofstream file(ruta);
    if (!file.is_open())
        throw runtime_error("ProblemaLp::grabar - no se pudo abrir '" + ruta + "'.");

    file << archivo;
    file.close();

    cout << "Archivo LP guardado en: " << ruta << endl;
}

// --- Resuelve ---
void ProblemaLp::resolverMonolitico() {
    throw runtime_error("ProblemaLp::resolverMonolitico - ProblemaLp es solo exportacion; use un solver externo.");
}

// --- Utilidad ---
void ProblemaLp::mostrar() {
    cout << "=== PROBLEMA LP ===" << endl;
    cout << "Archivo asociado: " << archivo << endl;
    cout << "Variables: " << variables.size() << endl;
    cout << "Restricciones: " << restricciones.size() << endl;
    cout << "Binarios: " << binarios.size() << endl;
    cout << "Terminos FO: " << terminosFuncionObjetivo.size() << endl;
    cout << "Constante FO: " << constanteFuncionObjetivo << endl;
}
