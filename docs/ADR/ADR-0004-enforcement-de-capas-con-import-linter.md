# ADR-0004: Verificación automática de la regla de dependencia con import-linter

## Estado

Aceptada — 2026-07-14

## Contexto

Las reglas de dependencia entre capas (ADR-0001, ADR-0003) son fáciles
de documentar y fáciles de violar sin querer: un import de conveniencia
en un momento de prisa (p. ej. `application` importando algo de
`infrastructure` para "ahorrar una interfaz") no falla ni en tests ni
en mypy, y puede pasar inadvertido en revisión de código durante años,
hasta que separar las capas se vuelve prácticamente imposible.

## Decisión

Se añade `import-linter` como dependencia de desarrollo, con un
contrato de tipo `layers` en `pyproject.toml` que declara el orden:

```
presentation → infrastructure → application → domain
```

Una capa únicamente puede importar capas por debajo de ella en esa
lista. Cualquier import que viole el orden hace fallar
`lint-imports` con un error explícito señalando el ciclo o la
violación. Se ejecuta junto con ruff, black, mypy y pytest como parte
de la verificación estándar del proyecto (ver `README.md`).

Como hoy `application` e `infrastructure` están vacíos, el contrato
pasa trivialmente; su valor es preventivo, para las fases 2 en
adelante.

## Consecuencias

**Beneficios:**
- Las dependencias circulares o las violaciones de capas se detectan
  en el momento de escribir el código (o en CI), no años después.
- El coste de añadir la herramienta ahora es prácticamente nulo (no
  hay código real que pueda violar el contrato todavía).

**Costes / riesgos aceptados:**
- Una dependencia de desarrollo más que mantener actualizada.
- Si en el futuro se decide que `presentation` no debe poder importar
  `infrastructure` directamente (arquitectura hexagonal estricta con
  composition root separado), este contrato tendrá que revisarse.
