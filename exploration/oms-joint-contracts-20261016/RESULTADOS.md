# Escalamiento conjunto exacto: resultado y límite editorial

**Se implementó un método global verificable**, restringido a potencias de dos,
con columnas enteras inmóviles, contratos y representación exacta de matriz,
RHS, objetivo y cotas. Devuelve un potencial entero o un ciclo negativo; un
certificado en t* y otro en t*-1 prueban el menor entero de centrado admisible.
La derivación y sus antecedentes están en [THEORY.md](THEORY.md).

El verificador independiente reconstruye los intervalos enumerando exponentes
y probando `ldexp`, sin importar el constructor del grafo. Verifica 84 celdas,
74 factibles, 84 ciclos negativos de incompatibilidad/optimalidad y 16.893.360
desigualdades enteras. Cinco tests adicionales contrastan grafos con enumeración,
LP continuos y extremos binary64. No se usa un MIP para seleccionar exponentes.

## Qué se recupera matemáticamente

En los seis modelos, para .01 MW/100 m3 y gamma=1e-9, el mejor entero de centrado
pasa de **t=17 con filas** a **t=8 con columnas continuas**. Son envolventes
de coeficientes [2^-t,2^t], no números de condición. Todos los datos se exportan
exactamente. Las binarias conservan su escala y dominios. Los límites de RHS y
cotas evitan cruzar los sentinelas de infinito del backend.

La reserva E por redondeo entero es invariante ante esta transformación. Por eso
la extensión tampoco puede rescatar el presupuesto de 10 m3 agotado en cinco
modelos. No se describe esa incompatibilidad como inviabilidad del MILP.

## Piloto y ablación con resultados adversos incluidos

Las 18 llamadas del piloto (seis modelos, semillas 59/71/89, presolve automático)
cumplen todos los objetivos originales y no tienen contradicciones de cota o
cierre detectadas. Los 18 puntos se desescalan exactamente en binary64.
Eso no prueba optimalidad MILP ni una ventaja universal.

Después del piloto se fijó una ablación 2x2: filas/filas+columnas, con/sin
contratos. Los 72 brazos corresponden a 54 llamadas únicas: las 18 del piloto,
36 nuevas y 18 aliases de filas declarados antes de resolver. Los dos controles
de filas producen exactamente la misma exportación y no se vuelven a resolver.

| Política | Cumple presupuestos | Cotas/cierres contradichos | Media geométrica Work |
|---|---:|---:|---:|
| Filas, con contratos | 18/18 | 0/0 | 1,922 |
| Filas, sin contratos — misma exportación | 18/18 | 0/0 | 1,922 |
| Conjunto, con contratos | 18/18 | 0/0 | 1,399 |
| Conjunto, sin contratos | 18/18 | 0/0 | 3,683 |

En el caso 001, la razón de trabajo conjunto con/sin contratos es **0,0355**:
aproximadamente 28 veces menos trabajo en media geométrica emparejada. En 027 y
046 las razones son 0,200 y 0,246. En cambio **031 empeora 2,81 veces** frente
al conjunto sin contratos. Comparado con filas solamente, el conjunto contractual
empeora en 005 y 027 y mejora en los otros cuatro. No se oculta esa heterogeneidad.

El conjunto sin contratos centra más agresivamente (t menor), pero puede gastar
mucho más trabajo. En 001 sus tres puntos tienen una violación de aproximadamente
77,06 m3, frente a residuos diminutos con contratos: ambos cumplen el objetivo
preestablecido de 100 m3. No se redefine después el umbral para proclamar una
recuperación primal que este experimento no solicitó.

Una comparación adicional con el control fuerte disponible es decisiva: frente
al **Budget-L2 por filas** de la frontera, con los mismos seis modelos, semillas,
presolve automático y tolerancias, el conjunto contractual consume **1,222 veces
el trabajo agregado** (media geométrica emparejada): empeora aproximadamente
22,2 %. Solo mejora en 022 y 031. Este contraste, calculado una vez terminadas
ambas campañas, queda en `strong-control-addendum.json` con hashes de las fuentes.
Las exportaciones binary64 no son idénticas y no se afirma igual certificación
de optimalidad; ambos métodos cumplen los objetivos numéricos. La extensión
conjunta **no desplaza al método existente** en esta comparación.

Las comparaciones de Work no incluyen la adquisición offline de factores, que
el prototipo Python tarda varios segundos en calcular. No se convierten estos
resultados en una aceleración del ciclo completo. Todas las variantes tienen
costos de candidato cercanos, pero no gaps MILP globalmente certificados en
todos los modelos. Los certificados globales posteriores cubren solo algunos.

## Qué se entrega verificablemente

El seguimiento con LP globales y refinamiento produce 18 puntos enteros
exactamente factibles, nueve certificados globalmente al 1 % y tres óptimos
exactos. Su costo y límites se documentan en
[el informe global](../oms-global-lp-20261016/RESULTADOS.md).
Esto separa garantías verdaderas de ausencia de contradicciones detectadas.

## Decisión

Es una dirección útil, con matemática, implementación y efecto computacional
comprobables. Permanece **separada del paper de escalamiento por filas**: no hay
validación externa del nuevo método ni novedad histórica suficientemente revisada
para presentarlo como otro aporte principal. La formulación logarítmica y los
grafos tienen antecedentes explícitos. El papel de los contratos en una elección
global exacta sí merece seguimiento, sin vender más centrado como mejor resolución.

Reproducción sin optimizadores:

```bash
python3 exploration/oms-joint-contracts-20261016/independent_check.py
python3 exploration/oms-joint-contracts-20261016/check_solves.py
python3 exploration/oms-joint-contracts-20261016/check_ablation.py
```

Para una extracción sin los paquetes históricos, el primer comando admite
`--allow-absent-historical`. La corrección bibliográfica del protocolo (1980, no
1989) y el sellado del diagnóstico completo antes del piloto quedan registrados;
no cambiaron modelos, exponentes, criterios ni asignaciones.
