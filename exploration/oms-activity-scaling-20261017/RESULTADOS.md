# Resultado del candidato basado en actividades SOS1

Se completaron las 54 llamadas declaradas: dos modelos externos de descubrimiento,
dos presupuestos en las activaciones (1e-4 y 1e-8), tres semillas nuevas y seis
políticas. Los controles lineales invariantes por presupuesto se resolvieron una
vez por semilla. Todos devolvieron puntos; casi todas las variantes útiles
alcanzaron WorkLimit=1, por lo que sus objetivos no son óptimos certificados.

Activity-budget satisface los presupuestos originales tras redondear las binarias
en sus 12 llamadas. SOS-unit también los satisface en sus 12 llamadas. En control30,
con el mismo tope de trabajo, las medianas de objetivo de minimización son:

| Presupuesto | Activity-budget | SOS-unit |
|---|---:|---:|
| 1e-4 | 2,36943 | 1,83523 |
| 1e-8 | 5,45573 | 1,83523 |

En cinca todos esos brazos devuelven esencialmente el mismo objetivo, sin una
ventaja computacional acreditada. Por eso el candidato no supera el control
convencional. Los resultados favorables frente a big-M no bastan para establecer
un aporte nuevo. El escalado de holguras indicadoras ya existe en SCIP.

El verificador revisó los 54 puntos, 18 exportaciones, 15.570 filas originales
en sus exportaciones y 3.456 conjuntos de hipótesis de activación. En los brazos
Activity-budget de control30 fallan 20 conjuntos de hipótesis: 16 distancias
enteras nominales y cuatro pruebas SOS. Aun así, las soluciones redondeadas
cumplen los presupuestos por comprobación directa. No se etiqueta esa observación
como garantía derivada de hipótesis incumplidas. Algunos puntos sin redondear
no cumplen sus presupuestos originales; el alcance favorable es explícitamente
el punto con binarias redondeadas y todas sus filas/cotas verificadas.

Se conserva el teorema condicional y su refinamiento posterior en THEORY.md,
sin cambiar el protocolo ni repetir la campaña para ajustar el selector.
Los datos son de descubrimiento y los presupuestos son algebraicos experimentales.
No hay validación general, certificado de optimalidad ni prueba de prioridad.

Los archivos solver.log contienen solo la cabecera: OutputFlag=0 también
suprimió el detalle del log de archivo. Se conservan los modelos completos,
hashes, parámetros, atributos finales y todos los puntos para repetir las
llamadas y verificar la precisión. No se dispone de trazas completas del árbol.
Los tiempos guardados no incluyen todo el desarrollo/selección/exportación;
no se afirma una mejora del tiempo completo.

Reproducir la comprobación sin solver: `python3 test_method.py` y
`python3 verify.py` desde esta carpeta. Para repetir las llamadas, preservar
`pilot/` y usar una copia de trabajo nueva; el preparador evita sobrescrituras.
Decisión: conservar como resultado de investigación separado; no incorporar a OMS.
