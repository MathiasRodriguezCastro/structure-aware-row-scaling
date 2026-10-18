# Budget-L2 frente al modelo sin escalado externo

18 de octubre de 2026. Control dirigido del resultado favorable de OMS.

**Sí: hay una ventaja de trabajo frente a Base y Base-tight en esta muestra.**
Los tres métodos cumplen todos los presupuestos en 18/18 llamadas, sin
contradicciones de cota/cierre detectadas. A 100 m³, el deterioro máximo
del costo candidato de Budget-L2 es inferior al 0,1%.

| Comparador | Trabajo Budget/control | Menor trabajo | Tiempo completo intercalado | Menor tiempo |
|---|---:|---:|---:|---:|
| Base | 0.316638 | 17/18 | 0.621018 | 9/18 |
| Base-tight | 0.264194 | 18/18 | 0.570007 | 9/18 |

Se agregan 36 controles (6 modelos × 3 semillas × 2 políticas) y se
reutilizan 36 llamadas Budget-L2 de 30/100 m³. Presolve automático,
IntFeasTol=1e-9, potencia 0,01 MW, Gurobi 13.0.2, cuatro hilos, 120 s,
gap solicitado 1%. Base mantiene el escalado interno automático;
Base-tight cambia solo FeasibilityTol a 1e-9. No se cambia el generador.
El diseño es posterior a los resultados anteriores y anterior a estos controles.

Se verifican exactamente las 10.080 filas originales antes/después de
redondear, cotas, dominios, objetivos y 18 testigos racionales existentes
de las representaciones realmente resueltas. No se adquieren nuevos LPs.

Los seis modelos mejoran en media frente a ambos controles. En instance031
la razón contra Base es 0,993: una mejora pequeña; una llamada Base es
ligeramente más barata que Budget-L2. Se conservan todos los pares.

El resultado pasa el filtro fijado de trabajo, precisión y calidad.
Se fijan entonces 54 repeticiones a 100 m³, en 18 bloques consecutivos
(modelo, semilla), con orden aleatorio de las tres políticas por bloque.
Solo esas mediciones contemporáneas se usan para comparar segundos.
Son más rápidos 9/18 pares ante cada control; los modelos cortos 005,022,031
pagan el costo de preparación y resultan más lentos.
Incluyen proceso fresco, generación una vez, selección/exportación cuando
corresponde, importación/cotejo, solver, extracción, verificación y persistencia.
Compilación y adquisición histórica de testigos son costos separados.

Cumplen 54/54; contradicciones detectadas de cota/cierre: 0/0; límites: 0.
Coinciden 54/54 extremos nativos y 54/54 puntos con los anteriores.

La mejora es de esfuerzo a los presupuestos y calidad candidata comprobados.
Base también cumple y obtiene residuos de agua menores. Son seis modelos
conocidos de una familia y las mismas semillas, en una máquina compartida.
El intercalado no equivale a aislar el hardware. Los costos candidatos no
son gaps MILP igualmente certificados. Ausencia de contradicción detectada
no certifica todas las cotas, optimalidad ni superioridad general.

Se incorporan los controles a OMS (resumen, introducción, Tabla 12 y S23).
Se agregan 90 MILP y se reutilizan 36; los 126 puntos permiten 2.540.160
comprobaciones de filas originales. La sensibilidad histórica, resultados
adversos y versión v1.3.14 se conservan. El DOI sigue diferido.

Reproducción sin resolver, desde la raíz:

```bash
python3 exploration/oms-base-control-20261018/check.py --allow-absent-historical
python3 exploration/oms-base-control-20261018/confirmation.py check
python3 scripts/research/oms_base_tables.py
```

El flag omite solo PDFs históricos ausentes; los insumos científicos son obligatorios.
