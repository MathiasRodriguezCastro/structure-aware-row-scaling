#ifndef PROBLEMALP_H
#define PROBLEMALP_H

#include "../Problema.h"
#include <vector>
#include <string>

class ProblemaLp : public Problema {
private:
    std::string archivo;
public:
    // Constructor / destructor
    ProblemaLp();
    virtual ~ProblemaLp() override = default;

    void setArchivo(const std::string& a)  { archivo = a; }
    std::string getArchivo() const { return archivo; }

    // --- Métodos de solución ---
    void setValorVariable(double coef, std::string nombre);

    // --- Procesar / Exportación / Resolución ---
    void procesar(bool flagConstante) override;
    virtual void grabar(std::string& ruta);
    void resolverMonolitico() override;

    // --- Utilidad ---
    void mostrar() override;
};

#endif // PROBLEMALP_H
