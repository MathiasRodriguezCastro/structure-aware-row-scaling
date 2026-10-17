# Qué permite concluir la implementación real

Fuentes inspeccionadas, copiadas sin modificar en `source-audit/`:

- `ProblemaBranchAndPrice.cpp`: árbol externo con maestro restringido de
  columnas/perfiles completos, pricing por bloque y fijaciones de binarias.
- `seccion_descomposicion_matematica.tex`: identifica acoples de demanda y
  adopta Dantzig–Wolfe; presenta Benders como alternativa condicionada a otra
  partición. Las instancias usadas son determinísticas o parametrizadas.
- `ANALISIS_BENDERS.md` y `verify_benders4.py`: análisis y ejemplo anterior
  de proyección de continuas con binarias en maestro. No constituyen un
  selector Benders productivo sobre el despacho. No se reejecutó aquí el
  barrido previo de ejemplos ni se contabilizó como evidencia nueva.

## Distinciones que importan

La igualdad entre el Benders-LP completo y el LP compacto es correcta para
esa proyección. **No demuestra** que Benders deba ser más lento: dos algoritmos
con la misma cota pueden tener costos de resolución diferentes. Tampoco que una
relajación más débil impida a cualquier algoritmo superar en tiempo a otro.
Las afirmaciones de rendimiento en la nota anterior son predicciones, no teoremas.

Un LP con una selección hidráulica fijada puede ser una buena heurística sin
certificar las decisiones enteras globales. No se debe equiparar su buen
resultado empírico con la equivalencia algorítmica entre fijación y Benders.
Finalmente, Benders lógico con recourse entero y DW no son intercambiables en
general. La conexión depende de formulación, partición y cortes concretos.
No se modificaron esas notas históricas ni las fuentes C++.

## El experimento nuevo

Los tres MPS son exportaciones reales almacenadas de ocho períodos. Contienen
104/192/192 variables y 168/240/240 filas, todas continuas. Se conservaron sus
coeficientes y regiones de confianza originales, con `escalas.tsv` como procedencia.
RN y RN-base están relacionados: no equivalen a modelos independientes nuevos.

Se colocan volúmenes, caudales y vertimientos en el maestro. Los balances de agua
permanecen íntegros allí y el resto se separa en ocho LP horarios. Se coteja
fila por fila que no se pierden filas, cotas, variables ni costo, y que ningún
subproblema necesita variables de recourse de otro período. Se usa separación
real de variables; no se agregan únicamente filas redundantes al monolítico.

El maestro tiene 24/64/64 variables físicas y ocho epígrafes de recourse. Sus
igualdades hidráulicas tienen rango numérico 8/24/24. Todos los duales de costo
se reconstruyen racionalmente; las filas nuevas se exportan con redondeo hacia
el exterior, comprobado sobre las cajas originales. La geometría usa SVD y es
una heurística numérica; no es necesaria para la validez de los cortes.

## Lo que se identificó y lo que no

Los gradientes horarios de un mismo lote usan soportes temporales disjuntos:
su coseno crudo es exactamente cero. Gram–Schmidt puede llamar diversos a todos
ellos aunque los balances del maestro coordinen las decisiones. Proyectar sobre
el núcleo de esas igualdades cambia la geometría, pero los cosenos medios
absolutos observados siguen por debajo de 0.000258. No produjo una ventaja.

La normalización por anchos usa un piso de una unidad para anchos pequeños o
variables libres. Es una elección heurística registrada, no una métrica física
universal ni una invariancia a todo cambio arbitrario de unidades. Antes de
aplicar PCA deben fijarse las escalas, y sus componentes no pueden sustituir
cortes mediante combinaciones de signos arbitrarios: pueden perder validez.

La regla de etiqueta dual agrupó **todos los 1896 candidatos** bajo balance/
demanda. El incentivo a representar otra familia quedó inactivo: este ensayo
no mide el valor de distinguir información hidráulica frente a térmica. Los
subproblemas tampoco produjeron rayos de inviabilidad; su filtrado no se evaluó.

All requirió 2/3/6 iteraciones y 8/16/30 cortes en RN/RN-base/SG. Cada filtro
requirió 3/5/9 iteraciones y terminó con el mismo número de cortes. Los maestros
son diminutos; el costo del conjunto de cortes no fue un cuello de botella.
El compacto tardó alrededor de 0.001–0.002 s, frente a 0.079–0.100 s del
procedimiento certificado incluyendo preparación. Son tiempos locales muy
pequeños, sin inferencia de significancia o generalización.

Dos referencias tienen certificado racional de óptimo LP. RN terminó
`unknown` en SoPlex: se conserva el intento, sin cambiar opciones para lograr un
resultado favorable. Las 45 corridas coinciden numéricamente con el compacto,
pero RN no adquiere un certificado de óptimo exacto por esa coincidencia.
El máximo residuo original observado en los puntos finales es 9.41e-10.

## Consecuencia

Hay un prototipo comprobable y un resultado negativo para este banco. No hay
fundamento para incorporar el selector a C++ ni presentarlo como contribución
de OMS. No se sigue que el filtrado Benders sea inútil para muchos escenarios
o grandes maestros. Para una siguiente etapa habría que demostrar primero
que el despacho elegido produce muchos cortes y que mantenerlos consume una
parte importante del tiempo; además, que la información física varía y puede
evaluarse. No se amplía este banco para buscar una mejora después del resultado.

La bibliografía reciente distingue selección entre duales de un subproblema y
filtrado de un lote de cortes. Nuestro ensayo estudia lo segundo. Existe un
antecedente muy directo de violación/diversidad/clustering en flujo con escenarios:
[Donkiewicz y Gaul, preprint de 2026](https://optimization-online.org/wp-content/uploads/2026/04/donkiewicz2026benderscutfiltering.pdf).
Para selección geométrica y Pareto, véanse
[Hosseini y Turner](https://arxiv.org/abs/2110.08448) y
[Glomb, Liers y Rösel](https://doi.org/10.1007/s12532-025-00291-1).
No se reprodujeron sus algoritmos completos ni sus benchmarks; no se afirma
superioridad sobre ellos ni novedad de combinar eficacia y diversidad.
