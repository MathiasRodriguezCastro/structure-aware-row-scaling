#ifndef BINARIO_H
#define BINARIO_H

#include <string>

class Binario {
private:
    std::string nombre;

public:
    explicit Binario(const std::string& n) : nombre(n) {}

    // --- Getters y Setters ---
    const std::string& getNombre() const { return nombre; }  
    void setNombre(const std::string& n) { nombre = n; }

    // --- Método útil ---
    std::string toString() const {
        return "binario: " + nombre;
    }
};

#endif // BINARIO_H