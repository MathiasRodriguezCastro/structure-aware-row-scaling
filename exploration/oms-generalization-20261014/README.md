# Exploración independiente de contratos de precisión

El [documento PDF de tres páginas](exploration-note.pdf) resume la decisión.
[RESULTADOS.md](RESULTADOS.md) conserva el análisis completo, con datos adversos,
referencias y comandos de reproducción. [EXPLORACION.md](EXPLORACION.md) registra
las líneas iniciales y [PILOT_PROTOCOL.md](PILOT_PROTOCOL.md) el diseño ejecutado.

Se completó un piloto separado de la entrega OMS v1.3.5: cinco modelos de fuentes
independientes, 55 brazos en Gurobi/HiGHS, 52 puntos y siete tests del prototipo.
No se encontró una mejora de aceptación primal de Budget-L2 respecto de su
control directo. La auditoría independiente revisa 12.148 factores y 96
incompatibilidades. No se incorporan resultados al artículo en esta etapa.

El prototipo devuelve únicamente asignaciones enteras comprobadas y conserva
la optimalidad como no verificada. Su demostración sobre intentos almacenados
no es una medición prospectiva de una política adaptativa.

## Reproducir sin solvers

Desde la raíz del repositorio o de la extracción del artefacto:

```bash
python3 exploration/oms-generalization-20261014/generalization_study.py verify
python3 exploration/oms-generalization-20261014/independent_check.py
python3 exploration/oms-generalization-20261014/certifying_workflow.py
python3 -m pytest -q exploration/oms-generalization-20261014/test_certifying_workflow.py
```

Entorno usado: CPython 3.10.12, NumPy 2.2.6, pytest 9.0.3. Para crear modelos y
resolver llamadas nuevas: Pyomo 6.10.1 (instalado en `.deps` aislado), Gurobi
13.0.2 con licencia, HiGHS 1.15.1. Generar el PDF requiere pdfLaTeX. Los solvers
y Pyomo no se importan para los cuatro comandos de verificación anteriores.

`pilot/design.json` y `pilot/source-snapshot.py` identifican el código de las
llamadas existentes. No alterar el runner y reanudar ese diseño; un seguimiento
requiere otro directorio y un protocolo nuevo.

Fuentes de terceros: STN-Scheduler conserva su licencia MIT en
`sources/STN-Scheduler/LICENSE`. Los MPS y metadatos originales de MIPLIB se
conservan con sus URLs, autores/grupos y hashes; no se les asigna una nueva
licencia por incluirlos en este estudio local. Las dependencias aisladas y los
caches no se incluyen en el artefacto. No se realizó publicación ni envío.
