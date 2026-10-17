# Resultado de las líneas de exploración

La pregunta de las notas originales era si los contratos podían aportar una
ventaja práctica transferible, verificable y defendible frente a alternativas
fuertes, sin agrandar el paper con resultados accesorios.

| Línea | Trabajo concluido | Resultado y límite |
|---|---|---|
| Aplicación independiente | Generador público STN-Scheduler con unidades identificadas y MIPLIB Numerics; piloto archivado en [el primer estudio](../oms-generalization-20261014/RESULTADOS.md). | El kernel se transfiere conservando el modelo. STN no demuestra una ventaja de aceptación del contrato. Las precisiones elegidas son numéricas, no estándares industriales. |
| Seleccionar, resolver, verificar, corregir o abstenerse | [Controlador y reparación](../oms-decision-study-20261014/RESULTADOS.md), retención y veto de cotas; después [Starts y cambio de representación](../oms-quality-followup-20261014/RESULTADOS.md). | Las entregas se verifican; reparación y abstención son necesarias. Un testigo exacto permite refutar cotas incompatibles, pero no validar las demás. La selección por menor costo numérico puede preferir un cero sin continuación exacta: este estudio lo diagnostica, sin reescribir las ejecuciones. |
| Diagnóstico previo de utilidad | Razón nominal mu, exportación, redondeo y factores incompatibles; comprobación posterior en grupos nuevos. | La condición suficiente no es un predictor de fallos. En el nuevo estudio hay 64 fuentes aceptadas con mu nominal mayor que uno. No se obtiene una regla validada para elegir automáticamente Budget frente a controles fuertes. |
| Generalización y comparación fuerte | 80 tratamientos congelados antes de resolver: cuatro grupos explícitos no usados, referencia conocida, dos semillas nuevas y dos solvers, presolve habitual. [Informe actual](RESULTADOS.md). | En otro grupo Gurobi, Budget recupera entregas que L2 pierde, pero Base/IntegralityFocus y tolerancias estrictas también cumplen. HiGHS no presenta esa ventaja de aceptación. No se prueba superioridad general. |
| Calidad y significado del objetivo | Auditoría posterior de las 16 entregas de nive, sin repetir MILP; 12 certificados primal/dual y cuatro rayos guardados y comprobados. | Un costo cero dentro del presupuesto puede tener mínimo exacto positivo o enteros sin continuación. El alcance es el LP con esos enteros fijados. Los recuentos son de entregas; L2/Budget duplican patrones. |

La observación nueva más útil es la última: obliga a separar costo nominal,
factibilidad exacta del patrón y optimalidad global, y muestra con certificados
por qué presupuestos ligados a un RHS big-M pueden ser inadecuados para atribuir
sentido al costo. No contradice el contrato de residuos ni constituye por sí
sola nueva dualidad o un algoritmo MILP globalmente certificado.

El diagnóstico de costo pondera cada presupuesto por su multiplicador dual o
costo reducido. En nive, el efecto permitido es tan grande que no protege el
costo. Es información comprobable para evaluar una especificación de precisión,
no una nueva garantía universal ni una prueba de que el método sea más rápido.

**Decisión:** se cierra esta tanda con todos sus resultados, favorables y
desfavorables. No se abre otra selección de instancias para buscar ventajas.
No hay evidencia que justifique añadir una tercera contribución o ampliar la
campaña principal de OMS. Una posible aclaración compacta del alcance queda
en [INCORPORACION_CANDIDATA.md](INCORPORACION_CANDIDATA.md), fuera del envío
congelado. El artículo v1.3.5 y los tres paquetes previos conservan sus hashes.

Para continuar con una hipótesis distinta, primero habría que definir un nuevo
requisito de aplicación o una regla de decisión y un diseño independiente que
lo pueda refutar. Repetir semillas o elegir otro caso favorable no resuelve
por sí solo la falta de ventaja frente a los controles.
