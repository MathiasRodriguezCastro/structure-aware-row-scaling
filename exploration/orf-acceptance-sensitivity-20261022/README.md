# Sensibilidad de aceptación por cotas escritas

Análisis **posterior a los resultados**, separado del experimento registrado.
No modifica el archivo científico congelado ni las conclusiones temporales.
La malla diagnóstica y las comprobaciones que permanecen fijas están en PLAN.json.

Se utilizan las 3.816 asignaciones elegibles y todos los candidatos guardados
que satisfacen el requisito de costo. El umbral cero reproduce los éxitos
registrados. Los otros umbrales solo cambian la admisión del residuo de las cotas
escritas, medido en las unidades algebraicas de cada variable; no son estándares
físicos ni una reparación de las soluciones.

Desde la raíz que contiene el archivo científico de la campaña y las fuentes
editoriales canónicas, sin licencias comerciales:

```sh
python3 scripts/research/orf_acceptance_sensitivity.py
python3 scripts/research/check_orf_acceptance_sensitivity.py
python3 scripts/research/orf_confirmation_tables.py
```

El primer programa usa los auditores ya reproducidos independientemente. El
segundo reconstruye directamente desde los vectores y las cotas del LP los
máximos de violación de cotas y de integralidad de 13.387 candidatos, y comprueba
todos los recuentos. Los otros requisitos reutilizan las comprobaciones físicas,
de filas y costo del archivo sellado. No se ejecutan optimizadores.

CPLEX pasa de 99/477 a 395/477 objetivos Budget-L2 al permitir un residuo de
cota de 10^-9; L2 pasa de 102/477 a 405/477. A 10^-5 son 430/477 y 431/477.
Las medianas de los residuos finales positivos son aproximadamente 3,41e-13 y
4,51e-13. La baja aceptación exacta depende mucho de residuos pequeños; esta
sensibilidad no identifica una ventaja adicional del contrato.

Los recuentos de dominios finales y de objetivos alcanzados se conservan por
separado: un candidato anterior puede satisfacer el objetivo. No se estiman
tiempos PAR2 alternativos porque solo se guardó el reloj de auditoría del primer
prefijo aceptado bajo el criterio original. Todos los resultados registrados,
tiempos y sus intervalos permanecen intactos.
