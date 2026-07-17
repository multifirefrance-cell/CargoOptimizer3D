# Product Backlog — CargoOptimizer3D

**Documento de gestión de producto** · Fase 10.1 · Convierte la auditoría de producto en un backlog ejecutable. No contiene código ni decisiones de tecnología — solo alcance, valor, esfuerzo relativo y secuencia.

---

## 0. Cómo leer este documento

- **Prioridad**: Crítico / Muy importante / Importante / Futuro — heredada de la auditoría, es la urgencia de *negocio*.
- **Versión objetivo**: `1.0` (lanzamiento comercial), `1.1` (primer fast-follow, meses después del lanzamiento), `1.2` (madurez competitiva), `2.0` (cambio de era: colaboración/nube). Una prioridad **Crítico** no siempre cae en `1.0` — a veces depende técnicamente de algo que debe ir primero; eso se explica en **Dependencias**.
- **MVP** es un subconjunto *dentro* de `1.0`: lo mínimo para cobrar, no lo mínimo para ganar. Se define aparte en la §4.
- **Estado** de todo el backlog: **No iniciado** (ningún ítem tiene desarrollo comenzado) — salvo lo que se registre explícitamente como avanzado en `docs/Roadmap.md` a medida que se implemente.
- Los ítems marcados **Futuro** llevan ficha reducida a propósito: detallarlos a fondo hoy sería trabajo de planificación desperdiciado.

---

## 1. Resumen ejecutivo

59 ítems, agrupados en 9 EPICs, agrupados a su vez en 4 versiones. El backlog no está ordenado por lo fácil de construir — está ordenado por lo que un comprador real (forwarder, 3PL, fábrica, distribuidor de equipos contra incendio) necesita ver para dejar de usar Excel. La sección 3 da el orden de ejecución real, cruzando EPICs.

---

## 2. EPICs

| EPIC | Nombre | Ítems | Resuelve |
|---|---|---|---|
| 1 — OPT | Motor de Optimización | 10 | Que el cálculo sea correcto, legal y a la escala real de un envío |
| 2 — LOG | Planificación Logística | 8 | Que el plan de carga sirva para la operación completa, no solo para un contenedor aislado |
| 3 — VIS | Visualización y Ejecución en Bodega | 5 | Que el plan salga del PDF y llegue a quien carga el camión |
| 4 — UX | Experiencia de Usuario | 8 | Que el software se sienta profesional, no interno |
| 5 — DAT | Catálogo y Productividad | 4 | Que la segunda carga sea más rápida que la primera |
| 6 — REP | Reportes e Inteligencia | 7 | Que el sistema explique y aconseje, no solo calcule |
| 7 — INT | Integraciones y Plataforma | 9 | Que el producto hable con el resto del stack del cliente |
| 8 — ADM | Administración y Colaboración | 3 | Que lo use un equipo, no una persona |
| 9 — COM | Comercialización | 5 | Que exista un motor de ventas alrededor del producto |

---

## 3. Orden de ejecución recomendado (por valor, cruzando EPICs)

No es el orden de los EPICs. Es el orden en que un Product Owner los pondría en el primer año si tuviera que elegir.

| # | ID | Ítem | Prioridad | Por qué va aquí y no más abajo |
|---|---|---|---|---|
| 1 | OPT-01 | Asignación multi-contenedor/vehículo | Crítico | Sin esto, el producto responde solo la mitad de la pregunta que hace el cliente |
| 2 | OPT-02 | Motor de rendimiento a escala | Crítico | Sin esto, OPT-01 es inutilizable con volúmenes reales (miles de bultos) |
| 3 | OPT-03 | Peso, centro de gravedad y carga por eje | Crítico | Sin esto el plan puede ser ilegal de transportar; riesgo, no solo producto |
| 4 | COM-01 | Decisión de modelo de despliegue | Crítico | Toda arquitectura posterior (nube, API, multiusuario) depende de esta decisión |
| 5 | UX-01 | Internacionalización end-to-end | Crítico | Bloquea literalmente "comercializar internacionalmente" |
| 6 | UX-02 | Deshacer / rehacer | Crítico | Higiene mínima; su ausencia se nota en la primera demo |
| 7 | INT-02 | Explotación comercial del SDK ya existente | Muy importante | Costo de desarrollo ≈ cero, canal de ingresos nuevo (B2B2B) |
| 8 | OPT-09 | Orientación obligatoria generalizada | Muy importante | El motor ya sabe hacerlo para extintores; generalizarlo es bajo esfuerzo, alto valor |
| 9 | UX-04 | Plantillas de proyecto por vertical | Muy importante | Reduce el "folio en blanco" que mata trials |
| 10 | COM-02 | Freemium / prueba gratuita | Muy importante | Sin motor de adquisición, todo lo anterior no se prueba |
| 11 | COM-03 | Casos de estudio por vertical | Muy importante | Contenido, no ingeniería; listo para vender desde el día uno |
| 12 | COM-05 | Calculadora de ahorro de flete | Importante | Herramienta de venta barata con alto efecto de cierre |
| 13 | OPT-04 | Modo rápido vs. óptimo | Muy importante | Complementa OPT-02; el usuario elige velocidad vs. calidad |
| 14 | VIS-02 | Etiquetas permanentes en el visor | Importante | Bajo esfuerzo, mejora percibida inmediata |
| 15 | UX-07 | Autocompletado de SKU | Importante | Bajo esfuerzo, fricción diaria menos |
| 16 | UX-03 | Autoguardado y recuperación | Importante | Bajo esfuerzo, evita el peor tipo de queja de soporte |
| 17 | UX-05 | Asistente de primer proyecto | Importante | Determina la tasa de conversión de trial a compra |
| 18 | DAT-03 | Botón de recalcular prominente | Importante | Trivial, corrige una fricción ya diagnosticada |
| 19 | INT-01 | API REST pública | Crítico | Puerta de entrada a todo lo demás en INT; depende de COM-01 |
| 20 | LOG-04 | Reglas de negocio propias sin código | Crítico | El diferenciador más defendible frente a competidores rígidos |
| 21 | LOG-03 | Secuencia de descarga multi-parada (LIFO) | Crítico | Depende de OPT-01; sin multi-contenedor no hay "ruta" que secuenciar |
| 22 | OPT-06 | Compatibilidad de mercancías (ADR/IMDG) | Muy importante | Abre el vertical de químicos/mercancías mixtas |
| 23 | OPT-05 | Multi-estrategia comparada | Muy importante | Sube el techo de calidad del algoritmo sin exponer complejidad al usuario |
| 24 | REP-03 | Explicación accionable de no-carga | Muy importante | Reutiliza datos que ya existen (`UnpackedReason`); esfuerzo medio, percepción de "IA" alta |
| 25 | VIS-04 | Escaneo de código de barras/QR | Muy importante | Elimina el error de tecleo, el punto de dolor más citado en bodega |
| 26 | LOG-01 | Empaquetado en dos niveles (pallet) | Muy importante | Habilita el vertical FMCG/distribución completo |
| 27 | LOG-02 | Carga parcial priorizada por valor | Muy importante | Convierte un "no cupo todo" en una decisión de negocio, no un accidente |
| 28 | DAT-01 | Plantillas de carga por cliente recurrente | Muy importante | Reutiliza infraestructura de catálogo ya construida |
| 29 | REP-07 | Panel de analítica del historial | Importante | El dato ya existe; falta la pantalla |
| 30 | REP-05 | Plantillas de informe personalizables | Importante | Ya diseñado conceptualmente en una fase anterior |
| … | — | *(resto del backlog: ver EPICs completos §6; todos con versión objetivo 1.2 o 2.0)* | — | — |

---

## 4. MVP — lo imprescindible para cobrar (no lo deseable)

Un Product Owner que recorte esto más abajo está regalando el producto; recortar menos es demorar el ingreso sin motivo. El MVP es la intersección exacta entre **"resuelve el problema real"** y **"no da vergüenza cobrarlo"**:

1. **OPT-01** Asignación multi-contenedor/vehículo
2. **OPT-02** Motor de rendimiento a escala
3. **OPT-03** Peso / centro de gravedad / carga por eje
4. **UX-01** Internacionalización end-to-end
5. **UX-02** Deshacer / rehacer
6. **COM-01** Decisión de modelo de despliegue (resuelta *antes* de escribir nada más)
7. **COM-02** Freemium / prueba gratuita
8. **INT-02** Explotación comercial del SDK (ya existe — no añade calendario)

Todo lo demás en `1.0` (ver §5) es lo que separa **"un MVP defendible"** de **"una v1.0 que gana comparativas frente a EasyCargo o Cargo-Planner"**. El MVP por sí solo alcanza para vender a un cliente que ya confía en el vendedor (venta consultiva, referido); no alcanza para ganar una demo a ciegas contra la competencia.

---

## 5. Qué entra en cada versión — y por qué

### Versión 1.0 — Lanzamiento comercial
Todo el MVP (§4) **más**: OPT-04, OPT-09, UX-03/04/05/07, VIS-02, DAT-03, COM-03/05.
**Criterio de corte**: cualquier ítem que (a) cueste poco y (b) se note en la primera demo entra en 1.0, aunque no sea "crítico" en la auditoría — una v1.0 sin fricciones visibles vale más que una v1.0 con un ítem más de motor y una UI que se siente inacabada.
**Justificación de lo que NO entra**: API pública (INT-01) y reglas configurables (LOG-04) son enormes en valor pero requieren decisiones de arquitectura post-COM-01 y no bloquean la primera venta consultiva — entran apenas un ciclo después.

### Versión 1.1 — Primer fast-follow (meses después del lanzamiento)
INT-01 (API), LOG-03 (secuenciación multi-parada), LOG-04 (reglas propias), OPT-05/06, VIS-03/04, UX-06/08, DAT-01, REP-03/05/07, INT-07, LOG-01/02/08, COM-04.
**Justificación**: es la versión que convierte "vendimos por confianza" en "vendimos por comparación técnica ganada". Todo lo que en la competencia se usa como argumento de venta (reglas propias, secuencia de ruta, API) vive aquí.

### Versión 1.2 — Madurez competitiva
OPT-07/10, LOG-05/07, VIS-01, DAT-02/04, REP-01/02/06, INT-03/04/05/06.
**Justificación**: son mejoras reales, pero cada una asume una base de clientes ya operando (analítica, integraciones ERP profundas, instructivos de bodega) — construirlas antes de tener clientes activos es optimizar para nadie.

### Versión 2.0 — Cambio de era: colaboración y nube
ADM-01/02/03, INT-08/09, LOG-06, OPT-08, REP-04, VIS-05.
**Justificación**: son las únicas piezas que exigen repensar la arquitectura de despliegue (multiusuario en la nube) o atacan nichos que aún no se han validado con ventas reales (cadena de frío, formas irregulares). Meterlas antes sería apostar la hoja de ruta a un mercado todavía no confirmado.

---

## 6. Backlog completo por EPIC

Cada ítem lleva: descripción funcional, problema, beneficios, ficha de gestión (prioridad · valor · impacto · esfuerzo · riesgo · dependencias · versión · estado), criterios de aceptación y caso de uso. Los ítems **Futuro** llevan ficha reducida.

---

### EPIC 1 — Motor de Optimización (OPT)

#### OPT-01 — Asignación multi-contenedor / multi-vehículo
**Descripción:** dado un pedido completo (no un espacio ya elegido), el sistema calcula cuántas unidades de carga hacen falta y distribuye automáticamente los productos entre ellas.
**Problema que resuelve:** hoy el usuario elige un espacio y optimiza contra ese único espacio; la pregunta real de un forwarder ("¿cuántos contenedores necesito?") no tiene respuesta.
**Beneficio usuario:** deja de hacer prueba y error manual contenedor por contenedor.
**Beneficio comercial:** es la funcionalidad que aparece primero en cualquier comparativa de mercado.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Crítico | Muy alto | Muy alto | Alto | Alto — nuevo nivel de orquestación sobre el motor greedy actual | Ninguna (es cimiento) | 1.0 | **Motor implementado** (`application.MultiSpaceAssignmentEngine`, ver `docs/MultiSpaceAssignment.md`); integración de interfaz pendiente |

**Criterios de aceptación:**
- El usuario puede pedir "optimiza este pedido" sin elegir de antemano cuántos espacios usar.
- El sistema debe proponer el número mínimo (o casi mínimo) de unidades de carga necesarias y repartir los productos entre ellas.
- El usuario puede fijar un tipo de espacio preferido y dejar que el sistema decida solo la cantidad.

**Caso de uso:** *Usuarios:* planificador de un freight forwarder. *Ejemplo:* un exportador entrega 40 pallets mixtos; el planificador pide el plan de carga y el sistema responde "3 contenedores de 40 pies, distribución adjunta" en vez de forzar a probar contenedor por contenedor.

---

#### OPT-02 — Motor de rendimiento a escala
**Descripción:** eliminar el cuello de botella de cálculo ya documentado (~80 s para 100 unidades) mediante una estructura de datos espacial en la evaluación de reglas.
**Problema que resuelve:** el motor no es usable en operaciones con miles de bultos por envío.
**Beneficio usuario:** espera segundos, no minutos, incluso en envíos grandes.
**Beneficio comercial:** sin esto, OPT-01 (multi-contenedor) es, en la práctica, inutilizable a la primera carga real de un cliente mediano.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Crítico | Muy alto | Muy alto | Alto | Medio-alto — ya se identificó la solución (índice espacial), el riesgo es de tiempo, no de incertidumbre técnica | Habilita OPT-01 a escala real | 1.0 | **Parcial**: caché de cajas ya conocidas entre `optimization`/`rules` implementada (~15% más rápido, cero cambio de resultado — ver `docs/OptimizerPerformance.md`, sección "Fase OPT-02"); el índice espacial real (el que cambiaría la complejidad, no solo el factor constante) sigue pendiente — investigado con evidencia nueva y formalizado como **OPT-11**, postergado sin ADR (ver más abajo) |

**Criterios de aceptación:**
- El sistema debe optimizar un envío de 500+ bultos en menos de 10 segundos en hardware estándar.
- El usuario puede ver una barra de progreso creíble mientras el cálculo corre.

**Caso de uso:** *Usuarios:* operador de un centro de distribución. *Ejemplo:* un pedido de 800 cajas mixtas se optimiza mientras el operador sigue trabajando en otra pantalla, sin bloquear su turno.

---

#### OPT-03 — Distribución de peso, centro de gravedad y carga por eje
**Descripción:** validar y, cuando aplique, forzar que el plan de carga respete límites de peso por eje y posición del centro de gravedad.
**Problema que resuelve:** en transporte terrestre, un plan de carga sin esto puede ser ilegal de circular, no solo subóptimo.
**Beneficio usuario:** confianza de que el plan que imprime es transportable, no solo geométricamente válido.
**Beneficio comercial:** cierra la puerta a una objeción de compra que cualquier gerente de flota va a hacer en la primera reunión.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Crítico | Muy alto | Muy alto | Medio-alto | Medio — requiere modelar normativa de peso por eje, que varía por país | Ninguna | 1.0 | No iniciado |

**Criterios de aceptación:**
- El sistema debe calcular la distribución de peso resultante del plan de carga.
- El sistema debe advertir cuando el centro de gravedad o la carga por eje excede un límite configurado.
- El informe muestra la distribución de peso como parte del resumen ejecutivo.

**Caso de uso:** *Usuarios:* transportista de carga terrestre. *Ejemplo:* al cargar un camión con productos de densidades muy distintas, el sistema avisa que el eje delantero quedaría sobrecargado y sugiere qué reubicar.

---

#### OPT-04 — Modo rápido vs. modo óptimo
**Descripción:** dos estrategias seleccionables por el usuario sobre el mismo motor: una prioriza velocidad, otra prioriza calidad de resultado.
**Problema que resuelve:** hoy solo existe una velocidad de cálculo; no todos los casos de uso necesitan el mejor resultado posible, algunos necesitan una respuesta inmediata.
**Beneficio usuario:** control real sobre el trade-off tiempo/calidad.
**Beneficio comercial:** argumento de venta directo frente a competidores de estrategia única.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Muy importante | Alto | Alto | Medio | Bajo — el motor ya expone la estrategia como un `Protocol` intercambiable | OPT-02 | 1.0 | No iniciado |

**Criterios de aceptación:**
- El usuario puede elegir "rápido" u "óptimo" antes de ejecutar la optimización.
- El sistema debe mostrar el tiempo estimado de cada modo antes de confirmar.

**Caso de uso:** *Usuarios:* planificador bajo presión de tiempo vs. planificador de un envío de alto valor. *Ejemplo:* para un envío urgente el planificador usa "rápido"; para un contenedor de electrónica de alto valor usa "óptimo" y acepta esperar más.

---

#### OPT-05 — Multi-estrategia comparada automáticamente
**Descripción:** correr internamente 2-3 heurísticas distintas y presentar la mejor, sin que el usuario tenga que elegir cuál.
**Problema:** una sola heurística (greedy extreme-point) puede no ser la mejor para todos los perfiles de carga.
**Beneficio usuario:** mejor resultado sin necesitar entender de algoritmos.
**Beneficio comercial:** sube el techo de calidad sin subir la complejidad percibida.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Muy importante | Alto | Alto | Alto | Medio-alto — exige mantener varias estrategias con contrato compatible | OPT-04 | 1.1 | No iniciado |

**Criterios de aceptación:** El sistema debe ejecutar más de una estrategia y quedarse con el resultado de mayor utilización sin intervención del usuario.

**Caso de uso:** *Usuarios:* cualquier planificador. *Ejemplo:* dos envíos con perfiles de producto muy distintos obtienen automáticamente su mejor heurística respectiva, sin que el usuario lo note.

---

#### OPT-06 — Compatibilidad de mercancías ampliada (ADR/IMDG)
**Descripción:** generalizar la matriz de incompatibilidad (hoy limitada a extintores) a grupos de segregación de mercancías peligrosas reconocidos internacionalmente.
**Problema:** hoy no se pueden modelar restricciones de mezcla para químicos, alimentos u otras cargas incompatibles entre sí.
**Beneficio usuario:** cumplimiento normativo automático en vez de manual.
**Beneficio comercial:** abre el vertical de mercancías peligrosas y mixtas.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Muy importante | Alto | Alto | Medio | Medio — requiere modelar tablas de segregación reales, no solo el mecanismo | Extiende el patrón ya usado para extintores | 1.1 | No iniciado |

**Criterios de aceptación:** El sistema debe rechazar o advertir una colocación que mezcle dos grupos de mercancías declarados incompatibles.

**Caso de uso:** *Usuarios:* operador logístico de químicos. *Ejemplo:* el sistema impide automáticamente colocar un producto oxidante junto a uno inflamable en el mismo espacio.

---

#### OPT-07 — Metaheurística "mejor resultado posible"
**Descripción:** un modo de cálculo prolongado (minutos, no segundos) para envíos de alto valor donde vale la pena exprimir el último punto de utilización.
**Problema:** el modo greedy es rápido pero no garantiza el óptimo global.
**Beneficio usuario:** mejor utilización cuando el tiempo no es la restricción.
**Beneficio comercial:** diferenciador de calidad de algoritmo frente a herramientas puramente greedy.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Importante | Alto (en envíos de alto valor) | Medio-alto | Alto | Alto — algoritmia no trivial (recocido simulado / genético) | OPT-05 | 1.2 | No iniciado |

**Criterios de aceptación:** El usuario puede lanzar un cálculo "overnight" y recibir un resultado con mayor utilización que el modo óptimo estándar.

**Caso de uso:** *Usuarios:* planificador de un envío de electrónica de alto valor. *Ejemplo:* se lanza el cálculo al final del día y el resultado mejorado está listo a la mañana siguiente.

---

#### OPT-08 — Formas irregulares / no ortogonales *(ficha reducida — Futuro)*
Empaquetado real de piezas no rectangulares (maquinaria, muebles). Valor medio-alto en nichos específicos, dificultad muy alta, versión `2.0`. No debe demorar nada de lo anterior.

---

#### OPT-09 — Orientación obligatoria generalizada
**Descripción:** extender la regla ya existente para extintores ("debe ir siempre horizontal/vertical") a cualquier producto marcado como de orientación fija (líquidos, equipos sensibles).
**Problema:** hoy esa regla es específica de un tipo de producto; cualquier otro caso similar no tiene forma de expresarse.
**Beneficio usuario:** una casilla más en la ficha de producto, no una regla nueva que aprender.
**Beneficio comercial:** bajo esfuerzo, alcance amplio — buena relación costo/beneficio de venta.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Muy importante | Alto | Alto | Bajo-medio | Bajo — reutiliza un patrón ya probado en producción | Ninguna | 1.0 | No iniciado |

**Criterios de aceptación:** El usuario puede marcar cualquier producto como "orientación fija" y el sistema debe respetarla igual que hace hoy con extintores.

**Caso de uso:** *Usuarios:* distribuidor de líquidos envasados. *Ejemplo:* se marca un tambor de líquido como "siempre vertical" sin que sea un extintor.

---

#### OPT-10 — Separación mínima obligatoria entre productos
**Descripción:** permitir declarar que dos productos no solo no deben apilarse, sino no deben quedar adyacentes.
**Problema:** hoy la única relación modelada es apilamiento; la adyacencia no se controla.
**Beneficio usuario:** cumple reglas de contaminación cruzada / seguridad más finas.
**Beneficio comercial:** nicho (alimentos, químicos), pero elimina una objeción puntual de compra.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Importante | Medio | Medio | Medio | Medio — añade una dimensión nueva a la evaluación de candidatos | OPT-06 | 1.2 | No iniciado |

**Criterios de aceptación:** El sistema debe impedir colocar dos productos declarados "no adyacentes" en contacto directo.

**Caso de uso:** *Usuarios:* fábrica de alimentos. *Ejemplo:* un producto con olor fuerte no puede quedar junto a uno absorbente, aunque ninguno esté apilado sobre el otro.

---

#### OPT-11 — Índice espacial para colisión/soporte (postergado, sin ADR)
**Descripción:** eliminar de raíz el cuello de botella real del motor —comprobaciones de
colisión (`geometry/collision.py::boxes_overlap`) y de soporte
(`geometry/support.py::horizontal_overlap_area_cm2`,
`rules/stacking_rules.py::find_direct_supporting_placements`)— mediante
una estructura de datos espacial (p. ej. una rejilla/hash espacial)
dentro de `rules`/`geometry` que descarte, antes de comparar
geometría, los `existing_placements` que no pueden compartir altura ni
solape horizontal con el candidato evaluado. Es la continuación
concreta, con evidencia nueva, de la parte de OPT-02 que ya se marcó
"pendiente" ("el índice espacial real... sigue pendiente" — ver tabla
de OPT-02, arriba).
**Problema que resuelve:** con cantidades grandes de bultos pequeños
que llenan o desbordan el espacio de carga, el tiempo de cálculo deja
de ser aceptable — no por un límite de volumen o peso, sino porque el
propio algoritmo se vuelve impracticablemente lento antes de terminar.
**Beneficio usuario:** poder cargar volúmenes reales grandes (miles de
bultos) sin que la optimización parezca "colgada".
**Beneficio comercial:** sin esto, OPT-01 (multi-espacio) y cualquier
caso de uso con volumen real de cliente mediano/grande quedan, en la
práctica, inutilizables — mismo argumento ya registrado en OPT-02.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Postergado | Muy alto | Muy alto | Alto | **Alto** — una implementación incorrecta puede introducir un falso negativo de colisión o de soporte, silencioso y grave (una caja "válida" que en realidad se solapa o no está soportada); exige verificación por equivalencia exhaustiva contra el comportamiento actual, no solo pruebas de humo | Profundiza OPT-02 | Sin asignar | **Investigado, sin ADR, sin código** — ver `docs/OptimizerPerformance.md`, sección "OPT-03 → OPT-11 (2026-07-17)", para las métricas completas |

**Hallazgo que motiva este ítem (2026-07-17):** perfilado real
(`cProfile`) del escenario reportado por el usuario (caja 20×20×50 cm,
peso 9 kg, contenedor 20', apilamiento hasta 30 niveles), reducido a
300 unidades (todas caben, sin desbordar) para que el perfilado fuera
completable en esta sesión:

| función | llamadas | tiempo propio (tottime) |
|---|---:|---:|
| `geometry/collision.py::boxes_overlap` | 54 529 308 | 566.588 s |
| `rules/stacking_rules.py::find_direct_supporting_placements` | 634 806 | 105.133 s |
| `geometry/support.py::horizontal_overlap_area_cm2` | 35 499 546 | 79.593 s |
| `geometry/box.py::overlaps` | 54 529 308 | 58.037 s |

Tiempo total instrumentado: **1262.476 s** (~21 min) para solo 300
instancias, sin desbordar el contenedor — confirma, con datos nuevos,
el mismo diagnóstico ya documentado en `docs/OptimizerPerformance.md`
(fases 4.2 y OPT-02): el costo dominante vive en comprobaciones O(n)
de colisión/soporte contra **todos** los `existing_placements`, y
crece de forma no lineal a medida que se acumulan más cajas colocadas.
El caso original reportado (1300 unidades del mismo bulto, solo 148
colocadas al cancelar tras ~15 s) **no es un bug de la interfaz ni del
hilo de optimización**: es el mismo crecimiento no lineal, aplicado a
un escenario donde la mayoría de las 1300 unidades termina sin caber.

**Por qué queda postergado, explícitamente, sin ADR todavía:**
1. Toca `rules`/`geometry`, las capas más protegidas del proyecto
   (`CLAUDE.md`: "Detente únicamente si... debes modificar reglas...
   debes cambiar semántica geométrica").
2. El riesgo de un falso negativo de colisión/soporte es real y grave
   — un resultado "válido" que en la práctica no lo es, en un dominio
   donde eso significa cargas mal calculadas fuera del software.
3. `stacking_rules.evaluate_supported_weight` necesita conocer, para
   cada soporte transitivo, todo lo que descansa sobre él en
   cualquier parte del layout — filtrar `existing_placements` por
   proximidad espacial antes de pasarlo a `rules` ya se evaluó y
   se descartó en la fase 4.2 por producir resultados incorrectos de
   peso soportado; cualquier índice espacial nuevo debe resolver esto
   sin romper esa garantía, lo cual no es trivial.
4. Decisión explícita del arquitecto del proyecto (2026-07-17): cerrar
   la investigación con la evidencia ya reunida, sin implementar nada
   todavía y sin redactar el ADR todavía, para volver de lleno al
   desarrollo funcional de la Beta 1.0.

**Criterios de aceptación (cuando se retome, no antes):**
- Un ADR explícito que documente la estructura de datos elegida y,
  sobre todo, cómo preserva la garantía de soporte transitivo completo.
- Pruebas de equivalencia exhaustivas (mismo patrón que
  `tests/rules/test_performance_cache_equivalence.py` de OPT-02):
  mismo `RuleEvaluation`/`PackingResult`, con y sin el índice, sobre
  varios escenarios de referencia — no solo que "no falle", sino que
  produzca exactamente el mismo resultado.
- El sistema debe optimizar un envío de 500+ bultos en menos de 10
  segundos en hardware estándar (mismo criterio ya fijado en OPT-02).

**Caso de uso:** *Usuarios:* cualquier operador que cargue una
cantidad grande de bultos pequeños relativos al espacio de carga.
*Ejemplo:* 1300 cajas de 20×20×50 cm en un contenedor de 20 pies — hoy
el cálculo no termina en un tiempo práctico; con el índice espacial,
debería completarse en segundos, con exactamente el mismo resultado
que produce hoy el algoritmo (mismas cajas colocadas, mismas
rechazadas, mismas razones).

---

### EPIC 2 — Planificación Logística (LOG)

#### LOG-01 — Empaquetado en dos niveles (armado de pallets + carga del espacio)
**Descripción:** un primer paso de optimización que arma pallets a partir de cajas sueltas, y un segundo paso que carga esos pallets (o cajas restantes) en el espacio final.
**Problema:** muchas operaciones reales arman pallets antes de cargar el camión; hoy el motor solo resuelve un nivel.
**Beneficio usuario:** refleja el proceso físico real de su bodega.
**Beneficio comercial:** abre el vertical de distribución/FMCG completo.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Muy importante | Alto | Alto | Media-alta | Medio — es un segundo motor de optimización anidado, con su propia geometría | OPT-01 | 1.1 | No iniciado |

**Criterios de aceptación:** El usuario puede pedir "arma pallets primero" y el sistema debe producir un plan de dos niveles (pallets, y pallets dentro del espacio).

**Caso de uso:** *Usuarios:* operador de un centro de distribución FMCG. *Ejemplo:* 300 cajas sueltas se agrupan en 12 pallets estándar antes de cargarlos al camión.

---

#### LOG-02 — Carga parcial priorizada por valor de negocio
**Descripción:** cuando no todo cabe, decidir qué se deja fuera según una prioridad de negocio explícita (valor, urgencia, cliente), no por orden de llegada.
**Problema:** hoy lo que no carga es simplemente lo último que el motor intentó colocar.
**Beneficio usuario:** control real sobre qué se sacrifica cuando hay que sacrificar algo.
**Beneficio comercial:** convierte una limitación en una herramienta de decisión.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Muy importante | Alto | Alto | Media | Bajo-medio — es un criterio de orden adicional sobre el motor existente | Ninguna | 1.1 | No iniciado |

**Criterios de aceptación:** El usuario puede asignar una prioridad a cada producto o pedido; el sistema debe preferir dejar fuera lo de menor prioridad cuando no todo cabe.

**Caso de uso:** *Usuarios:* planificador con pedidos de varios clientes en un mismo contenedor. *Ejemplo:* si algo debe quedarse fuera, se deja el pedido del cliente de menor prioridad contractual, no el que casualmente se intentó cargar al final.

---

#### LOG-03 — Secuencia de descarga multi-parada (LIFO real)
**Descripción:** cuando el vehículo visita varias paradas, ordenar la carga para que lo del último cliente en recibir quede al fondo y lo del primero quede junto a la puerta.
**Problema:** hoy el orden de carga es solo el orden de armado del algoritmo, no el orden de una ruta de reparto.
**Beneficio usuario:** el camión se descarga en el orden correcto sin mover nada de más en cada parada.
**Beneficio comercial:** crítico para última milla y distribución multi-tienda — un vertical completo depende de esto.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Crítico | Muy alto | Muy alto | Alta | Alto — es una dimensión de secuenciación nueva, no solo un criterio de orden | OPT-01 (sin múltiples destinos no hay ruta que secuenciar) | 1.1 | No iniciado |

**Criterios de aceptación:** El usuario puede declarar el orden de las paradas de un reparto; el sistema debe generar un plan donde la carga de la última parada quede más lejos de la puerta que la de la primera.

**Caso de uso:** *Usuarios:* transportista de reparto multi-tienda. *Ejemplo:* un camión visita 4 tiendas; el plan de carga garantiza que en cada parada se descarga exactamente lo de esa tienda sin mover el resto.

---

#### LOG-04 — Reglas de negocio propias sin programar
**Descripción:** un sistema de reglas configurables por el usuario final ("nunca apilar A sobre B", "máximo 2 pallets de este cliente por contenedor") sin tocar código.
**Problema:** hoy las reglas de negocio (extintores, fragilidad, apilamiento) están fijas en el motor; un cliente con reglas propias no tiene forma de expresarlas.
**Beneficio usuario:** el sistema se adapta a su operación, no al revés.
**Beneficio comercial:** el diferenciador más defendible frente a competidores de reglas rígidas — sube el costo de cambio una vez adoptado.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Crítico | Muy alto | Muy alto | Alta | Alto — exige un motor de reglas extensible sin comprometer el determinismo del optimizador | Ninguna, pero compite en prioridad con OPT-01/02/03 | 1.1 | No iniciado |

**Criterios de aceptación:** El usuario puede crear una regla propia desde la interfaz; el sistema debe aplicarla en la siguiente optimización sin intervención técnica.

**Caso de uso:** *Usuarios:* gerente de operaciones de un cliente con reglas de mezcla propias. *Ejemplo:* se configura "nunca más de 2 pallets del cliente X por contenedor" sin abrir un ticket de soporte.

---

#### LOG-05 — Sugerencia automática de espacio óptimo
**Descripción:** el sistema recomienda el tipo de contenedor/camión más adecuado según el pedido, en vez de que el usuario lo elija a ciegas.
**Problema:** hoy el usuario adivina qué espacio probar primero.
**Beneficio usuario:** menos iteraciones manuales para llegar a la mejor opción.
**Beneficio comercial:** refuerza la percepción de "asesor", no solo "calculadora".

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Muy importante | Alto | Alto | Media | Medio | OPT-01 | 1.2 | No iniciado |

**Criterios de aceptación:** El sistema debe proponer un tipo de espacio antes de que el usuario elija uno manualmente, basado en el volumen/peso del pedido.

**Caso de uso:** *Usuarios:* planificador nuevo, sin experiencia en tipos de contenedor. *Ejemplo:* el sistema sugiere "contenedor 40' HC" en vez de dejar que pruebe con uno de 20'.

---

#### LOG-06 — Zonas de temperatura dentro de un mismo espacio *(ficha reducida — Futuro)*
Compartimentos de temperatura dentro de un mismo Loading Space (reefer). Alto valor en el nicho de alimentos/farma, dificultad alta, versión `2.0`. Depende de validar antes ese vertical con ventas reales.

---

#### LOG-07 — Datos de aduana en el packing list
**Descripción:** asociar código arancelario y país de origen a cada producto, y que aparezcan en el packing list exportado.
**Problema:** exportadores hoy llevan esos datos en un documento separado del plan de carga.
**Beneficio usuario:** un solo documento sirve para carga y para aduana.
**Beneficio comercial:** relevante para el segmento exportador puro.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Importante | Alto (exportadores) | Medio-alto | Media | Bajo — es una extensión de datos, no de algoritmo | Ninguna | 1.2 | No iniciado |

**Criterios de aceptación:** El usuario puede añadir código arancelario y país de origen a un producto; el informe muestra esos datos en el packing list.

**Caso de uso:** *Usuarios:* exportador. *Ejemplo:* el packing list adjunto a la factura de exportación ya trae los códigos arancelarios sin copiarlos a mano.

---

#### LOG-08 — Comparación de escenarios lado a lado
**Descripción:** ejecutar 2-3 configuraciones distintas del mismo pedido y compararlas en una sola vista.
**Problema:** hoy comparar alternativas exige repetir el proceso completo y recordar los números.
**Beneficio usuario:** decisión informada en minutos, no repitiendo el proceso manualmente.
**Beneficio comercial:** valor percibido de herramienta analítica, no solo calculadora.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Importante | Alto | Medio-alto | Media | Bajo-medio | Ninguna | 1.1 | No iniciado |

**Criterios de aceptación:** El usuario puede guardar dos o más resultados de optimización y verlos en una tabla comparativa (utilización, peso, unidades no cargadas).

**Caso de uso:** *Usuarios:* planificador evaluando contenedor de 20' vs. 40'. *Ejemplo:* compara ambos resultados uno junto al otro antes de decidir cuál reservar.

---

### EPIC 3 — Visualización y Ejecución en Bodega (VIS)

#### VIS-01 — Animación de secuencia de carga
**Descripción:** reproducir visualmente el orden de carga, caja por caja, en el visor 3D.
**Problema:** hoy el visor muestra el resultado final, no el proceso de cómo llegar a él.
**Beneficio usuario:** entrenamiento visual directo para el personal de bodega.
**Beneficio comercial:** demo muy vistosa, alto efecto en ventas.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Muy importante | Alto | Alto | Media | Bajo — el orden ya existe como dato (`sequence_number`), falta solo la reproducción visual | Ninguna | 1.2 | No iniciado |

**Criterios de aceptación:** El usuario puede reproducir, pausar y avanzar la animación de carga caja por caja.

**Caso de uso:** *Usuarios:* supervisor de bodega capacitando a un nuevo operario. *Ejemplo:* se reproduce la animación en una pantalla antes de empezar la carga física.

---

#### VIS-02 — Etiquetas permanentes en el visor
**Descripción:** mostrar SKU y orden de carga sobre cada caja de forma constante, no solo al seleccionarla.
**Problema:** hoy hay que hacer clic caja por caja para identificar qué es cada una.
**Beneficio usuario:** lectura del plan de un vistazo.
**Beneficio comercial:** bajo esfuerzo, mejora de percepción inmediata en cualquier demo.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Importante | Alto | Medio | Baja-media | Bajo | Ninguna | 1.0 | No iniciado |

**Criterios de aceptación:** El usuario puede activar etiquetas visibles de forma permanente sobre cada caja del visor.

**Caso de uso:** *Usuarios:* cualquier planificador revisando el resultado. *Ejemplo:* identifica el SKU de cada caja sin tener que hacer clic una por una.

---

#### VIS-03 — Filtros y vistas predefinidas del visor
**Descripción:** filtrar por SKU o capa, y saltar a vistas de cámara predefinidas (frontal, superior, isométrica).
**Problema:** hoy solo hay una cámara libre, sin atajos.
**Beneficio usuario:** inspección más rápida de casos específicos.
**Beneficio comercial:** madurez percibida del visor 3D.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Importante | Medio-alto | Medio | Media | Bajo | Ninguna | 1.1 | No iniciado |

**Criterios de aceptación:** El usuario puede filtrar la vista por SKU y cambiar a una vista predefinida con un clic.

**Caso de uso:** *Usuarios:* planificador verificando dónde quedó un producto específico. *Ejemplo:* filtra por SKU y ve solo esas cajas resaltadas en el espacio.

---

#### VIS-04 — Escaneo de código de barras / QR
**Descripción:** dar de alta productos escaneando en vez de tecleando, con cámara o lector USB.
**Problema:** la carga manual de productos es lenta y propensa a error de tecleo.
**Beneficio usuario:** velocidad y precisión en la captura de datos.
**Beneficio comercial:** elimina el punto de dolor más citado por operadores de bodega.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Muy importante | Muy alto | Alto | Media | Medio — integración de hardware de captura | Ninguna | 1.1 | No iniciado |

**Criterios de aceptación:** El usuario puede escanear un código y el sistema debe rellenar automáticamente el producto correspondiente del catálogo.

**Caso de uso:** *Usuarios:* operario de bodega dando de alta un pedido. *Ejemplo:* escanea 40 cajas en el tiempo que antes tomaba teclear 5.

---

#### VIS-05 — Realidad aumentada en bodega *(ficha reducida — Futuro)*
Vista en tablet superpuesta a la carga física real. Diferenciador fuerte a largo plazo, dificultad muy alta, versión `2.0`.

---

### EPIC 4 — Experiencia de Usuario (UX)

#### UX-01 — Internacionalización end-to-end
**Descripción:** extraer todo el texto orientado al usuario (interfaz, informes, plantillas de Excel) a un sistema de idiomas real, empezando por español e inglés.
**Problema:** hoy hay texto en español embebido directamente en varias capas del sistema.
**Beneficio usuario:** el software habla el idioma del cliente.
**Beneficio comercial:** literalmente bloquea la frase "comercializarlo internacionalmente" mientras no exista.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Crítico | Muy alto | Muy alto | Media-alta | Medio — es transversal a muchas capas, riesgo de omisiones más que de dificultad técnica | Ninguna | 1.0 | No iniciado |

**Criterios de aceptación:** El usuario puede cambiar el idioma de la interfaz; los informes generados deben respetar ese idioma.

**Caso de uso:** *Usuarios:* cliente angloparlante. *Ejemplo:* instala la aplicación y la usa por completo en inglés, informes incluidos.

---

#### UX-02 — Deshacer / rehacer
**Descripción:** historial de acciones reversible en el editor de proyecto.
**Problema:** cualquier error de edición hoy exige rehacer manualmente.
**Beneficio usuario:** confianza para experimentar sin miedo a romper el trabajo.
**Beneficio comercial:** ausencia notable en cualquier evaluación de un software de escritorio "serio".

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Crítico | Alto | Alto | Baja-media | Bajo | Ninguna | 1.0 | No iniciado |

**Criterios de aceptación:** El usuario puede deshacer y rehacer cualquier edición de espacio o producto con Ctrl+Z / Ctrl+Y.

**Caso de uso:** *Usuarios:* cualquier usuario editando un proyecto. *Ejemplo:* borra un producto por error y lo recupera con un atajo, sin volver a teclearlo.

---

#### UX-03 — Autoguardado y recuperación de sesión
**Descripción:** guardar el estado del proyecto periódicamente y ofrecer recuperarlo tras un cierre inesperado.
**Problema:** un cierre inesperado hoy puede perder todo el trabajo no guardado.
**Beneficio usuario:** tranquilidad frente a fallos de energía o de sistema.
**Beneficio comercial:** reduce quejas de soporte del peor tipo posible.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Importante | Alto | Medio | Baja | Bajo | Ninguna | 1.0 | No iniciado |

**Criterios de aceptación:** El sistema debe ofrecer recuperar el último estado autoguardado al reabrir tras un cierre inesperado.

**Caso de uso:** *Usuarios:* cualquier usuario. *Ejemplo:* un corte de energía no le cuesta 30 minutos de trabajo rehecho.

---

#### UX-04 — Plantillas de proyecto por vertical
**Descripción:** proyectos de ejemplo listos para usar según el tipo de operación (contenedor marítimo, camión nacional, van de última milla).
**Problema:** hoy cada proyecto empieza desde cero.
**Beneficio usuario:** menos fricción para llegar al primer resultado útil.
**Beneficio comercial:** mejora directa de la tasa de conversión de trial.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Muy importante | Alto | Alto | Baja | Bajo — reutiliza infraestructura de perfiles ya existente | Ninguna | 1.0 | No iniciado |

**Criterios de aceptación:** El usuario puede crear un proyecto nuevo eligiendo una plantilla por vertical en vez de un formulario en blanco.

**Caso de uso:** *Usuarios:* usuario nuevo en su primera sesión. *Ejemplo:* elige "camión nacional" y ya tiene un espacio y productos de ejemplo cargados para explorar.

---

#### UX-05 — Asistente de primer proyecto
**Descripción:** flujo guiado de 3 pasos (espacio → productos → optimizar) para el primer uso, sin exponer la ventana completa de una vez.
**Problema:** la interfaz completa puede intimidar a un usuario que la ve por primera vez.
**Beneficio usuario:** curva de aprendizaje más corta.
**Beneficio comercial:** determina cuántos trials llegan a ver un resultado real.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Importante | Alto | Alto | Media | Bajo | UX-04 | 1.0 | No iniciado |

**Criterios de aceptación:** El usuario puede completar su primer proyecto siguiendo un asistente paso a paso, sin ver los paneles avanzados hasta terminarlo.

**Caso de uso:** *Usuarios:* evaluador de una prueba gratuita. *Ejemplo:* llega a un resultado de optimización en menos de 5 minutos desde la instalación.

---

#### UX-06 — Edición rápida de perfil sin desbloqueo total
**Descripción:** permitir un ajuste puntual sobre un perfil de espacio "de catálogo" sin tener que pasarlo a "Personalizado" por completo.
**Problema:** hoy el formulario se bloquea salvo que el perfil sea "Personalizado", lo cual frustra a usuarios avanzados que solo quieren un ajuste menor.
**Beneficio usuario:** menos pasos para un cambio pequeño.
**Beneficio comercial:** reduce fricción sin renunciar a la protección contra ediciones accidentales.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Importante | Medio | Medio | Baja | Bajo | Ninguna | 1.1 | No iniciado |

**Criterios de aceptación:** El usuario puede sobrescribir un único campo de un perfil sin perder la protección del resto de campos.

**Caso de uso:** *Usuarios:* planificador experimentado. *Ejemplo:* ajusta solo el peso máximo de un perfil estándar sin tener que reconstruirlo como personalizado.

---

#### UX-07 — Autocompletado de SKU
**Descripción:** sugerir productos del catálogo mientras se escribe el SKU.
**Problema:** hoy hay que conocer o buscar el SKU exacto.
**Beneficio usuario:** carga de datos más rápida y con menos errores.
**Beneficio comercial:** bajo esfuerzo, mejora diaria constante.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Importante | Medio-alto | Medio | Baja | Bajo | Ninguna | 1.0 | No iniciado |

**Criterios de aceptación:** El sistema debe sugerir coincidencias del catálogo mientras el usuario escribe un SKU.

**Caso de uso:** *Usuarios:* cualquier usuario cargando productos. *Ejemplo:* escribe 3 caracteres y elige de una lista en vez de recordar el código completo.

---

#### UX-08 — Pegar tabla desde Excel directamente
**Descripción:** pegar una selección copiada de Excel directamente en la grilla de productos, sin pasar por un diálogo de importación.
**Problema:** hoy toda importación de Excel pasa por un flujo de archivo, aunque el usuario solo quiera pegar 5 filas.
**Beneficio usuario:** carga rapidísima para cambios pequeños.
**Beneficio comercial:** productividad diaria percibida.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Importante | Alto | Medio | Baja-media | Bajo | Ninguna | 1.1 | No iniciado |

**Criterios de aceptación:** El usuario puede pegar una tabla copiada de Excel en la grilla de productos y el sistema debe interpretarla sin abrir un diálogo de archivo.

**Caso de uso:** *Usuarios:* planificador ajustando un pedido. *Ejemplo:* copia 6 filas de un correo con Excel adjunto y las pega directo en la tabla de productos.

---

### EPIC 5 — Catálogo y Productividad (DAT)

#### DAT-01 — Plantillas de carga por cliente recurrente
**Descripción:** guardar la mezcla de productos habitual de un cliente para reutilizarla en el próximo pedido.
**Problema:** pedidos recurrentes se recrean desde cero cada vez.
**Beneficio usuario:** el segundo pedido de un cliente habitual toma minutos, no lo mismo que el primero.
**Beneficio comercial:** reutiliza infraestructura de catálogo ya construida — esfuerzo bajo, alto valor percibido.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Muy importante | Alto | Alto | Baja | Bajo | Ninguna | 1.1 | No iniciado |

**Criterios de aceptación:** El usuario puede guardar una combinación de productos como plantilla asociada a un cliente y reutilizarla en un nuevo proyecto.

**Caso de uso:** *Usuarios:* planificador con clientes recurrentes. *Ejemplo:* el pedido semanal del mismo cliente se carga en un clic.

---

#### DAT-02 — Cola de optimización por lotes
**Descripción:** encolar varios proyectos guardados para optimizarlos uno tras otro sin supervisión, por ejemplo durante la noche.
**Problema:** operaciones grandes con muchos envíos diarios optimizan uno por uno de forma manual.
**Beneficio usuario:** libera tiempo del planificador para tareas de mayor valor.
**Beneficio comercial:** relevante para operaciones de volumen alto.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Importante | Alto (volumen alto) | Medio-alto | Media | Bajo-medio | OPT-02 | 1.2 | No iniciado |

**Criterios de aceptación:** El usuario puede encolar varios proyectos y el sistema debe procesarlos en secuencia sin intervención.

**Caso de uso:** *Usuarios:* operación con 20+ envíos diarios. *Ejemplo:* se encolan todos los pedidos del día al cierre y los resultados están listos a la mañana siguiente.

---

#### DAT-03 — Botón de recalcular prominente
**Descripción:** cuando el resultado queda obsoleto por un cambio en el proyecto, ofrecer un botón visible de "recalcular ahora" en vez de solo un aviso pasivo.
**Problema:** hoy el aviso de resultado obsoleto es fácil de pasar por alto.
**Beneficio usuario:** una acción clara en vez de un mensaje que hay que interpretar.
**Beneficio comercial:** esfuerzo trivial, corrige una fricción ya diagnosticada.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Importante | Medio | Medio | Muy baja | Muy bajo | Ninguna | 1.0 | No iniciado |

**Criterios de aceptación:** El sistema debe mostrar un botón de acción directa para recalcular cuando el resultado quede marcado como obsoleto.

**Caso de uso:** *Usuarios:* cualquier usuario que edita el proyecto tras optimizar. *Ejemplo:* cambia una cantidad y recalcula con un clic en vez de buscar el menú de optimización de nuevo.

---

#### DAT-04 — Recalculo incremental
**Descripción:** cuando cambia un solo producto, recalcular solo lo necesario en vez de todo el layout desde cero.
**Problema:** hoy cualquier cambio dispara un recálculo completo, sin importar cuán pequeño sea el cambio.
**Beneficio usuario:** respuesta casi instantánea a cambios menores.
**Beneficio comercial:** mejora de percepción de velocidad en el uso diario.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Importante | Alto | Medio-alto | Alta | Alto — exige repensar el estado interno del motor para soportar recalculo parcial | OPT-02 | 1.2 | No iniciado |

**Criterios de aceptación:** El sistema debe recalcular en menos de 2 segundos cuando el cambio afecta a un solo producto de un layout ya calculado.

**Caso de uso:** *Usuarios:* planificador ajustando cantidades. *Ejemplo:* sube la cantidad de un SKU y ve el nuevo resultado casi al instante, sin esperar el cálculo completo de nuevo.

---

### EPIC 6 — Reportes e Inteligencia (REP)

#### REP-01 — Instructivo de carga paso a paso
**Descripción:** un informe con imágenes secuenciales del proceso de carga, no solo una tabla de posiciones.
**Problema:** una tabla de coordenadas no es instrucción operativa para quien carga físicamente.
**Beneficio usuario:** instrucciones que un operario puede seguir sin interpretar datos técnicos.
**Beneficio comercial:** cierra el círculo entre planificar y ejecutar — muy valorado en bodega.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Muy importante | Muy alto | Alto | Media | Bajo-medio — el motor de informes PDF ya existe, es una plantilla nueva | VIS-01 (comparte la fuente de imágenes por paso) | 1.2 | No iniciado |

**Criterios de aceptación:** El informe muestra una secuencia de imágenes o diagramas, uno por paso de carga, con instrucciones en texto simple.

**Caso de uso:** *Usuarios:* operario de bodega. *Ejemplo:* sigue el instructivo impreso paso a paso mientras carga el camión, sin necesitar al planificador presente.

---

#### REP-02 — Recomendaciones proactivas de mejora
**Descripción:** tras calcular un resultado, sugerir ajustes concretos ("si mueves 3 unidades a otro espacio, ahorras 8%").
**Problema:** hoy el sistema entrega un resultado, pero no sugiere cómo mejorarlo.
**Beneficio usuario:** valor añadido más allá del cálculo — se siente como un asesor.
**Beneficio comercial:** el argumento de "inteligencia" real frente a un bin-packing genérico.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Muy importante | Muy alto | Alto | Alta | Alto — requiere explorar variantes del resultado y compararlas | OPT-05 | 1.2 | No iniciado |

**Criterios de aceptación:** El sistema debe ofrecer al menos una sugerencia concreta y cuantificada de mejora tras cada optimización, cuando exista una.

**Caso de uso:** *Usuarios:* planificador buscando exprimir la utilización. *Ejemplo:* recibe la sugerencia "reubicando 2 pallets ahorras un contenedor completo" antes de confirmar el plan.

---

#### REP-03 — Explicación accionable de por qué algo no cargó
**Descripción:** enriquecer el motivo de no-carga ya existente con una sugerencia concreta ("cabría si giras la caja" o "con un espacio 10 cm más largo").
**Problema:** hoy se sabe *que* algo no cargó y por qué en términos técnicos, pero no *qué hacer* al respecto.
**Beneficio usuario:** convierte un dato técnico en una decisión accionable.
**Beneficio comercial:** esfuerzo medio, aprovecha datos que ya existen en el sistema.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Muy importante | Alto | Alto | Media-alta | Medio | Ninguna (reutiliza `UnpackedReason` ya existente) | 1.1 | No iniciado |

**Criterios de aceptación:** El informe muestra, para cada producto no cargado, al menos una acción sugerida cuando el sistema pueda inferirla.

**Caso de uso:** *Usuarios:* planificador con productos que no cupieron. *Ejemplo:* ve "esta caja cabría si se gira 90°" en vez de solo "no cupo por espacio insuficiente".

---

#### REP-04 — Aprendizaje de patrones históricos *(ficha reducida — Futuro)*
Sugerir configuraciones que funcionaron bien en cargas pasadas similares. Alto valor a mediano plazo, dificultad alta, versión `2.0` — depende de tener suficiente historial real acumulado primero.

---

#### REP-05 — Plantillas de informe personalizables
**Descripción:** permitir activar/desactivar y reordenar secciones de un informe sin programar.
**Problema:** hoy los cinco tipos de informe son fijos; un cliente con necesidades propias no puede ajustarlos.
**Beneficio usuario:** el informe se adapta a su formato interno, no al revés.
**Beneficio comercial:** ya existe un diseño conceptual previo — el esfuerzo real es menor de lo que aparenta.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Importante | Alto | Medio-alto | Media | Bajo — el sistema de secciones ya está diseñado para esto | Ninguna | 1.1 | No iniciado |

**Criterios de aceptación:** El usuario puede crear una plantilla de informe propia eligiendo qué secciones incluir y en qué orden.

**Caso de uso:** *Usuarios:* cliente con su propio formato de informe interno. *Ejemplo:* arma una plantilla que omite el apéndice técnico y antepone los datos del cliente.

---

#### REP-06 — Informe comparativo multi-escenario
**Descripción:** un único PDF que compara dos o más resultados de optimización.
**Problema:** hoy comparar dos escenarios exige dos informes separados.
**Beneficio usuario:** un solo documento para presentar una decisión.
**Beneficio comercial:** complementa LOG-08 (comparación en pantalla) con una versión imprimible/enviable.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Importante | Medio-alto | Medio | Media | Bajo | LOG-08 | 1.2 | No iniciado |

**Criterios de aceptación:** El informe muestra dos o más escenarios lado a lado con sus métricas principales.

**Caso de uso:** *Usuarios:* planificador presentando una decisión a un gerente. *Ejemplo:* envía un PDF comparando contenedor de 20' vs. 40' en vez de dos archivos separados.

---

#### REP-07 — Panel de analítica del historial
**Descripción:** exponer como pantalla el historial de ejecuciones ya registrado (tendencia de utilización en el tiempo, ejecuciones por período).
**Problema:** el dato ya se guarda, pero no hay dónde verlo salvo consultarlo manualmente.
**Beneficio usuario:** visibilidad de la mejora (o no) de la operación en el tiempo.
**Beneficio comercial:** esfuerzo bajo (el dato existe), refuerzo de valor sostenido tras la venta inicial.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Importante | Alto | Medio-alto | Media | Bajo — el dato ya existe, falta la interfaz | Ninguna | 1.1 | No iniciado |

**Criterios de aceptación:** El usuario puede ver un gráfico de utilización promedio por semana/mes sobre su historial de optimizaciones.

**Caso de uso:** *Usuarios:* gerente de operaciones. *Ejemplo:* revisa si la utilización promedio mejoró tras adoptar el sistema.

---

### EPIC 7 — Integraciones y Plataforma (INT)

#### INT-01 — API REST pública
**Descripción:** exponer las capacidades de optimización, importación y reportes como una API que otros sistemas puedan invocar.
**Problema:** hoy el producto es una aplicación aislada; nada externo puede hablar con él sin intervención manual.
**Beneficio usuario:** integrarlo con su propio flujo de trabajo, no al revés.
**Beneficio comercial:** decide si el producto es una app aislada o una plataforma — puerta de entrada a todo lo demás de este EPIC.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Crítico | Muy alto | Muy alto | Alta | Alto — primera superficie pública del sistema, exige diseño cuidadoso de contrato y seguridad | COM-01 | 1.1 | No iniciado |

**Criterios de aceptación:** Un sistema externo puede enviar un pedido y recibir un plan de carga de vuelta sin usar la interfaz gráfica.

**Caso de uso:** *Usuarios:* equipo de TI de un cliente integrando su ERP. *Ejemplo:* el ERP envía el pedido automáticamente al cerrarse una venta y recibe el plan de carga en la respuesta.

---

#### INT-02 — Explotación comercial del SDK ya existente
**Descripción:** empaquetar y promover comercialmente el motor de optimización, que ya es utilizable como librería independiente, como oferta para integrarlo dentro del software de un tercero.
**Problema:** el activo ya existe técnicamente y no figura en ninguna conversación comercial.
**Beneficio usuario (del socio B2B2B):** motor de cubicaje de nivel profesional sin construir uno propio.
**Beneficio comercial:** canal de ingresos nuevo con desarrollo adicional prácticamente nulo.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Muy importante | Muy alto | Muy alto | Baja | Muy bajo — es trabajo comercial y de empaquetado, no de desarrollo | Ninguna | 1.0 | No iniciado |

**Criterios de aceptación:** Existe material comercial y contractual para ofrecer el motor como componente embebido a un tercero.

**Caso de uso:** *Usuarios:* fabricante de contenedores o naviera con su propio software. *Ejemplo:* integra el motor de CargoOptimizer3D dentro de su portal de cotización, con su propia marca.

---

#### INT-03 — Conectores ERP directos
**Descripción:** integraciones nativas con ERPs habituales (SAP, Odoo, NetSuite, Dynamics), sin pasar por un archivo Excel intermedio.
**Problema:** hoy toda entrada de datos empresarial pasa por exportar/importar Excel manualmente.
**Beneficio usuario:** datos siempre sincronizados con el sistema de registro real.
**Beneficio comercial:** habilita la venta a mediana y gran empresa, donde el ERP es innegociable.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Muy importante | Muy alto | Muy alto | Alta | Alto — cada ERP exige su propio conector y mantenimiento continuo | INT-01 | 1.2 | No iniciado |

**Criterios de aceptación:** El sistema debe poder leer pedidos directamente desde al menos un ERP soportado, sin exportación manual intermedia.

**Caso de uso:** *Usuarios:* mediana empresa con SAP. *Ejemplo:* el pedido de venta en SAP dispara automáticamente un plan de carga.

---

#### INT-04 — Importación de formatos estándar de transporte (EDI/CSV)
**Descripción:** aceptar formatos de manifiesto habituales en la industria del transporte, como EDIFACT o CSV estandarizado.
**Problema:** freight forwarders reciben datos en estos formatos y hoy no hay forma directa de importarlos.
**Beneficio usuario:** una fuente de datos menos que convertir a mano.
**Beneficio comercial:** relevante específicamente para el segmento forwarder.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Importante | Alto (forwarders) | Medio-alto | Media | Medio | Ninguna | 1.2 | No iniciado |

**Criterios de aceptación:** El usuario puede importar un archivo EDI/CSV de manifiesto estándar y el sistema debe reconocer sus campos automáticamente.

**Caso de uso:** *Usuarios:* freight forwarder. *Ejemplo:* importa el manifiesto recibido de una naviera sin reformatearlo manualmente.

---

#### INT-05 — Exportación a WMS
**Descripción:** exportar el plan de carga en un formato que un sistema de gestión de almacén pueda ejecutar directamente.
**Problema:** hoy el plan queda en PDF/Excel, desconectado de la ejecución en el almacén.
**Beneficio usuario:** el plan se convierte en tareas ejecutables sin retrabajo.
**Beneficio comercial:** cierra el ciclo planificación-ejecución del lado del software, no solo del papel.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Muy importante | Alto | Alto | Media | Medio | INT-01 | 1.2 | No iniciado |

**Criterios de aceptación:** El sistema debe exportar el plan en un formato compatible con al menos un WMS de referencia.

**Caso de uso:** *Usuarios:* centro de distribución con WMS propio. *Ejemplo:* el plan de carga genera automáticamente las tareas de picking/carga en el WMS.

---

#### INT-06 — Exportación de etiquetas a formato de impresora industrial (ZPL)
**Descripción:** generar etiquetas de orden de carga imprimibles en impresoras térmicas industriales.
**Problema:** hoy no hay forma de imprimir etiquetas físicas asociadas al plan.
**Beneficio usuario:** identificación física de cada unidad en bodega.
**Beneficio comercial:** cierre operativo del flujo de bodega.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Importante | Alto (bodega) | Medio | Media | Bajo-medio | Ninguna | 1.2 | No iniciado |

**Criterios de aceptación:** El sistema debe generar un archivo de etiquetas en formato ZPL con SKU y orden de carga por unidad.

**Caso de uso:** *Usuarios:* operario de bodega. *Ejemplo:* imprime etiquetas con el orden de carga y las pega en cada pallet antes de cargar.

---

#### INT-07 — Webhooks (entrantes y salientes)
**Descripción:** disparar la optimización automáticamente al recibir un evento externo, y notificar a otro sistema cuando termina.
**Problema:** hoy toda ejecución requiere un usuario abriendo la aplicación.
**Beneficio usuario:** automatización de punta a punta sin intervención manual.
**Beneficio comercial:** requisito habitual en cualquier integración empresarial moderna.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Importante | Alto | Medio-alto | Media | Medio | INT-01 | 1.1 | No iniciado |

**Criterios de aceptación:** El sistema debe poder disparar una optimización al recibir un evento externo y notificar el resultado a una URL configurada.

**Caso de uso:** *Usuarios:* equipo de integración de un cliente. *Ejemplo:* al confirmarse un pedido en el ERP, el plan de carga llega automáticamente por correo o a otro sistema.

---

#### INT-08 — Inicio de sesión único (SSO/SAML) *(ficha reducida — Futuro)*
Requisito estándar de despliegue empresarial una vez exista acceso multiusuario en la nube. Depende de ADM-01. Versión `2.0`.

---

#### INT-09 — Exportación de modelo 3D abierto *(ficha reducida — Futuro)*
Exportar a glTF/OBJ para verlo sin instalar la aplicación. Valor medio, esfuerzo medio, versión `2.0` — no urgente frente a lo demás de este EPIC.

---

### EPIC 8 — Administración y Colaboración (ADM)

#### ADM-01 — Proyectos multiusuario en la nube
**Descripción:** mover el proyecto de un archivo local en una máquina a un espacio compartido accesible por varios usuarios.
**Problema:** hoy un proyecto vive en un archivo, en una máquina; un equipo no puede trabajarlo junto.
**Beneficio usuario:** varias personas planifican sobre el mismo proyecto sin enviarse archivos.
**Beneficio comercial:** decide si el producto se vende a una persona o a un departamento completo.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Crítico | Muy alto | Muy alto | Muy alta | Muy alto — exige backend, sincronización y resolución de conflictos; es un cambio de arquitectura, no una función más | COM-01 | 2.0 | No iniciado |

**Criterios de aceptación:** Dos usuarios distintos pueden abrir el mismo proyecto desde equipos distintos y ver los cambios del otro.

**Caso de uso:** *Usuarios:* equipo de planificación de un 3PL. *Ejemplo:* dos planificadores revisan y ajustan el mismo envío desde oficinas distintas el mismo día.

---

#### ADM-02 — Roles y permisos
**Descripción:** distinguir entre planificador, supervisor y usuario de solo lectura dentro de un mismo espacio de trabajo.
**Problema:** sin roles, cualquiera con acceso puede modificar cualquier cosa.
**Beneficio usuario:** control apropiado para cada función dentro del equipo.
**Beneficio comercial:** requisito habitual de compra en cuentas empresariales.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Muy importante | Alto | Alto | Media | Medio | ADM-01 | 2.0 | No iniciado |

**Criterios de aceptación:** El sistema debe restringir la edición según el rol asignado a cada usuario.

**Caso de uso:** *Usuarios:* supervisor y planificadores de un mismo equipo. *Ejemplo:* el supervisor aprueba cambios que un planificador junior solo puede proponer.

---

#### ADM-03 — Comentarios y flujo de aprobación
**Descripción:** permitir anotar un plan de carga y pasar por un ciclo de revisión antes de darlo por aprobado.
**Problema:** hoy la aprobación de un plan ocurre fuera del sistema (correo, verbal).
**Beneficio usuario:** trazabilidad de quién aprobó qué y cuándo.
**Beneficio comercial:** valor de auditoría para operaciones reguladas.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Importante | Alto | Medio-alto | Media | Medio | ADM-01 | 2.0 | No iniciado |

**Criterios de aceptación:** El usuario puede dejar un comentario sobre un plan de carga y marcarlo como aprobado o rechazado.

**Caso de uso:** *Usuarios:* cliente final aprobando el plan que le envía su forwarder. *Ejemplo:* revisa, comenta un ajuste y aprueba antes de que se ejecute la carga.

---

### EPIC 9 — Comercialización (COM)

#### COM-01 — Decisión de modelo de despliegue (desktop / SaaS / híbrido)
**Descripción:** definir explícitamente si el producto se vende como aplicación de escritorio, servicio en la nube, o ambos, antes de construir nada que dependa de esa decisión.
**Problema:** hoy la arquitectura es 100% de escritorio local; toda función de plataforma, API o colaboración depende de resolver esto primero.
**Beneficio usuario:** claridad sobre cómo va a acceder al producto y qué esperar de él.
**Beneficio comercial:** determina el modelo de ingresos completo (licencia perpetua vs. suscripción) y toda la hoja de ruta posterior.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Crítico | Muy alto | Máximo | Alta (no de construcción, de decisión con consecuencias arquitectónicas) | Alto si se decide tarde — revertir una decisión de despliegue ya construida es carísimo | Ninguna — debe resolverse antes de INT-01 y ADM-01 | 1.0 | No iniciado |

**Criterios de aceptación:** Existe una decisión documentada y comunicada de modelo de despliegue antes de iniciar cualquier desarrollo de API o multiusuario.

**Caso de uso:** *Usuarios:* dirección de producto. *Ejemplo:* se define "desktop + API opcional en la nube" como modelo, y todo el roadmap de INT y ADM se planifica en consecuencia.

---

#### COM-02 — Freemium / prueba gratuita
**Descripción:** una versión de uso gratuito con límite de tamaño de carga, como motor de adquisición de clientes.
**Problema:** sin forma de probarlo sin comprar, cada venta depende de una demo asistida.
**Beneficio usuario:** puede validar el producto con su propio caso antes de pagar.
**Beneficio comercial:** motor de adquisición escalable, no dependiente de ventas uno a uno.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Muy importante | Alto | Alto | Baja-media | Bajo | COM-01 | 1.0 | No iniciado |

**Criterios de aceptación:** Un usuario puede usar el producto sin pagar hasta un límite definido de tamaño de carga.

**Caso de uso:** *Usuarios:* prospecto evaluando el producto. *Ejemplo:* prueba con un pedido pequeño real antes de decidir comprar la versión completa.

---

#### COM-03 — Casos de estudio por vertical
**Descripción:** material de venta (casos, cifras, testimonios) específico para cada segmento objetivo: extintores, alimentos, e-commerce, etc.
**Problema:** hoy no existe material que hable el idioma de cada vertical específico.
**Beneficio usuario (del comprador):** ve su propio problema reflejado antes de hablar con ventas.
**Beneficio comercial:** contenido, no ingeniería — listo para producir de inmediato.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Muy importante | Alto | Alto | Baja | Ninguno — es trabajo de contenido | Ninguna | 1.0 | No iniciado |

**Criterios de aceptación:** Existe al menos un caso de estudio publicado por cada vertical prioritario antes del lanzamiento.

**Caso de uso:** *Usuarios:* equipo comercial y prospectos. *Ejemplo:* un distribuidor de equipos contra incendio encuentra un caso de estudio de su propio sector antes de agendar una demo.

---

#### COM-04 — White-label para revendedores
**Descripción:** permitir que un revendedor (consultora logística, fabricante de contenedores) lo ofrezca con su propia marca.
**Problema:** hoy no existe un canal de venta indirecta.
**Beneficio usuario (del revendedor):** ofrece una capacidad avanzada bajo su propia marca sin desarrollarla.
**Beneficio comercial:** canal de distribución adicional sin equipo de ventas propio adicional.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Importante | Alto | Alto | Media | Bajo-medio | COM-01 | 1.1 | No iniciado |

**Criterios de aceptación:** Un revendedor puede desplegar el producto con su propia marca e identidad visual.

**Caso de uso:** *Usuarios:* consultora logística. *Ejemplo:* ofrece el producto a sus clientes bajo su propio nombre comercial.

---

#### COM-05 — Calculadora de ahorro de flete
**Descripción:** una herramienta simple que estima cuánto ahorra un cliente en fletes al mejorar su utilización en X%.
**Problema:** el equipo comercial no tiene una forma rápida de cuantificar el valor antes de la venta.
**Beneficio usuario (del prospecto):** ve el retorno esperado en cifras propias antes de comprar.
**Beneficio comercial:** herramienta de cierre de venta barata de construir y de alto efecto.

| Prioridad | Valor usuario | Impacto comercial | Esfuerzo | Riesgo técnico | Dependencias | Versión | Estado |
|---|---|---|---|---|---|---|---|
| Importante | Alto | Medio-alto | Baja | Muy bajo | Ninguna | 1.0 | No iniciado |

**Criterios de aceptación:** El usuario puede introducir su utilización actual y ver una estimación de ahorro anual en fletes.

**Caso de uso:** *Usuarios:* equipo comercial en una reunión de venta. *Ejemplo:* calcula en vivo el ahorro estimado con los números propios del prospecto.

---

## 7. Dependencias — qué va primero, qué es paralelo

**Debe ir primero (bloquea todo lo demás si no se resuelve):**
- **COM-01** (decisión de despliegue) — bloquea INT-01, ADM-01 y por extensión buena parte de 1.1/2.0.
- **OPT-01 + OPT-02** (multi-contenedor + rendimiento) — se construyen juntos; uno sin el otro no es usable con datos reales.

**Cadenas de dependencia relevantes:**
- OPT-01 → LOG-03 (secuencia multi-parada necesita saber que hay varios destinos/espacios).
- OPT-01 → LOG-01 (empaquetado en dos niveles).
- OPT-02 → OPT-04 → OPT-05 → OPT-07 (la cadena completa de calidad de algoritmo).
- INT-01 → INT-03, INT-05, INT-07 (todo lo que "habla" con otro sistema pasa por la API primero).
- ADM-01 → ADM-02 → ADM-03 → INT-08 (todo el EPIC de colaboración depende del salto arquitectónico a nube).
- COM-01 → COM-02, COM-04, ADM-01, INT-01.

**Puede desarrollarse en paralelo, sin pisarse:**
- UX-01 a UX-08 (todo el EPIC de experiencia de usuario) es independiente del motor y puede avanzar con otro equipo en simultáneo.
- COM-02, COM-03, COM-05 (comercialización) no dependen de ingeniería nueva — pueden empezar ya, en paralelo a cualquier fase técnica.
- REP-05, REP-06, REP-07 no dependen del EPIC de motor ni de plataforma.
- OPT-09, OPT-10 (reglas de carga) son independientes del resto y de bajo riesgo — buen relleno para equipos con capacidad libre.

---

## 8. Ventajas competitivas — 10 funcionalidades que diferencian, no que igualan

Frente a EasyCargo, Cargo-Planner, Cube-IQ, TOPS Pro y equivalentes: todos resuelven bien el bin-packing de un solo contenedor. Ninguno compite fuerte en lo siguiente:

1. **LOG-04 — Reglas de negocio propias sin código.** *Por qué:* la competencia ofrece reglas fijas de fábrica. *Problema que resuelve:* cada operación logística tiene excepciones propias que hoy se gestionan "de memoria". *Por qué elegirlo:* una vez que un cliente configura sus reglas, cambiarse de proveedor significa reconfigurar todo de cero — retención altísima.

2. **INT-02 — El motor como SDK embebible.** *Por qué:* la competencia vende software terminado, no un componente. *Problema que resuelve:* fabricantes y navieras que quieren ofrecer cubicaje dentro de su propio portal, sin desarrollarlo. *Por qué elegirlo:* es la única opción que se puede integrar dentro de otro producto, no al lado de él.

3. **OPT-01 — Multi-contenedor con reglas logísticas reales (no solo bin-packing).** *Por qué:* varios competidores hacen esto de forma básica, pero sin las reglas de fragilidad/apilamiento/extintores que este motor ya tiene. *Problema que resuelve:* "cuántos necesito" respondido con reglas de negocio reales aplicadas, no solo geometría. *Por qué elegirlo:* la combinación multi-contenedor + reglas de negocio finas no existe junta en el mercado genérico.

4. **LOG-03 — Secuencia de descarga multi-parada.** *Por qué:* la mayoría de herramientas de cubicaje ignoran la ruta de reparto. *Problema que resuelve:* transporte de última milla y distribución multi-tienda, un mercado enorme y mal servido por herramientas de "un solo destino". *Por qué elegirlo:* nadie más conecta cubicaje con logística de ruta en un mismo producto.

5. **El vocabulario universal ya construido (Loading Space / Load Unit).** *Por qué:* casi toda la competencia está pensada primero para contenedores marítimos y adapta después. *Problema que resuelve:* onboarding sin fricción a cualquier vertical (camiones, vans, bodegas, racks) sin sentirse "forzado" a un molde marítimo. *Por qué elegirlo:* mensajes de venta específicos por vertical sin mentir sobre el producto.

6. **La especialización ya construida en reglas de extintores.** *Por qué:* ningún competidor genérico modela esto con este nivel de detalle. *Problema que resuelve:* el nicho completo de distribución de equipos contra incendio, hoy sin herramienta especializada. *Por qué elegirlo:* es, literalmente, el único software de cubicaje que ya entiende ese negocio sin configuración adicional.

7. **REP-02/REP-03 — Recomendaciones proactivas y explicación accionable.** *Por qué:* la mayoría de competidores muestran solo el resultado, no el razonamiento. *Problema que resuelve:* la sensación de "caja negra" que genera desconfianza en decisiones de negocio importantes. *Por qué elegirlo:* percepción real de inteligencia, no solo cálculo.

8. **OPT-03 — Peso, centro de gravedad y ejes integrado al mismo cálculo (no un módulo aparte).** *Por qué:* varias herramientas lo ofrecen como add-on separado o no lo ofrecen. *Problema que resuelve:* riesgo legal de transporte terrestre resuelto en el mismo flujo, sin pasos extra. *Por qué elegirlo:* una sola herramienta, un solo resultado, sin reconciliar dos sistemas.

9. **Informes PDF de cinco tipos distintos por audiencia (ejecutivo, técnico, operativo, interno, cliente).** *Por qué:* la mayoría de competidores exportan un único formato de reporte. *Problema que resuelve:* cada interlocutor (gerente, operario, cliente final) necesita un documento distinto del mismo resultado. *Por qué elegirlo:* un mismo cálculo sirve a toda la cadena de decisión sin reformatear nada a mano.

10. **COM-04 — White-label real, apoyado en una arquitectura ya desacoplada por capas.** *Por qué:* pocos competidores de este tamaño ofrecen reventa de marca blanca genuina. *Problema que resuelve:* consultoras y fabricantes que quieren ofrecer esto sin construir su propia marca de software. *Por qué elegirlo:* canal de distribución que la competencia directa no abre.

---

## 9. Matriz Valor / Esfuerzo

**Alto valor / Bajo esfuerzo — hacer primero, sin excusas:**
OPT-09, VIS-02, UX-03, UX-07, DAT-03, DAT-01, INT-02, COM-02, COM-03, COM-05, REP-07, REP-03 (esfuerzo medio pero valor tan alto que entra aquí).

**Alto valor / Alto esfuerzo — el corazón del roadmap, no se puede evitar:**
OPT-01, OPT-02, OPT-03, LOG-03, LOG-04, INT-01, INT-03, ADM-01, COM-01, LOG-01, OPT-05, REP-02.

**Bajo valor / Bajo esfuerzo — rellenar huecos de calendario, no priorizar:**
UX-06, VIS-03, DAT-04 (esfuerzo en realidad alto, pero valor no crítico — vigilar que no se cuele antes de tiempo).

**Bajo valor / Alto esfuerzo — evitar mientras no haya evidencia de demanda real:**
OPT-08 (formas irregulares), LOG-06 (zonas de temperatura), VIS-05 (realidad aumentada), INT-09 (exportación 3D abierta), REP-04 (aprendizaje histórico antes de tener historial suficiente).

**Regla de oro de esta matriz:** todo lo de "Alto valor / Alto esfuerzo" son los ítems críticos de la auditoría — no son opcionales, son el producto. Lo peligroso no es evitarlos, es empezar por lo fácil (cuadrante bajo-bajo) y postergarlos indefinidamente.

---

## 10. Riesgos

**Riesgos técnicos**
- OPT-02 (rendimiento) es el riesgo técnico más alto de todo el backlog: si no se resuelve bien, **degrada silenciosamente** el valor de OPT-01, LOG-01, LOG-03 y DAT-02, que dependen de poder calcular rápido a escala.
- LOG-04 (reglas sin código) arriesga el determinismo del motor si no se diseña con cuidado — una regla mal expresada por un usuario final podría producir resultados inconsistentes o contradictorios entre sí.
- ADM-01 (multiusuario en la nube) es, técnicamente, un producto nuevo dentro del producto — subestimar su esfuerzo es el riesgo de calendario más grande de todo el roadmap.

**Riesgos comerciales**
- Vender la v1.0 sin OPT-01 o sin OPT-03 invita a perder cualquier comparativa contra competidores que ya resuelven ambas.
- No resolver COM-01 (modelo de despliegue) a tiempo genera el riesgo de construir dos veces lo mismo (una arquitectura desktop y después otra en la nube).
- Depender solo de venta consultiva (sin COM-02 freemium) limita el crecimiento a la capacidad del equipo comercial, no a la calidad del producto.

**Riesgos de adopción**
- UX-01 (i18n) y UX-02 (undo/redo), si se posponen, generan una primera impresión de "prototipo" que es muy difícil de revertir en la mente de un comprador, incluso después de corregirlas.
- Un asistente de primer proyecto (UX-05) ausente puede hacer que un trial gratuito (COM-02) se abandone antes de ver el primer resultado útil — dos ítems que se refuerzan o se anulan mutuamente.

**Riesgos de mantenimiento**
- Cada conector ERP (INT-03) y cada integración de hardware (VIS-04) es una superficie de mantenimiento continuo, no un desarrollo de una sola vez — subestimar esto infla silenciosamente el costo de todas las versiones posteriores a 1.1.
- LOG-04 (reglas propias) exige soporte y documentación continuos: cuantas más reglas cree cada cliente, más difícil de depurar un caso reportado como "error" que en realidad es una regla mal configurada.

---

## 11. Cierre — recomendación del Product Owner

**Si yo fuera responsable del éxito comercial de CargoOptimizer3D, en los próximos seis meses invertiría en, por este orden:**

1. **OPT-01, OPT-02, OPT-03** — porque sin resolver "cuántos contenedores necesito", "que el cálculo no tarde minutos" y "que el plan sea legal de transportar", no hay producto que comparar con nadie. Todo lo demás es, literalmente, secundario mientras esto no exista.
2. **COM-01** — porque cada semana que pase sin esta decisión es una semana de riesgo de construir algo (una API, un backend) sobre una arquitectura que después haya que deshacer.
3. **UX-01 y UX-02** — porque son baratas comparadas con lo anterior y su ausencia cuesta ventas ya ganadas técnicamente, solo por sensación de producto inacabado.
4. **INT-02** — porque es, con diferencia, el ítem de mayor retorno por esfuerzo de todo el backlog: el activo ya existe, falta venderlo.
5. **COM-02, COM-03, COM-05** — porque no requieren ingeniería nueva y son el motor de adquisición que hace que todo lo anterior llegue a manos de un cliente real.

**En lo que NO invertiría tiempo en estos seis meses, y por qué:**

- **ADM-01 (multiusuario en la nube).** Es de altísimo valor, pero es un cambio de arquitectura completo que compite directamente por el mismo tiempo de ingeniería que OPT-01/02/03. Priorizarlo ahora significa no tener ninguno de los dos listo a tiempo. Se hace después, con clientes reales ya validando qué necesitan de colaboración — no antes.
- **LOG-06 (zonas de temperatura), OPT-08 (formas irregulares), VIS-05 (realidad aumentada).** Son diferenciadores reales, pero para nichos (frío, maquinaria, operación de bodega futurista) que hoy no tienen ni un solo cliente piloto confirmado. Construir para un mercado hipotético antes que para el mercado que ya está pidiendo multi-contenedor es la forma más común de fracasar sin darse cuenta.
- **REP-04 (aprendizaje de patrones históricos).** No hay suficiente historial real todavía para que "aprender del pasado" signifique algo — es una funcionalidad que se vuelve valiosa sola, con el tiempo, una vez que exista una base de clientes activos generando datos.
- **Cualquier conector ERP específico (INT-03) antes de tener la API pública (INT-01) construida.** Construir un conector sin la base sobre la que se apoya es trabajo que se rehace, no trabajo que se adelanta.

La razón que conecta todas estas decisiones es la misma: **el dinero de los próximos seis meses debe ir a lo que decide si el producto compite, no a lo que lo hace más completo.** Completo se puede perseguir después, con ingresos entrando. Competitivo hay que resolverlo antes de que exista el primer contrato.
