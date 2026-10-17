# Antecedentes revisados y alcance de la búsqueda

Consultas del 15 de octubre de 2026. Se usaron fuentes primarias. Las búsquedas
de factores acotados, escalamiento unilateral y error ponderado no constituyen
una revisión exhaustiva ni permiten reivindicar prioridad.

## Exportación exacta

- D. Goldberg, *What Every Computer Scientist Should Know About Floating-Point
  Arithmetic* (1991), [texto del autor reproducido por Oracle](https://docs.oracle.com/cd/E19957-01/806-3568/ncg_goldberg.html).
  Se contrastaron la representación binaria, los 53 bits de precisión doble y
  los límites de exponente. Descomponer datos en entero impar y potencia de dos,
  y contar los bits de sus productos, usa esa aritmética estándar. No se
  reivindica como descubrimiento de un nuevo principio de redondeo.
- T. Berthold y G. Hendel, *Learning To Scale Mixed-Integer Programs* (2021),
  [artículo original, p. 3662](https://ojs.aaai.org/index.php/AAAI/article/view/16482/16289).
  Se leyó la sección de antecedentes: Xpress restringe los factores a potencias
  de dos para evitar errores al transformar los datos; presenta ST y Curtis–Reid.
  Esto respalda el control conservador del estudio. La selección aprendida entre
  políticas ya tiene antecedentes: un predictor nuevo requeriría evidencia
  propia y comparación. El artículo no prueba la optimalidad del selector
  ampliado implementado aquí.

## Límites conjuntos: ampliación de la revisión anterior

- A. Charnes y W. W. Cooper, *Programming with Linear Fractional Functionals*
  (1962), [original conservado por CMU](https://iiif.library.cmu.edu/file/Cooper_box00010_fld00009_bdl0001_doc0001/Cooper_box00010_fld00009_bdl0001_doc0001.pdf).
  Se revisaron pp. 181–184, la sustitución y=t x, la normalización del
  denominador y las equivalencias con programación lineal. El cambio v=t/alpha
  de la nota anterior pertenece a la misma técnica de homogeneización: no
  constituye una técnica general nueva. Esto no equivale a afirmar que este
  artículo de 1962 contenga nuestro problema específico de escalamiento.
- Z. Qu et al., *Optimal Diagonal Preconditioning*,
  [versión primaria v2](https://arxiv.org/html/2209.00809v2).
  Se revisaron secciones 1, 2.1 y 3.1 y la definición de condición del apéndice A.
  Estudian condición espectral, reformulaciones cuasiconvexas y SDP unilaterales;
  incluyen una cota sobre una matriz diagonal en una formulación bilateral.
  No son una demostración del mínimo explícito en norma infinito con cajas
  por fila de nuestras notas. Tampoco justifican atribuirle novedad: norma,
  sistema fijo, precisión y restricciones deben compararse específicamente.
- N. J. Higham, *A Survey of Componentwise Perturbation Theory* (1994),
  [original del autor, ecuaciones 2.11–2.12](https://eprints.maths.manchester.ac.uk/651/1/SURVEY.pdf).
  La invariancia de Skeel y el mínimo libre por escalamiento de filas ya se
  verificaron en la nota anterior. Aquí se conserva su atribución; no se
  vuelve a presentar el resultado clásico como contribución.

## Decisión editorial

La revisión permite descartar dos argumentos de novedad: eliminar errores
mediante potencias de dos y convertir un problema fraccional positivo mediante
homogeneización. No permite resolver la prioridad de todas las extensiones
acotadas. Sin un caso de aplicación útil ni una ventaja práctica, esa prioridad
no se investiga como requisito para añadir otro teorema a OMS. Las derivaciones
e implementaciones permanecen en notas separadas. No se modifica el manuscrito.

## Búsquedas y límites de acceso

Se consultaron combinaciones de "optimal row scaling bounds infinity condition
number", "row scaling bounded factors", "diagonal preconditioning box
constraints condition number", "matrix scaling bounds on the scaling",
"optimal scaling weighted error infinity norm" y "exact scaling powers of two
linear programming". Los resultados secundarios no se usaron como pruebas.
La descarga web del libro de Boyd–Vandenberghe devolvió error: no se afirma
haberlo revisado. La ausencia de una coincidencia en estas búsquedas no es
certificado de novedad. La búsqueda no abarca exhaustivamente patentes,
literatura de aritmética ni implementaciones de todos los optimizadores.
