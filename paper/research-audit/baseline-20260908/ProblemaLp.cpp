// ProblemaLp.cpp
#include "ProblemaLp.h"
#include "../../utils.h"
#include <sstream>
#include <iostream>
#include <fstream>


using namespace std;

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
        resultado += "  " + to_string_mod(termino->getCoeficiente()) + " " + termino->getVariable();
        resultado += "\n";
    }
    if (flagConstante && constanteFuncionObjetivo != 0.0) {
        resultado += "  " + to_string_mod(constanteFuncionObjetivo) + "\n";
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
            resultado += to_string_mod(terminos[i].first) + " " + terminos[i].second + "\n";   
        }
        resultado += restriccion->getOperador() + " " + to_string(restriccion->getTerminoIndependiente()) + "\n";
    }
    resultado += "\n";
    
    // 3. Cotas (Bounds)
    resultado += "bounds\n";
    for (const auto& variable : variables) {
        int tipoCota = variable->getTipoCota();
        if (tipoCota == 0) { // ambas cotas
            resultado += "  " + to_string(variable->getCotaInf()) + " <= " + variable->getNombre() + " <= " + to_string(variable->getCotaSup()) + "\n";
        } else if (tipoCota == 1) { // sin cota inferior
            resultado += "  -inf <= " + variable->getNombre() + " <= " + to_string(variable->getCotaSup()) + "\n";
        } else if (tipoCota == 2) { // sin cota superior  
            resultado += "  " + to_string(variable->getCotaInf()) + " <= " + variable->getNombre() + " <= +inf\n";
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