# Presupuestos uniformes para patrones desconocidos: existencia y utilidad

Nota matemática preliminar, separada de OMS. No se afirma novedad ni se presenta
un método eficiente. El experimento de realimentación no satisface la hipótesis
de familias completas que sigue. El argumento permite precisar qué falta.

Consideremos datos racionales y el subproblema

\[
v_z(w)=\min_y\{c_C^\top y:Ay\le b-Bz+w\},\quad z\in\mathbb Z^p,\quad w\ge0.
\]

Todas las cotas continuas se escriben como filas, de modo que y sea libre.
Suponemos al menos un patrón con subproblema factible y valor finito. El conjunto
dual común D={π≤0:Aᵀπ=c_C} es entonces no vacío. Es un poliedro apuntado;
sea V su conjunto **completo y finito** de vértices. Sea R un conjunto **completo
y finito** de generadores extremos del cono K={r≤0:Aᵀr=0}. Son hipótesis sobre
descripciones exactas, no sobre una colección de certificados encontrados.

## Costo para cualquier patrón factible

Para un patrón factible, la dualidad permite elegir π_z∈V óptimo en w=0.
La factibilidad dual no cambia al relajar el RHS. Por tanto

\[
0\le v_z(0)-v_z(w)\le |\pi_z|^\top w
\le \max_{\pi\in V}|\pi|^\top w.
\]

Así, imponer |π|ᵀw≤ε para **todo** π∈V protege el costo de cualquier patrón
factible, sin conocerlo previamente. El costo entero c_Iᵀz se cancela. Un punto
que respeta el modelo relajado no puede subestimar el óptimo de continuación
exacta en más de ε. La afirmación no limita cuánto sobreestima ese óptimo,
ni proporciona una continuación cercana al punto observado.

## Excluir todos los patrones falsamente factibles

Para cada r∈R, multiplicamos por un racional positivo para que la función afín
g_r(z)=rᵀ(b−Bz) tenga coeficientes **enteros, incluido el término constante**.
Tal normalización existe por racionalidad. Los generadores cuya función es
idénticamente cero pueden omitirse. Si un patrón entero es inviable, Farkas
y la completitud de R dan algún r con g_r(z)>0; la normalización implica
g_r(z)≥1. Si se impone

\[
|r|^\top w\le\rho\qquad\text{para todo }r\in R,\quad 0<\rho<1,
\]

entonces rᵀ(b−Bz+w)≥1−ρ>0. El patrón sigue siendo inviable en el modelo
relajado. La inclusión inversa es automática porque w≥0: se preserva exactamente
el conjunto de patrones con continuación factible. No hace falta acotar z para
este argumento de retícula; sí hacen falta datos racionales y normalizaciones
exactas comunes a todos los patrones.

## Qué resuelve y qué no

V y R son finitos: para ε>0 y cualquier dirección finita w₀>0 existe un t>0
suficientemente pequeño tal que w=t w₀ cumple ambas familias. Es un argumento
de existencia derivado de dualidad poliédrica, Farkas y racionalidad. **Existencia
no equivale a utilidad computacional**. Las familias pueden ser muy grandes,
la cota puede resultar excesiva y t quedar por debajo de la precisión de trabajo.
Verificar unas cuantas π y r válidas no certifica completitud. La biblioteca
del ensayo solo aprende cortes locales en ese sentido y no aporta esta garantía.

Si primero se redondean enteros numéricos, el presupuesto efectivo debe incluir
la perturbación de Bz; por ejemplo |B|γ componente a componente. Una tolerancia
fija γ puede consumir todo el margen y volver incompatibles las condiciones.
También deben incluirse residuos de cotas y exportación. El resultado es
condicional a que los residuos efectivos cumplan w; no obliga al solver a
cumplirlo, no construye el punto exacto y no certifica optimalidad MILP global.

## Ejemplo racional comprobable a mano

Minimizar y con y≥z, y≤1/2, z∈{0,1}. En forma ≤:
A=(−1,1)ᵀ, b=(0,1/2)ᵀ, B=(1,0)ᵀ. D tiene el único vértice (−1,0).
El cono de Farkas tiene generador (−1,−1); normalizado, r=(−2,−2) da
g_r(z)=2z−1. Para w=(t,t), la pérdida de costo del patrón factible z=0 es t.
La condición 4t<1 excluye z=1. En t=1/4 aparece el punto espurio z=1,y=3/4,
que respeta ambas filas relajadas: el margen estricto es necesario en este ejemplo.
Esto muestra por qué proteger solo costo no basta para proteger factibilidad.

## Antecedentes y pregunta pendiente

Las cotas de Hoffman ofrecen otra vía uniforme para patrones factibles, con
control de distancia además del costo. Peña, Vera y Zuluaga caracterizan esas
constantes respecto de un poliedro de referencia:
[artículo](https://arxiv.org/abs/1905.02894). Stein estudia cotas a priori y
a posteriori para redondeos de óptimos de la relajación LP en problemas mixtos:
[artículo y resumen del autor](https://optimization-online.org/2013/11/4132/).
No se establece aquí equivalencia ni novedad respecto de esos trabajos.

La pregunta con potencial sería obtener **una envolvente estructural certificada
de las familias completas**, sin enumerarlas, que dé presupuestos compatibles
con las tolerancias y unidades de un modelo real. No está resuelta en esta nota.
No justifica extender el ensayo negativo ni agregar un teorema al paper OMS.
