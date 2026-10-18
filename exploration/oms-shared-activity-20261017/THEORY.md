# Actividad normalizada compartida y contratos: derivación

Es un algoritmo candidato, no una declaración de prioridad bibliográfica.
La formulación indicadora/SOS y compartir holguras son antecedentes explícitos.
La pregunta es la selección exacta de una representación que cumple presupuestos,
su independencia de unidades y su efecto computacional frente a esos controles.

## 1. Proyección equivalente

Para un conjunto de filas g_i(x_C)<=M_i z, con una misma z binaria y M_i>0,
usar una única y en [0,R], w en [0,1], w+z=1, SOS1(w,y) y

    g_i(x_C) - h_i y <= 0, h_i=M_i/R.

Si z=0, y=0 fuerza todas las filas. Si z=1, elegir
y=max(0,max_i g_i(x_C)/h_i)<=R. Por tanto las proyecciones MILP coinciden.
La envolvente convexa de (z,y) es 0<=y<=Rz y proyecta las mismas filas
g_i<=M_i z. Ignorar completamente SOS en un LP no equivale a esa envolvente.
La prueba no afirma que un backend construya la envolvente ni preserve su matriz.

## 2. Transferencia de precisión al punto decodificado

Se supone round(z) en {0,1}, error de complemento <=epsilon_c,
1/2-epsilon_c>gamma_s, soporte SOS1 con a lo sumo un miembro de valor absoluto
>gamma_s, residuo exportado de cada enlace <=epsilon, y y<=R+tau.
Si round(z)=0, z<=1/2 y w>=1/2-epsilon_c>gamma_s, de modo que |y|<=gamma_s.
Así, g_i<=epsilon/alpha_i+h_i gamma_s. Si round(z)=1,
g_i-M_i<=epsilon/alpha_i+h_i tau. Se obtiene

    violacion_i tras redondear z <= epsilon/alpha_i + (M_i/R) T,
    T=max(gamma_s,tau).

No se usa una hipótesis de distancia de z a entero. Las demás filas, cotas e
integridades del modelo necesitan su propia comprobación. Una tolerancia nominal
no garantiza que un punto devuelto satisfaga las hipótesis anteriores.

## 3. Intervalo necesario y suficiente de radios diádicos

Tomar R=2^r y alpha_i=2^u. Todos los datos se interpretan como sus racionales
binary64 almacenados. Para cada coeficiente no nulo a de g_i, sean [slo(a),shi(a)]
los exponentes de desplazamiento que producen un resultado binary64 finito exacto.
Usar la ventana [ell,U] y definir, con m=min|a| y H=max|a|,

    A=min(floor(log2(U/H)), min_a shi(a), 1023),
    C=max(ceil(log2(ell/m)), max_a slo(a), -1074),
    B=min(floor(log2(U/M_i)), shi(M_i)),
    D=max(ceil(log2(ell/M_i)), slo(M_i)).

Las condiciones de magnitud y exportación de la fila son exactamente

    max(C,r+D) <= u <= min(A,r+B).

Además, h_i=M_i 2^-r debe representarse exactamente y R debe ser finito y <=cap:
r pertenece a [-shi(M_i),-slo(M_i)] intersectado con [-1074,1023,floor(log2(cap))].
Si A<C o B<D, no hay representación admisible. En otro caso los extremos de
coeficientes requieren C-B<=r<=A-D. Para r fijo, el menor límite de error
se consigue con u_max=min(A,r+B). Es

    max(P + M_i*T/2^r, (Q+M_i*T)/2^r),
    P=epsilon*2^-A, Q=epsilon*2^-B.

Por tanto, dado T>0, la precisión es posible si y solo si delta_i>P y

    r >= ceil(log2(M_i*T/(delta_i-P))),
    r >= ceil(log2((Q+M_i*T)/delta_i)).

La intersección de esos extremos enteros con los de representación anteriores
es un intervalo exacto [r_i^-,r_i^+]. Para un bloque con una sola y compartida,
la factibilidad es equivalente a max_i r_i^- <= min_i r_i^+.
El menor radio es R*=2^(max_i r_i^-). Esto minimiza exactamente el mayor valor
permitido de la actividad auxiliar dentro de esta familia; no el trabajo solver.
Después se elige el u más cercano a L2 dentro del intervalo admisible.

El algoritmo usa un recorrido de los coeficientes y las filas para construir
extremos racionales, sin búsquedas de radios ni llamadas a optimizadores.
La afirmación es sobre cantidad de operaciones; no supone costo constante de
aritmética racional ni reemplaza una medición de su implementación.
Si la intersección es vacía, dos extremos incompatibles o una fila inviable
constituyen un certificado verificable. No certifican inviabilidad del MILP.

## 4. Covariancia exacta bajo cambios coherentes de unidades

Multiplicar independientemente g_i, M_i y delta_i por 2^k_i. Cuando la conversión
y su inversa dan una correspondencia entre las representaciones admisibles
relevantes para minimizar, el radio admisible y la elección R* no cambian.
h_i cambia por 2^k_i y alpha_i por 2^-k_i.
Todos los coeficientes exportados y las cotas de y,w son entonces idénticos.
El criterio L2 usa productos escalados idénticos y conserva el desempate.
Esta propiedad se prueba comparando las condiciones efectivas de exportación;
no se extrapola a conversiones decimales que introducen redondeo de datos.
COVARIANCE_SCOPE.md precisa por qué conservar solo un minimizador representable
no basta cerca de las fronteras de binary64. Los 25 exports se cotejan directamente.

La invariancia no es exclusiva de este algoritmo: SOS-range y otras escalas
normalizadas pueden tenerla. Lo que se contrasta es conservarla junto con el
presupuesto de precisión y un costo útil frente a normalizaciones competidoras.

## 5. Comparación de alcance con escalado por filas

La cota uniforme del contrato de una fila original contiene M_i*gamma_z,
independiente de alpha_i. Si delta_i<=M_i*gamma_z, ningún factor de fila puede
satisfacer ese contrato. La actividad compartida sustituye ese término por
(M_i/R)*T y puede admitir un radio dentro del intervalo anterior. Es una
extensión del conjunto de representaciones con ese tipo de garantía condicional,
no una prueba de que todos los puntos de un solver sin la extensión fallen.
Tampoco es superioridad sobre cualquier reformulación o mecanismo numérico.
