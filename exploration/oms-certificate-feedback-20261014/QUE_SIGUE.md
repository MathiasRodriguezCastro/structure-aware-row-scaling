# Decisión después del ensayo

La variante monolítica de realimentación con hasta tres fases queda cerrada.
No mejoró el costo exacto de reparar o reiniciar sin cortes. No se añaden
modelos, semillas o iteraciones a esta campaña ni material a OMS v1.3.5.

Lo reutilizable es concreto: proyección dual exacta, conflictos parciales
certificados, exportación sin fortalecimiento accidental y separación entre
costo nominal, costo respaldado y optimalidad global. La selección de 20
binarias es una estructura observada, no un algoritmo global demostrado.

La nota preventiva delimita otra pregunta: la existencia de presupuestos
uniformes bajo racionalidad es fácil con familias completas; lo difícil es
encontrar envolventes certificadas útiles sin enumerar duales y rayos.
No hay todavía un resultado computacional que justifique incorporarlo a OMS.

## Siguiente prueba posible en la tesis, todavía no ejecutada

Estudiar selección en un **maestro Benders realmente descompuesto** del despacho,
donde los cortes aproximan una función ausente del maestro y no solo agregan
filas redundantes al modelo monolítico. Antes de implementar debe verificarse
la partición, qué variables quedan enteras, el subproblema y los términos de
costo/cotas que garantizan la validez de cada corte. No se presupone que el
despacho actual tenga ya esa estructura implementada.

Registrar para cada corte: subproblema y familia física de origen, violación
normalizada, actividad, contribución a la cota, edad, soporte temporal y dirección.
Comparar, sobre los mismos candidatos y presupuesto, agregar todos, selección
por mayor violación normalizada y un selector geométrico documentado. Solo
entonces comparar un selector que añada información hidráulica/térmica/temporal.
No confundir la identidad física de la restricción con la utilidad del corte.

Medir tiempo completo, cota y gap con testigo válido, tamaño del maestro,
repeticiones y comportamiento con presolve habitual. Las ablasiones deben
separar utilidad de información física, diversidad y simple reducción de filas.
Cerrar si no hay mejora frente a selectores fuertes, sin ampliar para buscarla.

La geometría por sí sola no establece novedad:
[Hosseini y Turner](https://arxiv.org/abs/2110.08448) y
[Glomb, Liers y Rösel](https://doi.org/10.1007/s12532-025-00291-1) son
antecedentes directos. La certificación racional general tampoco es una
contribución nueva por sí sola:
[SCIP exacto y VIPR](https://scipopt.org/doc-10.0.0/html/EXACT.php).
No se ejecutó aquí una comparación de rendimiento con esos métodos.

Esta es una propuesta independiente para la tesis, no un beneficio ya probado,
ni una promesa de resultados para el artículo actual. El código C++ no se tocó.
