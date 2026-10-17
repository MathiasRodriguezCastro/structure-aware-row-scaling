# Reformulación de activaciones guiada por presupuestos

17-10-2026. Investigación separada de OMS v1.3.14. El diagnóstico previo del
escalado mínimo ya es conocido: ningún caso real requiere columnas, y cinca
conserva un certificado local de incompatibilidad. Mathias pidió buscar un
método nuevo sin restringir la familia de transformaciones.

## Candidato y antecedentes
Se investiga un procedimiento de contracción certificada de coeficientes de
activación antes del escalado. El fortalecimiento de coeficientes y la propagación
de cotas son clásicos; no se afirma que sean inventos de esta investigación.
La pregunta es si exigir presupuestos explícitos permite decidir qué contracción
se necesita y obtener una representación admisible donde ninguna escala diagonal
con columnas enteras inmóviles puede hacerlo. Es una reformulación equivalente
para puntos enteros, no una equivalencia de la relajación LP ni puro escalado.

## Selección y puerta de oportunidad
Usar todos los modelos externos ya archivados: H10/H12, control30-3-2-3,
neos-3421095-cinca y ta1-UUM. Normalizar sentidos y detectar exclusivamente
filas g(x_cont)<=M*z con RHS cero y una única binaria z de dominio [0,1].
No modificar otras clases de restricciones. Presupuestos originales del piloto,
gamma=1e-9, epsilon=1e-6, ventana [1e-9,1e9].
Se seleccionan las filas cuyo M supera el umbral necesario derivado del contrato.
El diagnóstico previo identificó candidatos en control30 y cinca; no se oculta
que esa información motivó esta dirección. Los otros tres son controles nulos.

Primero propagar cotas racionales con certificado, hasta ocho barridos completos
y un máximo de 15 segundos por modelo. Detener al final de un barrido si todos
los candidatos ya tienen una cota suficiente. Conservar cada deducción y su
procedencia. No se ejecuta un LP ni MILP en esta primera fase.
Una cota global exacta g(x)<=B permite sustituir M por max(0,B) cuando es menor
que M: z=0 conserva la fila y z=1 queda justificado por esa cota. Redondear B
hacia arriba a binary64; verificar de nuevo los contratos diádicos de las filas.
Se conservan todas las incompatibilidades y los casos sin cota útil.

Solo si el diagnóstico restaura los contratos completos de algún modelo se
prepara una campaña aparte, con controles fuertes que incluyan propagación y
fortalecimiento estándar. No se atribuye a escalado una mejora de la relajación.
Una mejora solo frente a la formulación defectuosa con M excesivo no establece
por sí sola novedad ni superioridad respecto del preprocesamiento existente.

Los modelos originales, estudios anteriores, paper y releases no se modifican.
