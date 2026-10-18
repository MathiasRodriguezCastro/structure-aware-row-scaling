# Contratos ante riesgo numérico nativo

La campaña terminó con **57 ejecuciones MIP**, diez llamadas auxiliares de LP
exacto y una decisión de alcance. OMS v1.3.14 no se modificó.

**Resultado concreto:** se encontraron dos grupos MIPLIB nuevos con estructura
real y dificultades de precisión observadas. Budget-L2 recupera los presupuestos
que L2 y NumericFocus=3 incumplen. Sin embargo, Base y L2 estricto ya los cumplen;
Budget no supera a esos controles. No se añade este piloto como nueva ventaja
competitiva al artículo.

## Selección previa a resolver

Se inventariaron las 193 instancias de la colección
[MIPLIB Numerics](https://miplib.zib.de/tag_numerics.html), fuera del conjunto
Benchmark. `selection.json` contiene las doce elegidas por el protocolo, sin
consultar resultados nuevos. Ocho provienen del estrato de grupos nuevos con
descomposición, tres son ejemplos industriales/energéticos y ta2-UUE es una nueva
instancia de un grupo ya conocido, no validación de un grupo independiente.

Las fuentes incluyen [gases industriales](https://miplib.zib.de/instance_details_gasprod1-2.html),
[lotificación con capacidad](https://miplib.zib.de/instance_details_cmflsp50-24-10-4.html)
y [microrred](https://miplib.zib.de/instance_details_minutedispatchstrategy.html).
Se conservan MPS y DEC originales. No hay perturbaciones artificiales de unidades,
coeficientes, capacidades o demanda. Las descomposiciones se cotejan con todos los
nombres de filas; las columnas compartidas no se reasignan a bloques ficticios.

Nueve modelos pasan el filtro fijado de rango/heterogeneidad, contratos compatibles
y factores activos. Tres quedan fuera, conservando sus diagnósticos. En ocho de
los nueve hay acoplamiento real entre columnas privadas de varios bloques; el
caso australia-abs-cta se evalúa solo con los contratos generales. Los archivos
DEC no prueban por sí mismos la hipótesis triangular del artículo.

Se elige, exclusivamente desde la matriz, la meta absoluta más exigente compatible
de {1e-1,1e-3,1e-5,1e-7}, con epsilon=1e-6 e hipótesis de redondeo eta=1e-9.
Son metas algebraicas experimentales, no estándares físicos u operativos.
Los factores diádicos preservan exactamente coeficientes y RHS binary64; objetivo,
cotas y dominios permanecen iguales. La importación completa de los nueve MPS
nativos y las 18 exportaciones iniciales se cotejó independientemente con Gurobi.

## Ejecuciones y resultados

Etapa B: nueve modelos por cinco controles, semilla 239, cuatro hilos, presolve y
escalado automáticos, IntFeasTol=1e-9, WorkLimit=1 y TimeLimit=20 s.
Base, Base-tight, L2 diádico, L2 diádico estricto y L2 con NumericFocus=3.
El control estricto cambia la tolerancia primal de 1e-6 a 1e-9.
Solo después de verificar los puntos se ejecutó Budget-L2 en los dos modelos con
fallos observados. Se mantuvieron sus datos, metas, semilla y límites.

| Modelo | Meta | L2: máximo original | NF3: máximo original | Budget-L2: máximo original |
|---|---:|---:|---:|---:|
| neos-619167 | 0.1 | 1 | 1 | 9.3342e-15 |
| neos-3762025-ognon | 0.001 | 138.1454 | 270.2157 | 2.5696e-7 |

Los residuos corresponden a los datos originales y al punto con enteros redondeados.
La aritmética racional también verifica el punto bruto, cotas y dominios.
Los parámetros nominales del solver no sustituyen la comprobación del residuo
exportado efectivamente observado.

En neos-619167, L2 admite un residuo original 1 que, multiplicado por 2^-20,
queda en 9.5367e-7. El mismo punto bajo el factor contractual 2^-16 excede
la hipótesis epsilon. Es una explicación exacta de esa transferencia puntual,
no una identificación causal de toda la trayectoria interna del solver.
En ognon, algunas filas de L2/NF3 incluso exceden la hipótesis exportada 1e-6;
no se presupone que un parámetro nominal las garantice.

En la ampliación de esfuerzo se conservaron los dos casos cuyos cinco controles
no habían dado incumbente: lotificación y microrred, con semilla nueva 241,
WorkLimit=16 y TimeLimit=90 s, sin cambiar metas ni exportaciones. Los cinco
controles de microrred entregan puntos que cumplen la meta. En lotificación solo
L2 entrega un punto, también dentro de la meta; los otros cuatro quedan desconocidos.
No se ejecuta Budget en ellos porque no se observó un fallo de precisión que remediar.

Total: 57 llamadas, 40 puntos conservados, 36 dentro de las metas, cuatro fallos y
17 sin punto. Estas cuentas mezclan modelos, controles y límites: no son tasas
poblacionales ni un ranking de solvers. Un caso sin punto no es un fallo de precisión.

## Validación exacta del patrón y costo

Para los dos casos de recuperación se fijaron los enteros de las seis políticas.
Son doce referencias a ocho patrones distintos. Se adquirieron certificados con
SoPlex y se comprobaron otra vez contra el MPS original sin usar sus atributos.

- Siete patrones tienen continuación primal exacta y óptimo LP condicional certificado.
- El patrón de L2/NF3 en neos-619167 es imposible: un rayo de Farkas exacto anula
  todas las columnas libres y produce la contradicción racional **1 > 0**.
- El patrón de Base, L2 estricto y Budget en ese modelo es el mismo y admite costo
  exacto **4**. En ognon, el patrón Budget admite costo exacto aproximadamente
  **609824.5554908613**.

Estos son certificados de patrones fijos y sus LP, no certificados de óptimo MILP.
Una reparación posterior no se acredita a la entrega original. Dos adquisiciones
LP iniciales encontraron un error de looping; una única alternativa declarada,
sin presolve y con escalado geométrico, obtuvo sus certificados. Se conservan
ambas configuraciones y los logs adversos. `RECOVERY.md` documenta una recuperación
del wrapper sin repetir su llamada nativa.

## Comparación con controles fuertes y decisión

En neos-619167, Base, L2 estricto y Budget alcanzan la misma calidad de costo
verificada. Todos agotan aproximadamente una unidad de trabajo, y Budget añade
preparación sin ventaja de entrega. En ognon, Budget requiere **2.73 veces el
trabajo de L2 estricto**, con un costo final algo mayor. Base también cumple.
La comparación con puntos inexactos rápidos no se utiliza como una ventaja.

No se activa la regla de confirmación ni la de incorporación del protocolo:
no hay una recuperación exclusiva frente a controles fuertes ni una mejora del
20% del ciclo a calidad común. La campaña acotada se cierra, conservando los dos
casos reales de recuperación y sus límites. Los resultados no prueban que otras
instancias o límites carezcan de oportunidades. La extensión matemática está
en el documento separado `oms-incidence-spectral-20261018`.

## Verificar sin resolver

Desde la raíz del repositorio o del ZIP extraído:

```bash
python3 exploration/oms-native-numerics-20261018/verify_design.py
python3 exploration/oms-native-numerics-20261018/verify.py b
python3 exploration/oms-native-numerics-20261018/verify.py c
python3 exploration/oms-native-numerics-20261018/verify.py b2
python3 exploration/oms-native-numerics-20261018/verify_exact.py
python3 exploration/oms-native-numerics-20261018/summarize.py
python3 exploration/oms-native-numerics-20261018/manifest.py
```

Estos comandos necesitan solo la biblioteca estándar de Python y no llaman a
ningún optimizador. Los registros completos son inmutables; no se sobrescriben
ejecuciones terminadas ni se reintenta un proceso incompleto sin diagnosticarlo.
`contracts.csv.gz` conserva sin pérdida el gran diagnóstico por fila;
`contracts.retention.json` permite comprobar el CSV descomprimido original.
