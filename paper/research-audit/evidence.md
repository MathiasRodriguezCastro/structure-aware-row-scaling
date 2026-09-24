# Auditoría de evidencia y reproducibilidad

Fecha: 2026-09-09. Alcance: repositorio local, resultados de revisión, código de
medición y lectura de estado/copia de logs del cluster. No se enviaron trabajos
SLURM. Se aplicaron las instrucciones de `mip-preprocesamiento-experimental` y
`tesis-optimizacion-cpp`; no se encontraron archivos `AGENTS.md` aplicables en
la carpeta ni sus ancestros inspeccionados.

## Resultado central

La evidencia disponible permite un paper de atribución, falsación y fiabilidad
de transformaciones de filas. No sostiene que los metadatos de bloques sean la
causa de una mejora computacional o espectral frente a controles que usan el
mismo kernel y la misma cobertura. La revisión positiva anterior del manuscrito
no incorporaba los controles que refutaban su interpretación central.

1. `results-revision/attribution-controls/FINDINGS_optionB_closed.md` documenta
   que SA-Mat y Local-GM-Coupling-L2 producen matrices byte-idénticas en 30/30
   semillas de la celda estudiada. La ventaja frente a Flat-Mat es una diferencia
   entre normas de normalización de las filas de acoplamiento. No identifica
   utilidad de la asignación bloque-escala.
2. La variante que usa escalas antes de la normalización local pierde frente al
   control ciego en 30/30 semillas. La asignación verdadera nunca es la mejor
   entre 24 permutaciones; su rango mediano es 18. Esta falsación debe conservarse.
3. La campaña operacional final no establece una variante consistentemente
   superior a Base. El resumen histórico de Work contiene errores materiales
   de instrumentación, unidades y selección. Se reconstruyó toda la evidencia
   operacional desde los 240 logs; las cifras corregidas están en
   `results-revision/research-audit/operational/`.

## Evidencia operacional utilizable

La tabla `operational/main_table_four_cells.tex` tiene cuatro celdas y conserva
las 15 instancias asignadas a cada método. Reporta PAR10 como media aritmética
de segundos, con costo 18,000 para cada no terminación a un límite de 1,800.
Los valores [Base, Flat-GM, Flat-L2, Role-Hybrid] son:

| Clase y gap | PAR10 segundos |
|---|---|
| Simple 1% | [11.90, 2.12, 20.44, 2.11] |
| Simple 0.1% | [52.00, 72.98, 33.17, 72.63] |
| SG-Ter-Mer 1% | [116.15, 1216.51, 1217.60, 1217.34] |
| SG-Ter-Mer 0.1% | [134.08, 1216.24, 1216.05, 1216.91] |

Base completa 15/15 en las cuatro celdas. Todos los métodos escalados completan
14/15 en las dos celdas SG-Ter-Mer: el único caso responsable es `instance077`.
Simple completa 15/15 para todos. Las seis no terminaciones no son seis
instancias independientes. Los intervalos bootstrap de `paired_contrasts.csv`
son exploratorios y dejan ver la influencia de ese caso.

Work se recuperó de los resúmenes nativos de Gurobi, con resolución 0.01 para
todos los métodos. Se calcula únicamente en el mismo subconjunto de instancias
completadas por los cuatro métodos: 15 Simple y 14 SG-Ter-Mer. Flat-GM muestra
una reducción condicional en SG-Ter-Mer (razones geométricas 0.698 y 0.682), que
coexiste con el mal resultado operacional de PAR10. No debe ocultarse ninguno
de los dos endpoints.

## Errores y riesgos encontrados

- **Precisión dependiente del tratamiento.** El reporte del preprocesador deja
  `cout` en `fixed`, precisión cero; `[NUM-EFIC]` y `[NUM-KAPPA]` heredan ese
  estado. Los 180 Work escalados se registraron como enteros, frente a Base con
  decimales; 28 valores escalados se redondearon a cero y 178 difieren de la
  salida nativa por más de 0.005. Esto afecta comparaciones contra Base y
  supuestos de igualdad entre variantes.
- **Unidades de penalización.** `analizar_final_variants.py::par10` asigna
  `10*timeout` también cuando la métrica es Work. No existe justificación
  dimensional para esa sustitución; el nuevo análisis no la hace.
- **Selección oculta de ceros.** El promedio geométrico anterior descarta
  numeradores cero, pero conserva esos pares en el conteo y en otras métricas.
  Su denominador efectivo difiere del anunciado.
- **Regla de decisión incompleta.** El script histórico anuncia ausencia de
  nuevos timeouts y validez residual como requisitos de una victoria, pero el
  código sólo consulta el intervalo bootstrap. Sus conclusiones favorables no
  pueden leerse como chequeos completos de fiabilidad.
- **PAR10 versus razones.** Una media geométrica de razones entre costos PAR10
  no es la razón de sus medias PAR10. La campaña anterior usa lenguaje que los
  aproxima. El nuevo archivo define cada endpoint por su fórmula operacional.
- **Estado del wrapper.** `status=OK` incluye `status_solver=TIME_LIMIT`.
  `seed_noise_floor.py` filtra sólo por el primero y describe tiempos como
  truncados sin implementar una truncación explícita. Sus afirmaciones de
  replicación requieren reconstrucción con estado de solver y población común.
- **Interpretación de residuos.** El famoso valor 4.97 de Flat-L2 es un residuo
  absoluto de una igualdad con RHS cero; no es un error físico del 497%. En la
  misma solución, el residuo máximo normalizado por actividad es 1.15e-7.
  Reportar ambos; fijar tolerancias físicas antes de clasificar aceptabilidad.
- **Dependencia y selección.** Las instancias operacionales tienen familias y
  las dos tolerancias comparten instancias. Las muestras finales son pequeñas,
  determinísticas y elegidas tras campañas previas. No son un holdout aleatorio
  ni un estudio confirmatorio. Si se combinan celdas, bootstrap por instancia o
  familia, nunca tratar tolerancias/semillas como problemas independientes.
- **Diagnósticos condicionales.** La kappa del LP fijado al incumbente de cada
  variante depende de su trayectoria. El control de base fija es más adecuado
  para comparar representación, pero no demuestra un efecto sobre todo el
  árbol de branch-and-bound.

Los comentarios históricos afirmaban que Work es independiente de hardware y
cantidad de hilos. Gurobi garantiza determinismo para igual modelo, hardware,
parámetros y atributos; no esa invariancia. Se corrigió el comentario junto a
la emisión de marcadores. Fuente primaria:
[Gurobi, atributo Work](https://docs.gurobi.com/projects/optimizer/en/current/reference/attributes/model.html#attrwork).

## Cambios y validación realizados

- Script nuevo `scripts/audit_operational_evidence.py`, lectura y salidas nuevas.
- 240 logs copiados mediante acceso read-only al cluster, sin editar originales;
  hashes de fuentes en `operational/input_manifest.json`.
- CSV por corrida, tabla de cuatro celdas, contrastes, análisis de igualdad de
  métricas y figura PDF/PNG regenerables. `analysis_metadata.json` especifica
  semillas bootstrap, denominadores, unidades y límites.
- `ProblemaGurobi.cpp`: `[NUM-KAPPA]` y `[NUM-EFIC]` usan streams nuevos y
  `max_digits10`. Compiló la unidad modificada; el enlace local requiere la
  configuración existente Gurobi+CPLEX. Smoke local de dos variantes en
  `caso01a` finalizado óptimo, Work decimal preservado y consistente con la
  salida nativa. `operational/precision-smoke/validation.json` contiene checks.

No se cambió lógica matemática ni configuración del solver; el smoke no integra
la campaña operacional. Los datos históricos de kappa y Work siguen requiriendo
esta precaución cuando se reutilizan fuera de las 240 corridas reconstruidas.

## Cluster: acceso y estado comprobados

Funciona `ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes
mathiasr@login.cluster.uy`; el host respondió `login.datos.cluster.uy`. `squeue`
del usuario estaba vacío durante la inspección. La partición `ute` estaba
habilitada, con límite cinco días y nodos disponibles. Esto es una instantánea,
no una reserva.

El deploy está en `$HOME/generator-aware-row-scaling`, sin `.git`; no se puede
dar por idéntico al commit local. El git del login es antiguo y no soporta
`git -C`. Se verificaron el contenedor `$HOME/containers/gcc13.sif` y las
bibliotecas de Gurobi 13.0.1 en `$HOME/solvers/gurobi1301/linux64`. Los scripts
fijan 16 hilos y el contenedor. Los secretos de licencia no se leyeron.

Comandos seguros de estado:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes mathiasr@login.cluster.uy 'squeue -u mathiasr -o "%.18i %.12P %.20j %.8T %.10M %.6D %R"'
ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes mathiasr@login.cluster.uy 'sinfo -p ute -o "%P %a %l %D %t"'
```

Antes de un experimento nuevo: deploy en ruta distinta con manifiesto/hash de
código, instancia, contenedor y parámetros; preservar resultados históricos;
compilar en nodo asignado y registrar versiones. No usar el script existente
`build_cluster.slurm` sobre un deploy compartido con otro trabajo porque elimina
su carpeta `build`. Su array final no limita concurrencia; campañas históricas
registran fallos de sesiones WLS, de modo que conviene inicialmente `%1` hasta
comprobar el límite de sesiones disponible.

## Protocolo prioritario de bajo costo

1. **Atribución algebraica y matricial, sin solver.** En 30 semillas nuevas y
   tamaños moderados, probar equivalencia de SA-Mat y el control híbrido con la
   misma cobertura/kernel, luego permutar bloques conservando el multiconjunto
   de escalas. Archivar factores por fila y diferencias de matrices, no sólo
   kappa. Repetir con factores multiplicativos representables como potencias
   de dos para separar redondeo de identidad algebraica. Una identidad exacta
   no necesita pruebas estadísticas de mejora.
2. **Límites de tolerancia, sin solver al comienzo.** Construir un ejemplo
   analítico de una fila y uno de dos bloques donde una tolerancia absoluta
   escalada se amplifica en unidades originales por 1/d_r. Variar d_r y validar
   con aritmética de alta precisión. Esto identifica un mecanismo numérico
   general y comprobable que los datos operacionales ya ilustran.
3. **Verificación corta de solver.** Congelar antes de correr: Gurobi 13.0.1,
   un hilo, gap 0.1%, semillas 101/102/103, Base/Flat-GM/Flat-L2/Role-Hybrid,
   cuatro instancias inéditas por clase, límite 60 s. Total máximo 96 solves,
   1.6 CPU-h con un hilo. Orden de tratamientos aleatorizado dentro de cada
   instancia y semilla; misma máquina y parámetros. Guardar Work a precisión
   completa, valores de solución, factores, residuo original por fila,
   objetivo/cota, estado y tiempo de preprocessing separado.
4. **Éxito definido antes de los datos.** Endpoint primario: número de
   soluciones que alcanzan gap y pasan tolerancias originales definidas por
   fila; secundario: PAR10 de todo el pool. Work sin imputación de segundos y
   sólo descriptivo cuando hay censura temporal. No seguir ampliando muestras
   hasta que aparezca p<0.05. Para una afirmación computacional nueva se necesita
   replicación en holdout, tamaño de efecto y comparación con controles ciegos.
5. **No bloquear el paper por ausencia de aceleración.** Si la teoría de colapso
   y los controles matriciales cierran, presentar un resultado de atribución y
   criterios de evaluación reproducibles. Reservar una nueva heurística
   positiva para un estudio posterior si supera el piloto preespecificado.

El protocolo puede refinarse cuando esté definida la contribución matemática;
los resultados disponibles ya justifican abandonar la narrativa de superioridad
de metadatos. No permiten prometer aceptación editorial.
