# Incrustación entera redundante guiada por precisión

17-10-2026. Candidato posterior al piloto SOS de 54 llamadas, cuyo resultado
conocido no mejora SOS-unit. Búsqueda abierta autorizada por Mathias. No se
modifica OMS. No se afirma prioridad a partir de una búsqueda bibliográfica.

## Propiedad que se ensaya

Para cada binaria seleccionada z, añadir q entera, 0<=q<=K, y sigma*(K*z-q)=0,
con K=2^k entero y sigma diádico positivo. Es redundante exactamente: q=K*z.
La proyección de la relajación LP también permanece idéntica al modelo de partida.
Una copia continua es un control estructural con idéntica matriz y cotas.

Si |z-round(z)|<=gamma, |q-round(q)|<=gamma y
|sigma*(K*z-q)|<=epsilon, entonces, cuando

    K*gamma + epsilon/sigma + gamma < 1/2,

los enteros round(q) y K*round(z) coinciden. Por tanto

    |z-round(z)| <= (gamma+epsilon/sigma)/K = gamma_eff.

El contrato de una fila con una sola binaria utiliza
epsilon/alpha + |a_z|*gamma_eff <= delta. Es una garantía condicional sobre los
residuos y distancias efectivamente comprobados, no sobre parámetros nominales.
Se usa la contracción M certificada en la exploración anterior, en todos los
controles. No se atribuye al escalado el fortalecimiento previo.

## Selector y puerta estática

Agrupar las 96 filas críticas por binaria. Elegir el menor t entero con todos
los coeficientes de las filas seleccionadas y ecuaciones de copia en
[max(1e-9,2^-t),min(1e9,2^t)]. Para cada k=0,...,28 se usa el mayor sigma
diádico que respeta esa ventana en la ecuación. Dentro de t mínimo, elegir
el menor k factible y factores de fila próximos a L2. Todos los cálculos de
admisibilidad son racionales. Mantener las mismas filas no seleccionadas del
piloto previo. Se guarda abstención explícita si no se cubren todas las filas.
Antes de resolver, contrastar enumeración finita y equivalencia proyectada.

## Piloto fijo posterior a la puerta estática

control30-3-2-3 y neos-3421095-cinca; presupuestos 1e-4 y 1e-8 exclusivamente
en activaciones; restantes presupuestos y cotas originales. Datos de
descubrimiento. Semillas nuevas 167,173,179; cuatro hilos, TimeLimit=30 s,
WorkLimit=1, MIPGap=.01, epsilon=1e-6, gamma=1e-9. Presolve automático y
desactivado, sin otros cambios. PreSOS1BigM=0 común a todos los brazos.

Por celda: Contracted-L2, Raw-budget (contrato sin redondeo, si es admisible),
SOS-unit, Integer-copy y Continuous-copy. Los dos brazos de copia solo se
resuelven si el selector íntegro es admisible; la copia continua usa los mismos
factores aunque carece del contrato entero. Se conservan todas las abstenciones.
Controles invariantes por presupuesto se resuelven una vez y se verifican frente
a ambos presupuestos. Orden intercalado con semilla fija. Verificación original
racional, hipótesis de amplificación y costo/objetivo de puntos aceptados.

Si presolve destruye las hipótesis, o la copia continua logra lo mismo, no se
atribuye la mejora al mecanismo propuesto. Ningún resultado con presolve-off
establece utilidad con presolve automático. No se ajusta K a partir de objetivos.
No se incorporará al paper sin beneficio sobre controles fuertes.

## Antecedentes relevantes

La introducción de variables redundantes y la eliminación de integridades
implícitas en presolve son técnicas conocidas. El objetivo experimental es una
selección contractual de la incrustación, no reclamar aquellas operaciones como
nuevas. El análisis de prioridad de este criterio sigue abierto.

Gurobi, IntFeasTol y tolerancias:
https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html
HiGHS, eliminación y agregación de variables enteras:
https://github.com/ERGO-Code/HiGHS/blob/master/highs/presolve/HPresolve.cpp
