# ADR-0002: Vocabulario de dominio — Loading Space y Load Unit

## Estado

Aceptada — 2026-07-14 (formaliza una decisión de producto ya vigente
desde la fase 0/1, documentada en `CLAUDE.md`)

## Contexto

CargoOptimizer3D no es un optimizador de contenedores marítimos: es un
sistema universal de optimización de carga 3D. Usar terminología
específica de un caso de uso (p. ej. "contenedor", "producto") en el
código, la API o el dominio limitaría conceptualmente el sistema y
obligaría a un renombrado masivo el día que se soporte un caso de uso
distinto (camión, bodega, avión, rack).

## Decisión

Todo el sistema gira en torno a dos conceptos universales:

- **Loading Space**: cualquier espacio de carga — contenedor marítimo,
  camión, furgón, van, semirremolque, bodega, plataforma, vagón, avión
  o espacio definido por el usuario.
- **Load Unit**: cualquier unidad a cargar — caja, pallet, cilindro,
  tambor, bobina, tubo, maquinaria, carga irregular o grupo de cajas.

Prohibido usar "Container" o "Product" como concepto genérico en
nombres de clases, módulos, tablas de base de datos, endpoints de API
o textos de interfaz, en cualquier capa del sistema.

## Consecuencias

**Beneficios:**
- El dominio (`cargo_optimizer.domain`) puede modelar cualquier
  combinación de espacio/unidad sin refactorización conceptual futura.
- La terminología es consistente entre código, API y UI, reduciendo
  ambigüedad para futuros desarrolladores e integradores de ERP.

**Costes / riesgos aceptados:**
- Requiere vigilancia activa en revisión de código: es fácil que un
  desarrollador nuevo escriba "container" por costumbre del dominio
  marítimo. Se mantiene como regla explícita en `CLAUDE.md`.
