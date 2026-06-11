# Benchmark sintético MIP bloque-estructurado

Módulo **independiente** para generar y evaluar MIPs sintéticos bloque-estructurados
sobre las variantes de preprocesamiento/escalado del proyecto (`PreprocesamientoMIP`).
No toca la lógica de despacho hidrotérmico: reutiliza `Problema`, los backends de solver
y `PreprocesamientoMIP` sin modificarlos, y se activa **solo** por el comando
`benchmarkSintetico`. Si el comando no se invoca, el binario se comporta igual que antes.

## Estructura del MIP generado

Para `B` bloques (cada bloque ≈ un generador):

- Continuas de bloque `i`: `a{i}_x{j}` ∈ `[0, 100]`.
- Binarias de bloque `i`: `a{i}_z{k}` ∈ `{0,1}`.
- Restricciones locales `a{i}_local_{r}` (combinaciones sparse de las continuas del bloque).
- Restricciones de activación `a{i}_act_{k}`: `a{i}_x{j} ≤ U·a{i}_z{k}` (gating binario).
- Restricciones globales de acoplamiento `coupling_{t}`:
  `Σ_i c·a{i}_x{·} + short_t − surp_t = D_t`.
- Holguras `short_t`, `surp_t ≥ 0` con costo "big-M" → el modelo es **siempre factible**.

La convención de nombres `a{i}_…` / `coupling_…` es la que `PreprocesamientoMIP` usa para
detectar bloques y filas globales (escalado *generator-aware*). El runner además registra
los bloques y prefijos globales explícitamente.

## Desbalance artificial (parámetros del manuscrito)

- `pattern` ∈ `{none, local, coupling, mixed}` — qué **tipo de filas** reciben desbalance.
- `S` ∈ `{0, 3, 6}` — severidad. Para cada fila seleccionada: `θ_r = 10^{ξ_r}`,
  `ξ_r ~ Uniform[-S, S]`. Se multiplica **toda la fila, incluido el RHS** (equivalencia
  algebraica). `θ_r` se registra como `applied_scale_factor`.
- `coefficient_family` ∈ `{uniform, block_heterogeneous, banded}` (flag `--coef-family`,
  separado de `pattern`) — familia/sparsity de los coeficientes base.

## Variantes de preprocesamiento

| Nombre     | PreprocesamientoMIP::Config                                                   |
|------------|-------------------------------------------------------------------------------|
| `Base`     | sin escalado                                                                  |
| `SA-Aug`   | `escalamientoLocalPorFila + normalizarBloqueTrasFilas`                        |
| `SA-Mat`   | SA-Aug + `modoMatricial`                                                       |
| `Ruiz`     | `usarEquilibradoRuiz + escalamientoLocalPorFila + normalizarBloqueTrasFilas`  |
| `Ruiz+Cols`| Ruiz + `escalarColumnasContinuas + normalizacionFisica`                       |

## Comando

```
benchmarkSintetico [--out <dir>] [--volcar-lp <dir>] [--coef-family <fam>] [--timeout <s>] [--mipgap <v>]
<solver>                 # DummyLp | Gurobi | Cbc | Cplex | Hexaly
<seed>
<numInstancias>
<numBloques>
<varsContinuasPorBloque> <varsBinariasPorBloque>
<restrLocalesPorBloque> <restrAcoplamiento>
<pattern>                # none | local | coupling | mixed
<S>                      # 0 | 3 | 6
<variantes>              # lista separada por comas, ej: Base,SA-Aug,SA-Mat,Ruiz,Ruiz+Cols
<rutaCsvSalida>
```

Los parámetros posicionales se leen de las **líneas siguientes** al comando (como hacen
los agentes hidrotérmicos). Las flags opcionales van en la **misma línea** del comando.
Con `numInstancias > 1`, la instancia `idx` usa `seed = seedBase + idx`.

## Salidas

- **CSV de métricas** (siempre, `<rutaCsvSalida>`): una fila por `(instancia, variante)` con
  `kappa_antes/despues`, `rho_antes/despues`, tiempos, objetivo, etc.
- **`manifest.json`** (con `--out`): parámetros de la instancia + de la corrida + rutas.
- **`row_metadata.csv`** / **`column_metadata.csv`** (con `--out`): metadata explícita de
  filas y columnas (incluye `applied_scale_factor`, `block_id`, tipos…).
- **`.lp`** (con `--volcar-lp`): export del modelo por `(instancia, variante)`.

## Ejecución

```bash
cd Implementacion_Cpp/Codigo_Cpp
make USE_HEXALY=0
cat synthetic/ejemplo_sintetico.txt | ./build/SistemaElectrico
```

> **Nota:** `DummyLp` solo exporta el modelo (no resuelve); usá un solver real
> (`Gurobi`, `Cplex`, `Cbc`) para obtener objetivo y tiempos de resolución.

## Alcance actual (primera etapa)

Generador + comando + smoke test + CSV/manifest/metadata + corrida de variantes
(Monolítica). **Fuera de alcance** por ahora: Dantzig-Wolfe, integración con el
pipeline Python hidrotérmico, grilla completa de instancias y análisis estadístico.
