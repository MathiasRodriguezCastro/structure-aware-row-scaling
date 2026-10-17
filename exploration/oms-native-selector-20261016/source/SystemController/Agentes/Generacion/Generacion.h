#ifndef GENERACION_H
#define GENERACION_H

#include <string>
#include <vector>
#include "../Agente.h"

/// Representa una unidad de generación de energía en el sistema.
class Generacion : public Agente {
public:
    explicit Generacion(int idAgente, int h_c, int idGeneracion): 
        Agente(idAgente, h_c), 
        idGen(idGeneracion) 
    {}

    virtual ~Generacion() override = default;

    inline void setIdGen(int id) noexcept { idGen = id; }
    inline int getIdGen() const noexcept { return idGen; }

    inline void setCoefParticipacionDespacho(double coef) noexcept { coefParticipacionDespacho = coef; }
    inline double getCoefParticipacionDespacho() const noexcept { return coefParticipacionDespacho; }

protected:
    int idGen = -1; ///< Identificador único de la generación
    double coefParticipacionDespacho = 1;
};

#endif // GENERACION_H