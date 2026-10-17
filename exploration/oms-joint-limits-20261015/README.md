# Límites conjuntos: nota preliminar

Leer RESULTADOS.md y joint-limits-note.pdf. Álgebra exacta, un certificado Farkas
y auditoría de acumulación de agua, sin llamadas nuevas a optimizadores.
No se incorpora al manuscrito; la novedad y utilidad de la extensión están
pendientes. La invariancia de Skeel/equilibración libre son resultados clásicos.

Requiere Python 3.10+ y NumPy; pytest para cuatro tests; pdflatex para el PDF.

```bash
python3 joint_limits.py --math-only
python3 -m pytest -q test_properties.py
```

Para auditar los 1093 candidatos hace falta el paquete padre completo, sin
extraerlo: `oms-precision-work-20261015/precision-work-artifact.zip`. Su SHA256
está fijado en design.json y storage-audit.json; no se incluye otra copia.

```bash
python3 joint_limits.py --parent /ruta/a/precision-work-artifact.zip
python3 write_note.py
pdflatex -halt-on-error -interaction=nonstopmode joint-limits-note.tex
```

El código verifica hashes del manifiesto padre al leer cada modelo/punto,
extrae los balances originales de 360 períodos y comprueba exactamente todas
sus entradas de volumen, la inversa analítica y el telescopado de cada candidato.
Los prefijos 8/24 son bloques condicionales, no modelos enteros de despacho.
No constituyen el diagnóstico LP–DW, que sigue pendiente.

El ZIP de esta nota es pequeño pero tiene una dependencia de datos explícita:
el ZIP padre. La validación en extracción limpia ejecuta las fórmulas y toda la
auditoría con ese padre externo fijado por SHA256 y bloquea solvers/procesos.
No se afirma un paquete completamente autosuficiente de datos.

Código propio bajo licencia del repositorio. Los datos siguen las condiciones
de su fuente y de la tesis; las referencias bibliográficas se enlazan, no se
redistribuyen textos completos de terceros.
