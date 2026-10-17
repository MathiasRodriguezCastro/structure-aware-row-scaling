# Dos líneas pendientes: protocolo de exploración separado de OMS

Fijado antes de optimizaciones nuevas de esta exploración. OMS v1.3.5, los seis
paquetes anteriores y las fuentes C++ no se modifican.

## Garantías preventivas

Derivar una envolvente suficiente de todos los vértices duales y rayos mediante
cofactores de una matriz de filas racionales convertidas exactamente a enteras.
Verificarla contra familias completas en sistemas pequeños de rango reducido,
con aritmética racional. Medir conservadurismo en los cinco MILP canónicos ya
archivados y tres LP de despacho. No confundir una cota suficiente diminuta con
una demostración de que todo presupuesto mayor es imposible. La cota de costo
solo protege patrones factibles; la exclusión de patrones inviables requiere
por separado el margen discreto de Farkas. Parámetros continuos no tienen ese
margen uniforme: documentar un contraejemplo.

## Selección/filtrado de cortes del despacho

Auditar primero las fuentes existentes. El sistema implementa DW/B&P; sus notas
Benders prueban igualdad de la relajación proyectada, pero la predicción de
tiempo de ejecución no queda demostrada por esa igualdad.

Construir un Benders multicut temporal aislado en Python sobre tres exportaciones
reales archivadas de ocho períodos: SG (cierre_dw/monolitico), RN (rn_t8) y
RN-base (rn_t8_base). Las dos RN están relacionadas; no son tres muestras
independientes. Son LP condicionales sin enteros, no el MILP completo del despacho.
No se reconstruye ni se recorta arbitrariamente una instancia de 360 horas.

Maestro: volúmenes, caudales, vertimientos, variables sin índice temporal y
cualquier variable entera. Las filas que solo tocan maestro permanecen completas.
El resto se separa por período; se exige comprobar que no hay fila con variables
de recourse de distintos períodos. Subproblemas LP horarios incluyen cotas como
filas. Cada dual/rayo se reconstruye racionalmente y se comprueba antes del corte;
el redondeo del corte al exportar se debilita por soporte sobre la caja original.
El maestro conserva todas las filas temporales de agua.

Cinco políticas: All (todos), Top (eficacia), RawDiverse (diversidad cruda),
ProjectedDiverse (diversidad tras escalar por anchos de dominio y proyectar sobre
el núcleo de las igualdades del maestro), Physical (mismo criterio y bonificación
fija 0.2 por familia física aún no representada en el lote). Los métodos diversos
usan eficacia*(0.25+0.75*diversidad), con diversidad=1-máximo coseno absoluto.
Las etiquetas físicas proceden de contribuciones duales activas de producción,
balance/demanda o cotas; no de resultados futuros. No se afirma novedad del criterio.

Todos los selectores acotados eligen hasta cuatro cortes de costo por iteración,
incluyendo siempre el de mayor eficacia. Los cortes de factibilidad violados
siempre se agregan todos. No se usa PCA para reemplazar desigualdades por
combinaciones de signo arbitrario. Se generan todos los subproblemas, por tanto
solo se compara filtrado de cortes, no selección de subproblemas/duales alternativos.

Tres repeticiones con semillas 211,223,227 y orden de trabajos permutado con 20261014.
Un solver, Gurobi 13.0.2, un hilo, presolve y escalado normales, LP dual simplex,
tolerancia de factibilidad/optimalidad 1e-9. Referencia compacta por cada repetición.
Cada brazo hasta 80 iteraciones o 60 s totales; solicitud individual hasta 10 s,
sin promesa de tiempo real. Parada con gap LP numérico <=1e-7 max(1,abs(U)).
No se vende el gap numérico como certificado racional de optimalidad global.

Medir tiempo completo (preparación, maestro, subproblemas, reconstrucción exacta,
selección y exportación), iteraciones, número de cortes, residuo original,
calidad frente al LP compacto y geometría cruda/proyectada. Los pisos iniciales
de cada recourse se obtienen de LP locales con cajas originales, se debilitan
hacia abajo y su costo de preparación se cobra íntegramente a cada brazo.
Registrar fallos y truncamientos. No agregar políticas, modelos o semillas después
de ver resultados para buscar una ventaja. Un selector solo merece avanzar si
mejora sobre Top y All, manteniendo calidad; resultados de este banco pequeño
seguirían siendo exploratorios.
