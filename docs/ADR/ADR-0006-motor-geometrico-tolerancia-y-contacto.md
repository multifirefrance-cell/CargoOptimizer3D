# ADR-0006: Motor geométrico separado del dominio, tolerancia y semántica de contacto

## Estado

Aceptada — 2026-07-14

## Contexto

La fase 2.2 introduce el primer motor real del sistema:
`cargo_optimizer.geometry`. Tres decisiones de esta fase son
suficientemente significativas y difíciles de revertir después como
para merecer un ADR conjunto: dónde vive la geometría, qué tolerancia
numérica usa, y qué significa exactamente que dos cajas "colisionen".

## Decisión 1: `geometry` es un paquete hermano de `domain`, no un subpaquete

`domain` describe objetos y estados (`LoadingSpace`, `LoadUnit`,
`Placement`...) y sus invariantes; no realiza cálculos espaciales.
`geometry` calcula sobre esos objetos: cajas ortoédricas, colisiones,
soporte, límites. Mezclar ambos en un solo paquete habría hecho
`domain` depender de decisiones algorítmicas (p. ej. cómo se calcula
una unión de rectángulos) que nada tienen que ver con qué es un
`LoadUnit`. Separarlos, con `geometry → domain` como única dependencia
permitida (verificado por `import-linter`, ver Decisión 3 de
ADR-0001), permite que `domain` siga siendo la capa más estable del
sistema mientras `geometry` evoluciona con el algoritmo de colisiones
o se sustituye por una implementación más eficiente sin tocar el
modelo de dominio.

## Decisión 2: tolerancia geométrica única y centralizada

Todas las comparaciones de punto flotante del motor geométrico usan
`GEOMETRY_EPSILON_CM = 1e-9` (definida una sola vez en
`geometry/constants.py`). La alternativa — comparar floats
directamente o dispersar tolerancias ad-hoc por archivo — produce
bugs sutiles y no reproducibles (dos cajas que deberían tocarse
exactamente no lo hacen por un error de redondeo de la
16ª cifra decimal). El valor elegido (1e-9 cm) es muchísimo menor que
cualquier tolerancia de fabricación real, por lo que no introduce
imprecisión perceptible.

## Decisión 3: `intersects` / `overlaps` / `touches` son conceptos distintos

Se definen tres relaciones entre cajas, no una:

- **`overlaps`**: intersección con volumen estrictamente positivo en
  los tres ejes. Es la definición de "colisión" que usa
  `boxes_overlap`.
- **`touches`**: contacto (cara, arista o vértice compartidos) sin
  volumen de intersección. No es una colisión.
- **`intersects`**: verdadero en cualquiera de los dos casos
  anteriores (test AABB estándar sobre regiones cerradas). Se expone
  porque a veces solo importa saber si dos regiones cerradas se tocan
  de cualquier forma, sin distinguir el caso.

Sin esta distinción explícita, dos cajas perfectamente apiladas (cara
superior de una tocando la base de otra) se habrían reportado como
"colisión", lo cual haría inviable cualquier apilamiento en el futuro
motor de optimización.

## Consecuencias

**Beneficios:**
- El modelo de dominio permanece intacto y estable mientras el motor
  geométrico se desarrolla y, eventualmente, se optimiza.
- Un único punto de verdad para la tolerancia elimina una clase de
  bugs de redondeo.
- El apilamiento de cajas (caso normal en carga de mercancía) no se
  confunde con una colisión real.

**Costes / riesgos aceptados:**
- Quien use `AxisAlignedBox` debe entender la diferencia entre las
  tres relaciones; se documenta explícitamente en cada método y en
  `docs/GeometryEngine.md`.
- Si en el futuro se detecta que 1e-9 cm es insuficiente o excesivo
  para algún caso real (p. ej. maquinaria industrial con tolerancias
  de fabricación mayores), cambiar la constante es un cambio de una
  sola línea, pero afecta a todo el motor geométrico simultáneamente.
