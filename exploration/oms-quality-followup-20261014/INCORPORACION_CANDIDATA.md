# Redacción candidata, fuera del manuscrito

Este texto se prepara para revisión científica futura. No modifica OMS v1.3.5
ni anuncia una contribución adicional. El umbral pedido fue una mejora muy útil
al objetivo del artículo, con evidencia defendible y sin sobrecargarlo.

## Qué sí respalda la evidencia

- En un modelo MIPLIB auténtico, la proyección contractual del mismo kernel L2
  diádico evita objetivos pobres y declaraciones de optimalidad contradichas.
- El cruce de orígenes/destinos identifica un efecto de la representación final,
  bajo presolve automático e IntegralityFocus, no solamente del punto inicial.
- Los controles Base/IF1 dan calidad competitiva. Los tiempos Budget son mayores
  que las terminaciones incorrectas rápidas L2, por lo que no se declara aceleración.
- Una entrega dentro de los presupuestos y una cota/gap fiable son propiedades
  distintas. Los contratos no certifican optimalidad; el checker sí refuta
  informes incompatibles mediante testigos exactos y consistencia del gap.

## Qué impide elevarlo todavía a una contribución general

El mecanismo se estudió en un modelo elegido después de observar la señal.
Las semillas nuevas aportan repetición, no independencia de aplicación.
El seguimiento conservó los otros dos modelos: Budget no supera a los controles
fuertes o se abstiene. La fase warm no produce una ventaja general.
No se identificó una regla previa que prediga beneficios de contrato sobre Base/IF1.

## Párrafo inglés acotado, si se decide incluir evidencia de mecanismo

> A separate, source-preserving MIPLIB mechanism study found that the contract
> projection of dyadic L2 scaling avoided poor incumbents and independently
> contradicted completion reports obtained with the dyadic L2 control without the
> residual-budget projection, including
> with automatic presolve and IntegralityFocus enabled. A crossover of initial and
> final representations localized the observed effect to the final representation
> in that model. Unscaled IntegralityFocus controls remained competitive, and the
> contract did not certify global optimality. These selected-model results support
> a limited software robustness observation rather than a claim of general solver
> superiority or a new optimality guarantee.

Si se incorpora más adelante, correspondería una tabla compacta en suplemento
con todos los controles y la explicación explícita de selección posterior.
No habría que crear otro teorema, cambiar el título o convertir el ciclo warm
en la contribución principal. Hoy el texto queda exclusivamente aquí.
