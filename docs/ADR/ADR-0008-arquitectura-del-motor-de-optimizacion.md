# ADR-0008: Arquitectura del motor de optimización

## Estado

Aceptada — 2026-07-14

## Contexto

La fase 4 introduce el componente que decide **dónde** colocar cada
unidad, a diferencia de `domain` (qué son las cosas), `geometry`
(cálculo espacial puro) y `rules` (si una colocación es válida). Esta
sesión (4.0) es de diseño puro; el paquete `optimization` no se crea
todavía (ver `docs/Roadmap.md`). Tres decisiones estructurales quedan
registradas aquí.

## Decisión 1: `optimization` es un paquete propio, hermano de `domain`/`geometry`/`rules`

No se implementa dentro de `rules` (que responde "¿es válido?", no
"¿dónde debería ir?") ni dentro de `application` (que orquesta casos de
uso completos, no algoritmos de búsqueda). Dependencias permitidas:
`optimization → domain`, `optimization → geometry`, `optimization →
rules`. Prohibidas: `application`, `infrastructure`, `presentation`, y
cualquier biblioteca externa. Cuando el paquete se cree (fase 4.1), el
contrato de `import-linter` pasará a:

```
presentation → infrastructure → application → optimization → rules → geometry → domain
```

## Decisión 2: `PackingStrategy` es un `Protocol`, no una `ABC`

No existe todavía comportamiento compartido real entre estrategias que
justifique una jerarquía de clases con métodos concretos heredados. Un
`Protocol` (PEP 544) permite tipar estructuralmente el contrato
(`name`, `capabilities()`, `pack(...)`) sin forzar herencia, dejando a
cada estrategia futura implementarlo como una clase simple, sin
acoplarse a una superclase que, con una sola implementación real hoy,
no tiene forma de demostrar qué comportamiento es genuinamente
compartido. Si eso cambia (dos o más estrategias con lógica interna
idéntica de verdad), esa lógica se extraerá a funciones libres
reutilizables por composición, no a una superclase.

## Decisión 3: determinismo como requisito de diseño, no como optimización posterior

El motor debe producir el mismo `PackingResult` ante la misma entrada,
siempre. Esto se logra fijando el orden en cada etapa (orden de
`LoadUnit` de entrada, orden de expansión, orden de instancias, orden
de orientaciones, orden de posiciones candidatas, criterio de
desempate final) y prohibiendo explícitamente cualquier dependencia de
estructuras cuyo orden de iteración no esté garantizado (p. ej. un
`set` de cadenas, sensible a la aleatorización de hash de Python). Ver
`docs/OptimizationEngineDesign.md`, sección "Determinismo", para la
lista completa de reglas y cómo se prueban.

## Consecuencias

**Beneficios:**
- El motor de negocio (`domain`+`geometry`+`rules`) sigue siendo
  reutilizable sin arrastrar ningún algoritmo de búsqueda concreto.
- Añadir una segunda estrategia (`BestFitStrategy`, `SkylineStrategy`,
  ...) no requiere tocar `PackingEngine`, `PackingRequest` ni
  `PackingResult`: solo implementar el `Protocol`.
- Dos ejecuciones idénticas son comparables byte a byte, lo cual es
  imprescindible para probar el motor y para comparar algoritmos entre
  sí de forma justa.

**Costes / riesgos aceptados:**
- Un `Protocol` no impone en tiempo de definición que una clase lo
  implemente (a diferencia de una `ABC`, que falla al instanciar si
  falta un método); el coste se acepta porque `mypy --strict` sí
  verifica la conformidad estructural en tiempo de tipado, y las
  pruebas de integración detectarían cualquier implementación
  incompleta en tiempo de ejecución.
- Exigir determinismo estricto descarta, para v1, cualquier
  aleatoriedad incluso beneficiosa (p. ej. reinicios aleatorios para
  escapar de mínimos locales); se acepta porque la primera prioridad
  es corrección verificable, no calidad de solución.
