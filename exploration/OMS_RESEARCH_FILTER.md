# Filtro de investigación para el artículo OMS

Actualizado el 16 de octubre de 2026 por indicación de Mathias: investigar
solamente lo que pueda fortalecer el objetivo de este artículo. Una tarea
pendiente de tesis no se convierte por ello en una prioridad para OMS.

## Preguntas que pertenecen al paper

1. **Mecanismo del escalamiento externo.** ¿Qué explica los efectos que sobreviven
   al escalamiento interno y presolve? Una intervención controlada debe aportar
   más información que otra tabla de tiempos o números de condición.
2. **Valor de información del generador.** ¿Cuándo presupuestos explícitos cambian
   una decisión útil frente a un control con el mismo kernel y frente a remedios
   numéricos competitivos? Cambiar factores sin mejorar una necesidad real no
   establece utilidad operacional.
3. **Uso verificable en software.** ¿La selección, exportación y comprobación
   permiten cumplir requisitos explícitos, abstenerse con una razón comprobable
   y distinguir precisión primal de afirmaciones de optimalidad?

La evidencia ya incorporada sobre activaciones responde parcialmente a 2 y 3,
con costos y dependencias de configuración explícitos. Las exploraciones más
recientes no han establecido otra ventaja práctica general.

## Investigaciones cerradas

La intervención con incumbente común y el control IF1 quedaron cerrados e
incorporados de forma acotada en las Tablas S14–S15. La nueva comparación
`oms-matched-accuracy-20261016` completa 144 resultados terminales, más un intento
interrumpido por reinicio y conservado. Compara los cuatro remedios en los seis
modelos y ambas configuraciones de presolve. El replay racional confirma que la
recuperación primal sigue limitada a instance046 sin presolve; el control NF3
cumple con mayor trabajo y sin las contradicciones detectadas en Budget-L2.
La incorporación breve en la sección 7.9 y Tabla S16 documenta ese límite.

No queda una búsqueda activa de más kernels, teoremas o barridos para OMS.
`oms-matched-accuracy-20261016/DECISION.md` distingue lo medido, los pilotos sin
ventaja adicional y las expansiones opcionales no realizadas.

## Líneas apartadas de esta búsqueda

- LP–DW, cortes y fortalecimiento de la formulación: otras preguntas de tesis;
  no continúan como pendientes que haya que resolver para OMS.
- Más generalizaciones teóricas del escalamiento sin necesidad demostrada en
  los casos reales: no se persiguen para engrosar el artículo.
- Factores exactos ampliados: extensión comprobada de software, sin beneficio
  adicional de admisibilidad en los presupuestos físicos actuales. No se abre
  otra campaña MILP por mejorar únicamente el centrado.
- Predictor: no se entrena con una muestra insuficiente ni se busca una regla
  después de observar resultados de confirmación.

## Criterio editorial

Para entrar al paper, un resultado debe responder a una de las tres preguntas,
tener controles pertinentes y comprobación independiente, declarar adquisición
y costos adicionales, y aportar información suficiente para justificar el espacio.
No hace falta que toda investigación produzca una adición. OMS v1.3.9 conserva las dos contribuciones principales; todas las versiones
anteriores permanecen congeladas.

## Reapertura autorizada el 16-10-2026

El documento nuevo de Mathias autorizó las líneas adicionales. La frontera de
330 MILP y 30 abstenciones sí cumple el criterio fijado de utilidad: los seis
modelos califican a 30 y 100 m3 con presolve auto. Se incorpora a OMS v1.3.11
con la integración C++ medida y los certificados Base en el suplemento. La
extensión conjunta y su refinamiento permanecen en notas separadas; no se
presentan sus antecedentes clásicos como una contribución nueva ya establecida.
La recuperación primal respecto de L2 sigue localizada, y la validez externa
sigue limitada. El cierre anterior se conserva como historia de la decisión.
