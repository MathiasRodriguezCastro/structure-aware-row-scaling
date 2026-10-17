# Decisión de incorporación y cierre

16 de octubre de 2026. La comprobación independiente pasó sobre los 144 puntos,
1.244.160 evaluaciones físicas antes/después de redondear y doce testigos exactos.

**No apareció una recuperación primal generalizable a más de una instancia.**
Las tres recuperaciones pertenecen a instance046 sin presolve. Los otros cinco
modelos ya cumplen con L2. Con presolve automático, las cuatro políticas cumplen
los 18 presupuestos por política. Esta exploración no sostiene el resultado
general deseado en la primera prioridad de la nota.

**Sí quedó resuelta la comparación competitiva directamente emparejada.**
NumericFocus=3 cumple en sus 36 llamadas y no presenta ninguna contradicción de
cota/gap detectada mediante los testigos disponibles. Budget-L2 cumple también
36/36, con una/tres cotas contradichas en los paneles auto/off, y ninguna
finalización al 1 % contradicha. Los cocientes geométricos de Work Budget/NF3
son 0,361/0,227 en cada panel de 18 pares. Menor trabajo con el mismo presupuesto
primal no equivale a igual calidad de optimización. No se declara una política
generalmente preferible ni se certifican cotas por ausencia de refutación.

Se incorpora una mención breve en la sección 7.9 y una tabla complementaria S16:
cierra la objeción de comparar remedios en paneles distintos y hace explícito el
límite del beneficio observado. No se añade otra contribución principal, algoritmo,
teorema ni sección al texto principal. Se conserva la Tabla 11 y su agregación
histórica; sus medias geométricas no se confunden con las medianas de la nota IF1.

La carta identifica el caso conocido y la configuración sin presolve. La
introducción aclara antes el recorrido presupuesto → factor admisible → archivo
escrito → solución verificada. El abstract y las dos contribuciones se conservan.

## Estado de las demás propuestas de la nota

- **Costo completo:** medido en cada proceso nuevo, con etapas disjuntas y sin
  amortizar la construcción. La campaña abarca un reinicio y carga variable;
  los tiempos describen el prototipo. El intento interrumpido está preservado y
  repetido mediante una enmienda explícita: 145 intentos, 144 resultados finales.
- **Frontera precisión–costo:** no se obtuvo una frontera completa. Se comparó un
  presupuesto común y la entrega terminal, sin callbacks para el primer incumbente
  verificado. No se adjudica al experimento ese resultado que no mide.
- **Segundo generador:** el piloto independiente STN-Scheduler/Kondili H10/H12
  ya cambia 88/104 factores, pero todas las políticas cumplen los presupuestos.
  No demuestra beneficio de aceptación de Budget frente a sus controles. Permanece
  en `oms-generalization-20261014`; no se amplía por ausencia de una señal útil.
- **Demanda corregida:** no se ejecutó una nueva campaña de los nueve casos
  históricos defectuosos. Se conservan sus resultados y límites explícitos;
  esta comparación utiliza únicamente los seis modelos sin ese defecto. No se
  afirma que reproduzca la ventaja histórica con datos corregidos.
- **Reserva de exportación:** ya existe en la implementación de activaciones y
  en el suplemento. Se conservan su hipótesis de caja finita y las comprobaciones
  racionales; no se presenta otra vez como contribución nueva.
- **Más kernels, condicionamiento, LP–DW y cortes:** fuera de este cierre OMS.

La cohorte y su replay quedan cerrados. No se añaden barridos para buscar un
resultado favorable. El nuevo paquete local es v1.3.9; v1.3.8 y los archivos de
investigación anteriores permanecen intactos. DOI y depósito remoto quedan para
el final, tal como indicó Mathias.
