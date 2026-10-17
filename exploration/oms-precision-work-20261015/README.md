# Precisión–trabajo con calidad común

Leer `RESULTADOS.md` y `precision-work-note.pdf`. Investigación independiente:
se preservan OMS v1.3.5 y los ocho paquetes cerrados anteriores.

Tres SG-Ter-Mer reales conocidos, 360 períodos, integralidad original. Noventa
brazos y 63 resoluciones MILP distintas; los alias coinciden exactamente en
matriz y parámetros. Todos los candidatos se guardan, no solo incumbentes que
mejoran el objetivo. Referencias factibles previas fijan una aspiración de calidad
común, sin proporcionar Starts. El replay separa residuos, calidad nominal y
continuación racional del mismo patrón. No certifica óptimos MILP.

Reproducción desde este directorio, sin optimizadores ni licencias:

```bash
python3 independent_check.py
python3 analyze.py
python3 write_report.py
python3 -m pytest -q test_math.py
pdflatex -halt-on-error -interaction=nonstopmode precision-work-note.tex
```

Python 3.10+, NumPy para arrays archivados, Matplotlib para las figuras, pytest
para seis invariantes y pdflatex con paquetes comunes para el PDF. El chequeo
independiente lee los Base.lp originales, usa exponentes locales por fila frente
al exponente global del productor, comprueba todos los candidatos, reconstruye
los LP de patrones y comprueba duales/testigos racionales.

`design.json`, snapshots y `input-hashes-before-mip.json` fijan parámetros,
modelos, referencias y fuentes antes de resolver. `posthoc-design.json` fija
todas las primeras llegadas que pasan a la comprobación posterior; no se buscan
patrones sustitutos para reemplazar una respuesta adversa. `IMPLEMENTATION_NOTES.md`
explica la semántica documentada de cotas 1e20 y las limitaciones del tiempo.

Nuevas corridas requieren Gurobi 13.0.2 con licencia y SoPlex 8.1.0/GMP en la
ruta declarada en `study.py`. En una copia nueva de este directorio, conservar
fuentes, protocolo, snapshots, `design.json`, entradas, referencias y sus hashes;
excluir `runs/`, `certificates/` y derivados. Ejecutar secuencialmente:

```bash
python3 study.py run
python3 study.py evaluate
python3 study.py certify
```

La referencia ya archivada basta; no se necesita el generador C++. `prepare`
solo reconstruye desde el banco anterior y requiere ese repositorio; se niega
si ya existe un diseño fijado. Los MILP y los LP de validación son experimentos
distintos. La validación LP posterior no se cobra gratuitamente como mejora del
algoritmo; sus costos y los de adquisición de referencias se informan aparte.

`package_study.py` crea ZIP y manifiesto, extrae en limpio y verifica replay con
importaciones/ejecuciones de solvers bloqueadas, los seis tests, PDF y hashes
de entregas previas. Los binarios y licencias no están incluidos. Código propio
bajo la licencia del repositorio; las entradas conservan procedencia y condiciones
de la tesis, sin relicenciarse por archivarlas aquí.
