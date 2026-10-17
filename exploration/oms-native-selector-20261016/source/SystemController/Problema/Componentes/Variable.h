#ifndef VARIABLE_H
#define VARIABLE_H

#include <string>
#include <sstream>

class Variable {
private:
    std::string nombre;   // Nombre de la variable
    int tipoCota;         // 0: ambas cotas, 1: sin cota inferior, 2: sin cota superior, 3: sin cota
    double cotaInf;       // Cota inferior
    double cotaSup;       // Cota superior

public:
    // Constructor
    Variable(const std::string& n, int t, double ci, double cs)
        : nombre(n), tipoCota(t), cotaInf(ci), cotaSup(cs) {}

    // Getters
    const std::string& getNombre() const { return nombre; }               
    int getTipoCota() const { return tipoCota; }                    
    double getCotaInf() const { return cotaInf; }                 
    double getCotaSup() const { return cotaSup; }                

    // Setters
    void setNombre(const std::string& n) { nombre = n; }
    void setTipoCota(int t) { tipoCota = t; }
    void setCotaInf(double ci) { cotaInf = ci; }
    void setCotaSup(double cs) { cotaSup = cs; }

    // --- Método útil ---
    std::string toString() const {
        std::ostringstream ss;
        ss << nombre << " [";
        switch(tipoCota) {
            case 0: ss << cotaInf << " <= x <= " << cotaSup; break;
            case 1: ss << "-inf <= x <= " << cotaSup; break;
            case 2: ss << cotaInf << " <= x <= +inf"; break;
            case 3: ss << "-inf <= x <= +inf"; break;
            default: ss << "Cota desconocida"; break;
        }
        ss << "]";
        return ss.str();
    }
};

#endif // VARIABLE_H