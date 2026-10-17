# Seguimiento OMS — 17 de octubre de 2026

[RESULTADOS.md](RESULTADOS.md) reúne los resultados, límites y comandos.
[PROTOCOL.md](PROTOCOL.md) fija los cuatro alcances antes de resolver.

Los datos están en `mechanism/`, `external/`, `tolerance/` y `native-cycle/`.
Los scripts `check_mechanism.py`, `check_external.py` y `check_dispatch.py`
comprueban resultados sin optimizar. `external_case.py` verifica el caso físico.
Los runners originales no se modifican. El generador C++ nativo aislado ya existe
bajo `exploration/oms-native-selector-20261016` y las fuentes STN conservan su MIT.
Se incluyen fallos de preflight y refinamientos desconocidos con sus logs.

176 nuevos MILP, 8 intentos LP y 18 abstenciones; las 54 llamadas de tolerancia
1e-9 son reutilizadas, no experimentos nuevos. El DOI permanece diferido.
