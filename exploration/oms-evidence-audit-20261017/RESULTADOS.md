# Respuesta a las tres objeciones científicas

Esta revisión fortalece la evidencia dentro de su alcance. No demuestra una
ventaja general entre familias ni identifica una operación interna del solver.
Es un análisis secundario de campañas ya observadas: no agrega optimizaciones.

## 1. Novedad y aporte a software

La transferencia de residuos y el escalado según tolerancias son antecedentes,
no una nueva identidad matemática. La documentación de
[Gurobi](https://support.gurobi.com/hc/en-us/articles/26284047605521-How-do-I-scale-my-model-to-improve-its-numerical-properties)
y el trabajo de [Pritchett, Howell y Grebow](https://engineering.purdue.edu/people/kathleen.howell.1/Publications/Conferences/2017_AAS_PriHowGre.pdf)
ya están citados en el artículo. La documentación de
[ScaleModel](https://pyomo.readthedocs.io/en/6.9.1/api/pyomo.core.plugins.transform.scaling.ScaleModel.html)
también establece que aplicar factores desde el modelador no es nuevo.

La contribución defendible está en la especificación implementada y evaluada:

| Función | Evidencia que la respalda |
|---|---|
| Seleccionar dentro del contrato o abstenerse con una razón | Intervalos, reservas enteras y pruebas del selector |
| Conservar la representación escrita y sus límites | Comprobaciones binary64, productos diádicos y lectura del exportado |
| Comprobar el punto en las unidades originales | Verificadores, puntos guardados y presupuestos declarados |
| Separar precisión, trabajo y validez de cotas | Controles emparejados, testigos exactos, resultados adversos y desconocidos |
| Integrar el selector con costo medido | Implementaciones Python/C++ y 18 ciclos con puntos, trabajo y extremos idénticos |

No se afirma prioridad universal para esta combinación ni se añade otro teorema.
El abstract, las contribuciones, el trabajo relacionado y la carta presentan ese
aporte como software y evaluación verificable.

## 2. Robustez dentro de la muestra conocida

Se comprueban las 14 celdas presupuesto/presolve de la frontera, incluidos los
resultados adversos y las abstenciones. La siguiente tabla resume los dos puntos
favorables con presolve automático e IntFeasTol=1e-9. El comparador es NF3.

| Medida | 30 m³ | 100 m³ |
|---|---:|---:|
| Pares con menor trabajo | 18/18 | 18/18 |
| Razón geométrica de trabajo | 0,411 | 0,362 |
| Rango al retirar cualquier modelo completo | 0,373–0,519 | 0,329–0,499 |
| Rango al retirar cualquier semilla completa | 0,380–0,446 | 0,347–0,387 |
| Pares con menor tiempo completo | 11/18 | 14/18 |
| Cumplen todos los presupuestos | 18/18 | 18/18 |
| Contradicciones detectadas de cota/cierre | 0/0 | 0/0 |
| Máximo deterioro del costo candidato | 0,799 % | 0,0074 % |

El promedio favorable no depende de un solo modelo ni de una sola semilla de los
observados. Las eliminaciones son análisis descriptivos, no intervalos de
confianza ni pruebas sobre una población de modelos. Los costos candidatos no
son gaps MILP certificados. Las semillas no crean modelos independientes.

Se conserva el contraejemplo de tolerancia: con 2^-28, 30 m³ produce 18
abstenciones y 100 m³ conserva una cota refutada. Se conserva asimismo cada celda
adversa con otro presupuesto o sin presolve. Solo se probaron los puntos 30 y
100: no se afirma un intervalo continuo favorable.

La auditoría anterior identifica las filas y los factores cambiados. No permite
atribuir la diferencia a una operación interna de presolve, LP o búsqueda. El
comparador NF3 representa otro remedio numérico; su diferencia de parámetros
impide interpretar esta comparación como una ablación de un componente interno.

## 3. Transferencia externa: procedimiento sí, aceleración general no

Las ocho instancias son horizontes del mismo ejemplo externo Kondili, con tres
semillas. Todos los cocientes siguientes son emparejados contra L2 y usan los
24 casos, sin seleccionar resultados.

| Método | Cumple presupuestos | Trabajo/L2 | Tiempo completo/L2 | Cotas contrastadas con testigo |
|---|---:|---:|---:|---:|
| L2 | 24/24 | 1,000 | 1,000 | 3/24 |
| Budget-L2 | 24/24 | 0,960 | 1,054 | 3/24 |
| L2-tight | 24/24 | 1,003 | 0,990 | 3/24 |
| L2-NF3 | 23/24 | 1,732 | 1,004 | 3/24 |

Budget-L2/NF3 da 0,554 en trabajo y 1,049 en tiempo completo. La caída del
trabajo no compensa el costo del proceso en estos solves cortos. El procedimiento
cumple los presupuestos externos, pero L2 también lo hace. Hay 84 de 96
contrastes de cotas desconocidos, no 84 certificados correctos. El desglose
predefinido de seis horizontes sin anclas conocidas se conserva en el CSV y
mantiene 18/18 cumplimientos de Budget-L2 y L2; sigue siendo la misma familia.

Demostrar una ventaja computacional semejante en otra familia sigue abierto.
Una futura campaña tendría que fijar familias, instancias, presupuestos y
comparadores antes de resolver, conservar los controles L2/tolerancias/NF3 y
medir todo el ciclo con calidad comparable. El resultado de esa campaña no se
puede prometer ni sustituir por otra redacción del manuscrito.

## Comprobación y reproducción

`check.py` no importa `analyze.py`: contrasta los 222 pares con los resultados
crudos y los tiempos registrados por los procesos padre, verifica 244 agregados
y reconstruye las razones externas desde los 96 resultados originales.
Los promedios geométricos calculados con logaritmos se comprueban con productos
decimales de 80 dígitos. Se guardan hashes de los insumos y todos los resultados.

```bash
python3 exploration/oms-evidence-audit-20261017/analyze.py
python3 exploration/oms-evidence-audit-20261017/check.py
python3 exploration/oms-evidence-audit-20261017/write_tables.py
```

La incorporación añade la Tabla S22 al suplemento y unas frases al artículo.
No modifica datos, factores, modelos, puntos ni campañas cerradas. La entrega
v1.3.13 permanece intacta; las revisiones usan un nuevo número de versión.
