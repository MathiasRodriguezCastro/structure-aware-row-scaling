#ifndef APORTE_FUNCION_OBJETIVO_H
#define APORTE_FUNCION_OBJETIVO_H

#include <string>
#include <sstream>

class AporteFuncionObjetivo {
private:
    double coeficiente;
    std::string variable;

public:
    explicit AporteFuncionObjetivo(double c, const std::string& v)
        : coeficiente(c), variable(v) {}

    ~AporteFuncionObjetivo() = default;

    // --- Getters ---
    double getCoeficiente() const { return coeficiente; }
    const std::string& getVariable() const { return variable; }

    // --- Setters ---
    void setCoeficiente(double c) { coeficiente = c; }
    void setVariable(const std::string& v) { variable = v; }

    // --- Representación como string ---
    std::string toString() const {
        std::ostringstream ss;
        ss << coeficiente << " * " << variable;
        return ss.str();
    }
};

#endif // APORTE_FUNCION_OBJETIVO_H