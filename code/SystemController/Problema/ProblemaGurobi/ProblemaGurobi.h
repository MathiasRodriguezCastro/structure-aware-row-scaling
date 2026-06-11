#ifndef PROBLEMAGUROBI_H
#define PROBLEMAGUROBI_H

#include "SystemController/Problema/Problema.h"
#include <vector>
#include <string>
#include <map>
#include <set>


class GRBEnv;
class GRBModel;
class GRBVar;

class ProblemaGurobi : public Problema {
private:
    GRBEnv*   env    = nullptr;
    GRBModel* modelo = nullptr;
    std::map<std::string, GRBVar> vars;

public:
    ProblemaGurobi();
    ~ProblemaGurobi() override;

    // No copiable ni movible (gestiona GRBEnv* y GRBModel* en heap).
    ProblemaGurobi(const ProblemaGurobi&) = delete;
    ProblemaGurobi& operator=(const ProblemaGurobi&) = delete;
    ProblemaGurobi(ProblemaGurobi&&) = delete;
    ProblemaGurobi& operator=(ProblemaGurobi&&) = delete;

    // --- Procesar / Exportación ---
    // Coincide con la firma de la clase base (void procesar()).
    void procesar(bool flagConstante) override;

    // --- Graba en memoria ---
    void grabar(std::string& ruta) override;

    // --- Resuelve ---
    void resolverMonolitico() override;

    // --- Utilidad ---
    void mostrar() override;

};

#endif // PROBLEMAGUROBI_H
