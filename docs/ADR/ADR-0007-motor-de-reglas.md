# ADR-0007: Motor de reglas separado del dominio y del optimizador, reglas de extintores, política de acumulación de violaciones

## Estado

Aceptada — 2026-07-14

## Contexto

La fase 3 introduce `cargo_optimizer.rules`: el primer módulo que
responde preguntas de negocio ("¿puede colocarse esta unidad aquí?",
"¿qué orientaciones están permitidas?") en lugar de solo describir
datos (`domain`) o calcular geometría pura (`geometry`). Tres
decisiones de esta fase merecen quedar registradas.

## Decisión 1: `rules` es un paquete propio, ni parte de `domain` ni del futuro optimizador

`domain` describe objetos y estados; `geometry` calcula sobre ellos sin
saber nada de negocio (no sabe qué es un extintor). `rules` sí conoce
reglas de negocio (extintores, apilamiento, fragilidad, peso) pero
**no decide dónde colocar nada** — eso es responsabilidad exclusiva del
futuro motor de optimización (fase 4), que consumirá `rules` para
saber si una posición que él mismo propone es válida. Mezclar reglas
con el optimizador habría acoplado "qué es válido" con "cómo buscar una
solución", impidiendo reutilizar las reglas desde una futura API o
desde una herramienta de validación manual sin arrastrar ningún
algoritmo de búsqueda.

Dependencia: `rules → domain` siempre; `rules → geometry` únicamente
donde una regla necesita información espacial (límites, colisión,
soporte). Nunca al revés, ni hacia `application`/`infrastructure`/
`presentation`. Verificado por `import-linter`
(`presentation → infrastructure → application → rules → geometry → domain`).

## Decisión 2: reglas de extintores basadas en el peso nominal, no en el peso bruto

> **Nota (2026-07-18): la mitad de apilamiento de esta decisión fue
> reemplazada por [ADR-0014](ADR-0014-eliminacion-limite-apilamiento-forzado-extintores.md).**
> Un extintor individual >= 3 kg nominales **ya no** se trata como no
> apilable de forma automática — respeta el `max_stack_count` de su
> propio SKU, igual que cualquier otro `LoadUnit`. La mitad de
> horizontalidad (descrita a continuación) sigue vigente sin cambios.
> El texto original de esta decisión se conserva tal cual para
> mantener el historial de por qué se tomó en su momento.

Dos reglas obligatorias, ambas dependientes exclusivamente de
`extinguisher_nominal_kg` (nunca de `weight_kg`, el peso bruto del
empaque):

- **Extintor individual >= 3 kg nominales**: debe ir horizontal, con
  la dimensión original `length_cm` paralela al eje X, y se trataba
  como no apilable (máximo efectivo de apilamiento = 1) — ver la nota
  de reemplazo arriba. Se verifica el mapeo real de `Orientation` (qué
  dimensión original queda en qué eje), no una heurística de "más largo
  que alto".
- **Caja grupal de extintores de 1, 2 o 3 kg nominales**: puede ir en
  cualquier orientación declarada y apilarse hasta `max_stack_count`;
  las capacidades recomendadas (10/8/6 unidades por caja) son
  advertencias, nunca rechazos, si el usuario configura otra cosa.

Se centraliza una tolerancia (`NOMINAL_WEIGHT_TOLERANCE_KG = 0.05`) para
comparar pesos nominales, documentada en `extinguisher_rules.py`.

## Decisión 3: política de acumulación de violaciones

`evaluate_candidate_placement` no se detiene en la primera violación:
ejecuta las 9 evaluaciones parciales y combina sus violaciones
(`RuleEvaluation.combine`), preservando el orden de entrada
(determinista). La única excepción: si hay colisión, se omiten
soporte, apilamiento, fragilidad y peso soportado — las cuatro
dependen de "qué soporta físicamente a la candidata", una pregunta sin
respuesta consistente cuando la candidata ocupa un volumen ya en
disputa con otra caja. Límites, orientación, configuración de
extintor y peso máximo del espacio se evalúan siempre, porque son
independientes de si el volumen está disputado.

## Consecuencias

**Beneficios:**
- El optimizador (fase 4) podrá pedir "todas las razones por las que
  esta posición no sirve" en una sola llamada, en vez de iterar
  corrigiendo un error a la vez.
- Las reglas de extintores son correctas por construcción: no es
  posible confundir peso bruto con nominal porque cada función recibe
  explícitamente el campo que necesita.
- La política de no-cascada evita reportar decenas de advertencias de
  soporte irrelevantes cuando el problema real es una colisión.

**Costes / riesgos aceptados:**
- La política de no-cascada es una decisión de producto (qué mostrar
  al usuario), no una ley física; si en el futuro se necesita ver
  *todas* las violaciones incluso con colisión, será un cambio
  explícito y documentado en un ADR posterior, no una corrección
  silenciosa.
- `evaluate_supported_weight` recorre transitivamente toda la cadena de
  soporte (no solo el soporte directo) para no pasar por alto que una
  caja muy por debajo del candidato reciba más peso del que declara
  soportar; esto es correcto pero más costoso que solo mirar el nivel
  inmediato, aceptable para los volúmenes de datos de esta fase.
