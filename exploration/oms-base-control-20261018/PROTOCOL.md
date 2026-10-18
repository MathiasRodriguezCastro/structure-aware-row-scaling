# Control pendiente del resultado favorable de OMS

Fecha: 18-10-2026. Estudio dirigido posterior a los resultados publicados en la
versión local v1.3.14; no se presenta como parte de su diseño original.

Pregunta: ¿Budget-L2 ofrece una ventaja frente al modelo sin escalado externo,
a precisión y calidad comparables, en los mismos seis modelos del estudio favorable?

## Asignaciones fijadas antes de las nuevas resoluciones

Modelos 001,005,022,027,031,046; semillas 59,71,89; presolve automático.
36 llamadas nuevas: Base y Base-tight, sin elegir modelos según resultados.
Base-tight cambia únicamente FeasibilityTol a 1e-9: la tolerancia entera común
ya es 1e-9. Threads=4, TimeLimit=120 s, MIPGap=.01, ScaleFlag=-1,
IntegralityFocus=0, NumericFocus=0. Sin starts ni modificaciones del generador.
La versión del solver debe coincidir con la histórica (Gurobi 13.0.2).
Orden aleatorio fijo 2026101807; procesos frescos y ejecución secuencial local.
No se fija WorkLimit, que tampoco estaba presente en el experimento original.

Se genera Base una sola vez por llamada y se comprueba su hash contra la
exportación histórica. Se cotejan matriz, RHS, objetivo, cotas y dominios con
el importador nativo antes de resolver. Los logs y puntos se conservan.

## Evaluación y controles históricos

Las soluciones nuevas se comprueban a 0.01 MW y a ambos presupuestos 30/100 m3,
sin resolverlas de nuevo por presupuesto. Se reconstruyen exactamente, mediante
Fraction, los residuos crudos y con enteros redondeados, las cotas de variables,
la integralidad y el objetivo de los datos binary64 originales. Se informa además
el máximo de cada familia física y las filas no físicas: satisfacer los objetivos
físicos no equivale a factibilidad racional exacta de todo el MILP.

Se reutilizan las 36 llamadas Budget-L2 históricas de ambos presupuestos para
comparar Work, verificando sus puntos, parámetros, hashes y modelo importado.
Los testigos racionales existentes se verifican en la representación realmente
resuelta antes de contrastar cotas y cierres (mismo criterio de ulps/1% histórico).
La ausencia de contradicciones detectadas no certifica optimalidad MILP.
El objetivo de cada candidato se compara por par, con diferencia relativa al
valor absoluto del objetivo del control; no se llama óptimo al incumbente.

Los tiempos nuevos se registran, pero no se comparan con los tiempos históricos
como un experimento de aceleración controlado. Si Budget-L2 mejora Work frente
a AMBOS controles en agregado y en al menos cuatro modelos, cumple todos los
presupuestos, no tiene más contradicciones detectadas y no pierde más del 1%
en ningún objetivo emparejado, se permite una confirmación temporal intercalada
de las políticas pertinentes, cuyo diseño deberá fijarse antes de resolver.
Una ventaja solo frente a Base convencional no supera este filtro si Base-tight
la explica. Ninguna pérdida de calidad puede contarse como aceleración.

Si no pasa ese filtro, se cierra con estos resultados y se limita explícitamente
la afirmación del artículo al comparador NF3. No se buscan otras instancias,
semillas, presupuestos o parámetros para rescatar una victoria. La comparación
puede revelar un compromiso precisión/esfuerzo o una interpretación adversa.

## Procedencia

Diseño, protocolo, runner, dependencias e insumos se fijan por SHA256 antes del
primer MILP. No se sobrescriben asignaciones interrumpidas: se retienen y requieren
una enmienda explícita. Las versiones congeladas anteriores permanecen intactas.
Equipo local compartido; mismo host/CPU que la campaña original. No se necesita
ClusterUY y no se ejecuta trabajo en su login. DOI pendiente para el final.
