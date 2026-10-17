# Escalado conjunto con el mínimo cambio de columnas

Exploración separada de OMS v1.3.14. Fecha: 17-10-2026. Los resultados previos
del método conjunto y sus desventajas frente a Budget-L2 son conocidos.

## Pregunta
¿Puede un método que minimiza el cambio de unidades de las columnas continuas
resolver incompatibilidades contractuales reales sin introducir transformaciones
innecesarias? La reducción a diferencias y los algoritmos de grafos son clásicos.
No se declara novedad antes de revisar antecedentes y obtener evidencia útil.

## Especificación antes del diagnóstico
- x_j=2^v_j y_j, v_j=0 en todas las columnas enteras. Toda la fila y RHS se
  multiplican por 2^u_i; matriz, RHS, objetivo y cotas se escriben exactamente.
- Ventana no ceros [1e-9,1e9], epsilon=1e-6, límite RHS/cotas 1e19.
- Minimizar H=max_j |v_j| sobre exponentes enteros admisibles. A H=0 el método
  es solo por filas; si existe una solución con columnas fijas, se conserva ese
  caso. No se afirma monotonicidad del tiempo del MILP.
- Fijadas las columnas, elegir en cada fila el factor diádico admisible más
  cercano al kernel L2. No optimizar el número de condición como sustituto del
  trabajo del solver.
- Contratos de filas con reserva gamma*sum_entero|a|. Agregar límites de
  precisión para cotas de variables continuas: epsilon_bound*2^v_j<=Delta_j.
  Una especificación incompatible produce un certificado, no otra tolerancia.

## Banco de diagnóstico
Seis despachos ya conocidos con presupuestos 30/100 m3 y .01 MW, gamma=1e-9;
cinco modelos externos ya archivados en el piloto de generalización: Kondili
H10/H12 y los tres MIPLIB control30-3-2-3, neos-3421095-cinca, ta1-UUM.
Se conservan todos. En los externos se estudian por separado el contrato crudo
original y el contrato redondeado a gamma=1e-9; no se confunden sus garantías.
Las cotas continuas externas usan sus presupuestos archivados de 1e-4/1e-5.
Para despacho, las unidades físicas de cotas se declaran antes de resolver;
por ahora se estudia el diagnóstico original de filas y se indica expresamente
cuando falta un contrato físico de cota. No se inventan unidades.

## Puerta de utilidad
Primero implementar, demostrar y comprobar el algoritmo con casos pequeños
exhaustivos y un verificador que no importe el constructor. Después diagnosticar
todo el banco, sin nuevas llamadas MILP. Si no hay una ampliación útil de
admisibilidad, no lanzar una campaña solo por obtener números más centrados.
Si hay candidatos, fijar otro protocolo antes de resolver: todos los candidatos,
controles Base/L2/Budget-L2/NF3 y método conjunto anterior, semillas nuevas,
costos completos, puntos en coordenadas originales, incertidumbre de cotas y
resultados adversos. La comparación con el Budget-L2 actual sigue siendo
obligatoria; una ventaja contra un control más débil no basta.

El paper y los releases congelados no se modifican durante esta exploración.
