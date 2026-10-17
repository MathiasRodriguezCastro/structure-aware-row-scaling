# Análisis: BENDERS LÓGICO sobre las binarias `varphi` (propuesta T2)

**Veredicto adelantado: NO-GO.** Benders sobre `varphi` con maestro relajado da
`z_LP` (la misma cota del LP compacto), **no** `z_DW`. Choca con la misma pared
que RLT. Como branch-and-Benders-cut da `z_MIP` pero con un maestro que es a su
vez el MIP duro de las binarias `varphi` (miles) y cortes de dualidad-LP con
big-M ~1e9 (duales débiles), no hay razón estructural para esperar speedup sobre
el monolítico; se predice un negativo análogo a DW y B&P. Documentar sin
implementar las ~500 líneas de callbacks.

---

## Pregunta 1 — ¿Qué COTA da Benders sobre `varphi`? → `z_LP`, NO `z_DW`

### Derivación rigurosa

Escribimos el MIP compacto separando binarias `y` (= `varphi`) y continuas `x`
(producción, volumen, falla):

```
z_MIP = min  f·y + c·x
        s.t. A x        >= b              (acoples de demanda, balance de agua)
             D x - M y  <= d              (enlaces big-M:  M·varphi - v <= M - V)
             E x        <= u·y            (theta <= UB·varphi)
             y ∈ {0,1}^n,  x >= 0
```

**Benders proyecta las continuas `x`.** Para `y` fijo, el subproblema es el LP
en `x`; su valor `Q(y)` es convexo y poliédrico, y Benders lo reconstruye por su
envolvente de cortes de optimalidad/factibilidad (duales del LP):
```
z = min_y  f·y + Q(y),   Q(y) = max_{(π,σ)∈dual} { π·b + σ·(d + M y + ...) }.
```
Cada corte `η ≥ const(π,σ) + coef(π,σ)·y` es **exacto** (LP fuerte): la
envolvente de TODOS los cortes describe `Q(y)` EXACTAMENTE sobre el dominio.

**Punto clave (la reformulación es equivalente al LP original).** El programa de
Benders `min_{y} f·y + Q(y)` con `y ∈ {0,1}` es una **reformulación exacta del
mismo MIP** — proyecta `x`, no cambia el conjunto factible. Por lo tanto su
**relajación** (tomar `y ∈ [0,1]`):
```
z_Benders-LP = min_{y∈[0,1]}  f·y + Q(y)
             = min_{y∈[0,1], x>=0}  f·y + c·x  s.t. (todas las filas)
             = z_LP   (la relajación LP del COMPACTO).
```
La segunda igualdad es porque `Q(y)` ya ES el LP en `x` proyectado; reintroducir
`x` y relajar `y` recupera fila por fila el LP compacto. **Benders no agrega
ninguna información que el LP compacto no tuviera**: solo reorganiza el MISMO
poliedro. No hay nada en los cortes de Benders que "vea" la integralidad de
bloque; los duales salen del LP del subproblema con `y` ya fijo a un valor
(posiblemente fraccionario).

**Por qué `z_DW > z_LP` requiere pricing IP por bloque (= DW, no Benders).**
`z_DW` es la cota de la relajación lagrangiana de los ACOPLES, donde cada
**bloque se resuelve como IP**: `z_DW = LP sobre conv(X_bloque entero) ∩ acoples`.
La fuerza de DW viene de `conv(X_bloque entero) ⊊ X_bloque-LP` — describe el
casco entero de cada bloque. Benders-sobre-`varphi` nunca resuelve un IP de
bloque: fija `y` y resuelve un LP. No puede acceder a `conv(X_bloque entero)`.
Para superar `z_LP` haría falta que el subproblema de Benders devolviera la cota
del casco entero del bloque — eso es exactamente el **pricing de Dantzig-Wolfe**,
no Benders.

### Verificación numérica (gurobipy)

MIP de 2 bloques con estructura análoga (binarias de activación con cobertura
`3y1+3y2 ≥ 4` → el casco entero exige `y1+y2 ≥ 2`, gap que el LP fracciona;
enlace `x ≤ 5·(y1+y2)`; acople de demanda `x0+x1+s ≥ D`):

```
z_LP  = 30.800   (LP compacto, y∈[0,1])
z_DW  = 38.000   (Lagrangiana del acople, bloques resueltos como IP)
z_MIP = 38.000

Benders, maestro y RELAJADO a [0,1]  →  converge a 30.800  (= z_LP, NO z_DW)
Benders, maestro y BINARIO           →  converge a 38.000  (= z_MIP)
```

Instancia con los TRES estrictamente distintos (sweep aleatorio):
```
z_LP=30.448 < z_DW=31.947 < z_MIP=32.160
Benders-LP = 30.448  (= z_LP exacto)   Benders-IP = 32.160  (= z_MIP)
```

**Robustez:** 40 instancias aleatorias, TODAS con `z_DW > z_LP` no trivial. En
las 40: `Benders-LP == z_LP`, `Benders-IP == z_MIP`, orden `z_LP ≤ z_DW ≤ z_MIP`.
Cero excepciones. (Scripts: `verify_benders4.py`, `verify_benders6.py`.)

**Conclusión P1: HIPÓTESIS CONFIRMADA.** Benders-LP da `z_LP`, no `z_DW`. El
objetivo declarado de T2 ("recuperar `z_DW` donde RLT falló") es **FALSO**.
T2 choca con la MISMA pared que RLT: el +24% de `z_DW` vive en el casco entero
POR BLOQUE (enlace de volumen / interacción `x·v`), y ni RLT-1 ni Benders-sobre-
`varphi` lo alcanzan — solo el pricing IP por bloque (DW) lo hace.

### Confirmación en el modelo REAL (no solo el toy)

Medido con el binario (Gurobi), corrobora la conclusión sobre las instancias de la tesis:

| instancia | z_LP (= raíz de Benders) | z_DW | z_MIP | brecha |
|---|---|---|---|---|
| **simple** (caso01a) | −344,520M | ≈ z_LP | −344,469M | **0,015%** (z_LP≈z_MIP) |
| **completo** (instance001) | **98 410** | ≈122 028 (+24%) | [130 274, 230 516] | **43%** (sin cerrar, MIP duro) |

- El `z_LP=98 410` del completo coincide exactamente con el `zLP_compacto` del kill-test de RLT
  (PLAN_RLT.md) — es el mismo poliedro, como predice la derivación.
- **Simple:** la brecha de integralidad es 0,015% (`z_LP≈z_MIP`): las `varphi` casi no importan,
  así que Benders es trivial pero **sin valor** (el LP ya resuelve). Confirma P2(b).
- **Completo:** Benders arrancaría en `z_LP=98 410`, que está **un 24% por debajo de `z_DW`** y
  por debajo incluso de la **cota propia del monolítico** (130 274 tras 360 s) — arranca más débil
  que el branch-and-cut del solver. Confirma P2(a)+(c).

---

## Pregunta 2 — Si NO da `z_DW`, ¿qué SÍ aporta? ¿Gana al monolítico?

Branch-and-Benders-cut corrido a convergencia da `z_MIP` (no `z_DW`). La
pregunta real es si lo hace **más rápido** que el monolítico para ESTA
estructura. Tres obstáculos estructurales, todos negativos:

**(a) El maestro de Benders es un MIP duro.** Mover las miles de binarias
`varphi` al maestro NO las hace fáciles: el maestro es un MIP sobre `varphi` +
`η`, con la combinatoria intacta. Benders solo elimina las CONTINUAS (que ya
eran fáciles: un LP). Se traslada el problema duro, no se resuelve.

**(b) `varphi` está casi predeterminada → Benders ≈ cabeza congelada sin valor
nuevo.** Premisa empírica: el volumen varía <0.1% por bloque, así que `varphi`
está casi fija por el volumen promedio. Pero ESA observación es justamente la que
**ya explota la cabeza congelada**: fija `varphi` y resuelve UN LP. Si `varphi`
se determina al toque, el maestro de Benders converge en pocos nodos al MISMO
`varphi` que la cabeza congelada elige — y entonces Benders no aporta nada que la
cabeza congelada (1 LP) no diera ya, mucho más barato. Si `varphi` NO se
determina al toque, entonces la premisa <0.1% es falsa y la cabeza congelada
estaría mal — pero la evidencia de la tesis dice que es buena. En ambos
escenarios Benders pierde: o es redundante con la cabeza congelada, o
contradiría una premisa validada.

**(c) Cortes de dualidad-LP con big-M ~1e9 → duales DÉBILES.** Los enlaces
`M·varphi − v ≤ M − V` con `M ~ 1e9` producen cortes de Benders clásicos
numéricamente débiles y mal escalados (los duales `σ` de filas big-M dan cortes
casi planos que no separan `y` fraccionario). Es el patológico conocido de
Benders con big-M. Los cortes combinatorios no-good (Codato–Fischetti) evitan el
big-M pero son DÉBILES en otro sentido: solo cortan el punto entero visitado (un
no-good por solución), convergencia lenta sobre miles de binarias. Ninguna de las
dos familias de cortes tiene fuerza para competir con el branch-and-cut del
solver sobre el compacto, que ya tiene cortes MIR/cover/flow afinados.

**Antecedente empírico:** DW y B&P ya se implementaron sobre ESTA estructura y
NO le ganaron al monolítico (DW: incumbente 50/50, cota peor por overhead;
DWCuts: recupera cota DW en la raíz pero no gana en el completo). Benders-sobre-
`varphi`, que da una cota AÚN MÁS DÉBIL (`z_LP < z_DW`), no tiene cómo invertir
ese resultado. **Predicción: dominado por monolítico**, igual que DW/B&P.

---

## Pregunta 3 — ¿Alguna variante SÍ recupera `z_DW` o gana?

La descomposición que da `z_DW` **NO es Benders-sobre-`varphi`**. Es:

- **Lagrangiana / Dantzig-Wolfe sobre los ACOPLES DE DEMANDA** con los bloques
  resueltos como IP (= pricing). Eso es exactamente lo que la tesis YA tiene
  implementado (DW + B&P). `z_DW = max_π L(π)` con `L(π)=π·b + Σ_bloque min_IP`.
  Verificado arriba: es la línea `z_DW=38.0` del ejemplo. **Ya está hecho** y ya
  se sabe que no le gana al monolítico.

- **Benders con el subproblema resuelto como IP por bloque** = "logic-based
  Benders" de Hooker, pero el subproblema NO es el LP de cabeza congelada: es un
  IP por bloque. Eso es funcionalmente el pricing de DW envuelto en otra
  notación (descomposición por bloque + cota de casco entero). Daría `z_DW`,
  pero es DW, no la propuesta T2 (que fija `varphi` y resuelve un LP).

- **Branch-and-check**: corre el maestro como MIP y verifica/refuerza con el
  subproblema. Da `z_MIP`, mismas pegas que P2(a)-(c).

**Distinción clave:** `z_DW` ⇔ pricing IP por bloque ⇔ DW/Lagrangiano sobre
demanda. **Benders proyecta continuas y nunca resuelve un IP de bloque**, por eso
está estructuralmente confinado a `z_LP`. La propuesta T2, tal como está
enunciada (subproblema = LP de cabeza congelada exacta), es la rama que da `z_LP`.
Para "recuperar `z_DW`" habría que cambiar el subproblema a IP-por-bloque, con lo
cual se reinventa el DW que ya existe y ya se sabe que no gana.

---

## Pregunta 4 — VEREDICTO go/no-go para C++

**NO-GO.** Razones:

1. **El objetivo declarado es matemáticamente inalcanzable por esta vía.**
   Benders-sobre-`varphi` da `z_LP`, no `z_DW` (derivado + verificado en 40/40
   instancias). No "recupera `z_DW` donde RLT falló"; choca con la misma pared.

2. **El maestro de Benders es el MIP duro de las `varphi`** (miles), con cortes
   de dualidad-LP debilitados por big-M ~1e9 o no-goods de convergencia lenta.
   No hay mecanismo para ganarle al branch-and-cut del solver sobre el compacto.

3. **Redundante con la cabeza congelada.** La premisa que motiva T2 (`varphi`
   casi predeterminada) es la MISMA que ya explota la cabeza congelada (1 LP).
   Donde T2 podría aportar, la cabeza congelada ya aporta más barato.

4. **Antecedente:** DW y B&P (que dan una cota MÁS FUERTE, `z_DW`) ya fueron
   implementados y NO le ganan al monolítico. Una técnica con cota más débil no
   puede revertir eso.

5. **Costo/riesgo:** ~500 líneas de lazy callbacks desde cero, para un negativo
   predicho por el análisis. El retorno esperado es negativo.

**Recomendación:** documentar este análisis (P1 con la derivación + el ejemplo
de 2 bloques verificado) como un resultado negativo a-priori, junto al RLT, en la
sección de descomposición. Cierra la pregunta "¿y Benders?" sin gastar la
implementación. La frase de cierre: *el +24% de `z_DW` vive en el casco entero
POR BLOQUE (enlace de volumen `x·v`), accesible solo por pricing IP de bloque
(DW), que ya está implementado y ya se sabe dominado por el monolítico; ni RLT-1
ni Benders-sobre-`varphi` (ambos confinados a `z_LP`) lo alcanzan.*

---

### Apéndice — números del ejemplo verificado
| cantidad | valor | cómo |
|---|---|---|
| z_LP | 30.800 | LP compacto, y∈[0,1] |
| z_DW | 38.000 | Lagrangiana del acople, bloques IP |
| z_MIP | 38.000 | MIP entero |
| Benders maestro-LP | **30.800 = z_LP** | loop de cortes, y∈[0,1] |
| Benders maestro-IP | 38.000 = z_MIP | loop de cortes, y∈{0,1} |
| robustez | 40/40 instancias | Benders-LP==z_LP, Benders-IP==z_MIP, orden OK |
| instancia 3-distintos | z_LP=30.448 < z_DW=31.947 < z_MIP=32.160; Benders-LP=30.448 | sweep |

Scripts: `verify_benders3.py` (cotas), `verify_benders4.py` (Benders decisivo),
`verify_benders6.py` (robustez 40 instancias).
