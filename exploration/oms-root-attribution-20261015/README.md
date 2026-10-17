# Atribución del escalamiento mediante incumbente común

Leer `RESULTADOS.md` y `root-attribution-note.pdf`. Este ensayo responde a una
pregunta central de OMS: dependencia de los efectos operativos respecto del
acceso temprano al incumbente, con mecanismos internos normales. No estudia
DW, cortes nuevos ni predicción. Son tres casos conocidos de una familia.

36 MILP nuevos, tres LP de referencia exactos y 15 LP posteriores de patrones.
Los 18 Start comunes se cargaron. Se conservan dos respuestas LP desconocidas;
no se sustituyen patrones. No se afirma optimalidad MILP ni un método gratuito
de adquisición de incumbentes. Se deja un párrafo concreto de posible
incorporación, sin modificar la entrega OMS v1.3.5.

Reproducción sin optimizadores, desde este directorio:

```bash
python3 analyze.py
python3 independent_check.py
python3 write_report.py
python3 -m pytest -q test_metrics.py
pdflatex -halt-on-error -interaction=nonstopmode root-attribution-note.tex
```

Python 3.10+, NumPy, pytest y pdfLaTeX. Entradas canónicas, factores, referencias,
puntos, LPs y certificados están incluidos. El estudio padre verificó las
entradas contra los MPS originales. Aquí se fijan sus hashes y se comprueban
los productos exactos; no se vuelve a ejecutar el generador C++.

Para nuevas llamadas en una copia limpia de los resultados, se necesita Gurobi
13.0.2 con licencia y SoPlex 8.1.0/GMP. La ruta del binario se declara en
`design.json`; el binario no se distribuye. Tras preservar entradas, diseño,
protocolo y fuentes, sin resultados derivados: `python3 study.py prepare`,
`python3 study.py run`, `python3 study.py certify`. Los diseños se fijan por
etapas antes de cada conjunto de llamadas y todas las llamadas son secuenciales.
No ejecutar prepare sobre la entrega cerrada.

`package_study.py` comprueba una extracción limpia con optimizadores bloqueados,
los cuatro tests, el PDF y los hashes de los once paquetes anteriores y OMS.
Código propio bajo LICENSE del repositorio; los datos mantienen procedencia
y condiciones de la tesis. El archivo de filtros temáticos del nivel superior
documenta por qué este diagnóstico pertenece a la pregunta del artículo.
