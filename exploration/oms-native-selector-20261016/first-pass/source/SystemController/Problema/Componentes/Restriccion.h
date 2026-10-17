#ifndef RESTRICCION_H
#define RESTRICCION_H

#include <string>
#include <vector>
#include <utility>
#include <sstream>

class Restriccion {
private:
    std::string nombre;
    std::vector<std::pair<double,std::string>> terminos;
    std::string operador;
    double terminoIndependiente;

public:
    // --- Constructor ---
    Restriccion(const std::string& n,
                std::vector<std::pair<double, std::string>> t,
                const std::string& op,
                double r)
        : nombre(n), terminos(std::move(t)), operador(op), terminoIndependiente(r) {}

    // --- Getters ---
    const std::string& getNombre() const { return nombre; }              
    const std::vector<std::pair<double,std::string>>& getTerminos() const { return terminos; }  
    const std::string& getOperador() const { return operador; }           
    double getTerminoIndependiente() const { return terminoIndependiente; }  

    // --- Setters ---
    void setNombre(const std::string& n) { nombre = n; }
    void setTerminos(const std::vector<std::pair<double,std::string>>& t) { terminos = t; }
    void setOperador(const std::string& op) { operador = op; }
    void setTerminoIndependiente(double r) { terminoIndependiente = r; }

    // --- Método útil ---
    std::string toString() const {
        std::ostringstream ss;
        ss << nombre << ": ";
        for (size_t i = 0; i < terminos.size(); ++i) {
            ss << terminos[i].first << "*" << terminos[i].second;
            if (i < terminos.size() - 1) ss << " + ";
        }
        ss << " " << operador << " " << terminoIndependiente;
        return ss.str();
    }
};

#endif // RESTRICCION_H