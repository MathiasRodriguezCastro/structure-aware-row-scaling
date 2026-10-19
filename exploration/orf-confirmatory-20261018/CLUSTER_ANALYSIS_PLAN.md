# Incertidumbre agrupada por escenario — 19 de octubre de 2026

Análisis solicitado después de conocer los resultados, separado del protocolo
prospectivo original. Las decisiones siguientes se registran antes de calcular
los intervalos. No hay nuevas resoluciones ni selección de resultados favorables.

- Se incluyen todos los 24 escenarios y sus tres semillas (101, 137, 173),
  también los casos con contradicciones. Las repeticiones técnicas de logging
  no aumentan el tamaño muestral y no entran en estos intervalos.
- Para cada control (Base, Base-tight, L2 y L2-NF3), se promedian primero los
  logaritmos de las tres razones emparejadas Budget/control en cada escenario.
  Se promedian después los 24 valores y se exponencia. Por estar balanceado el
  diseño, el estimador coincide con la media geométrica anterior de 72 pares.
- Bootstrap no paramétrico de 100000 remuestras: seleccionar 24 escenarios con
  reemplazo y conservar juntas sus tres semillas y las políticas emparejadas.
  Las mismas selecciones sirven para trabajo, tiempo completo y cuatro controles.
  No se remuestrean semillas individualmente. No se filtran contradicciones.
- Intervalos percentiles marginales del 95%, cuantiles 0,025 y 0,975 con
  interpolación lineal en escala logarítmica, seguidos de exponenciación.
  No son intervalos simultáneos ni pruebas de hipótesis.
- Generador NumPy PCG64, semilla 2026101902; escenarios ordenados por nombre.
  Después del cálculo global, se continúa el mismo flujo PRNG para los horizontes
  24, 72 y 168, remuestreando ocho escenarios dentro de cada uno. Esos intervalos
  por horizonte son descriptivos y especialmente inciertos con solo ocho grupos.
- Una victoria de escenario requiere que la media de los tres logaritmos sea
  menor que -1e-12; entre -1e-12 y 1e-12 se registra empate numérico. Se conservan
  las 96 agregaciones escenario/control y los hashes de las selecciones.
- La incertidumbre es condicional a los seis padres conocidos, el generador y
  las tres semillas fijadas. Remuestrear escenarios trata estos como unidades
  intercambiables de la mezcla empírica; no incorpora incertidumbre por elegir
  otros padres, aplicaciones o configuraciones. No prueba independencia de los
  padres compartidos, cobertura exacta con 24 grupos ni optimalidad MILP.

Referencia metodológica: C. A. Field y A. H. Welsh, *Bootstrapping clustered
data*, JRSS B 69 (2007), 369–390, DOI 10.1111/j.1467-9868.2007.00593.x.
El remuestreo de grupos conserva la dependencia dentro de cada grupo.
