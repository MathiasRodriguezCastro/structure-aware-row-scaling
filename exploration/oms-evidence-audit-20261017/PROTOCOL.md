# Auditoría de las tres objeciones para OMS

Análisis secundario de resultados ya conocidos, fijado antes de calcular estas
nuevas agregaciones. No es una campaña confirmatoria ni validación externa nueva.
No se cambia el generador, los factores, las semillas ni los resultados guardados.
Cero nuevas llamadas al optimizador.

1. Novedad: distinguir el antecedente de transferencia de residuos, la integración
   implementada y la evidencia que prueba cada función. No ampliar los teoremas.
2. Robustez: usar todas las evaluaciones de la frontera (siete presupuestos, ambos
   presolve y seis modelos). Informar por modelo y semilla las razones emparejadas
   de trabajo y ciclo completo frente a NF3. Para cada celda, eliminar por turno
   un modelo completo y una semilla completa; publicar todos los agregados y sus
   rangos, sin eliminar fallos, cotas refutadas o abstenciones. Informar cumplimiento,
   contradicciones y cambio relativo de objetivo por separado. Las repeticiones de
   semillas y presupuestos no cuentan como modelos independientes.
3. Transferencia: mostrar los cuatro controles externos, sus presupuestos, trabajo,
   ciclo completo y cobertura real de contrastes con testigos exactos. Conservar
   las ocho instancias; desglosar también los seis horizontes que no eran anclas
   conocidas. No convertir menor trabajo en menor tiempo o en un gap certificado.
4. Restricciones: relacionar los resultados con la sensibilidad de tolerancia
   entera ya existente y con la auditoría de factores. Identificar cambios de
   representación sin atribuirles una operación interna del solver no observada.

Entregables: programa de reproducción sin solver, CSV/JSON con procedencia y una
nota breve. Incorporar al manuscrito solo resultados útiles y verificables.
La versión v1.3.13 permanece inmutable. El DOI sigue diferido.
