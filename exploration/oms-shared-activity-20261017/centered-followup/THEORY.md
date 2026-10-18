# Radio equilibrado sujeto a precisión

Los bloques y las hipótesis de transferencia son los del estudio primario.
Compartir una holgura SOS y normalizarla por coeficientes tienen antecedentes;
la pregunta aquí es el valor de imponer precisión a esa elección.

Para q_i=M_i²/sum_j g_ij²>0, el coeficiente relativo de actividad al cuadrado
es q_i/2^(2r). La peor desviación multiplicativa respecto de uno es
F(r)=max(q_max/2^(2r),2^(2r)/q_min). Su primer argumento decrece estrictamente
y el segundo crece estrictamente. Se cruzan en
r0=log2(q_min*q_max)/4. Por ello el mínimo sobre un intervalo entero no vacío
[r_-,r_+] se alcanza en uno de los dos enteros que rodean r0, truncados al
intervalo. Compararlos como racionales y romper empates hacia menor r da una
regla exacta y determinista; no requiere resolver un problema de optimización.
La fórmula floor(log2(q_min*q_max))//4 produce floor(r0), incluso con
exponentes negativos.

El intervalo admisible se deriva de las ventanas de coeficientes, exportación
binary64 exacta y epsilon/alpha_i+(M_i/R)*max(gamma_SOS,tau)<=delta_i.
Por la caracterización necesaria y suficiente del estudio primario, proyectar
el centro de esta manera da el mejor centrado relativo entre todos los radios
diádicos admisibles. No demuestra menor esfuerzo ni optimalidad MILP.

Una conversión coherente por 2^k_i de g_i,M_i,delta_i conserva cada q_i y el
radio, cuando los límites de representación no recortan el minimizador
transformado; la escala de fila cambia por 2^-k_i. No se afirma invariancia
global cerca de subdesbordamiento/desbordamiento de binary64.

Si el centro sin restricciones pertenece al intervalo, el contrato no cambia
el radio. Solo cuando queda fuera puede atribuírsele una modificación. La
evaluación distingue estos casos y compara con el centro sin contrato, la
normalización individual de coeficientes, tolerancias estrictas e indicadores.
La normalización individual diádica basada en media absoluta aproxima la regla
de SCIP; estos ensayos usan Gurobi y no representan una comparación con SCIP.
