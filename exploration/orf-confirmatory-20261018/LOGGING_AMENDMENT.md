# Enmienda de registro nativo — 19 de octubre de 2026

Durante la auditoría del paquete se detectó un defecto del runner: el entorno
Gurobi tenía OutputFlag=0 y el modelo lo heredaba. Los archivos solver.log solo
contienen la cabecera, aunque resultados, puntos, parámetros, hashes y tiempos
se conservaron y sus residuos se verificaron independientemente.

Se conserva completa esa primera campaña. Antes de nuevas llamadas se fijó
LOGGING_AMENDMENT.json con el hash del diseño, de cada resultado anterior y del
runner corregido. Se repiten las 360 asignaciones, sin selección por resultado,
en el mismo orden y con los mismos modelos, factores y parámetros de optimización.
El único cambio es OutputFlag=1 para escribir trazas nativas completas. Los
resultados se guardan en logging-confirmation/, sin sobrescribir los anteriores.

Se cotejan puntos, trabajo, nodos, estado, objetivos y cotas con la primera
campaña; las soluciones nuevas se verifican de nuevo racionalmente. Los tiempos
se informan por separado. Son réplicas técnicas de las mismas instancias y
semillas, no nuevas instancias ni observaciones estadísticamente independientes.
Los 72 testigos exactos y las 17 cotas globales ya adquiridos se reutilizan porque
las representaciones son idénticas; no se hacen nuevas llamadas LP.

El total será 720 MIP (360 principales y 360 de confirmación del registro),
además de los 96 intentos LP originales. Las contradicciones o discrepancias
entre campañas se conservarán sin repetir selectivamente casos adversos.
