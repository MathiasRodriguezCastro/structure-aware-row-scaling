# Validación del piloto y hallazgo en los modelos truncados

19 de octubre de 2026. Investigación separada de `v1.5.0-orf-submission`.
No se modifican el artículo, sus resultados ni el generador original.

## Exportación reproducible

El primer piloto terminó con 118 workers registrados: 98 llegaron al solver,
20 se detuvieron antes por la comprobación de identidad del LP escalado y 138
no se intentaron al fallar el bloque. Se conserva completo en
`infrastructure-attempts/blas-runtime-6068582/`; sus 1.093 archivos se
contrastaron con el inventario de hashes. No se usó para elegir políticas.

La causa se aisló en el núcleo de producto escalar de OpenBLAS seleccionado
según la CPU. En una tangente de Bonete, la norma cambió de
`0x1.02ba885379450p+0` a `0x1.02ba885379451p+0`, y el factor de
`0x1.fa99ab3c4ad64p-1` a `0x1.fa99ab3c4ad62p-1`. Fijar
`OPENBLAS_CORETYPE=Haswell`, con un hilo BLAS, recupera los bytes originales.
El trabajo 6069319 verificó los 192 modelos Base y reprodujo 384 exports escalados.
Los fuentes de las políticas, factores esperados, datos y tolerancias no cambian.

La conversión de enteros decimales largos en Python también impedía verificar
un vector racional ya guardado. `PYTHONINTMAXSTRDIGITS=0` permite comprobarlo
sin relajar ningún criterio matemático. La recuperación común produjo tres
referencias adicionales mediante un MILP Base y dos LP auxiliares, y dejó
31/32 referencias verificadas. Todo intento y costo anterior permanece registrado.

## Dos modelos son exactamente incompatibles

El caso pendiente no se debe únicamente a una dificultad del solver.
`simple-v1_simple_000127-h168` y
`completo-v1_completo_000106-h168` tienen certificados exactos de
incompatibilidad. El primero es de piloto; el segundo pertenece al conjunto
previsto para confirmación. No se sustituyen por casos más fáciles.

En el caso Simple, dos filas del primer período imponen

\[
200483019.71359825\,\phi-v\le-3133787572.0000014,
\qquad v+3600x+3600y=3121290100,
\]

con \(\phi,x,y\ge0\). Sumándolas, el lado izquierdo es no negativo y el
derecho es negativo. Con los datos binario64 la combinación da exactamente

\[
0\le-\frac{26209098399747}{2097152}
\approx-12497472.00000143\ \mathrm{m}^3.
\]

La contradicción también se verifica usando los decimales escritos del LP
como racionales exactos. No requiere integralidad ni llamadas a un optimizador.
El caso Full da la misma contradicción con otro coeficiente positivo de
\(\phi\); los certificados conservan por separado los coeficientes de cada modelo.
La auditoría revisó los 192 modelos: este test suficiente certifica dos como
inviables; no encontrar un certificado en los demás no demuestra factibilidad.
`check_structural_certificates.py` reproduce las combinaciones de filas y cotas.

La fuente está en `RioNegro::calcular_M1`: calcula un M a partir del volumen
alcanzable al final del horizonte y luego lo aplica a todos los períodos.
En una fila \(M\phi-v\le M-T\), el estado apagado todavía exige
\(v\ge T-M\). Para que esa exigencia sea redundante respecto de una cota
inferior válida \(L_t\), es suficiente que \(M\ge T-L_t\) en cada período.
Un único M debe cubrir todos los períodos; una cota terminal no lo garantiza.
En estos dos modelos, la fila de activación exige más agua de la alcanzable
en la primera hora. Los prefijos de datos, por tanto, no garantizan regiones
factibles anidadas: el generador recalcula sus constantes al cambiar el horizonte.

## Consecuencia para la ampliación

El piloto de recursos se repite con los mismos 32 modelos y 256 asignaciones,
incluido el caso certificado incompatible. La incompatibilidad debe distinguirse
de un timeout y de una falta de referencia por motivos numéricos. No corresponde
intentar resolverla aumentando indefinidamente el límite de tiempo.

El tratamiento previsto para las 3.840 asignaciones principales se declara en
`CONFIRMATION_ANALYSIS_DRAFT.md`: conservar el modelo incompatible y sus
asignaciones como diagnóstico, con calidad primal no aplicable. No se le
atribuirá una ventaja a ninguna política por resolverlo rápidamente, ni se
suprimirá silenciosamente del banco. Faltan terminar el piloto, resolver la
calibración Base y congelar los recursos. La campaña principal todavía no se lanza.

Estos son resultados de validación y control de la formulación. No demuestran
una ventaja computacional de Budget-L2 y no se incorporan como tal al artículo.
