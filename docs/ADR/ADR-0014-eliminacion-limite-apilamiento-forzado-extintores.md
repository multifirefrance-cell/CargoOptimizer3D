# ADR-0014: Eliminación de la excepción automática que forzaba `max_stack_count=1` en extintores individuales >= 3 kg

## Estado

Aceptada — 2026-07-18. Reemplaza parcialmente la parte de apilamiento
de la Decisión 2 de [ADR-0007](ADR-0007-motor-de-reglas.md); la parte
de orientación (horizontalidad) de esa misma decisión sigue vigente,
sin cambios.

## Contexto

ADR-0007 (fase 3) estableció que un extintor individual de 3 kg
nominales o más se trataba siempre como "no apilable"
(`effective_max_stack_count` forzado a `1`), sin importar el
`max_stack_count` que el usuario configurase en el SKU. Era una regla
de negocio automática basada en: ser extintor, agente PQS/CO₂, peso
nominal >= 3 kg y `package_type=INDIVIDUAL`.

Tras la fase OPT-14 (cambio del valor por defecto de `max_stack_count`
de `1` a `30` para productos nuevos, ver `docs/OptimizerPerformance.md`),
el arquitecto del proyecto revisó el catálogo de reglas de extintores y
decidió que esta excepción automática ya no debe existir: el límite de
apilamiento de un extintor, igual que el de cualquier otro `LoadUnit`,
debe ser exclusivamente el que el usuario configure en su SKU — sin
ninguna regla oculta que lo sobrescriba por el mero hecho de ser
extintor.

## Decisión

Se elimina por completo (no se desactiva) la excepción automática de
apilamiento para extintores:

- `rules/extinguisher_rules.py::effective_max_stack_count` — eliminada.
- Su uso en `rules/stacking_rules.py::evaluate_stack_count` — sustituido
  por acceso directo a `context.load_unit.max_stack_count`.
- `RulesEngine.effective_max_stack_count` (método facade) — eliminado.
- Reexportación de `effective_max_stack_count` desde
  `rules/stacking_rules.__all__` y `rules/__init__.__all__` — eliminada.

A partir de esta fase, `evaluate_stack_count` no distingue tipo de
producto: `1` = no apilable, `N` = máximo N niveles, para cualquier
`LoadUnit`, incluidos los extintores individuales >= 3 kg.

**No se toca la regla de horizontalidad** (Decisión 2 de ADR-0007,
mitad de orientación): un extintor individual >= 3 kg sigue sin poder
colocarse en vertical
(`is_individual_large_extinguisher`/`evaluate_extinguisher_orientation`,
sin cambios). Tampoco se toca la regla de cajas grupales de 1/2/3 kg
(orientación libre, `max_stack_count` siempre respetado tal cual, sin
cambios desde antes de esta fase).

## Consecuencias

- Un extintor individual >= 3 kg con `max_stack_count=1` (explícito o
  heredado de un proyecto/catálogo anterior a OPT-14) se sigue
  comportando exactamente igual que antes: no apilable.
- Un extintor individual >= 3 kg con `max_stack_count` > 1 (incluido el
  nuevo valor por defecto, 30) ahora sí puede apilarse hasta ese
  límite, limitado naturalmente por la altura disponible y el resto de
  reglas del motor (soporte, colisión, peso del espacio).
- El orden de empaquetado (`optimization/ordering.py`) sigue colocando
  los extintores individuales grandes primero como heurística de
  cubicaje (mientras el espacio bajo está libre), con independencia de
  su `max_stack_count` — esto no es una restricción de negocio, es
  únicamente un criterio de orden, y se conserva sin cambios.
- No hay ningún ADR ni regla de negocio pendiente que reintroduzca esta
  excepción; si en el futuro se necesitara un límite de apilamiento
  distinto por tipo de producto, requeriría una decisión y un ADR
  nuevos, explícitos.
