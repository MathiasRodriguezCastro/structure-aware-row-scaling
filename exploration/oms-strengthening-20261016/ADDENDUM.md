# Control fuerte añadido después del cierre del archivo de datos

El archivo `oms-strengthening-artifact.zip` conserva su primera versión sin
modificar. Una comparación posterior entre dos CSV ya verificados muestra que
el prototipo conjunto usa **1,222 veces el trabajo de Budget-L2 por filas**
en los 18 pares a 100 m3 con presolve automático. Solo mejora en dos modelos.
Esto refuerza la decisión previa de dejarlo separado del artículo.

El informe PDF y los dos `RESULTADOS.md` correspondientes incorporan ahora ese
contraste. El archivo de datos original conserva el informe previo a este
addendum, cuya comparación con filas minimax y con el conjunto sin contratos
sigue siendo válida. No se modificó ni se repitió ningún experimento.

`strong_control.py` reconstruye el contraste y verifica los objetivos primales,
las banderas y los hashes de ambos CSV. `strong-control-addendum.json`, en el
directorio del estudio conjunto, identifica además el SHA256 del archivo padre.
La ausencia de contradicciones no certifica todos los gaps, y las dos políticas
no tienen idéntica exportación binary64. No se proclama superioridad del
prototipo nuevo frente al control disponible más competitivo.
