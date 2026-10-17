# Ablación posterior de mecanismo, fijada antes de ejecutar

Pregunta motivada por el seguimiento de 48 tratamientos: en control30-3-2-3,
Budget-warm-IF1 evita las terminaciones malas de L2-warm-IF1, aunque Cold-IF1
igualó o mejoró su calidad. Se desea separar representación final e inicio.
La elección del modelo procede de un resultado observado: **estudio de mecanismo**,
no confirmación independiente de generalización ni selección favorable omitida.

Modelo original, factores y presupuestos sin cambios; semillas nuevas 59 y 71.
Siete tratamientos en cada semilla, 14 asignaciones con orden aleatorio 20261017:

- Cold-Base-IF1, Cold-L2-IF1, Cold-Budget-IF1, cada uno hasta 15 s.
- Warm-L2-to-L2, Warm-L2-to-Budget, Warm-Budget-to-L2, Warm-Budget-to-Budget:
  fase ordinaria hasta 1 s en la representación inicial, comprobar/reparar y
  fase IF1 hasta 14 s en la representación final, con Start completo si existe.

Todos conservan FeasibilityTol=1e-6, IntFeasTol=1e-5, cuatro hilos, presolve
y escalado interno automáticos, gap 1 % y referencia global de 20 s.
Se reutilizan exactamente reparación, retención y auditoría final del protocolo
principal. La representación distinta entre fases escala filas/RHS equivalentes,
sin tocar variables, dominios, objetivo o presupuestos. El candidato se transmite
en coordenadas originales, después de verificar todas las restricciones.

El testigo exacto control/Cold-IF1/semilla 31 del seguimiento, costo mostrado
1,265277, está disponible antes de esta ablación y permite screening online.
Se registra la disponibilidad; no se lo incorpora como Start de los controles
ni se llama gratuita su adquisición. Los inicios derivan de las fases indicadas.

Se evalúan objetivos, costos completos, calidad de Start, entrega, cotas/gaps
contradichos y consistencia interna de las etiquetas óptimas con su gap mostrado.
No se selecciona el mejor intento ni se cambian parámetros tras observarlos.
Una asociación con la representación final identifica ese componente dentro de
esta implementación; no prueba una causa interna específica del solver.
