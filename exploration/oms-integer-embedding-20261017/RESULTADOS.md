# Resultado del candidato de copias enteras

El selector restaura el contrato completo de las activaciones en tres de los
cuatro pares modelo/presupuesto. En control30 a 1e-4 usa t=19 y K entre 2 y 256;
en cinca a 1e-4 usa t=16 y K=2048; en cinca a 1e-8 usa t=30 y K=2097152.
Se abstiene en control30 a 1e-8, incluido el control Raw-budget incompatible.
No se cambian ni relajan los presupuestos para ocultar esa abstención.

Se completaron 78 llamadas: tres semillas nuevas, presolve automático/desactivado,
controles de copia continua, escalado contractual sin redondeo, L2 y SOS-unit.
Todos los puntos devueltos se comprobaron con fracciones frente a filas y cotas
originales. Se comprobaron 2.592 conjuntos de hipótesis de amplificación y todos
los examinados las satisfacen. El selector se contrastó independientemente,
incluidos t mínimo, k mínimo dentro de t y la incompatibilidad declarada.

El resultado causal es negativo: en las nueve comparaciones emparejadas con
presolve automático, las copias enteras y continuas producen exactamente el
mismo vector completo de solución y el mismo objetivo. El trabajo no es idéntico,
pues el procesamiento inicial de las declaraciones enteras difiere ligeramente.
Un diagnóstico posterior de seis llamadas a presolve, sin optimize, comprueba que
los tres pares de modelos reducidos tienen matrices, dominios y objetivos idénticos.
Se eliminan las 24 copias de control30 y las 96 de cada variante de cinca.

Con presolve desactivado no aparece una ventaja consistente frente a la copia
continua. En control30, la mediana de objetivo con copia entera es 3,16534 y
con copia continua 2,66253 al mismo límite de trabajo (menor es mejor). En cinca
no se obtiene una mejora relevante respecto de controles que ya cumplen.
Los controles Raw-budget satisfacen los presupuestos redondeados en las celdas
ejecutadas, aunque su selección solo garantiza condicionalmente el punto bruto.

La formulación preserva exactamente la proyección LP y MILP del modelo contraído;
eso no hace nuevo el uso de redundancia. El criterio contractual tiene una
propiedad verificable, pero el piloto no acredita una contribución computacional
propia. No se anuncia un nuevo método validado ni se añade al artículo.

Límites: dos modelos seleccionados previamente, presupuestos algebraicos,
WorkLimit=1/TimeLimit=30 s, sin certificación de optimalidad original; logs de
cabecera por OutputFlag=0, con modelos/parámetros/atributos/puntos completos
preservados. Los tiempos no incluyen toda la construcción del selector.

Comprobación sin optimizar: `python3 test_method.py` y `python3 verify.py`.
Repetir el diagnóstico nativo de presolve: `python3 presolve_diagnostic.py`.
El análisis conjunto está en `../oms-method-search-20261017/`.
