#ifndef AGENTE_H
#define AGENTE_H

#include <vector>
#include <string>
#include <map>
#include "SystemController/Problema/Problema.h"

class Agente {
public:
    // Constructor
    explicit Agente(int idAgente, int horizonteTemporal) 
        : idAgente(idAgente), periodo(horizonteTemporal) 
    {}

    // Destructor
    virtual ~Agente() = default;

    // --- Métodos que cada agente debe implementar ---
    virtual void contribuirAlProblema(Problema* problema, int horizonteTemporal) = 0;
    virtual void posprocesamiento(Problema* problema) = 0;

    // --- Setters ---
    void setId(int id) { idAgente = id; }
    void setNombresVariables(const std::vector<std::string>& nombres) { nombresVariables = nombres; }
    void setNombre(const std::string& n) { nombre = n; }

    // --- Getters ---
    int getId() const { return idAgente; }
    const std::vector<std::string>& getNombresVariables() const { return nombresVariables; }
    const std::string& getNombre() const { return nombre; }
    int getPeriodo() const { return periodo; }

protected:
    std::string nombre;
    std::vector<std::string> nombresVariables;
    int idAgente;
    int periodo;
};

#endif // AGENTE_H