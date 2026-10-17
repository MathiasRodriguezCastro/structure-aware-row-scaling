# IntegralityFocus y costo completo del flujo

Fijado el 15 de octubre de 2026 antes de nuevas resoluciones MILP. Investigación
auxiliar a OMS v1.3.6, que se conserva sin modificaciones.

## Preguntas y alcance

1. ¿IF1 recupera la precisión original de L2 en el contraste conocido sin presolve?
2. ¿Cuál es el costo completo del procedimiento reproducible, desde la entrada del
   generador hasta verificar el punto devuelto, sin omitir la construcción común?

Un caso retrospectivo, SG-Ter-Mer/instance046; semillas ya fijadas 11, 23 y 47.
Diseño factorial: L2 y Budget-L2 × IF0/IF1 × tres semillas = doce llamadas nuevas.
Las seis IF0 son controles contemporáneos y permiten medir todo el flujo con la
misma instrumentación; no se agrupan con las llamadas históricas. Orden aleatorio
fijo con semilla 20261015. Ejecuciones secuenciales, sin inicios MIP.

## Transformación y controles

Cada tratamiento ejecuta el generador C++ solver-free sobre la entrada original,
construyendo una única vez el modelo. Obtiene Base y calcula factores usando el
selector y kernel L2 existentes. Ventana [1e-9,1e9], sin veto de banda identidad;
solo se multiplican filas completas y RHS. No se alteran variables, objetivo,
cotas o integralidad. Budget conserva los presupuestos exigentes 0,01 MW/100 m³,
las conversiones por fila y las reservas de redondeo/exportación del contraste.
Ambas políticas usan gamma = 2^-28. La regla y los factores no se ajustan tras
observar resultados. Todo Base y todo export escalado deben reproducir exactamente
el SHA-256 del archivo histórico correspondiente antes de resolver.

Gurobi 13.0.2: Threads=4, TimeLimit=120 s, MIPGap=0.01, FeasibilityTol=1e-6,
IntFeasTol=2^-28, ScaleFlag=-1, Presolve=0, IntegralityFocus en {0,1}. Los demás
parámetros quedan en sus valores predeterminados. Se conserva el archivo importado,
parámetros, log, punto y métricas nativas. Se cotejan matrices nombradas, RHS,
objetivo, cotas y dominios entre lectores antes de la optimización.

## Contabilidad temporal

Cada llamada usa un proceso Python nuevo. El padre mide la duración íntegra de
ese proceso, que incluye arranque, imports, creación del entorno del solver,
construcción del modelo, selección, serialización, importación, resolución,
extracción, verificación y persistencia. La orquestación del padre y los análisis
posteriores se separan. No se resta una preparación común ni se amortiza entre
políticas. Se informan además etapas disjuntas dentro del proceso:

- generación C++: lectura de entrada, lanzamiento, construcción y exportación Base;
- lectura/canonicalización y metadatos;
- selección de factores;
- exportación escalada;
- lectura de referencia y comprobaciones de integridad;
- entorno Gurobi, importación y parámetros;
- cotejo de la importación;
- resolución;
- extracción/persistencia del punto;
- verificación;
- resto del proceso, incluida persistencia del resultado.

El agregado de generación C++ no distingue construcción y escritura Base. Ambas
están incluidas; no se anuncia un tiempo aislado de construcción. Compilación del
ejecutable y adquisición histórica de testigos exactos son costos fuera de línea,
declarados y no incluidos en el ciclo. La factibilidad exacta de esos testigos se
revalida durante el análisis independiente y su tiempo se informa por separado.

Hay otro proceso de cálculo de tesis activo al preparar este estudio. Se registra
la carga del sistema; el reloj describe estas ejecuciones compartidas, no un
benchmark aislado ni evidencia de aceleración general. Work es el indicador de
trabajo comparativo, sujeto a los estados y a la calidad verificada.

## Verificación y decisión

Residuos exactos de datos binary64 y coordenadas guardadas en las filas físicas y
de activación, antes y después de redondear enteros; máximos por presupuesto,
violación entera observada, cotas y diagnóstico de las demás filas. Presupuestos
físicos son objetivos numéricos del estudio, no normas del operador.

Separar el cumplimiento primal de la información de optimalidad. Los testigos
existentes del mismo archivo importado dan cotas superiores exactas U. Se marca
B>U más el margen de presentación max(1e-6,8 ulps(B)), y una finalización nativa al
1 % contradicha si U<C-0.01|C|. No marcar una cota no la certifica. Un testigo no es
un óptimo MILP; no se ejecutan nuevos LP exactos ni se busca mejor testigo después
de ver las salidas. Toda llamada asignada, incluso fallida o sin punto, permanece
en el denominador; no se descartan semillas por resultado.

Si IF1 es suficiente, se documenta como alternativa competitiva; si falla, se
delimita el resultado a este caso/configuración. Solo una aclaración sustantiva y
breve justificaría una incorporación posterior al paper. El estudio de costos no
crea por sí solo otra contribución científica.
