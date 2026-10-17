# Incumbente común y efecto del escalamiento: resultados para OMS

**Pregunta del artículo:** ¿cuánto del beneficio observado del escalamiento
externo depende del acceso temprano a un incumbente, aun con escalamiento
interno y presolve normales?

**Resultado:** en los dos casos conocidos donde GM ayudaba, proporcionar un
incumbente común hace que Base pase de 0/3 a 3/3 terminaciones nativas y elimina
la ventaja de terminación de GM. En instance001, GM usa más trabajo en las tres
semillas con Start común. En instance003, las diferencias de trabajo tienen
signos mezclados. Esto aporta una explicación acotada para la contribución A
de OMS, sin proponer un algoritmo ni demostrar superioridad general.

## Diseño y control

Tres modelos conocidos del generador SG-Ter-Mer, 360 períodos, 6.120 variables,
10.080 filas y 1.440 binarias cada uno. Se eligieron retrospectivamente dos
casos favorables a GM (001,003) y un control donde costaba más (042). Son
diagnósticos, no validación externa ni muestra aleatoria. Se mantiene el modelo
canónico MPS del estudio de mecanismos, con todos sus enteros originales.
Este banco auxiliar usa GM en potencias de dos y sus salvaguardas congeladas.
No reproduce el exportador LP ni todos los factores de la campaña histórica
del artículo; el diagnóstico no atribuye retrospectivamente su ganancia de
trabajo a una causa única.

Cada caso tiene Base/GM x Cold/CommonStart x semillas nuevas 503,509,521:
36 MILP secuenciales. Parámetros iguales: Gurobi 13.0.2, cuatro hilos, 12 s y
12 unidades de trabajo, gap .001, tolerancias primal 1e-6 e integral 1e-5,
IntegralityFocus=0, presolve y escalamiento interno automáticos. No se usan
como comparación las configuraciones que desactivaban mecanismos internos.

Por caso se toma el patrón de GM archivado con semilla 307 y se resuelve una
sola continuación LP racional, máximo 15 s. Las tres producen óptimos exactos
del LP con enteros fijados. No son óptimos MILP certificados. El punto racional
se convierte a binary64 para Start; ambas representaciones reciben exactamente
el mismo vector. Se verifican sus residuos originales/exportados, cotas y
enteros. Los 18 Start se cargan y se observa su patrón y costo en los candidatos.

## Resultados, sin razones de velocidad sobre corridas censuradas

Cada celda indica terminaciones al criterio nativo / 3 y mediana del trabajo
de las tres llamadas, incluidas las censuradas. No es una tabla de velocidad
a optimalidad exacta ni de resultados con cotas MILP certificadas.

| Caso | Inicio | Base: termina; trabajo | GM: termina; trabajo |
|---|---|---:|---:|
| instance001 | Cold | 0/3; 12.0001 | 3/3; 5.4909 |
| instance001 | CommonStart | 3/3; 6.4158 | 3/3; 6.7719 |
| instance003 | Cold | 0/3; 12.0002 | 3/3; 4.3099 |
| instance003 | CommonStart | 3/3; 4.7903 | 3/3; 4.6932 |
| instance042 | Cold | 3/3; 0.3284 | 3/3; 0.4928 |
| instance042 | CommonStart | 3/3; 0.0000 | 3/3; 0.0000 |

Con inicio común y calidad comparable, los cocientes apareados GM/Base en 001
son 1,0555; 1,0519; 1,3686 (mediana 1,0555). En 003 son 0,9957; 1,1114;
0,7683 (mediana 0,9957). No se hace una prueba estadística poblacional con tres
semillas ni se agrupan velocidades de distintos modelos. En 042 ambos métodos
reportan cero unidades de trabajo con el Start: no se divide por cero ni se
interpreta ese contador como costo total nulo. Hay construcción, carga y
adquisición del punto fuera del contador nativo.

En los pares con relajación raíz impresa, su objetivo coincide entre Base y GM
para cada caso, modo y semilla: 15/15 pares. La precisión impresa no certifica
igualdad exacta ni el óptimo LP. El Start cambia algunos objetivos raíz frente
a Cold, por lo que tampoco se afirma que la intervención deje intacta toda la
tubería interna. En 042 con Start no se ejecuta una relajación raíz registrada.

**Interpretación:** la ventaja de terminación observada está condicionada por
el acceso al incumbente. El escalamiento cambia la trayectoria de búsqueda;
el beneficio no puede atribuirse solo a la condición de la matriz exportada.
Un Start también cambia cortes por objetivo, presolve y búsqueda posterior:
no se identifica una heurística específica ni se prueba que sea la única causa.
Estos datos no prueban una ventaja adicional de la información del generador.

## Adquisición y comprobación exacta

Los puntos iniciales no son una entrada gratuita de un algoritmo nuevo. Los
patrones provienen de resoluciones GM previas; su continuación racional tarda
lo siguiente, incluyendo exportación y chequeo del LP:

| Caso | Costo exacto factible, aprox. | Adquisición LP nueva, s | Trabajo GM archivado que obtuvo el patrón |
|---|---:|---:|---:|
| instance001 | -989742.724306 | 1.834 | 8.1860 |
| instance003 | 270411.409126 | 1.804 | 4.9312 |
| instance042 | -510159.000000 | 1.793 | 0.4509 |

No se suman costos de campañas distintas para anunciar una aceleración, ni se
omite el costo de encontrar el patrón como si el Start se obtuviera gratis.
La intervención es un diagnóstico con información fuera de línea.

Se conserva una cola fijada antes de comprobar todos los patrones finales
únicos: 15 LP, límite de 5 s, sin sustituciones. Trece tienen óptimos de patrón
certificados; dos quedan unknown por el límite. Ambos desconocidos corresponden
a Base-Cold de 001, donde no hubo terminación al gap solicitado. Se retienen
como desconocidos. Las comparaciones Warm tienen continuaciones exactas y
costos comparables. Ninguna cota reportada supera el testigo común en este
experimento; la ausencia de contradicción no certifica las cotas.

El verificador independiente reconstruye las 3 referencias y los 15 LP de patrones desde las filas originales; comprueba duales y primales racionales, 1,179,324 productos exactos, 226 objetivos de candidatos y los residuos de los 36 puntos finales. Verifica las 18 cargas del patrón/costo común y las 36 asignaciones a patrones. Cuatro tests pasaron antes de las llamadas MILP.

## Decisión para OMS

Este resultado pasa el filtro temático: esclarece una afirmación central sobre
el mecanismo del escalamiento y su dependencia de la trayectoria del solver.
Merece un párrafo corto de evidencia, sin anunciar otra contribución principal.
No es razón para reabrir DW, cortes, predictores ni otra campaña de tiempos.
Se deja PAPER_INSERT_CANDIDATE.tex como texto concreto, sujeto al mismo nivel
de cautela que el manuscrito. La versión congelada OMS v1.3.5 no se modifica
en esta exploración. Los once paquetes previos se preservan por hashes.

La evidencia se limita a tres casos conocidos, un solver/version y límites
breves. La aceptación nativa y la calidad de los patrones se distinguen de una
prueba global MILP. El estudio apoya una atribución acotada; no demuestra que
el escalamiento solo afecte heurísticas ni que el Start sea un método superior.

Referencia de API: [Gurobi, atributo Start](https://docs.gurobi.com/projects/optimizer/en/current/reference/attributes/variable.html#attr:Start).
El proveedor describe un intento de construir un incumbente, no una garantía
de carga; de ahí la comprobación adicional de logs, patrón y costo.
