# Sensibilidad del objetivo y aceptación certificada

Investigación posterior motivada por las notas recibidas. No modifica OMS
v1.3.5 ni diseños anteriores y no ejecuta nuevos MILP. No se afirma novedad de
dualidad, sensibilidad paramétrica, reparación racional o Farkas.

## Datos y tres etapas

Se usan todas las 72 entregas del diseño previo de 80 tratamientos, incluidos
controles fuertes, dos semillas y ambos solvers. Se agrupan por modelo y vector
entero completo: 41 patrones distintos, 12 de nive. Se conservan las ocho
ausencias de entrega. Los otros cuatro modelos son los ya elegidos, no nuevas
familias: control es referencia conocida. Esta generalización es retrospectiva.

1. Para cada uno de los 41 patrones, calcular v(0) y v(1). Para los 12 de nive,
   añadir lambda = 2^-30, 2^-26, 2^-22, 2^-18, 2^-14, 2^-10 y 2^-6.
   Son factores diádicos exactos, fijados antes de las nuevas llamadas LP.
   Cada valor se respalda con primal/dual racional, rayo o estado desconocido.
2. Para los 12 patrones de nive, minimizar lambda en [0,1] sujeto a las filas
   y cotas continuas ampliadas por lambda*presupuesto. Certificar ese umbral
   mediante primal/dual; se mantienen exactos enteros y sus cotas originales.
3. Sobre los mismos 80 tratamientos, evaluar aceptación primal sola, reparación
   exacta y un filtro que exige una continuación exactamente factible de costo
   U <= costo_nominal + epsilon_obj. Epsilon_obj = max(1e-6, abs(U)/100),
   numérico experimental y específico de cada modelo, no margen económico de
   operador. Reparación y filtro usan los mismos testigos y cache por patrón;
   se mide por separado la comprobación y adquisición de certificados.

La comparación es una reproducción sobre candidatos almacenados, no un nuevo
ensayo end-to-end ni una prueba de ventaja de rendimiento. El filtro acepta el
costo numérico cuando queda respaldado por ese U; en otro caso entrega una
corrección comprobada o se abstiene. No traslada gaps ni cotas globales.

## Construcción exacta

Tras fijar z, cada fila <= se amplía en +lambda*delta. Una fila >= se cambia
de signo y se amplía igual; una igualdad se reemplaza por sus dos lados. Cada
cota continua finita se amplía en lambda*beta. No se amplía ninguna cota o
dominio entero. Los datos originales son los canónicos binary64 archivados;
los cálculos y la exportación decimal completa conservan esos racionales.

Las variables continuas del LP exportado son libres; todas sus cotas se
expresan como filas. Así el checker puede verificar A^T*pi=c y pi<=0, sin
confiar en costos reducidos redondeados ni en el estado del solver. En los LP
de umbral se añade una variable lambda con cotas 0 y 1, también como filas.

LP exactos SoPlex 8.1.0/GMP, límite 2 s por llamada y watchdog 4 s.
Todos los intentos, límites y fallos se conservan, sin sustituciones o retuning.
El costo de estas auditorías se mide separado de las resoluciones anteriores.

## Protección adaptada al patrón

Después de v(0), para cada patrón exactamente factible de nive con certificado
se fija epsilon=max(1e-6,abs(v(0))/100). El objetivo umbral T se redondea hacia
arriba a un múltiplo de 2^-40 desde v(0)-epsilon, para exportarlo exactamente;
se comprueba T<v(0). Minimizar lambda con la fila costo<=T permite encontrar
la primera relajación que admite tal reducción de costo. Si es inviable en
[0,1], se informa ese certificado. Si el umbral es positivo, elegir el mayor
factor diádico estrictamente menor que él (hasta 1) y certificar v de ese factor.
Se compara con el factor diádico permitido por epsilon/Delta del dual v(0).

Esta elección es posterior al patrón y requiere LP adicionales: no es un
presupuesto universal o una regla preventiva para enteros todavía desconocidos.
Se publican solo garantías verificadas, incluida la pérdida v(0)-v(lambda).
Una cota dual fija es suficiente, mientras reoptimizar el dual proporciona
la cota ajustada del LP ampliado bajo dualidad fuerte. No se confunden ambas.

## Criterio de cierre

La medida ajustada y los umbrales pueden ser un diagnóstico útil. Una tercera
contribución o segundo artículo requiere además eficiencia o garantías superiores
a controles comparables. Si la reparación exacta ofrece la misma garantía al
mismo costo, se registra ese límite y no se presenta el filtro como superior.
