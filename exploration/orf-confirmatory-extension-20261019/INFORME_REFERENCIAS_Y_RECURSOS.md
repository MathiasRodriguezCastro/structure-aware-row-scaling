# Referencias comunes y calibración de recursos ORF

Continuación del piloto cerrado; artículo y generador original sin cambios.

## Referencias de confirmación

De los 160 modelos registrados: **159 con referencia factible racional verificada**, 1 certificado inviable y 0 desconocidos.

La referencia común no es un óptimo MILP certificado. Todos los intentos Base y sus costos permanecen separados de las políticas. La reproducción independiente revisó filas, cotas, integralidad, objetivos y hashes sin llamar a optimizadores.

Un segundo verificador lee el formato LP del generador usando solo Python estándar. Conserva y comprueba las cotas finitas escritas, incluso las que el lector nativo interpreta como infinitas, y reproduce el certificado de inviabilidad del caso diagnóstico.

Los contratos físicos conservan su mapa original de filas y unidades. No cubren todas las filas: las restantes mantienen el control separado de error relativo hacia atrás. En particular, no se atribuye el presupuesto de 100 m³ a las activaciones Río Negro sin unidad asignada en ese mapa. La verificación de referencias sí comprueba exactamente todas las filas y dominios.

Adquisición: 171 intentos MIP y 171 LP racionales. Calibración separada: 9 MIP Base.

Recuperación separada: 10 LP adicionales, cero MILP nuevos y 10 referencias recuperadas. El informe inicial permanece intacto. Los subproblemas de recuperación reutilizan los patrones guardados, conservan las filas originales y añaden un techo de costo explícito; los puntos se verifican contra el modelo original completo, incluidas las cotas escritas. Se descargaron los registros completos y se comprobaron localmente los hashes de ambos sellados, sin sobrescribir el archivo inicial.

## Límites de resolución

| Familia | Horizonte | Solver | Límite (s) | Criterio operativo Base alcanzado |
| --- | ---: | --- | ---: | --- |
| completo | 24 | cplex | 60 | sí |
| completo | 24 | gurobi | 60 | sí |
| completo | 72 | cplex | 60 | sí |
| completo | 72 | gurobi | 60 | sí |
| completo | 168 | cplex | 60 | sí |
| completo | 168 | gurobi | 60 | sí |
| completo | 360 | cplex | 120 | sí |
| completo | 360 | gurobi | 300 | no; censura explícita |
| sgtm | 24 | cplex | 60 | sí |
| sgtm | 24 | gurobi | 60 | sí |
| sgtm | 72 | cplex | 60 | sí |
| sgtm | 72 | gurobi | 60 | sí |
| sgtm | 168 | cplex | 60 | sí |
| sgtm | 168 | gurobi | 60 | sí |
| sgtm | 360 | cplex | 60 | sí |
| sgtm | 360 | gurobi | 120 | sí |
| simple | 24 | cplex | 60 | sí |
| simple | 24 | gurobi | 60 | sí |
| simple | 72 | cplex | 60 | sí |
| simple | 72 | gurobi | 60 | sí |
| simple | 168 | cplex | 60 | sí |
| simple | 168 | gurobi | 60 | sí |
| simple | 360 | cplex | 60 | sí |
| simple | 360 | gurobi | 60 | sí |

Se mantienen cuatro hilos, 8 GiB y una resolución simultánea. Cada límite se aplica por igual a las cuatro políticas del estrato. El criterio del 80% es operativo y no certifica optimalidad. Los estratos que no lo alcanzan al límite registrado de 300 s se conservan como censurados; no se presentan como superados.

## Estado de la campaña

Se congelaron los límites y la máscara común de referencias. Las **3.840 asignaciones comparativas siguen sin lanzar**. La calidad es evaluable en 3816 asignaciones; 24 permanecen diagnósticas y 0 tienen calidad desconocida.

No se seleccionó ninguna política ganadora. Estas comprobaciones no demuestran una ventaja computacional de Budget-L2 ni amplían la procedencia de los datos.

Los bancos siguen siendo recombinaciones históricas con exposición previa documentada. La inferencia posterior debe remuestrear padres completos, conservando horizontes, semillas y la máscara común de elegibilidad.
