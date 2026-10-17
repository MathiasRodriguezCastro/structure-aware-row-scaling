# Reformulación y límite de precisión

## Equivalencia exacta

Sea g una forma lineal en variables continuas y z binaria. Una cota válida
global g<=B permite reemplazar M por M'=min(M,max(0,B)). La validez de B debe
probarse sobre el modelo original; aquí la prueba racional está preservada en
`../oms-budget-reformulation-20261017/`.

Para h>0, sustituir g<=M'z por

    g-hy<=0, 0<=y<=M'/h, w+z=1, 0<=w<=1, SOS1(w,y).

Si z=0, w=1 implica y=0; si z=1, w=0 permite elegir
y=max(0,g/h). Esto prueba igualdad de las proyecciones de puntos enteros.
No prueba igualdad de las relajaciones lineales. Esta reformulación es conocida.

## Transferencia al punto redondeado

Denotar por epsilon el residuo máximo del enlace tras multiplicar por alpha,
epsilon_c el error absoluto de w+z=1, gamma_s el umbral SOS y tau el exceso
máximo permitido en la cota superior de y. Si round(z)=0, la hipótesis inicial
|z-round(z)|<=gamma implica w>=1-gamma-epsilon_c. Si esta cantidad es mayor
que gamma_s y SOS1 tiene a lo sumo un miembro mayor que gamma_s en valor
absoluto, resulta |y|<=gamma_s, y g<=epsilon/alpha+h*gamma_s.
Si round(z)=1, g<=epsilon/alpha+h*(M'/h+tau), que implica
g-M<=epsilon/alpha+h*tau. En ambos casos,

    violacion de la fila original redondeada <= epsilon/alpha+h*max(gamma_s,tau).

El selector usa estos límites, verifica exportación binaria exacta y maximiza h
para reducir M'/h. Esta optimalidad local del selector no implica menor trabajo
del optimizador. La prueba explica por qué desaparece M del límite de error;
no constituye un certificado de optimalidad MILP ni una prueba de prioridad.

## Observación posterior al piloto

La condición de distancia entera puede debilitarse para esta fila individual:
si round(z) pertenece a {0,1}, round(z)=0 implica z<=1/2. Basta entonces
1/2-epsilon_c>gamma_s para forzar |y|<=gamma_s. Esta observación no se usó
para rediseñar el piloto ni para cambiar su selector. Tampoco elimina la
necesidad de verificar las demás filas después de redondear otras binarias.

Las identidades y equivalencias básicas son sencillas. La posible novedad
residiría en un criterio de selección útil, contrastado con las escalas de
holguras ya existentes. El piloto no acredita esa utilidad adicional.
