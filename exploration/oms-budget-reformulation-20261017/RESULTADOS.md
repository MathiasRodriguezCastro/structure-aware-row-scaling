# Resultado: la contracción clásica sola no restaura el contrato redondeado

Se aplicó propagación racional con derivación verificable a los cinco modelos
externos preseleccionados. Se conservaron 1.753 deducciones de cotas y 96
contracciones equivalentes para puntos enteros. No hubo llamadas al optimizador.

En cinca, los 96 coeficientes de activación pasan de 1e17 a valores entre
2.264.972,9729729732 y 2.270.270,2702702703. La reducción es grande, pero para
el presupuesto 1e-4 y gamma=1e-9 el umbral necesario es aproximadamente 1e5.
Siguen siendo incompatibles las 96 filas. En control30 no se obtiene ninguna
contracción; permanecen 96 incompatibilidades. En ta1 permanecen 55. H10 y H12
son controles nulos sin filas críticas seleccionadas.

La contracción puede resolver el obstáculo de magnitud del contrato del punto
sin redondeo en cinca; no hay que confundirlo con la garantía del punto entero
redondeado. No se satisface la puerta prospectiva para abrir una campaña MILP
de este candidato solo. La contracción certificada se reutiliza por igual en
los controles de exploraciones posteriores, para separar sus efectos.

La propagación y el fortalecimiento de coeficientes son operaciones conocidas.
Este resultado no justifica presentarlas como método nuevo del artículo.
El verificador reconstruye cada cota mediante aritmética racional y comprueba
los modelos completos antes/después: `python3 verify.py` desde esta carpeta.

Antecedente primario: Andersen y Pochet, fortalecimiento de coeficientes,
https://research.dial.uclouvain.be/entities/publication/03ea6bfe-7105-4d5c-a48a-47578c173bd1
