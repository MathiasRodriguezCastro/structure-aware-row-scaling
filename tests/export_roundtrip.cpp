#include "SystemController/Problema/ProblemaLp/ProblemaLp.h"
#include <iostream>

int main() {
    ProblemaLp model;
    model.añadirVariable("x", 0, 2.345678901234567e-15, 1.2345678901234567);
    model.añadirVariable("y", 3, 0., 0.);
    model.añadirRestriccion("tiny", {{1e-300,"x"}, {-1.2345678901234567,"y"}}, "<=", 1e-20);
    model.añadirTerminoFuncionObjetivo(9.876543210987654e-100,"x");
    model.procesar(false);
    std::cout << model.getArchivo();
}
