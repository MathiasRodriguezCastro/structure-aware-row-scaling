# Resultado primario: actividad compartida de radio mínimo

195 configuraciones/semillas completadas y verificadas; 65 exportaciones con parámetros distintos.
Las cinco unidades de fila no son aplicaciones diferentes. Los aliases se fijaron antes de resolver.
Una escritura truncada se preservó y repitió una vez; no se cuenta como observación independiente.

| Modelo | Política | Precisión / 3 | Calidad / 3 | Trabajo mediano |
|---|---|---:|---:|---:|
| control30-3-2-3 | Raw-budget | 0 | 0 | 0.04839 |
| control30-3-2-3 | Tight-raw | 3 | 0 | 5.01 |
| control30-3-2-3 | NF3-raw | 0 | 0 | 0.1255 |
| control30-3-2-3 | SOS-unit | 0 | 0 | 5.011 |
| control30-3-2-3 | SOS-normalized | 3 | 0 | 5.011 |
| control30-3-2-3 | SOS-range | 0 | 0 | 5.002 |
| control30-3-2-3 | Individual-budget | 0 | 0 | 0.5858 |
| control30-3-2-3 | Shared-budget | 0 | 0 | 0.5788 |
| control30-3-2-3 | Indicator-budget | 3 | 0 | 5.009 |
| neos-3421095-cinca | Raw-budget | 3 | 3 | 1.922 |
| neos-3421095-cinca | Tight-raw | 3 | 3 | 1.732 |
| neos-3421095-cinca | NF3-raw | 3 | 3 | 5.011 |
| neos-3421095-cinca | SOS-unit | 3 | 3 | 5.001 |
| neos-3421095-cinca | SOS-normalized | 3 | 3 | 5.008 |
| neos-3421095-cinca | SOS-range | 1 | 1 | 5.001 |
| neos-3421095-cinca | Individual-budget | 3 | 3 | 5.007 |
| neos-3421095-cinca | Shared-budget | 3 | 3 | 5.011 |
| neos-3421095-cinca | Indicator-budget | 0 | 0 | 5.009 |
| neos-1112787 | Raw-budget | 1 | 1 | 1.18 |
| neos-1112787 | Tight-raw | 3 | 3 | 1.634 |
| neos-1112787 | NF3-raw | 1 | 1 | 5.017 |
| neos-1112787 | SOS-unit | 2 | 2 | 5.042 |
| neos-1112787 | SOS-normalized | 3 | 3 | 5.031 |
| neos-1112787 | SOS-range | 0 | 0 | 5.02 |
| neos-1112787 | Individual-budget | 3 | 3 | 5.013 |
| neos-1112787 | Shared-budget | 1 | 1 | 5.021 |
| neos-1112787 | Indicator-budget | 3 | 3 | 1.577 |
| beasleyC3 | Raw-budget | 3 | 3 | 3.059 |
| beasleyC3 | Tight-raw | 3 | 3 | 2.754 |
| beasleyC3 | NF3-raw | 3 | 2 | 5.046 |
| beasleyC3 | SOS-unit | 3 | 2 | 5.006 |
| beasleyC3 | SOS-normalized | 3 | 1 | 5 |
| beasleyC3 | SOS-range | 3 | 3 | 5 |
| beasleyC3 | Individual-budget | 3 | 3 | 5.003 |
| beasleyC3 | Shared-budget | 3 | 3 | 5.004 |
| beasleyC3 | Indicator-budget | 3 | 3 | 5 |
| k16x240b | Raw-budget | 3 | 2 | 5.038 |
| k16x240b | Tight-raw | 3 | 2 | 5.046 |
| k16x240b | NF3-raw | 3 | 1 | 5.012 |
| k16x240b | SOS-unit | 3 | 3 | 5.005 |
| k16x240b | SOS-normalized | 3 | 0 | 5.018 |
| k16x240b | SOS-range | 3 | 0 | 5.021 |
| k16x240b | Individual-budget | 3 | 1 | 5.015 |
| k16x240b | Shared-budget | 3 | 1 | 5.015 |
| k16x240b | Indicator-budget | 3 | 2 | 5.009 |

La propuesta de radio mínimo no muestra superioridad general. En control30 falla la entrega
redondeada en las tres semillas y algunas hipótesis nominales no se cumplen en las salidas.
La selección algebraica admisible no equivale a garantía incondicional del backend.
Las exportaciones compartidas son idénticas bajo cinco cambios de unidad en los cinco modelos;
esa propiedad también puede tenerla una normalización convencional.

El seguimiento prospectivo compara una elección centrada con normalización de coeficientes,
centro sin contrato, tolerancias estrictas e indicadores en tres precisiones.
