# Selección con la exportación efectiva

El prototipo incorpora al selector la condición del suplemento de v1.4.2;
la política experimental histórica permanece intacta. Solo escala filas.

Para cada candidato binario64 positivo alpha, el programa calcula exactamente
los errores de los productos escritos a 17 cifras y reconstruidos como binario64:

    e_a = a_escrito - alpha*a
    e_b = b_escrito - alpha*b
    B(alpha) = |e_b| + sum_j |e_a,j| X_j
    E = gamma sum_{j entero} |a_j|

Una columna sin cota finita impide esta reserva uniforme cuando su error es
distinto de cero. Si el error es exactamente cero, no hace falta su cota.
El filtro exige límites de magnitud de los coeficientes realmente escritos y

    epsilon + B(alpha) + alpha E <= alpha delta.

La implementación ensaya una lista fija: proyección ideal, extremos, 32 vecinos
por dirección, 65 puntos logarítmicos y potencias de dos en el intervalo ideal.
Entre los candidatos certificados elige el mínimo de la distancia logarítmica
calculada en binario64, con desempate hacia el factor mayor. La certificación
del residuo sí usa racionales exactos; no se certifica el orden de logaritmos
reales entre candidatos casi empatados ni un óptimo sobre todos los binarios64.
La búsqueda puede abstenerse aunque exista otro
factor. Agotar la lista no es un certificado de inexistencia global.

## Qué garantiza

Si el punto crudo cumple el residuo escrito <=epsilon, las cotas usadas en B
y la distancia entera <=gamma, el punto redondeado satisface el presupuesto
original. La transferencia usa la identidad ya documentada y la desigualdad
triangular. No afirma que el solver respete automáticamente esas hipótesis,
que el candidato sea exactamente factible en todas las filas originales ni
que una cota dual o un gap MIP sean correctos.

Si E>=delta, la condición suficiente es imposible para cualquier alpha positivo,
porque epsilon>0 y B>=0. Es incompatibilidad del contrato suficiente con esa
reserva entera; el modelo físico puede ser factible y un punto concreto puede
cumplir el presupuesto. Reducir la reserva exige justificar otra hipótesis de
redondeo o verificar el punto, no ignorar el certificado.

## Qué valor tiene la información física

Las unidades convierten una exigencia de la aplicación en delta algebraico.
Una vez compiladas las cotas numéricas y elegidos los factores, el solver recibe
solo números. Un control que reproduce esos factores exporta el mismo modelo:
no cabe atribuir a sus etiquetas una diferencia causal de tiempo o precisión.
La utilidad adicional debe demostrarse en la especificación de requisitos,
su compatibilidad y el cumplimiento observado, además del rendimiento.

## Alcance de la contribución

Es una extensión algorítmica implementada y comprobable de la condición de
exportación del artículo. La identidad de transferencia y la optimalidad sobre
una lista finita son elementales. Estos ensayos no establecen una novedad frente
a toda la literatura de escalado ni justifican por sí solos una tercera gran
contribución. `SELECTOR_VALIDATION.json` aporta un contraejemplo de la proyección
ideal sin reserva y pruebas racionales de frontera; los modelos aplicados se
auditan aparte en `selection-certificates.csv`.

`export_selector_fast.py` ordena esa misma lista por la misma puntuación antes
de certificar y se detiene en el primer candidato admisible. Conserva el factor
del prototipo exhaustivo: todos los candidatos restantes tienen puntuación no
mejor. El benchmark posterior exige identidad del archivo exportado completo;
sus tiempos de compilación no sustituyen retrospectivamente los tiempos de
proceso medidos durante las resoluciones.
