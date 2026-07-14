# ADR-0005: Dataclasses inmutables y enums con valores string estables en el dominio

## Estado

Aceptada — 2026-07-14

## Contexto

El modelo de dominio (fase 2 del roadmap) introduce las primeras
entidades y value objects reales del sistema: `Dimensions3D`,
`Orientation`, `Position3D`, `LoadingSpace`, `LoadUnit`, `Placement`,
`UnpackedUnit`, `PackingResult` y `CargoProject`. Al ser el modelo
sobre el que se apoyarán el motor geométrico, el de restricciones, el
de optimización, la persistencia (fase 7) y la futura API/ERP (fase
9), su forma de representar datos debe ser predecible y estable desde
el principio: cambiarla después de que existan datos persistidos o un
contrato de API público sería costoso.

## Decisión

1. **Todas las entidades y value objects del dominio son
   `@dataclass(frozen=True, slots=True)`.** Inmutables: cualquier
   "modificación" produce un nuevo objeto (p. ej. no hay setters). Esto
   elimina una clase entera de bugs (mutación compartida entre un
   `Placement` ya calculado y el estado en memoria del optimizador) y
   hace que los objetos de dominio sean seguros de compartir entre
   hilos o de cachear. `slots=True` evita la creación accidental de
   atributos no declarados y reduce el uso de memoria, relevante
   porque un `PackingResult` puede contener miles de `Placement`.

2. **Los enums de dominio (`enums.py`) heredan de `enum.StrEnum`**, no
   de `Enum` simple ni de `int, Enum`. Sus valores string (`"container"`,
   `"pallet"`, `"lwh_xyz"`, etc.) se consideran parte del contrato
   estable de persistencia y de API: no se renombran sin una migración
   explícita documentada en un ADR posterior. `StrEnum` (frente a
   `class X(str, Enum)`) da una conversión a string directa y
   predecible (`str(member) == member.value`), lo cual importa para
   serialización JSON futura (fase 7 y fase 9).

## Consecuencias

**Beneficios:**
- Los objetos de dominio pueden pasar de una capa a otra (p. ej. de
  `application` a `presentation`) sin riesgo de que una capa modifique
  silenciosamente el estado que otra capa cree tener.
- El futuro esquema de persistencia (fase 7) puede mapear
  `LoadUnit`/`LoadingSpace` a filas de base de datos sabiendo que la
  representación en memoria no cambia entre lecturas.
- Los valores de los enums pueden usarse directamente como valores de
  columna o claves JSON sin una capa de traducción adicional.

**Costes / riesgos aceptados:**
- Frozen + slots impide añadir atributos dinámicamente; cualquier
  cambio de estado de una entidad requiere construir una instancia
  nueva (aceptable: el dominio no modela procesos con estado mutable
  de larga vida, modela datos).
- Cambiar el valor string de un enum ya usado en datos persistidos
  requerirá una migración explícita en el futuro; se acepta el coste
  porque la alternativa (valores inestables) es peor a largo plazo.
