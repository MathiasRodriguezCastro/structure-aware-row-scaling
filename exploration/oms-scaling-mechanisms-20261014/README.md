# Escalamiento interno y valor de la información del generador

Leer `RESULTADOS.md` y `scaling-mechanisms-note.pdf`. Estudio independiente;
ningún resultado se incorporó al manuscrito OMS v1.3.5. El pedido LP–DW está
pendiente por la prioridad posterior del usuario.

`PROTOCOL.md`, `design.json` y los snapshots fijan diseño y código antes de las
resoluciones. `discovery-conclusions.json` fija lo concluido antes de la reserva.
`IMPLEMENTATION_NOTES.md` registra correcciones previas y el único LP racional
posterior. Las semillas no se cuentan como instancias independientes.

Replay sin Gurobi, SoPlex, licencia o generador (Python 3.10+):

```bash
python3 independent_check.py
python3 analyze.py
python3 write_report.py
python3 -m pytest -q test_math.py
pdflatex -halt-on-error -interaction=nonstopmode scaling-mechanisms-note.tex
```

El primer comando importa independientemente los seis MPS y evalúa cada punto
en aritmética racional. Un residuo no nulo no se presenta como factibilidad
exacta. El eventual testigo de `exact-witness/` se comprueba exactamente sobre
todas las restricciones, cotas e integralidad. Los tests son invariantes del
selector, unidades y distinción entre residuo observado y garantía condicional.

Para nuevas resoluciones: Gurobi 13.0.2 con licencia. Copiar este directorio a
otro que conserve `study.py`, snapshots, protocolo, `design.json`, `inputs/` y
`discovery-conclusions.json`, sin `runs/` ni archivos derivados. Ejecutar
`python3 study.py discovery`, luego `python3 study.py holdout` y
`python3 study.py summarize`. El código construye desde los datos canónicos
archivados; no necesita el ejecutable C++. No ejecutarlos en paralelo. El tiempo
es sensible a la máquina; el trabajo también depende de versión, parámetros,
semilla y formulación. La licencia y los binarios no se incluyen.

`study.py prepare` solo es para regenerar entradas desde la instalación de tesis
declarada en el script; se niega a preparar si ya existe `runs/`. Utiliza el
ejecutable existente sin compilar ni modificar fuentes. Los comandos archivados
incluyen rutas originales; la reproducción portátil usa los datos canónicos.

El testigo posterior se puede intentar con `python3 exact_witness.py` en un
directorio limpio `exact-witness/` y el binario SoPlex 8.1.0 con GMP en la ruta
declarada; no forma parte del replay ni del tiempo MILP. Su punto racional
archivado permite verificar sin solver y sin repetir la búsqueda.

`package_study.py` crea ZIP y manifiesto, verifica extracción limpia, replay,
tests, PDF y hashes de la entrega OMS y paquetes anteriores. Código propio
bajo la licencia del repositorio; entradas y modelos conservan las condiciones
y procedencia de la tesis, no se relicencian por incluirlos en este paquete.

Al cerrar, el ejecutable original de `build/` ya no estaba disponible. Su hash
de generación queda registrado; no se afirma haber verificado su persistencia.
Esto se detalla en IMPLEMENTATION_NOTES.md y VALIDATION.json. La reproducción
desde los modelos archivados no depende de ese ejecutable.
