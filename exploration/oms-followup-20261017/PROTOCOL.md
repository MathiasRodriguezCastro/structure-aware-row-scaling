# Seguimiento acotado OMS — 17 de octubre de 2026

Autorización: pendientes del adjunto de Mathias y pedido de continuar. No se modifica
ninguna campaña cerrada ni el generador original. No se promete un resultado favorable.

## B. Mecanismo, antes de nuevas llamadas
Reanalizar los seis casos y los siete presupuestos de la frontera existente.
Registrar, por fila, familia, factor L2 y contractual, reserva entera y de exportación,
intervalos, umbral de presupuesto a partir del cual L2 es admisible y coeficientes
exportados. Relacionar con las tres semillas existentes, sus residuos y B/G flags.
Verificar que las únicas filas cambiadas son las identificadas y distinguir asociación
de atribución de una operación interna del solver. Cero llamadas nuevas en esta fase.

## A. Portabilidad aplicada independiente
Usar la fuente STN-Scheduler/Kondili ya archivada, sin modificarla. Ocho horizontes
fijados: 8,10,12,16,20,24,32,40; 10 y 12 son anclas conocidas del piloto negativo,
los otros seis son nuevas instancias de la misma aplicación externa.
Presupuestos ya usados: masa 1e-5 kg, lógica 1e-5, dinero 1e-3 unidades de la fuente.
Son objetivos numéricos del estudio, no exigencias industriales. Selección diádica
exacta, ventana [1e-9,1e9], epsilon 1e-6 y reserva entera explícita; mismo gamma en
los cuatro controles de cada modelo: gamma=1e-9 (también L2-tight), FeasibilityTol
1e-6 salvo L2-tight=1e-9; NF3 añade NumericFocus=3. Semillas nuevas 131,137,149; L2, Budget-L2,
L2-tight y L2-NF3, presolve auto, 4 hilos, 30 s y gap pedido 1%: 96 asignaciones.
Ocho referencias NF3/semilla 127, previas y separadas, suministran un patrón entero
para un único intento de LP exacto por modelo (10 s). Si falta testigo, el control de
contradicciones se declara desconocido, sin buscar patrones hasta que funcionen.
Se conservarán límites, abstenciones y fallos. No se reejecutarán resultados adversos.
La portabilidad se evalúa separadamente de precisión adicional o menor trabajo.

## C. Tolerancia entera, mismo resto de parámetros
Seis modelos de despacho conocidos, semillas 59,71,89, presolve auto, presupuestos
30/100 m3 y 0.01 MW, gamma en {1e-9,2^-28}. Budget-L2 en ambos presupuestos y
NF3 como control: 108 asignaciones, de las cuales 54 ya existen a gamma 1e-9.
Solo resolver las asignaciones nuevas compatibles; incompatibilidad de la garantía
no es inviabilidad del MILP. Conservar testigos previos solo cuando se demuestre
igualdad de la exportación; de lo contrario un único LP exacto de patrón por exportación.
No ajustar el presupuesto ni el gamma según los resultados.

## D. Ciclo completo con selector nativo
Mismos seis modelos, Budget-L2 a 0.01 MW/100 m3/gamma 1e-9 y semillas 59,71,89.
Comparar Python/C++: 36 procesos nuevos, diseño emparejado con orden aleatorio.
Usar el binario C++ aislado ya verificado; activar/desactivar el selector en el mismo
binario. Ambas ramas incluyen startup, generación una vez, metadata, selección,
exportación, lectura/cotejo nativo, resolución, verificación física y persistencia.
La metadata Base archivada necesaria para auditar el original se lee dentro del
proceso en ambas ramas. Comprobar igualdad completa y orden de filas/columnas antes
de comparar trabajo; registrar discrepancias, no atribuirlas a velocidad del selector.
No ejecutar otras campañas propias simultáneamente con este benchmark. Registrar
carga del sistema y mantener todas las repeticiones; no seleccionar las más rápidas.
Compilation y testigos exactos se excluyen y se declaran por separado.

## Cierre y criterio editorial
Primero obtener resultados y verificarlos independientemente. No ampliar los teoremas
ni reclamar certificación general. Cada resultado adverso o nulo se conserva en la nota.
Solo incorporar al paper evidencia que delimite el mecanismo, la transferibilidad o
el coste real del procedimiento; no agregar una tercera contribución. Reducir abstract
a menos de 200 palabras; el autor confirmó que la beca CAP no apoyó este trabajo.
DOI sigue reservado para el final, sin publicación ni subida automática.
