# Seguimiento acotado para evaluar una posible versión 1.5

19 de octubre de 2026. Investigación separada: v1.4.2 sigue congelada.
Este plan se fija antes de las nuevas resoluciones. La selección de modelos no
depende de sus tiempos, resultados ni contradicciones anteriores. No se promete
un resultado favorable ni se interpreta una falta de significación como equivalencia.

## I. Primer candidato comprobado de calidad común

- Los 24 escenarios prospectivos ya conocidos; no son una nueva muestra ciega.
  Referencia independiente: el testigo racional Base de cada modelo, ya verificado.
- Base, L2, Budget-L2 (100 m3 / 0,01 MW), L2-NF3; semillas 211, 257 y 293:
  288 llamadas nuevas. Gurobi 13.0.2, cuatro hilos, 30 segundos, gap pedido 1%,
  presolve y ScaleFlag automáticos, FeasibilityTol 1e-6, IntFeasTol 1e-9.
  Nuevo orden intercalado fijado con Random(2026101905).
- Calidad primaria: z(x) <= U_ref + 0,001 max(1,|U_ref|); sensibilidad 0,01.
  Es comparación con un testigo factible, no certificación de un óptimo o gap.
- Capturar todos los eventos MIPSOL, incluyendo candidatos que no mejoren el
  incumbente, y el punto final postsolve. Guardar vector completo, instante de
  descubrimiento, trabajo, nodos y objetivo; ninguna prueba racional dentro del
  callback. No introducir starts, cortes ni criterios de parada dependientes del
  resultado del verificador. Los callbacks instrumentan todas las políticas.
- Comprobar racionalmente datos y puntos binarios64: presupuestos físicos en
  crudo y tras redondear enteros; distancia entera <=1e-9; cotas de variables
  exactas del punto redondeado; para filas sin unidad física declarada, error
  hacia atrás <=1e-6, con denominador max(1,|b|,sum |a_j x_j|). Reportarlo por
  separado de los presupuestos físicos, sin llamarlo factibilidad exacta total.
- Distinguir tiempo al descubrimiento de un candidato que luego pasa el control
  de tiempo de disponibilidad de esa comprobación: aquí el verificador corre
  después de que termina el solver. Reportar ambos y el costo del verificador.
  Un final nativo sin alcanzar el umbral es un objetivo no alcanzado durante la
  ejecución observada, aunque el solver declare optimalidad.
- Resultados primarios: éxitos, fallos de dominio/precisión/calidad, tiempos y
  trabajo al primer candidato aceptable. Razones de tiempos de descubrimiento
  solo entre éxitos emparejados, identificando su selección. Además, PAR2 sobre
  todos los casos: sustituir un objetivo no alcanzado por 60 s de resolución
  (más preparación en la métrica de proceso). Bootstrap de 24 escenarios,
  manteniendo juntas sus tres semillas, 100000 remuestras, semilla 2026101906.
  No ocultar fallos mediante el resumen de éxitos comunes.

## II. Presupuestos, información física y exportación efectiva

- Análisis de selección en los 24 modelos; resoluciones en escenarios 01 y 08
  de cada horizonte (seis modelos), elegidos por índice antes de nuevas llamadas.
- Cuatro especificaciones experimentales, no estándares del operador:
  uniforme 10 m3/0,01 MW; referencia 100 m3/0,01 MW;
  uniforme 1000 m3/0,01 MW; heterogénea: activación 10 m3,
  balance de agua 0,001 m3 y potencia 0,001 MW. El balance a un litro es una
  meta de conservación numérica, no una afirmación sobre medición operativa.
- Dos selectores: el Budget-L2 anterior y el prototipo de selección con errores
  reales de exportación. Reutilizar las llamadas de referencia del experimento I
  para el primero. Tres semillas por modelo/configuración: 54+72=126 llamadas.
- Evaluar también activación a 1 m3 sin resolver: comprobar si la reserva de
  redondeo entero agota el presupuesto. Incompatibilidad de la condición
  suficiente no significa infactibilidad física del modelo ni violación observada.
- Contrastar factores, porcentaje de intervención, q=v/delta por familia y
  reserva suficiente R/delta. No usar una tolerancia nominal como residuo observado.
- Control numérico compilado: retirar etiquetas físicas después de convertir
  todos los requisitos a unidades algebraicas. Si los factores/exportes son
  idénticos, documentar la identidad; no atribuir diferencias causales a etiquetas
  que el solver no recibe ni gastar otra campaña en modelos idénticos.
- Prototipo: buscar en un conjunto finito declarado de factores binarios64
  alrededor del factor ideal, extremos, una malla logarítmica y potencias de dos.
  Verificar coeficientes/RHS realmente serializados a 17 cifras y la desigualdad
  epsilon+B(alpha)+alpha E <= alpha delta con aritmética racional. Elegir el
  certificado de menor distancia logarítmica al L2 dentro de esa lista.
  No afirmar optimalidad sobre todos los factores representables. Si la lista no
  contiene una elección certificada, abstenerse sin afirmar inexistencia global.
  Un error exactamente cero no requiere una cota finita de esa variable.

## III. Robustez acotada

- CPLEX 22.1.2 completo: índices 01,03,05,07 por horizonte, tres semillas y
  Base/L2/Budget-L2: 108 llamadas, mismos exportes, precisión y límite de 30 s.
  EPRHS 1e-6, EPINT 1e-9, gap 1%, cuatro hilos, escalado predeterminado.
  Usar búsqueda tradicional para instrumentar IncumbentCallback en todas las
  políticas; documentar que no es una equivalencia interna con Gurobi.
- Gurobi ScaleFlag=0 y 2: índices 01 y 08 por horizonte, mismas tres políticas
  y semillas: 108 llamadas. Automático se reutiliza de I, sin nuevas réplicas.
- Conservar los fallos, puntos y trazas completos. Comparar precisión, calidad,
  objetivos alcanzados, tiempo y cotas contradichas cuando haya un testigo de la
  representación realmente importada. Una referencia del modelo original no
  demuestra factibilidad exacta en un exporte diferente. Marcar desconocidos.
  No comparar directamente unidades de trabajo entre solvers.

Total previsto: 630 MIP, más pruebas sintéticas y del selector identificadas como
tales. Sin cambios al generador, los modelos ni v1.4.2. Procesos frescos,
secuenciales, en esta máquina compartida; no CPU intensiva en login de ClusterUY.
No se publicará automáticamente una v1.5: primero informe y evidencia completa;
incorporar solo una contribución clara, sin agrandar el artículo por resultados
marginales. El DOI sigue reservado para el final por decisión del autor.
