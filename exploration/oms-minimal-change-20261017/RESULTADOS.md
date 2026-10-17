# Resultado: no aparece oportunidad real para cambiar columnas mínimamente

Se implementó un selector exacto que minimiza el mayor cambio logarítmico de las
columnas continuas, conserva las columnas enteras y aproxima después L2 por filas
dentro del conjunto admisible. Usa restricciones de diferencias y certificados
de ciclos negativos; esos ingredientes de escalado y grafos son clásicos.

El banco fijo tiene 27 casos: cinco modelos externos bajo tres alcances de
contrato y seis modelos de despacho bajo dos presupuestos. En los 22 casos
compatibles el cambio mínimo de columnas es cero. Los otros cinco conservan un
certificado de incompatibilidad. Ningún caso real se rescata mediante columnas.
No se hicieron llamadas nuevas a optimizadores.

El verificador independiente comprueba 125.538 filas y 293.996 exportaciones de
coeficientes. El caso construido exige un cambio de exponente 12 y un presupuesto
de cotas más estricto lo hace incompatible; se contrasta por enumeración directa.
Estos ejemplos positivos se completaron después del diagnóstico del banco real,
no constituyen un registro prospectivo del orden de toda la exploración.

En cinca, el coeficiente 1e17 de una binaria exige simultáneamente un exponente de
fila <=-27 por magnitud y >=-6 por precisión del punto sin redondeo. Una columna
continua no modifica ese conflicto. Al incluir redondeo, la reserva gamma*M ya
agota el presupuesto. Esto motivó examinar reformulaciones distintas del escalado
diagonal. Se descarta este selector como contribución nueva para OMS.

Reproducir: `python3 verify.py` y `python3 test_selector.py` desde esta carpeta.
Los resultados preservados están en `diagnostic/`; el diagnóstico no sobrescribe
esa carpeta. El artículo y sus versiones congeladas permanecen intactos.
