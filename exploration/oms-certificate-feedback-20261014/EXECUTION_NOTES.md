# Notas de ejecución y límites del registro

El protocolo, el generador de cortes, exportación, adaptadores, conductor y
verificador global quedaron fijados antes de nuevas optimizaciones en design.json
y cinco snapshots. El replay comprueba esos hashes. El verificador de análisis
de resultados, las notas, el informe y el empaquetador se elaboraron después de
observar resultados; no cambian decisiones de resolución.

Preflight: 24 cortes de los doce patrones de nive heredados se comprobaron por
álgebra exacta y caja. Ambos importadores preservaron las filas nuevas y aceptaron
Starts sin optimizar. Son preparación/validación, no llamadas MIP experimentales.
El ensayo no recibe esos testigos/cortes; únicamente la meta escalar anterior.

Ejecución: 24 llamadas iniciales y 36 posteriores, secuenciales según las colas
fijadas. Las 42 salidas de estrategia cuentan A/B por separado y cobran el
prefijo compartido en cada brazo que lo usa. No hay errores registrados, excesos
de referencia, nuevos brazos, semillas añadidas, llamadas descartadas ni retuning
después de congelar el diseño. Los datos importados coinciden con el original.

Los 51 LP no son 51 patrones distintos: una cache solo evita repeticiones dentro
del mismo brazo. Se certifican 44 patrones distintos, de los cuales 30 inviables.
Los nueve cache hits se resuelven por referencia a pruebas previas permitidas.
No se importan pruebas de otro brazo/semilla, salvo el prefijo compartido fijado.

La selección de nive y la meta proceden de investigaciones anteriores; no son
un conjunto de prueba independiente. Las tres semillas no constituyen réplicas
independientes de modelos distintos. No se estiman significancia o efectos
poblacionales. La máxima duración solicitada al solver es común, pero no la
duración efectiva por parada numérica temprana. Se informa calidad junto al tiempo.

La inferencia final se limita al ensayo: los cortes aprendidos no mejoraron
el costo exactamente respaldado y añadieron trabajo. No se concluye que Benders,
otras políticas de realimentación o toda certificación preventiva sean inútiles.
No se certifica optimalidad global ni completitud del banco de cortes. Las notas
teóricas/propuestas posteriores no se cuentan como resultados experimentales.
