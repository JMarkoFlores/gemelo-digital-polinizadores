1. Dar zoom en las vistas 2D.
2. Implemnetar gestion general en admin (pq ahora solo está de manera individual por usuario).
3. Poner Tabla de acciones concretas

=== ALCANCE ESTRICTO ===
Solo modifica la app React de Cliente. NO toques Streamlit, NO toques React Admin, NO toques
docker-compose.yml ni ningún Dockerfile salvo indispensable y de forma mínima/aditiva. Si es
indispensable instalar una librería nueva (ej. turf.js para cálculo de área geográfica),
instálala solo en la app Cliente y dime explícitamente qué agregaste. Al final, lista todos los
archivos modificados.

=== CONTEXTO ===
En la sección "Comparacion espacial" de la página de Optimizacion, actualmente se muestra el
Paisaje base y el Paisaje optimizado con sus % de Cultivo, Seminatural y Franjas Florales (más
la vista satelital 2D y la maqueta 3D). Esto es correcto pero puramente descriptivo — no le dice
al usuario QUÉ HACER concretamente para pasar del escenario base al optimizado.

=== TAREA: AGREGAR TABLA/LISTA DE "PLAN DE ACCIÓN" ===

Debajo de la sección "Comparacion espacial" (después de la maqueta 3D, antes del Frente de
Pareto), agrega un nuevo bloque titulado "Plan de Acción Recomendado" que traduzca la diferencia
entre el paisaje base y el optimizado en acciones concretas y priorizadas:

1. CÁLCULO DE ÁREA REAL EN HECTÁREAS
   - Usa el GeoJSON del polígono dibujado por el usuario para calcular el área total en
     hectáreas (usa la librería turf.js — específicamente turf.area() — si no está ya
     instalada en el proyecto de React Cliente, o cualquier función de cálculo de área
     geodésica ya disponible en el proyecto).
   - Con esa área total, convierte los porcentajes de cada categoría de uso de suelo (Cultivo,
     Seminatural, Franjas Florales) de base y optimizado a hectáreas absolutas.

2. TABLA DE CAMBIOS POR CATEGORÍA DE USO DE SUELO
   Genera una tabla con una fila por categoría (Cultivo, Seminatural, Franjas Florales),
   mostrando:
   - Hectáreas en el escenario base
   - Hectáreas en el escenario optimizado
   - Cambio neto (en hectáreas y en puntos porcentuales), con flecha o color indicando aumento/
     disminución
     Ordena las filas de mayor a menor cambio absoluto (la categoría con más cambio va primero).

3. ACCIONES DE MANEJO (variables de decisión, no solo uso de suelo)
   Agrega también, debajo o junto a la tabla anterior, el cambio en las variables de manejo que
   ya están disponibles en los datos de la optimización (Nivel de Pesticidas, Área Natural
   Mínima, y cualquier otra variable de decisión que ya se muestre en la tabla "Mejor
   solución"), expresando el cambio como una acción imperativa concreta, por ejemplo:
   - "Reducir el nivel de pesticidas de 30% a 2% (reducción del 93%)"
   - "Aumentar el área natural mínima de 20% a 24.5%"
     Usa los valores reales ya calculados por el optimizador — no inventes cifras.

4. TEXTO DE PRIORIZACIÓN
   Agrega una frase automática al inicio del bloque, generada dinámicamente a partir de cuál
   categoría tuvo el mayor cambio absoluto en hectáreas, ej.: "La acción de mayor impacto es
   incrementar las franjas florales en X.X hectáreas (de Y% a Z% del área total), seguida de..."

5. FORMATO
   - Usa una tabla clara o tarjetas tipo checklist, consistente con el estilo visual ya
     existente en el resto de la página (tarjetas blancas con bordes redondeados, como las
     de "Distribución de Superficie").
   - Texto en español, conciso, sin tecnicismos innecesarios — el usuario objetivo es un
     agricultor o gestor de paisaje, no un científico de datos.
   - No inventes unidades o cifras que no puedas derivar de los datos ya disponibles en la
     respuesta de la API de optimización; si algún dato necesario no está disponible
     (ej. el área del polígono no se está guardando en ningún estado accesible), dime
     exactamente qué falta antes de improvisar un valor.

=== ENTREGABLE ===
Muéstrame el diff de código, una captura o descripción de cómo se ve la nueva sección, y
confírmame si el área del polígono en hectáreas se pudo calcular correctamente con los datos
que ya tenías disponibles o si hizo falta agregar algo nuevo para obtenerla.
