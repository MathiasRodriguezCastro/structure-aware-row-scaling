# Factores exactos y reserva de exportación

Leer `RESULTADOS.md`, `exact-factor-note.pdf` y `LITERATURA.md`. Investigación
independiente de OMS: no hay nuevas llamadas a optimizadores ni cambios del
manuscrito. Se conservan los diez paquetes previos y la entrega v1.3.5.

Se implementa un selector completo sobre todos los factores binary64 que
multiplican exactamente coeficientes y RHS, además de un selector finito que
verifica la reserva por productos redondeados. Las tres entradas canónicas
se incluyen aquí, fijadas por hashes contra precision-work-artifact.zip.
Su procedencia y condiciones de uso siguen siendo las del banco de tesis;
no se relicencian los datos por incluirlos. El código propio usa LICENSE del
repositorio. Los modelos son conocidos, de una sola familia, con integralidad.

Reproducción completa, desde este directorio, sin licencias:

```bash
python3 study.py
python3 independent_check.py
python3 math_checks.py
python3 analyze.py
python3 write_report.py
python3 -m pytest -q test_factors.py
pdflatex -halt-on-error -interaction=nonstopmode exact-factor-note.tex
```

Python 3.10+, biblioteca estándar y pytest; pdfLaTeX para el PDF. No se requiere
NumPy ni optimizador. El verificador independiente no importa los selectores;
prueba optimalidad descartando un factor mejor mediante factibilidad exacta,
y vuelve a calcular las reservas sobre las cotas originales.

`design.json` y `PROTOCOL.md` se fijaron antes de calcular resultados. Las
fuentes de selección y pruebas iniciales se guardan en snapshots. Se corrigió
un contador derivado después de la primera corrida; ver
`IMPLEMENTATION_NOTES.md`. Las decisiones y resultados de estrés conservaron
exactamente sus hashes. No se retocaron las políticas. Los tiempos son una
medición del script, con caché, y no se reproducen bit a bit.

`package_study.py` crea un ZIP autocontenido con manifiesto, extrae en limpio
y comprueba reproducción determinista con importación/ejecución de solvers
bloqueadas, las cinco pruebas y el PDF de tres páginas. La búsqueda bibliográfica
es documentada y limitada; no hay reivindicación de prioridad ni rendimiento.
