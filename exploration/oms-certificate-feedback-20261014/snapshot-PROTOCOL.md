# Verificación exacta con realimentación de cortes

Exploración independiente de OMS y de la implementación C++ de la tesis.
El caso nive fue seleccionado después de resultados previos: este es un estudio
de mecanismo, no validación independiente de una población de MILP.

## Pregunta y variantes

¿Los certificados exactos producidos durante la resolución ayudan a obtener un
costo respaldado competitivo frente a reparar, reiniciar o usar controles fuertes?
Antes de resolver se fijan tres semillas nuevas 109,127,149 y Gurobi/HiGHS.
Presolve y escalado interno habituales, cuatro hilos, gap 1 %. Gurobi usa IF1
en todos los brazos. Tolerancias normales compartidas, con Base-tight usando
factibilidad/integralidad 1e-9. No se comparan tolerancias distintas como iguales.

Siete estrategias por solver/semilla (42 resultados):

- A: L2 numérico. Comparte la misma llamada nativa con B; su auditoría se
  informa como evaluación posterior, no trabajo que A efectuó.
- B: L2 seguido de reparación/certificación exacta.
- B-restart: tres fases L2 con el mismo patrón de reinicios y Starts que C,
  sin cortes. Retiene el mejor costo exactamente factible.
- C-aggregate: tres fases L2 y cortes agregados clásicos de dual/Farkas.
- C-guard: tres fases L2 y cortes sobre asignaciones binarias parciales,
  obtenidos de esos mismos certificados. Es Benders lógico conocido, no novedad.
- Base-B y Base-tight-B: controles fuertes sin escalado L2, con verificación.

A/B y cada control tienen una llamada hasta 30 s. B-restart y ambas C tienen
hasta tres fases de 10 s: máximo solicitado 30 s. Las tres comparten la primera
fase numérica y su auditoría, cobrada íntegramente a cada estrategia. Las otras
fases se ejecutan por separado, con cache de certificados por patrón local a
cada estrategia. No se reutilizan certificados de otros brazos o semillas.

Cada llamada solicita parada por objetivo nominal 28129.51, el 101 % del costo
factible de referencia anterior 27851. Solo se comparte ese escalar, no el punto,
sus cortes o sus certificados. La parada del procedimiento exige un costo exacto
U<=28129.51; cero numérico no basta. El objetivo es alcanzar una calidad conocida,
no probar optimalidad. Se registran también los estados y gaps del solver.

La primera fase compartida tiene prioridad de dependencia; los jobs de cada
nivel se permutan con semilla 20261014, llamadas secuenciales. Todos los tiempos
incluyen importación, cotejo, comprobación, construcción de cortes y Starts;
preparación compartida se mide aparte. Referencia de ciclo 45 s, ajustando la
solicitud MILP después de importar; no es garantía de tiempo real. Los LP exactos
tienen hasta 2 s y watchdog hasta 4 s. Se conservan fallos y excesos sin retuning.

## Certificados y cortes

Se conservan los coeficientes, objetivo, RHS, cotas y dominios originales. Los
factores L2 diádicos son los ya archivados. Los presupuestos experimentales de
aceptación siguen siendo delta=1e-4 max(1,|RHS|), beta=1e-4, enteros exactos.
No se presentan como tolerancias físicas ni operativas.

Cada patrón se verifica con LP racional, todas las cotas continuas como filas.
Un dual pi<=0, A^T pi=c_C, da una cota g(z)=pi^T(b-Bz) válida para cualquier z.
Un rayo r<=0, A^T r=0, da la condición r^T(b-Bz)<=0. Las cotas continuas
constantes se incluyen. En el MILP monolítico, los cortes agregados son
redundantes en aritmética exacta; no son una descomposición Benders completa.

Para C-guard se usan los dominios binarios originales. Un mínimo de g(z) sobre
la caja de las variables no fijadas certifica un piso de costo para una
asignación parcial S. Se elige S sin pérdida: se liberan las variables que ya
están en su extremo minimizador de g. Con piso V y piso global continuo L,
el corte c_C^T y >= V-(V-L)*dist_H(z_S,z_S^k) es válido para todo patrón binario.
Un rayo genera un conflicto parcial: se liberan variables en orden creciente
de pérdida de margen, solo si el mínimo restante sigue siendo estrictamente
positivo. La cláusula exige cambiar al menos una decisión de ese subconjunto.

Estos cortes utilizan técnicas conocidas de dualidad/Benders lógico. La validez
para otros patrones se demuestra por identidad y soporte de caja, no enumerando
solo los patrones observados. No se afirma cobertura de todo patrón desconocido.

## Exportación y comprobación

Los cortes se multiplican por una potencia de dos en la ventana de coeficientes
[1e-9,1e9]. Se impone un presupuesto de residuo exportado equivalente a 1 unidad
de costo para cortes de costo y 0.25 para desigualdades primitivas enteras de
factibilidad. Se elige la escala cercana a normalizar el máximo, respetando esas
condiciones. Un corte incompatible se omite con razón explícita.

Si hay redondeo, se calcula el soporte de alpha*a-a_hat sobre la caja original
y se redondea el RHS hacia abajo para el sentido >=. Así la fila exportada es
una consecuencia segura del corte exacto sobre la región original. Coeficientes
con extremo necesario no acotado provocan abstención, nunca debilitamiento sin
prueba. Se coteja cada coeficiente y RHS después de la importación nativa.

Las salidas crudas y sus enteros redondeados se verifican por separado, incluidas
las filas nuevas. Una etiqueta óptima o la presencia de un corte no sustituye
la certificación del patrón/costo. Se retienen los mejores testigos exactos,
conversión binary64 comprobada, y disponibilidad temporal explícita.

## Criterio de cierre

Se compara C con B, B-restart y los controles fuertes usando tiempo completo,
éxito en el objetivo de calidad, costo exacto U, patrones inviables, repeticiones,
cortes y discrepancias comprobables de cota/gap. Una mejora solo sobre L2 no
demuestra ventaja frente a controles fuertes. Tres semillas de un solo caso no
permiten inferencia poblacional. Si C solo añade trabajo sin mejora clara,
se cierra este prototipo; no se agregan semillas o modelos para buscar ventajas.
