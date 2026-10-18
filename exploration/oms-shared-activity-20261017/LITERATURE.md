# Antecedentes y límites de la prioridad

Consulta del 17-10-2026. Fuentes primarias; la búsqueda no demuestra ausencia
de antecedentes ni prioridad de una fórmula.

- [SCIP, implementación de indicadores](https://scipopt.org/doc-10.0.2/html/cons__indicator_8c_source.php):
  `scaleslackvar` y `usesameslackvar` ya implementan normalización de holguras y
  uso compartido. La regla basada en la media absoluta de coeficientes sirve
  como control específico del seguimiento; se aproxima diádicamente y se
  ejecuta con Gurobi, por lo que no es una comparación entre solvers.
- [SCIP, descripción de indicadores](https://scipopt.org/scip/doc-9.0.1/html/cons__indicator_8c.php):
  la representación mediante una holgura y SOS1 es conocida. No se reclama
  novedad por sustituir una implicación big-M por esa formulación.
- [Gurobi, tolerancias y escalado](https://docs.gurobi.com/projects/optimizer/en/current/concepts/numericguide/tolerances_scaling.html):
  las tolerancias son absolutas; las implicaciones big-M pueden sufrir fugas,
  y SOS/indicadores pueden mejorar precisión con mayor costo. Ese diagnóstico
  y esa recomendación tampoco son nuevos.
- [Gurobi, restricciones SOS](https://docs.gurobi.com/projects/optimizer/en/current/concepts/modeling/constraints.html):
  la condición de cero SOS usa `IntFeasTol`; la reformulación automática puede
  introducir big-M. Se fija `PreSOS1BigM=0` en todos los brazos.
- [MIPLIB 2017, artículo de la biblioteca](https://link.springer.com/article/10.1007/s12532-020-00194-3):
  el verificador de la biblioteca utiliza un criterio relativo para filas y
  cotas. Aquí se usan presupuestos algebraicos absolutos declarados. Un fallo
  de este estudio no implica necesariamente rechazo del punto por MIPLIB.

La parte candidata que se investiga es la caracterización necesaria y
suficiente del radio diádico sujeto simultáneamente a precisión, ventana de
coeficientes y representación exacta; su selección sin optimizador; y la
proyección del mejor centrado dentro de ese intervalo. Las pruebas no bastan
para presentarla como contribución práctica: necesita superar controles fuertes
en puntos verificados y costo. La invariancia de unidades por sí sola tampoco
es exclusiva de la propuesta.
