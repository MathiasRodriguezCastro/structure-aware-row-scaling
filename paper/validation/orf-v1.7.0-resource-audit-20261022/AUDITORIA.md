# Hallazgo de empaquetado en v1.7.0

El inventario confirmó los 3.840 conjuntos de resultados, archivos de candidatos,
logs nativos y relojes completos, además de los 480 informes por bloque. La
comprobación ampliada detectó que faltaban auxiliares de instalación del clúster,
entre ellos `cluster/WHEELS.json` y programas `.py` referidos por los lanzadores.
El filtro del archivo crudo incluía `.slurm` y `.sh`, pero no esos `.py` y `.json`.

Las fuentes editables recompilaron y los verificadores prospectivos y del
seguimiento pasaron antes de llegar a ese control de cobertura. No se declara
que esta auditoría ampliada haya pasado íntegramente. El registro anterior
corresponde a sus controles originales; no comprobaba esta cobertura adicional.

La corrección v1.7.1 añade un complemento pequeño con los auxiliares existentes,
sin modificar el tar sellado ni los resultados científicos. Se valida la versión
corregida antes de congelarla. FINDING.json identifica los archivos afectados.
