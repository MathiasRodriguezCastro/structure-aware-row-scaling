#ifndef PROBLEMACBC_H
#define PROBLEMACBC_H

#include "SystemController/Problema/Problema.h"
#include <vector>
#include <string>
#include <map>
#include <set>

// Forward declarations de CBC
class OsiClpSolverInterface;
class CbcModel;

class ProblemaCbc : public Problema {
private:
    OsiClpSolverInterface* solver = nullptr;
    CbcModel* modelo = nullptr;
    std::map<std::string,int> varIndex;

public:
    ProblemaCbc();
    virtual ~ProblemaCbc() override;

    void setValorVariable(double coef, std::string nombre);

    void procesar(bool flagConstante) override;
    void grabar(std::string& ruta) override;
    void resolverMonolitico() override;
    void mostrar() override;

};

#endif // PROBLEMACBC_H