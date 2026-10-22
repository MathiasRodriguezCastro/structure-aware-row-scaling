# Campaña confirmatoria ORF

3.840 ejecuciones registradas: 3.816 con calidad evaluable y 24 diagnósticas. Todos los bloques pasaron su reproducción independiente.

## Comparación primaria Budget-L2/L2

| Solver | Estrato | Pares | Éxitos Budget/L2 | PAR2 (IC 95%) | Trabajo | Tiempo completo |
| --- | --- | ---: | --- | --- | ---: | ---: |
| gurobi | all | 477 | 432/423 | 0.995 [0.923, 1.062] | 1.038 | 1.079 |
| gurobi | simple | 168 | 157/157 | 1.006 [0.982, 1.033] | 1.000 | 1.001 |
| gurobi | sgtm | 156 | 148/145 | 1.047 [0.964, 1.134] | 1.060 | 1.151 |
| gurobi | completo | 153 | 127/121 | 0.934 [0.759, 1.119] | 1.060 | 1.095 |
| gurobi | h24 | 120 | 120/120 | 1.020 [0.978, 1.071] | 0.986 | 1.015 |
| gurobi | h72 | 120 | 112/111 | 0.977 [0.786, 1.154] | 0.887 | 1.031 |
| gurobi | h168 | 117 | 102/101 | 0.974 [0.848, 1.101] | 0.985 | 1.025 |
| gurobi | h360 | 120 | 98/91 | 1.011 [0.880, 1.142] | 1.349 | 1.260 |
| cplex | all | 477 | 99/102 | 1.000 [0.963, 1.030] | 0.987 | 1.005 |
| cplex | simple | 168 | 3/3 | 0.997 [0.989, 1.001] | 1.000 | 1.018 |
| cplex | sgtm | 156 | 94/93 | 0.986 [0.883, 1.075] | 0.990 | 1.019 |
| cplex | completo | 153 | 2/6 | 1.018 [1.001, 1.047] | 0.969 | 0.977 |
| cplex | h24 | 120 | 32/32 | 0.999 [0.978, 1.023] | 1.001 | 0.992 |
| cplex | h72 | 120 | 29/30 | 1.042 [1.004, 1.113] | 0.996 | 1.032 |
| cplex | h168 | 117 | 18/20 | 1.000 [0.968, 1.034] | 0.961 | 0.987 |
| cplex | h360 | 120 | 20/20 | 0.961 [0.845, 1.047] | 0.990 | 1.008 |

Las razones son medias geométricas emparejadas. El bootstrap remuestrea 100.000 veces los padres completos, conservando horizontes, semillas y elegibilidad. Los intervalos son marginales. Un intervalo que contiene uno no demuestra equivalencia.

Simple produce representaciones L2 y Budget-L2 idénticas: sus diferencias de tiempo o trabajo no prueban un beneficio de modificar factores. Los bancos son recombinaciones históricas con exposición previa documentada, no observaciones operativas nuevas independientes.

La referencia es una solución factible verificada, no un óptimo MILP. La ausencia de contradicciones detectadas no certifica cotas ni optimalidad. El trabajo a un límite finito conserva censura y no equivale a una comparación a calidad certificada igual.

El PAR2 usa la disponibilidad verificada después del solver en los éxitos y dos veces el límite más preparación en los objetivos no alcanzados. Los tiempos en éxitos comunes son condicionales y se reportan separados. El alcance físico conserva el mapa congelado: las otras filas se controlan por error relativo hacia atrás.

El manuscrito y su generador original permanecen sin cambios. Estos resultados requieren valoración científica antes de incorporarlos al artículo.
