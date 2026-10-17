# Selección de factores considerando exportación: resultados

**Decisión:** se implementó y verificó un selector que amplía las potencias de
dos a todos los multiplicadores binary64 que exportan la fila exactamente.
También se implementó un selector finito que reserva el defecto de exportación
de candidatos redondeados. Hay una mejora de centrado y menos abstenciones
en pruebas artificiales, pero **ninguna admisibilidad adicional en los tres
escenarios físicos solicitados**. No se inicia otra campaña MILP ni se añade
este estudio al artículo. No se afirma novedad histórica.

## 1. Qué se implementó

Para cada dato no nulo, z=signo N_z 2^p_z, con N_z impar. Todo factor binary64
positivo tiene alpha=h 2^k, h impar. El producto es exactamente representable
si y solo si h N_z tiene a lo sumo 53 bits, p_z+k>=-1074 y su mayor exponente
no excede 1023; se comprueban también los límites del propio factor. Por tanto
el significando impar permitido cumple h<=floor((2^53-1)/max N_z).

El selector **Exact** recorre exponentes y, para cada uno, obtiene el intervalo
de significandos impares admisibles. Compara exactamente los vecinos del óptimo
real y los extremos. Encuentra el mínimo global de Q(alpha)=max(alpha M,
1/(alpha m)) sobre todos los factores binary64 de exportación exacta. Q es la
exponencial del objetivo logarítmico de centrado; no es un número de condición.
El RHS participa en la exactitud y representabilidad, no en m/M.

El control **Pow2** restringe h=1. **Rounded** escoge el GM binary64 sin
reserva por exportación. **Aware** compara un conjunto finito declarado: Exact,
Pow2, Rounded, extremos redondeados hacia dentro y ocho vecinos nextafter a cada
lado de Rounded. Conserva solo candidatos que cumplen el contrato completo y
la ventana de coeficientes realmente exportados. Aware no es un óptimo global
entre factores que redondean productos.

Para ahat=fl(alpha a), bhat=fl(alpha b), se calcula exactamente sobre la caja
original rho(alpha)=max_x |(a-ahat/alpha)^T x+bhat/alpha-b|.
El contrato suficiente es epsilon/alpha + E + rho(alpha) <= delta.
La hipótesis epsilon es un límite del residuo efectivamente exportado, no una
promesa de FeasibilityTol. E es la reserva independiente por redondeo entero.
Si un error no nulo multiplica una coordenada sin cota finita, esta prueba de
caja no da una envolvente finita; no se inventan cotas para obtenerla.

## 2. Banco y escenarios reales

Tres modelos SG-Ter-Mer conocidos, 360 períodos, cada uno con 6.120 variables,
10.080 filas y 1.440 variables enteras. Se preservan los datos binary64
canónicos del paquete precision-work. Son 30.240 filas y 12.960 filas físicas
por escenario, incluyendo la extensión documentada de activaciones.
No se vuelven a resolver los modelos ni se cambia el generador.

Ventana [1e-9,1e9], epsilon=1e-6 y E=1e-9 sum_entero |a_j|, con las entradas
binary64 del padre. Los objetivos físicos son exigente (.01 MW,100 m3),
referencia (.1 MW,1000 m3) y permisivo (1 MW,10000 m3). Se convierten a unidades
algebraicas fila a fila. No son tolerancias establecidas por UTE.

| Escenario | Filas | Pow2 cumple | Exact cumple | Aware cumple | Exact cambia respecto de Pow2 |
|---|---:|---:|---:|---:|---:|
| Demanding | 12960 | 12960 | 12960 | 12960 | 2160 |
| Reference | 12960 | 12960 | 12960 | 12960 | 2160 |
| Permissive | 12960 | 12960 | 12960 | 12960 | 2160 |

Sin presupuesto, Exact cambia 5.364/30.240 factores (17,74 %), todos con defecto
de exportación cero. La mediana del cociente Q_Exact/Q_Pow2 sobre todas las
filas es 1; el mejor cociente es 0,70710678. Una mejora de Q no prueba una
mejora de condición, de solución o de trabajo del solver. En cada escenario
físico cambia 2.160/12.960 factores, sin rescatar ningún contrato.

En 17.773/30.240 filas, las potencias de dos son los únicos multiplicadores
exactos posibles incluso antes de imponer el intervalo. En otras filas existen
significandos impares mayores que 1. Por ejemplo, a1_cota_altura_4(1) de
instance001 pasa de factor 32 a 36, con todos los productos exactos.
No hay una garantía de invariancia ante reemisión arbitraria: la representación
de los datos puede modificar el conjunto de multiplicadores exactos.

Rounded también cumple todos los contratos físicos de este banco. Su máximo
defecto de exportación dividido por el presupuesto restante es 1,732e-8 en el
escenario exigente, 1,535e-9 en referencia y 1,517e-10 en permisivo. Este dato
explica por qué reservarlo explícitamente no rescata casos aquí; no dice que
el defecto sea despreciable en cualquier problema.

En el banco completo sin presupuestos, 4.320 filas falla_tramo no tienen una
envolvente finita del defecto sobre la caja almacenada para Rounded. Intervienen
variables con cotas infinitas en el modelo importado. Es una limitación del
certificado por caja, no prueba de error infinito en la región factible: otras
restricciones podrían proporcionar cotas. La exportación exacta evita ese
defecto sin necesitar tales cotas.

## 3. Sensibilidad construida con intervalos estrechos

Se reemplaza el presupuesto de cada fila física por delta=E+epsilon/(theta H),
con H=1e9/M. Son presupuestos artificiales dependientes de la fila. No se mezclan
con los tres escenarios físicos ni se presentan como necesidades del despacho.

| theta | Filas | Pow2 admite | Exact admite | Abstenciones evitadas |
|---|---:|---:|---:|---:|
| 1/2 | 12960 | 12960 | 12960 | 0 |
| 3/4 | 12960 | 5400 | 8640 | 3240 |
| 7/8 | 12960 | 1080 | 4320 | 3240 |
| 15/16 | 12960 | 1080 | 4320 | 3240 |
| 1 | 12960 | 0 | 3240 | 3240 |

En theta=1, por ejemplo, las filas físicas con coeficientes de magnitud 1
exigen alpha=1e9. Ese número es binary64 exacto y sus productos por +/-1 son
exactos, pero no es potencia de dos. Se evitan 3.240 abstenciones: filas
g4h_def, gh_total y gen_menor_demanda. El presupuesto residual correspondiente
es del orden de 1e-15 MW, lejos del escenario exigente solicitado de .01 MW.
Esto ilustra una limitación de la grilla conservadora; no descubre una necesidad
práctica ni refuta el certificado de incompatibilidad para factores reales.
El selector del paper ya distingue abstención dyádica de intervalo real vacío.

## 4. Verificación y alcance

El verificador independiente comprobó 246,240 decisiones, 852,075 productos, 138,240 condiciones de optimalidad discreta y 64,800 intervalos de estrés.

La optimalidad se verifica excluyendo la existencia de un factor con mejor Q,
sin reutilizar el minimizador del productor. Se validan también 14.000
comparaciones exhaustivas en un formato binario pequeño, 300 pares binary64
con límites de exponente y cinco tests. Se corrigió un contador agregado después
de la primera corrida; los dos archivos de decisiones conservaron exactamente
sus hashes. Ver IMPLEMENTATION_NOTES.md. No se modificó ninguna política.

Los datos canónicos se incluyeron en el paquete. Su procedencia y hashes quedan
fijados; el estudio padre ya comprobó su identidad con los LP originales. Este
paquete no vuelve a importar esos LP ni ejecuta un solver. La medición de costo
es tiempo del script con caché y verificaciones; no es rendimiento MILP.

## 5. Revisión de los límites conjuntos y decisión para OMS

LITERATURA.md amplía la revisión: la homogeneización fraccional tiene un
antecedente explícito en Charnes–Cooper (1962), y el mínimo libre por filas y la
invariancia de Skeel ya eran clásicos. Se revisaron las reformulaciones de
precondicionamiento diagonal de Qu et al.; trabajan con condición espectral y
no certifican ni descartan prioridad de la extensión acotada en norma infinito.
La novedad específica continúa sin establecerse. La ausencia de un caso real
útil sigue siendo el límite práctico principal.

**Resultado tangible:** ahora existe un selector completo de factores de
exportación exacta y otro selector finito que verifica la reserva de exportación.
La mejora observada se limita a centrado y estrés construido. No hay evidencia
suficiente para otra contribución al paper ni para invertir en una campaña de
solver sobre estos escenarios. La versión OMS v1.3.5 y los diez paquetes previos
se preservan por SHA256. El diagnóstico LP–DW entero y el predictor validado
siguen pendientes y no se confunden con esta exploración.
