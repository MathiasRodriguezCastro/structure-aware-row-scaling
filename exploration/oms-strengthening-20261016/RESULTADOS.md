# Resultados nuevos para fortalecer OMS

La versión OMS v1.3.11 incorpora el resultado de frontera y dos comprobaciones
acotadas de software y validez. Mantiene dos contribuciones principales. La
extensión conjunta permanece en un documento separado.

## Régimen precisión–esfuerzo

La campaña fijada antes de resolver conserva **330 MILP y 30 abstenciones**.
Con potencia fija .01 MW, presolve automático y presupuestos de **30–100 m3**,
los seis modelos califican en las tres semillas frente a NF3: cumplen los
objetivos, usan menos trabajo, no presentan más contradicciones detectadas y
no empeoran más de 1 % en costo de candidato.

A 100 m3 la razón emparejada Budget/NF3 es **0,362 en trabajo** y **0,629 en
tiempo total**. Se conservan todos los resultados adversos. Esto no certifica
la cota global de cada optimización. La recuperación primal sobre L2 sigue
localizada en 046 sin presolve; la evidencia nueva es un régimen más amplio de
esfuerzo y consistencia de los informes.

[Protocolo y resultados](../oms-frontier-20261016/RESULTADOS.md).

## Implementación sin cambiar el modelo

El selector C++ integrado reproduce exactamente los factores y los datos
binary64 de Python en doce pares modelo/política. La preparación Budget-L2 es
**3,70–6,37 veces más rápida** según la mediana por modelo. Se conservan
**336 mediciones**: se repitió todo el diseño después de corregir el CSV de
auditoría. Se verifican 120.960 filas y 25.920 contratos.

Es una mejora de preparación, no una aceleración demostrada del MILP completo.
Se incorpora brevemente al suplemento.

[Implementación y mediciones](../oms-native-selector-20261016/RESULTADOS.md).

## Garantías globales comprobables

Se verificaron **seis cotas LP globales exactas**, relajando todas las binarias.
Junto con testigos enteros exactos, certifican al 1 % tres modelos y prueban el
**óptimo MILP exacto de 031**. Son certificados del Base original; no se transfieren
gratuitamente a todas las exportaciones flotantes. Esta tabla de referencia se
incorpora al suplemento.

El seguimiento separado refina las 18 salidas del prototipo conjunto mediante
**13 LP de patrón distintos**. Devuelve **18 puntos exactamente factibles**:
**9 certificados globalmente al 1 % y 3 óptimos exactos**. Los otros nueve
mantienen intervalos amplios. El costo adicional suma 23,98 s de adquisición
global y 48,52 s de refinamiento, además de selección, solver y adquisición de
los testigos de referencia.

[Certificados, costos y límites](../oms-global-lp-20261016/RESULTADOS.md).

## Algoritmo conjunto: dirección separada

Se caracterizó e implementó el escalamiento dyádico conjunto con contratos,
RHS, objetivo, cotas y columnas enteras inmóviles mediante un grafo de
diferencias. Un verificador independiente comprueba potenciales y ciclos:
84 casos y 16.893.360 desigualdades enteras.

Para 100 m3, el mejor entero de centrado pasa de **17 a 8** en los seis modelos.
La ablación compara 72 brazos con **54 llamadas únicas**: 18 del piloto, 36
nuevas y 18 aliases declarados antes de resolver. El conjunto contractual usa
menos trabajo que el conjunto sin contratos en cinco modelos; en 001 la razón
es **0,0355**, pero en 031 **empeora 2,81 veces**. Todas las variantes cumplen
el objetivo preestablecido de 100 m3; no se redefine después para fabricar una
recuperación de factibilidad.

El control más fuerte aclara el límite: frente al Budget-L2 por filas ya
disponible, el conjunto consume **22,2 % más trabajo agregado** y solo mejora
en dos modelos. El addendum conserva los hashes de los dos CSV ya verificados.
No se presenta la mejora frente a un control más débil como una ventaja sobre
el método actual.

La formulación logarítmica y los grafos son clásicos. Hay matemática e impacto
computacional tangibles, pero faltan una revisión de novedad más amplia y
validación externa. Tampoco se ha medido una ventaja del ciclo completo que
incluya selección. Por eso no se añade como otra contribución principal.

[Derivación y ablación](../oms-joint-contracts-20261016/RESULTADOS.md).

## Alcance y entrega

Los seis modelos siguen siendo de una familia conocida. Los pilotos externos
anteriores de STN-Scheduler y MIPLIB no mostraron una ventaja general de
aceptación del contrato; no se repitieron para buscar un resultado favorable.
No se retoman DW, cortes o predictores sin una necesidad demostrada.

La evidencia fortalece el artículo, pero no vuelve innegable su publicación.
Se preservan resultados adversos, versiones anteriores y límites de cada
garantía. No se envió el manuscrito ni se publicó un depósito. El DOI de Zenodo
queda para el último paso, según lo pedido.
