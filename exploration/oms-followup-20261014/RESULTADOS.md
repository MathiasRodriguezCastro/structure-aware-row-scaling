# Resultado y decisión de incorporación — 14 de octubre de 2026

Sí hay una ampliación útil para el paper: un caso donde los contratos modifican
factores y recuperan precisión, acompañado por testigos factibles exactos que
distinguen esa mejora de la validez de las cotas MILP. Se incorpora una subsección
breve y se deja el detalle en el suplemento. No se añade otro teorema ni se reclama
una garantía de optimalidad.

## Qué se comprobó

Se conservaron las 132 soluciones anteriores y se hicieron 122 llamadas nuevas:
8 de piloto separado, 72 del contraste en seis modelos, 27 de controles de
mecanismo, 9 con semillas nuevas y presolve desactivado, y 6 de sensibilidad.
Los 114 resultados que no son piloto se reprodujeron sin optimizar, verificando
factores, errores de exportación, residuos, parámetros, objetivos y certificados.
Los seis modelos del contraste no tienen la inversión de demanda documentada.
Esto no supone validación operativa completa ni generalización a otra aplicación.

En instance046, una binaria casi igual a uno permite una componente acreditada
de 13,606 MW cuando el almacenamiento está 4.840 m³ por debajo del umbral.
Con las cantidades continuas fijas, elegir uno viola el volumen; elegir cero
viola la cota de esa componente de potencia. Ninguna opción cumple los objetivos
numéricos de referencia. Se trata del modelo generado, no de un déficit físico
medido en una central.

La reserva uniforme con IntFeasTol=1e-5 agota el presupuesto de la activación.
Al usar la reserva guiada por presupuesto, y reservar también el error de
exportación, el intervalo es no vacío. El escenario exigente modifica únicamente
las 1.440 activaciones por modelo. En instance046, L2 pasa de un factor 1e-9
a aproximadamente 1,87e-8; el control y el método comparten la misma tolerancia
entera. El resto de sus factores coincide.

| Contraste principal: seis modelos, tres semillas | Cumplen presupuestos | Cotas sobre testigo exacto | Completamientos contradichos al 1 % |
|---|---:|---:|---:|
| GM | 18/18 | 3/18 | 0/18 |
| L2 con tolerancia entera igualada | 18/18 | 7/18 | 6/18 |
| Budget-L2 | 18/18 | 1/18 | 0/18 |
| L2 con ambas tolerancias en 1e-9 | 18/18 | 6/18 | 5/18 |

Una cota no marcada no queda certificada. Un testigo es un punto factible, no el
óptimo global; permite refutar algunas cotas y declaraciones de terminación,
pero no aprobar automáticamente las restantes. Se comparan certificados del
mismo archivo importado, identificado por SHA-256. Los veinte testigos pasan
todas las 10.080 filas, las cotas de las 6.120 variables y los 1.440 dominios
enteros de cada exportación correspondiente.

En las tres semillas nuevas, con presolve desactivado, L2 devuelve un residuo
de 4.837,338 m³. Budget-L2 lo reduce a un máximo de 1,4782e-5 m³. Ajustar ambas
tolerancias globales a 1e-9 baja ese residuo a cero, pero sigue reportando costo
aproximado -572.330 y brecha cero frente a un testigo factible exacto de costo
aproximado -799.086. La precisión primal y la información de optimalidad son
criterios distintos.

El costo adicional de selección y exportación es aproximadamente 0,14 s por
modelo en este prototipo: 0,354–0,360 s para L2 y 0,497–0,505 s para Budget-L2.
Las 36 mediciones reprodujeron exactamente los archivos congelados. Estos tiempos
son separados del costo de importación y optimización; no incluyen la lectura
común de LP ni la verificación.

## Resultados que limitan la conclusión

NumericFocus 3 recupera resultados útiles en los tres controles. Los indicadores
también cumplen los presupuestos comprobados. M más ajustados todavía dejan una
violación grande después del redondeo en una semilla. La exportación diádica
convencional conserva una declaración de terminación contradicha en otra semilla,
aunque sus coeficientes y RHS son exactamente proporcionales al modelo Base.
El redondeo de productos no explica por sí solo todos los fallos.

| Sensibilidad de Budget-L2 en instance046 | Factores modificados | Cumplen presupuestos | Completamientos contradichos |
|---|---:|---:|---:|
| Exigente: 0,01 MW / 100 m³ | 1.440 | 3/3 | 0/3 |
| Referencia: 0,1 MW / 1.000 m³ | 1.440 | 3/3 | 1/3 |
| Permisivo: 1 MW / 10.000 m³ | 0 | 3/3 | 3/3 |

Los valores eran los objetivos numéricos ya declarados; su extensión a las
activaciones es explícitamente exploratoria. No son estándares del operador.
Incluso cuando el contrato modifica factores y cumple el presupuesto, puede
persistir una cota MILP inválida. Por eso el paper conserva la garantía condicional
primal y presenta los testigos exactos como verificación independiente.

## Qué entra en la versión OMS

Una subsección conecta el caso de redondeo, los factores activos y los resultados
comprobados. Tres tablas compactas del suplemento presentan el contraste,
controles y sensibilidad. El artefacto incluye los veinte certificados, todos los
datos de las llamadas, exportaciones, fuentes y un replay sin solver comercial.
Las dos contribuciones principales del artículo se mantienen. La versión local
anterior v1.3.2 permanece intacta; la ampliación se prepara como v1.3.3.

Desde la raíz del repositorio:

```bash
python3 exploration/oms-followup-20261014/verify_and_summarize.py
make research-oms-check
```

No se necesita SoPlex ni una licencia comercial para comprobar los certificados
suministrados. SoPlex 8.1.0/GMP se usó solamente para producirlos; su fuente y
opciones se documentan en los registros. Las dependencias de compilación se
descargaron y extrajeron localmente, sin instalar paquetes del sistema.
