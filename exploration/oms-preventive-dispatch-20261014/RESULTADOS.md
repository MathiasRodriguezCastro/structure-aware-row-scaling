# Resultados de las otras dos líneas

Estudio independiente de OMS, con fuentes C++ sin modificar.

## Garantías preventivas

Hay una envolvente computable de todas las familias duales y de Farkas usando
menores enteros y Hadamard, sin enumerar vértices/rayos. Protege costo para
patrones factibles y excluye los inviables bajo las hipótesis racionales y
enteras indicadas. Se comprobaron las hipótesis de acotación con ocho pruebas
duales y las familias completas de tres sistemas pequeños (diez patrones).
No se establece novedad; la prueba es una cota suficiente muy conservadora.

| Modelo | Continuas | Factor uniforme suficiente | Aproximación decimal |
|---|---|---|---|
| breastcancer-regularized | 9 | 2^(-88) | 10^(-26) |
| control30-3-2-3 | 242 | 2^(-15540) | 10^(-4678) |
| neos-1112787 | 1640 | 2^(-100092) | 10^(-30131) |
| neos-3083784-nive | 1539 | 2^(-35429) | 10^(-10665) |
| neos-3661949-lesse | 135 | 2^(-8555) | 10^(-2575) |
| rn8 | 192 | 2^(-15425) | 10^(-4643) |
| rn8-base | 192 | 2^(-14081) | 10^(-4239) |
| sg8 | 104 | 2^(-7559) | 10^(-2275) |

El factor multiplica todos los presupuestos algebraicos originales, incluidas
cotas; epsilon=1 unidad de costo, margen de Farkas rho=1/2. No es el presupuesto
máximo admisible. Su pequeñez no prueba que todo presupuesto mayor sea inseguro.
No se calculó la constante de Hoffman óptima de esos modelos.

Para un maestro continuo, el margen entero no se traslada automáticamente:
y>=z,y<=1/2 admite parámetros inviables z arbitrariamente cercanos a 1/2.
No existe un presupuesto positivo uniforme que preserve todos sus parámetros
continuos. La existencia de una continuación y la precisión de su costo son
garantías distintas. Ver DERIVACION.md y complete-small-checks.json.

## Selección de cortes del despacho

Se implementó Benders temporal multicut sobre tres LP reales archivados de ocho
períodos, dos RN relacionados y un SG. Cinco políticas y tres repeticiones:
45 corridas, 1896 LP de recourse, 237 LP maestros, 24 LP para pisos compartidos
y nueve referencias compactas. Los pisos y los 1896 duales/cortes se comprueban
racionalmente; las decisiones de filtrado se reproducen sin solver.

| Modelo | Política | Iteraciones | Cortes | Mediana de segundos completos |
|---|---|---|---|---|
| SG | All | 6 | 30 | 0.0855 |
| SG | Top | 9 | 30 | 0.0982 |
| SG | RawDiverse | 9 | 30 | 0.0991 |
| SG | ProjectedDiverse | 9 | 30 | 0.0993 |
| SG | Physical | 9 | 30 | 0.0996 |
| RN | All | 2 | 8 | 0.0799 |
| RN | Top | 3 | 8 | 0.0851 |
| RN | RawDiverse | 3 | 8 | 0.0855 |
| RN | ProjectedDiverse | 3 | 8 | 0.0855 |
| RN | Physical | 3 | 8 | 0.0855 |
| RN-base | All | 3 | 16 | 0.0787 |
| RN-base | Top | 5 | 16 | 0.0900 |
| RN-base | RawDiverse | 5 | 16 | 0.0907 |
| RN-base | ProjectedDiverse | 5 | 16 | 0.0907 |
| RN-base | Physical | 5 | 16 | 0.0906 |

Los filtros no mejoran All y no reducen el número final de cortes. La geometría
cruda es ortogonal por soportes horarios disjuntos; la proyección hidráulica no
produjo una mejora. La etiqueta física fue siempre balance/demanda: la ablasión
física no tuvo variación y no permite afirmar que esa información carezca de valor.
El compacto tarda alrededor de 1–2 ms. No hubo un maestro grande cuyo costo
justificara filtrar, ni se estudió el MILP completo.

Todas las corridas coinciden numéricamente con la referencia; residuo máximo
original final 9.41e-10. Dos LP tienen certificado racional de óptimo; en RN,
SoPlex devolvió unknown, sin prueba de inviabilidad ni certificado de óptimo.
Los tres intentos exactos fueron posteriores y no influyeron en las políticas.
Ver AUDITORIA_DESPACHO.md para las conclusiones y límites de las notas anteriores.

## Estado real

Ambas líneas avanzaron más allá de una propuesta. No se resolvió todavía cómo
obtener presupuestos uniformes útiles para los modelos grandes, ni apareció un
selector que mejore el despacho. No se incorporó material a OMS v1.3.5. Los
resultados y el intento de referencia sin certificar se conservan completos.
