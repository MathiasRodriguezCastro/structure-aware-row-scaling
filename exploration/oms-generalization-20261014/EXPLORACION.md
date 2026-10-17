# Exploración preliminar: contratos transferibles y decisión numérica

Trabajo separado de la entrega congelada `v1.3.5-oms-submission`. Se incorpora
evidencia al artículo únicamente si aporta una conclusión clara, verificable y
acotada. No se promete encontrar superioridad ni se seleccionan modelos por sus
resultados. Este documento se actualizará con observaciones y conclusiones.

**Estado al cierre del piloto:** [RESULTADOS.md](RESULTADOS.md) y
[exploration-note.pdf](exploration-note.pdf) contienen las observaciones verificadas.
Se conservaron 55 brazos y 52 puntos. La portabilidad quedó comprobada; no se
demostró una ventaja de aceptación primal de Budget-L2. El artículo no se amplía.
Hay un prototipo finito con siete tests y 96 certificados de incompatibilidad.

## Pregunta central

¿Un contrato explícito mejora la precisión primal verificada fuera del generador
hidrotérmico, con presolve normal, y qué costo tiene frente a normalizar filas,
reducir tolerancias o usar controles numéricos existentes?

Hay cuatro líneas separadas:

1. Aplicación independiente: planificación de producción por lotes mediante el
   generador público STN-Scheduler. Se conservarán los datos originales y el commit
   de la fuente. El método `trace` identifica kg para inventarios y lotes. La
   precisión numérica se declara en esas unidades, sin tolerancias industriales.
2. Seleccionar, resolver, verificar y corregir o abstenerse: prototipo separado,
   con comprobación de todas las filas, cotas y dominios y un número finito de
   alternativas. Aceptación primal y validez de optimalidad son estados distintos.
3. Diagnóstico previo: razones de presupuesto, amplificación entera y deriva de
   exportación. La inadmisibilidad es falta de una garantía suficiente, no una
   predicción de que el solver fallará. Se registrarán los falsos positivos.
4. Piloto externo en MIPLIB Numerics: selección anterior a cualquier resolución,
   por dimensiones, número de no ceros y diversidad de grupos. Se guardan todos
   los resultados, incluidos los desfavorables. No hay presupuestos físicos.

## Diseño preliminar

La selección de MIPLIB se fija en `MIPLIB_SELECTION.json`: modelos mixtos
etiquetados Numerics y easy, hasta 5.000 variables, 5.000 filas y 50.000 no ceros;
los primeros tres grupos distintos al ordenar por no ceros y nombre. El estado
easy permite limitar el costo de un piloto y no equivale a facilidad numérica.
Este diseño no es una muestra representativa de MIPLIB.

Antes de resolver se archivarán modelos y decisiones de factores. Los kernels
serán los existentes, aplicados a toda la fila y RHS. Se conservarán objetivo,
cotas y dominios. Controles: Base, GM, Row-L2, Budget-L2, tolerancias estrictas y,
en Gurobi, NumericFocus 3. HiGHS proporciona una segunda implementación; no tiene
un parámetro NumericFocus equivalente. Se usan presolve y escalado interno
normales, llamadas secuenciales, cuatro hilos, semilla piloto 17, gap 1 % y límite
15 s. Pilotos y confirmación con semillas nuevas se identificarán por separado.

Los objetivos de precisión, las tolerancias enteras igualadas y cualquier
incompatibilidad se fijarán al inspeccionar las unidades y los modelos, antes de
observar resultados. Si un dato es no finito o una importación elimina términos,
se documentará el impedimento; no se reemplazará una fila problemática por otra
más conveniente. La verificación se referirá al modelo realmente identificado
por sus hashes y distinguirá toda diferencia con el archivo de origen.

## Error de exportación: formulación a comprobar

Para una fila `aᵀx ≤ b`, factor positivo α y fila efectivamente importada
`âᵀx ≤ b̂`, sean `e = αa − â` y `e_b = αb − b̂`. En una caja válida `[l,u]`,

`R⁺ = Σ max(e_j l_j, e_j u_j) − e_b`.

Así, si el residuo exportado firmado es a lo sumo ε y el redondeo entero puede
aumentar la actividad original en E, la violación del punto redondeado está
acotada por `max(0, (ε + R⁺)/α + E)`. Para igualdades se comprueban ambos signos.
La hipótesis sobre la caja debe verificarse para el punto crudo; no basta confiar
en el parámetro de tolerancia. Los términos con error cero no requieren cotas
finitas. Una cota necesaria infinita produce abstención del certificado uniforme.

Esto es una cota de soporte elemental, no una novedad demostrada. Se contrastará
con la reserva ya presente en el seguimiento de activaciones y con la literatura
de verificación numérica. El posible aporte es el procedimiento ejecutable y su
utilidad comprobada, no renombrar una desigualdad conocida.

## Criterio para incorporar algo al artículo

Una transferencia de código que simplemente funciona no basta para ampliar las
contribuciones. Una mejora aislada diseñada tras observar resultados tampoco.
Se requiere precisión mejor verificada en un modelo independiente, controles
adecuados, explicación del mecanismo y costo declarado. Un hallazgo útil pero
negativo puede orientar la investigación y quedarse en este documento.

## Fuentes primarias y alcance

- [MIPLIB Numerics](https://miplib.zib.de/tag_numerics.html): la página consultada
  enumera 193 instancias excluidas del benchmark por dificultades numéricas.
- [STN-Scheduler](https://github.com/jckantor/STN-Scheduler): generador independiente
  de planificación de procesos por lotes. Fuentes y licencia se guardan en `sources`.
- [Guía numérica de Gurobi](https://docs.gurobi.com/projects/optimizer/en/current/concepts/numericguide/tolerances_scaling.html):
  contexto de tolerancias, escala, presolve y reformulación de activaciones.

Las páginas, metadatos y hashes de descarga se conservan en `sources`.
