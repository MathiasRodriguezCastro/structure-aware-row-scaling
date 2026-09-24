# Campaña de robustez solver-level — documento de diseño (para aprobación)

16-sep-2026. Estado: **diseño; no se lanzó ningún job de solver**. Datos de inventario y scripts en
`results-revision/solver-robustness/` y `scripts/research/robustness_{inventory,history,design}.py`.

## 1. Inventario de instancias

| Pool | Ubicación (ClusterUY) | n | Filas | Columnas (binarias / continuas) | nnz | Rango \|a\| |
|---|---|---:|---:|---|---:|---|
| Simple | `Grupos/UTE_FING/mathiasr/soluciones_seccion45/simple/instancias` | 500 | 14.400 | 10.800 (2.160 / 8.640) | 35.590 | 1,3e-3 – 1,8e9 |
| SG-Ter-Mer | `…/sgtm/instancias` (**corregido**) | 500 | 10.080 | 6.120 (1.440 / 4.680) | 22.679 | 2,8e-4 – 1,4e10 |
| Full | `…/completo/instancias` | 500 | 23.763 | 16.561 (3.600 / 12.961) | 57.555 | 1,7e-4 – 1,4e10 |
| Simple 10k | `…/simple/banco_10000/instancias` | 10.000 | — | — | — | — |

- Generación: banco recombinado `v1` (seed 20260717), recombina bloques de hidrología, demanda y
  costos de las instancias históricas. Metadata por instancia (fuentes de cada componente, huella
  semántica, validación estructural) en `inventory/instance-manifest.csv`.
- Coherencia (verificada): 500 archivos distintos, 500 modelos distintos y 500 huellas semánticas por
  familia; 1.500/1.500 exportan con el binario del paper; dimensiones idénticas dentro de cada
  familia; **0 coinciden con las 204/68/34 históricas; 0 están en el pool de 10k**.
- Simple y Full son byte a byte los de la release sellada `banco-v1-20260719-r2`.
- **SG-Ter-Mer: hay dos versiones.** La release sellada tiene la serie `demandaTotal` defectuosa
  (291/500 instancias con demanda residual > total en alguna hora); el pool de
  `soluciones_seccion45` es la versión corregida (0/500), con el dato autoritativo de demanda. **Se
  usa la corregida.**
- **Hallazgo que afecta al paper actual:** 39/68 SG-Ter-Mer históricas tienen el mismo defecto,
  incluidas **instance077** (22 horas) y 9 de las 15 de la campaña operacional histórica. Siguen
  siendo MILP válidos para comparar representaciones, pero no son escenarios de mercado fieles. Hay
  que declararlo en el SI. La versión corregida de instance077 existe (tesis, commit 340c69bd).
- Uso previo del pool: sólo campañas de la tesis (MIP base y pipeline). Ningún resultado del paper
  lo usa. El pool de 10k (desplazamientos cíclicos, MIP más duros) queda fuera, reservado.
- Controles: el binario del paper exporta exactamente las mismas dimensiones (filas, columnas, nnz)
  que registraron las corridas históricas.

## 2. Información histórica de tiempos

**Fuente principal (Base, previa a esta revisión):** logs nativos de la tesis sobre este mismo pool,
Gurobi 13.0.1, **1 thread**, seed 1, MIPGap 1e-3, 3600 s, nodos Intel de 40 cores. El tiempo al 1%
se reconstruye de la trayectoria del gap en el log (resolución de la línea de log, ~5 s; es una cota
superior).

| Familia | Completa al 1% (≤1800 / ≤3600 s) | Completa al 0,1% (≤1800 / ≤3600 s) | CPU media con cap (1% / 0,1%) |
|---|---|---|---|
| Simple | 100% / 100% | 100% / 100% | 4,5 s / 39,2 s (cap 1800) |
| SG-Ter-Mer (corregido) | 98,2% / 98,6% | 96,6% / 97,2% | 70 s / 100 s (cap 1800) |
| Full | 82,8% / 86,4% | 67,6% / 75,8% | 729 s / 1290 s (cap 3600) |

- En Full, las 121 censuradas a 3600 s terminan con un gap mediano de 1,50%; sólo 14 están a ≤0,2% y
  38 a ≤0,5%. **Subir a 7200 s agregaría pocas completaciones al 0,1% con el doble de costo en el
  peor caso.**
- Otros históricos, para contexto:
  - GARS 204/68/34 con Gurobi y CPLEX, 16 threads;
  - la campaña final 15+15 (16 threads, 1800 s);
  - la réplica con 5 seeds (16 threads): IQR relativo del tiempo dentro de cada instancia de 12–18%,
    rango de 29–45%. **El ruido por seed es grande**, lo que justifica el diseño multi-seed.
- **No hay historia de CPLEX ni de HiGHS a 1 thread sobre este pool.**

## 3. Calibración

- **Caps:** se fijan con los logs históricos de Gurobi (Base únicamente; no hay datos de políticas
  involucrados).
- **Piloto de calibración (Base, CPLEX y HiGHS):**
  - **Conjunto:** 10 Simple, 10 SG-Ter-Mer y 30 Full, elegidos por orden de
    `sha256("solver-robustness-v1" | familia | hash del archivo)` (`design/instance-split.csv`).
    Quedan **fuera** de la evaluación.
  - **Configuración:** 1 thread, gap 0,1%, cap 7200 s; el tiempo al 1% sale de la trayectoria.
  - **Qué decide:**
    - (a) si CPLEX exige un cap mayor (regla R1);
    - (b) el alcance de HiGHS (regla R2);
    - (c) el costo esperado.
    
    No compara políticas.

**Regla R1 (cap por familia).** Se elige el menor T ∈ {1800, 3600, 7200} tal que, **para Gurobi
(historia) y para CPLEX (piloto)**, Base complete ≥ 80% al 1% y ≥ 70% al 0,1%. Si ningún valor
cumple, T = 7200.
- **Por qué 80/70:**
  - con ≥80% de completación al 1%, el PAR10 mide algo más que el conteo de timeouts;
  - exigir 80% también al 0,1% llevaría Full a 7200 s por una ganancia marginal (ver §2);
  - 70% conserva unos dos tercios de los pares completados para las comparaciones condicionales.
- **Advertencia honesta:** propongo estos umbrales *después* de ver las distribuciones históricas de
  Base (nunca de políticas).

**Regla R2 (HiGHS).** HiGHS no entra en R1; su censura es un resultado. Si su Base completa < 50% al
1% con T_F en el piloto de la familia F, HiGHS en F se corre sólo sobre el subconjunto multi-seed
(50 instancias, seed primaria) y se reporta como brazo descriptivo.

## 4. Caps propuestos

| Simple | SG-Ter-Mer | Full |
|---|---|---|
| **1800 s** | **1800 s** | **3600 s** (Gurobi: 86,4% al 1% / 75,3% al 0,1% en el conjunto de evaluación) |

- Full podría pasar a 7200 s sólo por R1 aplicada a CPLEX.
- PAR10 = 10 × cap de la familia.
- Nunca se promedia entre familias.

## 5. Threads

- **Propuesta:** **1 thread** para todos los solvers y todas las políticas. Hay historia a 1 thread,
  es determinista y permite comparar entre solvers.
- **Hardware:** fijado a los nodos **Intel** de `ute` (los de la historia), con 2 cores reservados por
  job (sin hiperthreading) para reducir la contención.
- **Declaración:** los tiempos se miden en nodos compartidos; Work y ticks son menos sensibles a eso.
- **16 threads no resuelve el cuello de botella** (§11): el límite es de sesiones de licencia, no de
  cores.

## 6. Solvers

| | Gurobi | CPLEX | HiGHS |
|---|---|---|---|
| Versión (cluster) | 13.0.1 | 22.1.2 (libs estáticas) | 1.15.1 (a compilar) |
| Licencia | WLS académica 2849920, **~2 sesiones sostenidas** | académica, sin límite de sesiones | libre |
| API en el pipeline | C++ (existe) | C++ (existe) | **no existe**: propongo backend C++ `ProblemaHighs` (~300 líneas, como el de Cbc), para tener el mismo pipeline en memoria, la misma verificación original y el mismo logging |
| Gap relativo | MIPGap: \|zP−zD\|/\|zP\| | EpGap: \|zD−zP\|/(1e-10+\|zP\|) | mip_rel_gap (definición propia, parecida) |
| Tolerancias (explícitas) | FeasibilityTol 1e-6, IntFeasTol 1e-5 | EpRHS 1e-6, EpInt 1e-5 | primal_feasibility 1e-6, mip_feasibility 1e-6 (una sola tolerancia MIP) |
| Seed | Seed | RandomSeed | random_seed |
| Presolve / escalado interno | por defecto | por defecto | por defecto |
| Esfuerzo determinista | Work | ticks deterministas | no tiene (se usan nodos e iteraciones de LP) |

- Los valores por defecto se dejan intactos porque el estudio es escalado externo *encima* del
  pipeline estándar.
- Hay que agregar flags explícitos de tolerancia y **apagar la instrumentación que agrega tiempo**:
  el muestreo KappaStats de CPLEX y el LP fijo de Gurobi para κ.

## 7. Conteos

- **Evaluación:** 490 Simple, 490 SG-Ter-Mer y 470 Full = **1.450 instancias**.
- **Primaria:** 1.450 × 4 políticas × 3 solvers × 2 gaps × 1 seed = **34.800 corridas**.
- **Multi-seed:** 50 + 50 + 50 (primeras de la evaluación por orden de hash) × 4 × 3 × 2 × 4 seeds
  extra = **14.400 corridas**.
- **Piloto:** 50 × 2 solvers × 1 corrida = 100 corridas (cap 7200 s).
- **Auditoría de instance077:**
  - dos versiones (la histórica defectuosa y la corregida) × 3 × 4 × 2 × 5 seeds = 240 corridas con
    el cap de la familia, más una extensión a 2× cap para las censuradas, que no altera nada primario;
  - además, 8 corridas de Gurobi en la condición histórica exacta (16 threads, seed 42, 1800 s).
- **Stress con CPLEX (local):** 1.584 llamadas más 576 de los controles GCD, sobre los mismos 96
  modelos y factores.

## 8. Seeds

- **Primaria:** 1. Es la de la historia de calibración y la default del pipeline. La campaña 15+15
  usó 42; se declara.
- **Multi-seed:** {2, 3, 4, 5}; la primaria cuenta como la quinta.
- **Orden de políticas por instancia:** permutación aleatoria con semilla derivada del hash de la
  instancia (queda registrada).

## 9. Costo (proxy: Base de Gurobi a 1 thread; overhead de 10 / 10 / 30 s por corrida)

| Por solver | Esperado | Peor caso |
|---|---:|---:|
| Primaria | **1.246 CPU-h** (Simple 35, SG-Ter-Mer 105, Full 1.106) | 7.733 CPU-h |
| Multi-seed | **499 CPU-h** (Full 439) | 3.222 CPU-h |
| Piloto (CPLEX + HiGHS) | — | 200 CPU-h |
| instance077 | — | 124 CPU-h |

- **CPLEX y HiGHS:**
  - costo desconocido hasta el piloto; supuesto de trabajo: CPLEX ≈ 1,5× Gurobi, HiGHS cercano al
    peor caso en Full;
  - sin límite de licencia, así que con ~100 cores concurrentes son **1–3 días de pared** cada uno.
- **Gurobi (el cuello de botella):**
  - **con 2 sesiones:** 1.745 CPU-h / 2 ≈ **36 días de pared**;
  - **con 16 sesiones:** ≈ **4,5 días**.
- **Almacenamiento:**
  - ~3 GB (fila de resumen + log comprimido + JSON de procedencia);
  - los CSV de despacho se descartan después de la verificación interna.
- **Carga en el scheduler:** arrays con una tarea por (solver, familia, gap, seed, shard de 10
  instancias), unas 5.000 tareas en total. Gurobi va con throttle igual al número de sesiones.

## 10. Endpoints

**Primarios (dentro de familia × solver × gap):**
- PAR10 sobre el pool completo asignado;
- tasa de completación y de timeout;
- gap final entre las censuradas.

**Secundarios:**
- **Condicionales:** cociente de tiempo pareado (media geométrica y mediana) sobre las instancias que
  completan las 4 políticas.
- **Esfuerzo por solver:** Work (Gurobi), ticks (CPLEX), nodos e iteraciones (los tres); nunca se
  comparan entre solvers.
- **Diagnóstico numérico:**
  - estado, objetivo, cota, advertencias;
  - residuos en los datos originales (absoluto, normalizado por RHS y por actividad);
  - etiqueta de verificación pre-especificada: residuo absoluto ≤ 1e-4 y normalizado por actividad
    ≤ 1e-6.
- **Multi-seed:**
  - dispersión dentro de cada instancia;
  - estabilidad del signo por seed;
  - frecuencia de timeouts raros;
  - bootstrap por instancia.

**Contrastes confirmatorios:**
- (C1) cociente de esfuerzo en corridas completadas Flat-GM/Base;
- (C2) diferencia de PAR10 Flat-GM − Base;
- (C3) diferencia de completación;
- (C4) estabilidad del signo de C1 y C2 a través de las seeds;
- (C5) en el stress con CPLEX, la discordancia pareada de la regla con budget frente a la misma regla
  sin budget.

**Exploratorios:** Flat-L2 y Role-Hybrid frente a Base y entre sí, perfiles de performance, gap al
timeout y la auditoría de instance077.

## 11. Decisiones que necesito de vos

1. **Capacidad de Gurobi (bloqueante).** Opciones:
   - (A) conseguir ≥16 sesiones sostenidas: más WLS académicas del grupo o una licencia académica
     named-user validada en un nodo fijo de `ute`. Recomendada.
   - (B) con 2 sesiones: reducir Full por hash (p. ej. 150 en evaluación, 30 en multi-seed). Aun así
     serían ~15 días.
   - (C) aceptar ~5 semanas.
2. **Umbrales R1 (80/70) y R2 (50%)**, y los caps propuestos.
3. **1 thread**, nodos Intel, 2 cores reservados por job.
4. **Backend C++ de HiGHS** (recomendado) frente a exportar LP y resolver con highspy.
5. **Tamaños:** calibración 10/10/30; multi-seed 50/50/50 con seeds 2–5.
6. **Congelar el código:** autorizar un commit y un tag (sin trailer de IA) antes de producción; el
   hash va en cada corrida.
7. **Declaración en el paper** del defecto de demanda de las 68 SG-Ter-Mer históricas.

## 12. Esquema de logging por corrida

- **Procedencia:** commit git, id de campaña, versión del manifest, familia, id y hash de la
  instancia.
- **Configuración del solver:** política, solver y versión, seed, gap, tolerancias primal y de
  integralidad, presolve, escalado interno, threads, cap.
- **Ejecución:** nodo, modelo de CPU, inicio y fin, id de job y tarea de array, orden de la política.
- **Resultado:** razón de terminación, objetivo, incumbente, cota, gap final, tiempo de pared, tiempo
  de solver, tiempo de preprocesamiento, esfuerzo determinista, nodos, iteraciones de LP, advertencias
  numéricas.
- **Verificación:** resumen de residuos originales; código de salida y clasificación de ausencia
  (infraestructura / licencia / error del solver).

## 13. Manifest congelado

Se genera **después** de aprobar y congelar el código:
- `design/instance-split.csv` (ya generado, determinista);
- `inventory/instance-manifest.csv`;
- `campaign-manifest.json` con los hashes del split, el manifest, los scripts, el binario, las
  versiones de solvers, los parámetros y las reglas R1/R2.

**Reglas de re-ejecución:** sólo por fallos de infraestructura documentados. Los timeouts y los
errores del solver son resultados.

## 14. Trabajo previo a producción (sin comparar políticas)

- (E1) Backend HiGHS: validado contra Gurobi en instancias históricas con Base.
- (E2) Flags de tolerancia y de instrumentación apagada.
- (E3) Runner con procedencia, sharding e idempotencia.
- (E4) Auditor que reconstruye desde los logs y clasifica ausencias.
- (E5) Build del cluster y smoke tests; sonda de licencia desde un nodo de cómputo.
- (E6) Brazo CPLEX del stress (local).

Estimación: ~3 días de ingeniería antes del piloto.

## 15. Cambios anticipados en el paper

- **§6:** la campaña nueva pasa a ser la evidencia operacional principal; la de 15+15 queda como
  campaña histórica, con la advertencia del defecto de demanda.
- **§7.3:** se reescribe con los resultados primarios, los multi-seed y instance077.
- **§7.4 y Tabla 4:** se agregan columnas de CPLEX.
- **§8.2:** se quitan las advertencias que dejen de ser ciertas.
- **Abstract, introducción, conclusión:** sólo las frases de nivel solver.
- **SI:** protocolo, calibración, auditoría de jobs y tablas completas.
