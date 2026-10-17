# Refinamiento y garantía global de las salidas conjuntas

El LP exacto reveló una cota global suficientemente cercana al testigo existente
en 005,022,031, con igualdad exacta en 031. Antes de nuevas adquisiciones se fija
este seguimiento sobre TODAS las 18 salidas del piloto conjunto, incluidos los
tres modelos donde el intervalo LP no permite certificar 1 %.

Se fija el patrón entero redondeado de cada salida y se resuelve el LP restante
exactamente sobre el Base binary64 original. Una llamada por patrón distinto,
sin sustituir patrones fallidos; aliases por identidad del patrón se declaran
antes de llamar a SoPlex. Límite 15 s por LP. Se verifican todas las filas,
cotas y dominios del punto racional reparado.

La cota inferior es exclusivamente la del LP GLOBAL con todas las binarias
relajadas, ya verificado. El LP de patrón aporta solamente U, nunca una cota
inferior global. Si U-LB <= .01|U| se certifica una solución MILP al 1 %;
si U=LB se certifica óptimo exacto. En los demás casos se devuelve el intervalo
y no se anuncia optimalidad. La salida certificada es el vector racional
refinado, no el vector flotante inicial. No se alteran ni repiten las llamadas
MIP del piloto. Costos de adquisición global y de refinamiento se declaran.
