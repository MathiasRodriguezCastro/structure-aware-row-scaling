#ifndef PROBLEMAHIGHS_H
#define PROBLEMAHIGHS_H

#include "SystemController/Problema/Problema.h"
#include <map>
#include <memory>
#include <string>
#include <vector>

class Highs;

// Backend HiGHS: el modelo se pasa en memoria (sin archivo intermedio), igual que Gurobi y CPLEX.
class ProblemaHighs : public Problema {
private:
    std::unique_ptr<Highs> highs;
    std::map<std::string, int> varIndex;
    std::vector<std::string> nombresColumnas;

public:
    ProblemaHighs();
    ~ProblemaHighs() override;

    void procesar(bool flagConstante) override;
    void grabar(std::string& ruta) override;
    void resolverMonolitico() override;
    void mostrar() override;
};

#endif // PROBLEMAHIGHS_H
