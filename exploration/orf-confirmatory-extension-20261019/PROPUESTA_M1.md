# Propuesta aislada para corregir las activaciones de Bonete

19 de octubre de 2026. No se aplica al generador, al banco congelado, al piloto
en ejecución ni al artículo. Es una propuesta de corrección de formulación.

Para una fila \(M\phi-v\le r\), con \(\phi\in\{0,1\}\), el umbral activo
es \(T=M-r\). Con \(\phi=1\), debe conservarse \(v\ge T\). Con
\(\phi=0\), la fila debe ser redundante respecto de la cota válida \(v\ge L\).
Por tanto, basta elegir un nuevo par \((\widehat M,\widehat r)\) tal que

\[
\widehat M-\widehat r=T,
\qquad T-\widehat M\le L.
\]

El prototipo lee \(T\) como racional exacto de los datos binario64 originales.
En este caso, elegir \(\widehat M=\operatorname{float}(T)\) y
\(\widehat r=\widehat M-T\) produce dos números binario64 cuya diferencia
reproduce exactamente el umbral. El programa comprueba esa propiedad en cada
fila escrita; no la supone por una aproximación decimal. También comprueba
que la cota inferior de volumen vuelve redundante el estado apagado.

Se reemplazan las 336 filas `restriccion_varphi1_1` y `restriccion_varphi1_2`
del Simple de 168 horas. Permanecen iguales el objetivo, las cotas, los dominios
enteros y todas las otras restricciones. El par de activación conserva el
umbral activo y elimina la cota artificial del estado apagado.

La trayectoria racional previamente verificada del mismo padre a 360 horas,
restringida a 168, viola 25 filas del modelo original. Esa misma trayectoria
satisface exactamente todas las filas, cotas e integralidad de la propuesta.
La comprobación no requiere resolver otro MILP ni otro LP. El resultado y sus
hashes están en `PROPOSED_FORMULATION_REPAIR.json`; el prototipo es
`propose_safe_activation_m.py`.

Esto cambia la formulación original incompatible. No es un escalado de filas
ni una transformación equivalente de ese modelo. El M elegido tampoco se
presenta como el más ajustado: puede debilitar la relajación frente a un M
válido menor. No se ha medido una ventaja de trabajo o tiempo.

Una adopción posterior requeriría definir y congelar una variante corregida,
aplicarla por igual a todas las políticas, rehacer sus referencias y documentar
la diferencia de población. El estudio actualmente registrado conserva las
matrices originales y los casos incompatibles como diagnóstico explícito.
