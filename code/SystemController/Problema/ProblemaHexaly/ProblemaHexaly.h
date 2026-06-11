#ifndef PROBLEMAHEXALY_H
#define PROBLEMAHEXALY_H

#include "SystemController/Problema/Problema.h"
#include <string>
#include <map>

// Forward declarations para no exponer los headers de Hexaly
// en toda la cadena de includes del proyecto.
namespace hexaly {
    class HexalyOptimizer;
}

class ProblemaHexaly : public Problema {
private:
    hexaly::HexalyOptimizer* optimizer = nullptr;

public:
    ProblemaHexaly();
    virtual ~ProblemaHexaly() override;

    void procesar(bool flagConstante) override;
    void grabar(std::string& ruta) override;
    void resolverMonolitico() override;
    void mostrar() override;
};

#endif // PROBLEMAHEXALY_H
