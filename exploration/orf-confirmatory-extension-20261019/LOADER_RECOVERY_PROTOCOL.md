# Corrección del cargador y repetición íntegra de la confirmación

Registro del 20 de octubre de 2026 (Montevideo), previo al relanzamiento.

El intento `6071904–6071909` usa el plan con SHA-256
`b960242359f2645cb6b6b9e05558e80c64ff2385b6daae7130a0716cdce85fda`.
En los bloques 45 y 64 fallaron doce comprobaciones de identidad del export
escalado, antes de llamar a un optimizador. Los Base coinciden con sus hashes;
los exports difieren en uno o dos ULP. Se conservaron los dieciséis procesos de
ambos bloques, incluidos los cuatro Base terminados, con sus registros.

La prueba registrada `6072392` aísla el entorno de carga. Con precarga global de
la biblioteca completa de CPLEX, `math.exp` difiere en un ULP y ninguno de los
cuatro exports de prueba coincide. Sin precarga, los cuatro coinciden, pero
CPLEX usa la edición limitada. Con `LD_LIBRARY_PATH` apuntando a la biblioteca
completa, los cuatro coinciden y CPLEX resuelve el LP técnico de 2.501 variables.
La carga global tardía también pasa, pero no se adopta: el cambio elegido se
limita al mecanismo de carga del wrapper, sin editar el selector.

1. Retener y cancelar solamente los trabajos pendientes del intento original;
   permitir que termine el bloque ya activo. No interrumpir una resolución.
2. Exigir la reproducción byte a byte de los 192 Base y 384 exports escalados,
   junto con las dos pruebas de licencia completa, en cómputo y bajo el entorno
   corregido. No cambiar los hashes esperados ni aceptar diferencias numéricas.
3. Consolidar y sellar en cómputo el intento incompleto. Conservar todos sus
   artefactos, planes, fuentes registradas, contadores, costos y contabilidad
   Slurm. Archivar también la validación estadística registrada y no enviada.
4. Cambiar solamente el wrapper de confirmación: sustituir la precarga global
   por la ruta de búsqueda de biblioteca. Registrar una enmienda sucesora y
   verificar que el diseño científico coincide exactamente con el original.
5. Repetir las 3.840 asignaciones completas, en su orden original, con la misma
   puerta de admisión, primer bloque y array serial. No combinar observaciones
   de los dos entornos. El intento completo anterior queda excluido del análisis
   primario por la falla del entorno de reproducción, sin consultar rankings.
6. Mantener modelos, generador, semillas, políticas, factores originales,
   referencias, tolerancias, límites, máscara diagnóstica y análisis primario.
   Separar los costos del intento de infraestructura de los tiempos del nuevo
   experimento. No presentar la reparación como evidencia de eficacia del método.
7. Registrar de nuevo la verificación estadística independiente contra el plan
   sucesor. Exigir resultados completos, reproducción de candidatos y sellado
   antes de cualquier comparación final.

La versión de envío y sus archivos permanecen intactos. Toda compresión,
recorrido voluminoso y cálculo de hashes remoto se ejecuta mediante `sbatch`.
Las transferencias usan el puerto 10022 sin compresión en el login.
