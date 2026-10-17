# Registro técnico

Antes de la primera llamada de optimización, la preparación se detuvo en dos
comprobaciones: las cotas infinitas de la API no son JSON finito y la huella
distinguía -0.0 de 0.0 en la constante. Se corrigió la serialización (None para
cota ausente, cero canónico para la constante), se regeneraron los seis modelos
y se congelaron de nuevo script/diseño. No se observó ningún resultado MILP o
LP antes de esas correcciones. No cambió el protocolo ni se reparó ningún dato.

Durante el descubrimiento se observaron estados OPTIMAL con ScaleFlag=0 y
cotas muy superiores a otros incumbentes numéricamente verificados del caso
001. Se añade después del factorial UNA comprobación racional de factibilidad:
fijar el patrón entero del mejor incumbente del descubrimiento, conservar todas
las filas/cotas originales y exigir costo <=0. SoPlex exacto, 30 s, watchdog
45 s. Un testigo factible refutaría cotas positivas mayores que su costo; no
certificaría el óptimo entero. Un estado desconocido no prueba inviabilidad.
Es una validación posterior de la observación, no un brazo nuevo ni evidencia
prospectiva. No se cambian configuraciones, presupuesto, casos o semillas.

En la agregación final se corrigió una clave de unión de diagnósticos: el
agregador conservaba el sufijo `-diagnostic` y sus campos anidados quedaban
vacíos. Los diagnósticos originales se habían guardado y leído directamente;
la corrección no cambia resoluciones ni endpoints. `discovery-analysis.json`
reconstruye exactamente el agregado anterior a la reserva (incluyendo los
campos vacíos); su SHA256 coincide con el fijado en las conclusiones. El análisis
final sí une esos campos. Los hashes de todos los resultados de descubrimiento
permanecen idénticos a los fijados antes de optimizar la reserva.

Al cerrar (15 de octubre, alrededor de medianoche local), la comprobación
detectó ausente `Implementacion_Cpp/Codigo_Cpp/build/SistemaElectrico`. El hash
inicial del ejecutable usado para exportar se conserva en protected-files.json;
no puede comprobarse su persistencia al cierre. No se reconstruyó ni restauró
el binario. Se desconoce la causa de su ausencia. Los otros 23 archivos
protegidos sí conservan su hash: incluyen la entrega OMS, los siete paquetes
previos y las dos fuentes C++ auditadas. El replay no necesita el ejecutable y
verifica los seis MPS archivados, datos canónicos y resultados. La validación
final distingue esta ausencia de un archivo comprobado sin cambios.
