# Auditoría de Online Resource 2 — v1.7.1

**PASÓ** la validación desde extracción limpia, sin nuevos experimentos MIP.
El registro completo está en `paper/submission/orf/VALIDATION.json` y en la
entrega congelada; el JSON adyacente identifica sus hashes y el alcance.

| Cobertura verificada | Cantidad |
|---|---:|
| Resultados de la confirmación | 3.840 |
| Archivos de candidatos, logs nativos y relojes completos | 3.840 de cada tipo |
| Informes independientes por bloque | 480 |
| Archivos del tar reconstruidos y comprobados | 43.335 |
| Archivos auxiliares de clúster en el complemento | 38 |
| Comparaciones / intervalos reproducidos | 48 / 80 |
| Comprobaciones de dominio desde los vectores | 13.387 |
| Fragmentos de tablas regenerados idénticos | 7 |

Los 24 diagnósticos del modelo exactamente infactible se conservan; las otras
3.816 asignaciones forman la máscara común de calidad. Los archivos de candidatos
pueden estar vacíos en los diagnósticos. Se comprobaron los cuatro archivos
públicos de dependencias, los cinco manifiestos de integridad del tar, cada
auxiliar Python referido por los lanzadores y la coincidencia de `WHEELS.json`
con el registro de instalación. No se redistribuyen solvers propietarios ni licencias.

Se ejecutaron nuevamente los verificadores prospectivos, los seis del seguimiento,
la reproducción estadística de la confirmación y la sensibilidad de dominios.
Solo se reutiliza la auditoría de cuatro comandos del archivo histórico cuyo
SHA-256 permanece idéntico. Los 42 archivos de tablas heredados y las fórmulas
se conservan. Las cuatro fuentes LaTeX recompilan sin desbordamientos ni
referencias indefinidas: manuscrito 45 páginas, suplemento 42, carta y portada una.

## Corrección realizada

La auditoría ampliada de v1.7.0 detectó que el filtro de metadatos del tar omitía
auxiliares `.py` y `.json` de `cluster/`. El hallazgo original está conservado
en `orf-v1.7.0-resource-audit-20261022/FINDING.json`. La versión corregida añade
`confirmation-support-20261022.zip` con los archivos existentes y sus hashes.
El tar de resultados sellado y todas las conclusiones científicas son idénticos.

Para reproducción completa se extraen tanto el tar como ese ZIP sobre la misma
raíz, siguiendo REPRODUCE.md. La reconstrucción opcional de las 1.530 bases
históricas sigue requiriendo el archivo masivo publicado por separado; los
crudos de intentos de infraestructura excluidos no integran la muestra final.
Estas exclusiones están declaradas y no representan ejecuciones faltantes de
la confirmación.

## Entrega

- ZIP completo: 959,700,169 bytes.
- SHA-256: `e40df976d489c1d82c1620572aabc2542dcfc1a9e2d2d17693f55c8f037863f5`.
- `orf-editable-sources.zip` se entrega separadamente con TeX, bibliografía,
  figuras, clase, estilo y archivos de compilación.
- Las descripciones breves de Online Resource 1/2 y los campos editoriales están
  preparados; no se ha registrado una carga en el portal ni un depósito DOI.
