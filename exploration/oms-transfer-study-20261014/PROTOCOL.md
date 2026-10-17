# Transferencia a grupos no usados y un segundo solver

Investigación separada de OMS v1.3.5. Pregunta: ¿la señal observada en control
se repite fuera de su grupo y del solver, y supera a controles existentes?
Se conserva el alcance seleccionado y los resultados negativos. No se modifica
ningún artefacto previo ni se busca iterativamente otro caso favorable.

## Selección anterior a resolver

SELECTION.json se congeló antes de descargar las nuevas instancias. Usa el
inventario Numerics ya archivado: easy, variables/filas <=5000, no ceros <=50000,
mezcla de enteros y continuos, orden por no ceros/nombre. Se toman los primeros
cuatro grupos explícitos distintos de los tres ya utilizados; grupos desconocidos
no cuentan como nuevos. Resultan neos-1112787, breastcancer-regularized,
neos-3083784-nive y neos-3661949-lesse. No son una muestra aleatoria ni una garantía
de dificultad bajo cada configuración. control30-3-2-3 es referencia conocida,
no evidencia retenida fuera del desarrollo. Todos los grupos seleccionados quedan.

Los MPS originales se conservan con hashes y atribución. Los lectores deben
preservar coeficientes, RHS, sentidos, costos y dominios. Características no
soportadas o pérdida de datos producen un fallo documentado, sin sustituir modelo.
El MPS de nive tiene 12.123 no ceros frente a 11.583 en la ficha; se conserva.

## Diseño fijado antes de las llamadas

Cinco modelos × dos semillas nuevas (83,97) × ocho tratamientos = 80 asignaciones.
Cuatro por solver:

- Gurobi/Base-IF1, L2-IF1 y Budget-IF1: IntegralityFocus=1, FeasibilityTol=1e-6,
  IntFeasTol=1e-5 compartidos; Gurobi/Base-tight: ambas tolerancias 1e-9, IF predeterminado.
- HiGHS/Base, L2 y Budget: primal_feasibility_tolerance y mip_feasibility_tolerance
  1e-6 compartidos; HiGHS/Base-tight: ambas 1e-9. El control IF no existe en HiGHS.

Gurobi 13.0.2/HiGHS 1.15.1, cuatro hilos, gap relativo 1 %, presolve y escalado
interno habituales. Límites MILP hasta 15 s, referencia global de ciclo 20 s.
Se ajusta la solicitud de tiempo al restante, se registran excesos de overhead.
Orden aleatorio fijo (20261018), llamadas secuenciales. No hay warm starts.
No se llama equivalentes a tolerancias enteras distintas entre solvers.

Las reglas L2/Budget son el mismo kernel diádico existente, ventana de coeficientes
[1e-9,1e9], hipótesis exportada epsilon=1e-6. Presupuesto original por fila
delta_r=1e-4 max(1,|RHS|), cotas 1e-4 y dominios enteros exactos. Son objetivos
numéricos algebraicos experimentales, no requisitos físicos/operativos. La
selección contractual se refiere al punto crudo, no garantiza todo redondeo entero.
Incompatibilidad de factor provoca abstención, no resolución o reemplazo silencioso.

## Verificación, calidad y auditoría

Se mide aceptación antes de reparar: punto crudo y entero redondeado, todas las
filas/cotas, dominios enteros exactos. La importación nativa se coteja contra los
datos originales y factores exactos. Una etiqueta óptima no sustituye esa prueba.

Cada tratamiento aplica el mismo postproceso. Si falla la entrega, se fija su
patrón entero y se intenta LP flotante (0,5 s) y, si todavía falla, exacto (1 s),
con tiempo restante. Solo se devuelve un candidato comprobado. Se retiene el de
menor costo original entre los aceptados. Una auditoría LP exacta de hasta 1 s
intenta obtener un testigo del mejor candidato si todavía no es factible exacto.
Se conserva la salida numérica aunque no haya testigo exacto. Nada certifica
optimalidad global ni transfiere el gap después de modificar el punto.

Un testigo previo exacto de control permite veto online en la referencia. En
los grupos nuevos, testigos generados después solo permiten auditoría posterior,
con disponibilidad explícita. Cualquier contradicción B>U usa factibilidad exacta
del mismo modelo, con guarda max(1e-6,8 ulp(B)). Ausencia de contradicción no
valida una cota. También se registra la compatibilidad del gap informado con
el objetivo fuente, respetando gap absoluto de cada solver y una guarda.

Endpoints: aceptación fuente/entrega, objetivos originales, tiempo completo y
etapas, reparaciones, incompatibilidades/importaciones fallidas, testigos y
contradicciones. Se informan por modelo/solver, separando la referencia del resto.
Mejora de precisión y calidad, frente a L2 y Base/strict, son preguntas distintas.
La selección de datos y la preparación compartida se cronometran aparte. Los
archivos auxiliares forman parte de su etapa; la persistencia final, aparte.

## Decisión para el paper

La incorporación requiere una ventaja defendible en grupos no usados frente a
controles fuertes, sin ignorar costos, precisión o adversos. Activar contratos o
mejorar solo frente a L2 no prueba novedad científica o superioridad general.
Si no ocurre, se cierra esta línea con sus límites en un documento independiente.
